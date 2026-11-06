"""Bloom API.

.venv/bin/uvicorn backend.api.app:app --reload
"""

from __future__ import annotations

import secrets
import urllib.error
import uuid
from collections.abc import Iterator
from datetime import date, datetime, timedelta
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from backend.api import claude, oura_oauth
from backend.api.db import (
    Database,
    HabitCheckRow,
    HabitRow,
    OAuthStateRow,
    OuraTokenRow,
    PeriodRow,
    SelfReportRow,
    UserRow,
)
from backend.api.schemas import (
    CycleView,
    DoctorRecord,
    HabitCheck,
    HabitCheckCreate,
    HabitConsistency,
    HabitSuggestions,
    OuraConnected,
    PeriodCreate,
    SyncResult,
    TodayPlan,
    User,
    UserCreate,
    VoiceLogRequest,
    VoiceLogResult,
)
from backend.api.services import (
    WearableKind,
    build_plan,
    build_record,
    habit_consistency,
    last_observed_day,
    latest,
    lifestyle_averages,
    load_dataset,
    replace_wearable_days,
    to_habit,
    to_log_entry,
    to_user,
)
from backend.canonical.models import PeriodLog, Source
from backend.canonical.oura_adapter import (
    adapt_activity,
    adapt_readiness,
    adapt_sleep,
    adapt_stress,
)
from backend.connectors.oura import OuraConnector

SYNC_WINDOW = timedelta(days=90)
OAUTH_STATE_TTL = timedelta(minutes=15)


def get_session(request: Request) -> Iterator[Session]:
    database: Database = request.app.state.database
    yield from database.session()


SessionDep = Annotated[Session, Depends(get_session)]


def require_user(session: Session, user_id: uuid.UUID) -> UserRow:
    row = session.get(UserRow, user_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found.")
    return row


def oura_access_token(session: Session, user_id: uuid.UUID) -> str | None:
    stored = session.get(OuraTokenRow, user_id)
    if stored is None:
        return None
    now = datetime.now()
    if stored.refresh_token and oura_oauth.needs_refresh(stored.expires_at, now):
        try:
            token = oura_oauth.refresh(oura_oauth.OuraClientConfig.from_env(), stored.refresh_token)
        except (oura_oauth.OuraNotConfigured, httpx.HTTPError) as error:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Could not refresh the Oura connection.") from error
        stored.access_token = token.access_token
        stored.refresh_token = token.refresh_token or stored.refresh_token
        stored.expires_at = token.expires_at(now)
        session.commit()
    return stored.access_token


def create_app(database: Database | None = None) -> FastAPI:
    app = FastAPI(title="Bloom API", description="Lifestyle record for women. Not a medical device.")
    app.state.database = database or Database()

    @app.post("/users", status_code=status.HTTP_201_CREATED)
    def create_user(profile: UserCreate, session: SessionDep) -> User:
        row = UserRow(**profile.model_dump(mode="json"))
        session.add(row)
        session.commit()
        return to_user(row)

    @app.get("/oura/authorize")
    def oura_authorize(user_id: Annotated[uuid.UUID, Query()], session: SessionDep) -> RedirectResponse:
        require_user(session, user_id)
        try:
            config = oura_oauth.OuraClientConfig.from_env()
        except oura_oauth.OuraNotConfigured as error:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error)) from error
        state = secrets.token_urlsafe(32)
        session.add(OAuthStateRow(state=state, user_id=user_id))
        session.commit()
        return RedirectResponse(oura_oauth.authorize_url(config, state))

    @app.get("/oura/callback")
    def oura_callback(
        session: SessionDep,
        state: Annotated[str, Query()],
        code: Annotated[str | None, Query()] = None,
        error: Annotated[str | None, Query()] = None,
    ) -> OuraConnected:
        pending = session.get(OAuthStateRow, state)
        if pending is None or datetime.now() - pending.created_at > OAUTH_STATE_TTL:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "This Oura sign-in link has expired. Please try again.")
        user_id = pending.user_id
        session.delete(pending)
        session.commit()
        if error or not code:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Oura access was not granted.")
        try:
            token = oura_oauth.exchange_code(oura_oauth.OuraClientConfig.from_env(), code)
        except oura_oauth.OuraNotConfigured as config_error:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(config_error)) from config_error
        except httpx.HTTPError as exchange_error:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Oura did not accept the sign-in.") from exchange_error
        session.merge(
            OuraTokenRow(
                user_id=user_id,
                access_token=token.access_token,
                refresh_token=token.refresh_token,
                expires_at=token.expires_at(datetime.now()),
            )
        )
        session.commit()
        return OuraConnected(user_id=user_id, connected=True)

    @app.post("/users/{user_id}/sync")
    def sync(user_id: uuid.UUID, session: SessionDep) -> SyncResult:
        require_user(session, user_id)
        # An empty string, not None: None would make the connector fall back to the
        # process-wide OURA_TOKEN and sync one personal ring into every user's record.
        connector = OuraConnector(token=oura_access_token(session, user_id) or "")
        end = date.today()
        start = end - SYNC_WINDOW + timedelta(days=1)
        try:
            raw = connector.fetch_all(start, end)
        except urllib.error.URLError as error:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Could not reach Oura.") from error
        counts = {
            kind: replace_wearable_days(session, user_id, kind, records, Source.OURA)
            for kind, records in (
                (WearableKind.SLEEP, adapt_sleep(raw["daily_sleep"], raw["sleep"])),
                (WearableKind.READINESS, adapt_readiness(raw["daily_readiness"])),
                (WearableKind.ACTIVITY, adapt_activity(raw["daily_activity"])),
                (WearableKind.STRESS, adapt_stress(raw["daily_stress"])),
            )
        }
        session.commit()
        return SyncResult(
            user_id=user_id,
            live=connector.is_live,
            start=start,
            end=end,
            sleep=counts[WearableKind.SLEEP],
            readiness=counts[WearableKind.READINESS],
            activity=counts[WearableKind.ACTIVITY],
            stress=counts[WearableKind.STRESS],
        )

    @app.post("/users/{user_id}/periods", status_code=status.HTTP_201_CREATED)
    def log_period(user_id: uuid.UUID, period: PeriodCreate, session: SessionDep) -> PeriodLog:
        require_user(session, user_id)
        if period.end_day is not None and period.end_day < period.start_day:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "end_day must be on or after start_day.")
        log = PeriodLog(start_day=period.start_day, end_day=period.end_day, flow=period.flow)
        session.merge(
            PeriodRow(user_id=user_id, start_day=log.start_day, source=log.source, end_day=log.end_day, flow=log.flow)
        )
        session.commit()
        return log

    @app.get("/users/{user_id}/cycle")
    def cycle(user_id: uuid.UUID, session: SessionDep) -> CycleView:
        require_user(session, user_id)
        dataset = load_dataset(session, user_id)
        return CycleView(periods=dataset.periods, today=latest(dataset.cycle, date.today()), days=dataset.cycle)

    @app.post("/users/{user_id}/logs/voice", status_code=status.HTTP_201_CREATED)
    def voice_log(user_id: uuid.UUID, body: VoiceLogRequest, session: SessionDep) -> VoiceLogResult:
        require_user(session, user_id)
        answer = claude.sort_voice_log(body.text)
        rows = [
            SelfReportRow(
                user_id=user_id,
                day=date.today(),
                category=entry.category,
                text=entry.text,
                detail=entry.detail,
                source=Source.SELF_REPORT,
            )
            for entry in answer.value.entries
        ]
        session.add_all(rows)
        session.commit()
        return VoiceLogResult(used_ai=answer.used_ai, entries=[to_log_entry(row) for row in rows])

    @app.post("/users/{user_id}/habits/suggest", status_code=status.HTTP_201_CREATED)
    def suggest_habits(user_id: uuid.UUID, session: SessionDep) -> HabitSuggestions:
        user = to_user(require_user(session, user_id))
        dataset = load_dataset(session, user_id)
        answer = claude.suggest_habits(user, lifestyle_averages(dataset, last_observed_day(dataset)))
        rows = [
            HabitRow(user_id=user_id, title=idea.title, why=idea.why, goal=idea.goal, created_on=date.today())
            for idea in answer.value.habits
        ]
        session.add_all(rows)
        session.commit()
        return HabitSuggestions(used_ai=answer.used_ai, habits=[to_habit(row) for row in rows])

    @app.post("/users/{user_id}/habits/{habit_id}/checks", status_code=status.HTTP_201_CREATED)
    def check_habit(user_id: uuid.UUID, habit_id: uuid.UUID, body: HabitCheckCreate, session: SessionDep) -> HabitCheck:
        habit = session.get(HabitRow, habit_id)
        if habit is None or habit.user_id != user_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Habit not found.")
        day = body.day or date.today()
        if day < habit.created_on or day > date.today():
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, "Check-ins must fall between the habit's start and today."
            )
        session.merge(HabitCheckRow(habit_id=habit_id, day=day))
        session.commit()
        return HabitCheck(habit_id=habit_id, day=day)

    @app.get("/users/{user_id}/habits/consistency")
    def consistency(user_id: uuid.UUID, session: SessionDep) -> list[HabitConsistency]:
        require_user(session, user_id)
        return habit_consistency(session, user_id, date.today())

    @app.get("/users/{user_id}/plan/today")
    def plan_today(user_id: uuid.UUID, session: SessionDep) -> TodayPlan:
        user = to_user(require_user(session, user_id))
        return build_plan(user, load_dataset(session, user_id), date.today())

    @app.get("/users/{user_id}/record")
    def record(user_id: uuid.UUID, session: SessionDep) -> DoctorRecord:
        user = to_user(require_user(session, user_id))
        return build_record(session, user, date.today())

    return app


app = create_app()
