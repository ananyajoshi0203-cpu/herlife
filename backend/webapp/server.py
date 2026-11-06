"""HerLife as a real web app: serves the UI and the backend that replaces claude.ai's runtime.

The page talks to `window.claude.use(...)`. On claude.ai the platform answers; here
static/bloom-platform.js answers the same calls with this server, so one UI ships to both.

    ANTHROPIC_API_KEY=... OURA_CLIENT_ID=... OURA_CLIENT_SECRET=... \\
      .venv/bin/uvicorn backend.webapp.server:app --port 8080
"""

from __future__ import annotations

import json
import os
import re
import secrets
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Literal

import anthropic
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.api import oura_oauth
from backend.canonical.daily_rows import DayRow, merge_days
from backend.canonical.oura_adapter import adapt_activity, adapt_readiness, adapt_sleep, adapt_stress
from backend.connectors.oura import OuraConnector
from backend.webapp import google_calendar as gcal
from backend.webapp import store

ROOT = Path(__file__).resolve().parents[2]


def load_dotenv(path: Path) -> None:
    """Read KEY=value lines from a local .env (git-ignored). Real environment variables win."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and key and not key.startswith("#"):
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_dotenv(ROOT / ".env")
PAGE = ROOT / "web" / "index.html"
STATIC = Path(__file__).resolve().parent / "static"
PERSON_COOKIE = "bloom_person"
OAUTH_STATE_COOKIE = "bloom_oura_state"
GOOGLE_STATE_COOKIE = "bloom_google_state"
# Single-person local development only: lets you see your own ring before registering an
# Oura OAuth app. Never set it on a shared deployment, or every visitor reads your ring.
DEV_OURA_TOKEN = os.environ.get("BLOOM_DEV_OURA_TOKEN") or os.environ.get("DEV_OURA_TOKEN")
SECURE_COOKIES = os.environ.get("BLOOM_SECURE_COOKIES", "0") == "1"
MODELS: dict[str, str] = {"quick": "claude-haiku-5-5", "default": "claude-sonnet-5-5", "complex": "claude-opus-5-5"}
# The models think before answering; 1,500 tokens could be spent entirely on thinking, leaving no text.
MAX_OUTPUT_TOKENS = 4000
MAX_PROMPT_CHARS = 12_000
MAX_STATE_BYTES = 512_000
OURA_DAYS_MAX = 120
JSON_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)

app = FastAPI(title="HerLife web")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


def person_id(request: Request) -> str:
    """Anonymous per-browser identity. Accounts come later; the record is already per person."""
    return request.state.person_id


@app.middleware("http")
async def assign_person(request: Request, call_next):  # type: ignore[no-untyped-def]
    existing = request.cookies.get(PERSON_COOKIE)
    request.state.person_id = existing or uuid.uuid4().hex
    response: Response = await call_next(request)
    if not existing:
        response.set_cookie(PERSON_COOKIE, request.state.person_id, max_age=60 * 60 * 24 * 365,
                            httponly=True, samesite="lax", secure=SECURE_COOKIES)
    return response


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    page = PAGE.read_text()
    # The artifact publisher wraps the page in a document skeleton; here we add it ourselves,
    # plus the platform shim, which must load before the app script reads window.claude.
    page = page.replace('<script>\n"use strict";', '<script src="/static/bloom-platform.js"></script>\n<script>\n"use strict";', 1)
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '<meta name="theme-color" content="#7655C2">'
        "<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}"
        "body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>"
        f"</head><body>{page}</body></html>"
    )


@app.get("/api/me")
def me(request: Request) -> dict[str, str]:
    return {"id": person_id(request)}


class AiRequest(BaseModel):
    prompt: str = Field(max_length=MAX_PROMPT_CHARS)
    tier: Literal["quick", "default", "complex"] = "quick"


@app.post("/api/ai/json")
def ai_json(body: AiRequest) -> object:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise HTTPException(503, detail={"code": "not_configured"})
    client = anthropic.Anthropic()
    try:
        message = client.messages.create(
            model=MODELS[body.tier],
            max_tokens=MAX_OUTPUT_TOKENS,
            system="You are HerLife's assistant for a women's lifestyle app. Reply with JSON only, no prose, no code fences.",
            messages=[{"role": "user", "content": body.prompt}],
        )
    except anthropic.APIError as error:
        raise HTTPException(502, detail={"code": "upstream_error", "message": str(error)}) from error
    text = "".join(block.text for block in message.content if block.type == "text")
    try:
        return json.loads(JSON_FENCE.sub("", text.strip()))
    except json.JSONDecodeError as error:
        raise HTTPException(502, detail={"code": "invalid_json"}) from error


class StateBody(BaseModel):
    json_: str = Field(alias="json", max_length=MAX_STATE_BYTES)
    updatedAt: int


@app.get("/api/state")
def get_state(request: Request) -> dict[str, object]:
    row = store.load_state(person_id(request))
    return {"exists": row is not None, "json": row.state_json if row else None, "updatedAt": row.updated_at if row else 0}


@app.put("/api/state", status_code=204)
def put_state(request: Request, body: StateBody) -> None:
    store.save_state(person_id(request), body.json_, body.updatedAt)


@app.delete("/api/state", status_code=204)
def delete_state(request: Request) -> None:
    store.delete_person(person_id(request))


@app.get("/api/oura/connect")
def oura_connect() -> RedirectResponse:
    try:
        config = oura_oauth.OuraClientConfig.from_env()
    except oura_oauth.OuraNotConfigured:
        return RedirectResponse("/?oura=not_configured")
    state = secrets.token_urlsafe(24)
    response = RedirectResponse(oura_oauth.authorize_url(config, state))
    response.set_cookie(OAUTH_STATE_COOKIE, state, max_age=600, httponly=True, samesite="lax", secure=SECURE_COOKIES)
    return response


@app.get("/oura/callback")
def oura_callback(request: Request, code: str = "", state: str = "") -> RedirectResponse:
    if not code or not secrets.compare_digest(state, request.cookies.get(OAUTH_STATE_COOKIE, "")):
        return RedirectResponse("/?oura=denied")
    token = oura_oauth.exchange_code(oura_oauth.OuraClientConfig.from_env(), code)
    store.save_oura_token(person_id(request), token.access_token, token.refresh_token, token.expires_at(store.utcnow()))
    response = RedirectResponse("/?oura=connected")
    response.delete_cookie(OAUTH_STATE_COOKIE)
    return response


class OuraDaily(BaseModel):
    mode: Literal["live"]
    days: list[DayRow]


def live_access_token(pid: str) -> str | None:
    saved = store.oura_token(pid)
    if saved is None:
        return DEV_OURA_TOKEN
    if saved.refresh_token and oura_oauth.needs_refresh(saved.expires_at, store.utcnow()):
        fresh = oura_oauth.refresh(oura_oauth.OuraClientConfig.from_env(), saved.refresh_token)
        store.save_oura_token(pid, fresh.access_token, fresh.refresh_token or saved.refresh_token, fresh.expires_at(store.utcnow()))
        return fresh.access_token
    return saved.access_token


@app.get("/api/oura/daily")
def oura_daily(request: Request, days: int = 90) -> OuraDaily:
    token = live_access_token(person_id(request))
    if token is None:
        try:
            oura_oauth.OuraClientConfig.from_env()
        except oura_oauth.OuraNotConfigured:
            raise HTTPException(409, detail={"code": "oura_not_configured"}) from None
        raise HTTPException(409, detail={"code": "oura_not_connected"})
    end = date.today()
    start = end - timedelta(days=max(1, min(days, OURA_DAYS_MAX)) - 1)
    raw = OuraConnector(token=token).fetch_all(start, end)
    rows = merge_days(
        adapt_sleep(raw["daily_sleep"], raw["sleep"]),
        adapt_readiness(raw["daily_readiness"]),
        adapt_activity(raw["daily_activity"]),
        adapt_stress(raw["daily_stress"]),
    )
    return OuraDaily(mode="live", days=rows)


@app.get("/api/calendar/connect")
def calendar_connect() -> RedirectResponse:
    try:
        config = gcal.GoogleClientConfig.from_env()
    except gcal.GoogleNotConfigured:
        return RedirectResponse("/?calendar=not_configured")
    state = secrets.token_urlsafe(24)
    response = RedirectResponse(gcal.authorize_url(config, state))
    response.set_cookie(GOOGLE_STATE_COOKIE, state, max_age=600, httponly=True, samesite="lax", secure=SECURE_COOKIES)
    return response


@app.get("/google/callback")
def google_callback(request: Request, code: str = "", state: str = "") -> RedirectResponse:
    if not code or not secrets.compare_digest(state, request.cookies.get(GOOGLE_STATE_COOKIE, "")):
        return RedirectResponse("/?calendar=denied")
    token = gcal.exchange_code(gcal.GoogleClientConfig.from_env(), code)
    store.save_google_token(person_id(request), token.access_token, token.refresh_token, token.expires_at(store.utcnow()))
    response = RedirectResponse("/?calendar=connected")
    response.delete_cookie(GOOGLE_STATE_COOKIE)
    return response


def google_access_token(pid: str) -> str:
    saved = store.google_token(pid)
    if saved is None:
        try:
            gcal.GoogleClientConfig.from_env()
        except gcal.GoogleNotConfigured:
            raise HTTPException(409, detail={"code": "calendar_not_configured"}) from None
        raise HTTPException(409, detail={"code": "calendar_not_connected"})
    if saved.refresh_token and gcal.needs_refresh(saved.expires_at, store.utcnow()):
        fresh = gcal.refresh(gcal.GoogleClientConfig.from_env(), saved.refresh_token)
        store.save_google_token(pid, fresh.access_token, fresh.refresh_token or saved.refresh_token, fresh.expires_at(store.utcnow()))
        return fresh.access_token
    return saved.access_token


@app.get("/api/calendar/events")
def calendar_events(request: Request, start: datetime, end: datetime) -> list[gcal.CalendarEvent]:
    return gcal.events_between(google_access_token(person_id(request)), start, end)


@app.post("/api/calendar/events")
def calendar_create(request: Request, event: gcal.NewEvent) -> gcal.CalendarEvent:
    return gcal.create_event(google_access_token(person_id(request)), event)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "database": store.DB_URL.split(":", 1)[0].split("+", 1)[0]}
