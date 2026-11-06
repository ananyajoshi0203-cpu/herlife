from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.api import claude
from backend.api.app import create_app
from backend.api.db import Database
from backend.api.guidance import (
    SEASON_BY_MONTH,
    SEASONS,
    SeasonName,
    age_band_for,
    season_for,
)
from backend.api.impact import LEVER_OUTCOMES
from backend.api.schemas import (
    DataSource,
    GymAccess,
    ImpactStatus,
    LifeStage,
    LogCategory,
    SignalLevel,
)
from backend.canonical.models import Flow
from backend.connectors.oura import RAW_DIR

GOALS = ["sleep better", "less stress"]
SLEEP_AMOUNT = "6 hours"
VOICE_SENTENCES: list[tuple[LogCategory, str]] = [
    (LogCategory.SLEEP, f"I slept about {SLEEP_AMOUNT} and woke up twice"),
    (LogCategory.NUTRITION, "Had oatmeal for breakfast"),
    (LogCategory.MOVEMENT, "Walked 30 minutes at lunch"),
    (LogCategory.SYMPTOMS, "Bad cramps this afternoon"),
    (LogCategory.MOOD, "Feeling anxious tonight"),
]
VOICE_NOTE = ". ".join(sentence for _, sentence in VOICE_SENTENCES) + "."


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OURA_TOKEN", raising=False)
    with TestClient(create_app(Database(f"sqlite:///{tmp_path / 'herlife.db'}"))) as test_client:
        yield test_client


def onboard(client: TestClient, life_stage: LifeStage, age: int = 32) -> str:
    response = client.post(
        "/users",
        json={
            "name": "Maya",
            "age": age,
            "gym_access": GymAccess.NONE,
            "diet": ["vegetarian"],
            "conditions": [],
            "life_stage": life_stage,
            "goals": GOALS,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_onboarding_to_doctor_record(client: TestClient) -> None:
    user_id = onboard(client, LifeStage.CYCLING)

    synced = client.post(f"/users/{user_id}/sync").json()
    assert synced["live"] is False
    assert synced["sleep"] > 0 and synced["readiness"] > 0

    periods = json.loads((RAW_DIR / "herlife_period_log.json").read_text())
    for period in periods:
        logged = client.post(
            f"/users/{user_id}/periods", json={key: period[key] for key in ("start_day", "end_day", "flow")}
        )
        assert logged.status_code == 201
    cycle = client.get(f"/users/{user_id}/cycle").json()
    assert len(cycle["days"]) == synced["readiness"]
    assert cycle["today"]["cycle_day"] >= 1

    voice = client.post(f"/users/{user_id}/logs/voice", json={"text": VOICE_NOTE}).json()
    assert voice["used_ai"] is False
    assert [(entry["category"], entry["text"]) for entry in voice["entries"]] == VOICE_SENTENCES
    assert voice["entries"][0]["detail"] == SLEEP_AMOUNT

    suggested = client.post(f"/users/{user_id}/habits/suggest").json()
    habits = suggested["habits"]
    assert len(habits) == 3
    assert {habit["goal"] for habit in habits} == set(GOALS)

    habit_id = habits[0]["id"]
    assert client.post(f"/users/{user_id}/habits/{habit_id}/checks", json={}).status_code == 201
    future = (date.today() + timedelta(days=1)).isoformat()
    assert client.post(f"/users/{user_id}/habits/{habit_id}/checks", json={"day": future}).status_code == 422
    consistency = client.get(f"/users/{user_id}/habits/consistency").json()
    this_week = {row["habit_id"]: row["weeks"][-1] for row in consistency}
    assert this_week[habit_id]["days_checked"] == 1
    assert this_week[habits[1]["id"]]["days_checked"] == 0

    plan = client.get(f"/users/{user_id}/plan/today").json()
    assert plan["ease_off"] == bool(plan["reasons"])
    assert plan["cycle"]["phase"] == cycle["today"]["phase"]
    assert "lentils" in plan["eat"]

    record = client.get(f"/users/{user_id}/record").json()
    expected_counts = {category: 0 for category in LogCategory} | {category: 1 for category, _ in VOICE_SENTENCES}
    assert record["self_reports"]["counts"] == expected_counts
    assert record["lifestyle"]["sleep_min"] is not None
    assert record["cycle"]["regularity"]["logged_period_starts"] == [period["start_day"] for period in periods]
    assert [row["habit_id"] for row in record["habits"]] == [habit["id"] for habit in habits]


def test_cycle_stays_out_of_plan_and_record_when_not_cycling(client: TestClient) -> None:
    user_id = onboard(client, LifeStage.HORMONAL_BIRTH_CONTROL)
    client.post(f"/users/{user_id}/sync")
    client.post(f"/users/{user_id}/periods", json={"start_day": date.today().isoformat(), "flow": Flow.LIGHT})

    assert client.get(f"/users/{user_id}/plan/today").json()["cycle"] is None
    assert client.get(f"/users/{user_id}/record").json()["cycle"] is None


def test_onboarding_requires_two_goals(client: TestClient) -> None:
    response = client.post(
        "/users",
        json={
            "name": "Ana",
            "age": 40,
            "gym_access": GymAccess.GYM,
            "life_stage": LifeStage.PREFER_NOT,
            "goals": GOALS[:1],
        },
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    ("age", "label"),
    [(18, "18 to 25"), (25, "18 to 25"), (26, "26 to 34"), (34, "26 to 34"), (35, "35 to 44"), (44, "35 to 44"),
     (45, "45 to 55"), (55, "45 to 55"), (56, "56 and up"), (90, "56 and up")],
)
def test_age_band_is_on_the_user_and_the_plan(client: TestClient, age: int, label: str) -> None:
    user_id = onboard(client, LifeStage.PREFER_NOT, age)
    band = age_band_for(age)
    assert band.label == label and band.focus
    record = client.get(f"/users/{user_id}/record").json()
    assert record["patient"]["age_band"] == band.model_dump()
    assert client.get(f"/users/{user_id}/plan/today").json()["age_band"] == band.model_dump()


@pytest.mark.parametrize(
    ("month", "season"),
    [(12, SeasonName.WINTER), (1, SeasonName.WINTER), (2, SeasonName.WINTER), (3, SeasonName.SPRING),
     (5, SeasonName.SPRING), (6, SeasonName.SUMMER), (8, SeasonName.SUMMER), (9, SeasonName.FALL),
     (11, SeasonName.FALL)],
)
def test_season_by_month_with_sourced_recs(month: int, season: SeasonName) -> None:
    found = season_for(date(2026, month, 15))
    assert found.name == season
    assert found.recs and all(rec.title and rec.body and rec.source for rec in found.recs)
    assert set(SEASON_BY_MONTH.values()) == set(SEASONS)


def test_season_and_age_band_reach_the_plan_and_both_claude_prompts(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    prompts: list[str] = []

    def capture(system: str, prompt: str, schema: type[object]) -> None:
        prompts.append(prompt)

    monkeypatch.setattr(claude, "ask_structured", capture)
    age = 48
    user_id = onboard(client, LifeStage.PERIMENOPAUSE_MENOPAUSE, age)
    season = season_for(date.today())
    band = age_band_for(age)

    client.post(f"/users/{user_id}/habits/suggest")
    plan = client.get(f"/users/{user_id}/plan/today").json()

    assert plan["season"] == season.model_dump(mode="json")
    assert plan["used_ai"] is False
    assert len(prompts) == 2
    for prompt in prompts:
        assert season.label in prompt
        assert ", ".join(band.focus) in prompt


def test_no_wearable_plan_and_record_run_on_check_ins(client: TestClient) -> None:
    user_id = onboard(client, LifeStage.CYCLING)
    steady_days, steady_hours = 6, 7.5
    for offset in range(steady_days, 0, -1):
        day = (date.today() - timedelta(days=offset)).isoformat()
        body = {"day": day, "sleep_hours": steady_hours, "energy": 4, "stress": 2}
        assert client.post(f"/users/{user_id}/checkins", json=body).status_code == 201
    period_start = date.today() - timedelta(days=3)
    client.post(f"/users/{user_id}/periods", json={"start_day": period_start.isoformat(), "flow": Flow.MEDIUM})

    calm = client.get(f"/users/{user_id}/plan/today").json()
    assert calm["data_source"] == DataSource.SELF_CHECK_IN
    assert calm["ease_off"] is False
    assert calm["cycle"]["cycle_day"] == (date.today() - period_start).days + 1

    rough_hours, rough_energy, rough_stress = 5.0, 2, 4
    today_check = {"sleep_hours": rough_hours, "energy": rough_energy, "stress": rough_stress}
    assert client.post(f"/users/{user_id}/checkins", json=today_check).status_code == 201
    rough = client.get(f"/users/{user_id}/plan/today").json()
    assert rough["ease_off"] is True
    assert rough["reasons"] == [
        f"You slept about {rough_hours:g} hours last night.",
        f"You rated your energy {rough_energy} out of 5.",
        f"You rated your stress {rough_stress} out of 5.",
    ]

    record = client.get(f"/users/{user_id}/record").json()
    assert record["data_source"] == DataSource.SELF_CHECK_IN
    assert record["self_check_ins"]["days"] == steady_days + 1
    expected_hours = round((steady_days * steady_hours + rough_hours) / (steady_days + 1), 1)
    assert record["self_check_ins"]["sleep_hours"] == expected_hours
    assert record["first_day"] == (date.today() - timedelta(days=steady_days)).isoformat()

    future = (date.today() + timedelta(days=1)).isoformat()
    assert client.post(f"/users/{user_id}/checkins", json=today_check | {"day": future}).status_code == 422
    assert client.post(f"/users/{user_id}/checkins", json=today_check | {"energy": 6}).status_code == 422


@pytest.mark.parametrize(("age", "mentions_menopause"), [(32, False), (48, True)])
def test_cycle_signal_endpoint(client: TestClient, age: int, mentions_menopause: bool) -> None:
    user_id = onboard(client, LifeStage.IRREGULAR, age)
    assert client.get(f"/users/{user_id}/cycle/signal").json() is None
    lengths = [29, 30, 41, 52]
    start = date.today() - timedelta(days=sum(lengths) + 10)
    for length in [0, *lengths]:
        start += timedelta(days=length)
        client.post(f"/users/{user_id}/periods", json={"start_day": start.isoformat(), "flow": Flow.MEDIUM})

    signal = client.get(f"/users/{user_id}/cycle/signal").json()
    assert signal["level"] == SignalLevel.WATCH
    assert signal["cycle_lengths_days"] == lengths
    assert signal["clinician_question"]
    assert ("menopause" in (signal["title"] + signal["body"]).lower()) == mentions_menopause
    assert client.get(f"/users/{user_id}/record").json()["cycle_signal"] == signal


def test_habit_impact_endpoint(client: TestClient) -> None:
    user_id = onboard(client, LifeStage.CYCLING)
    client.post(f"/users/{user_id}/sync")
    habits = client.post(f"/users/{user_id}/habits/suggest").json()["habits"]
    client.post(f"/users/{user_id}/habits/{habits[0]['id']}/checks", json={})

    impacts = client.get(f"/users/{user_id}/habits/impact").json()
    assert [row["habit_id"] for row in impacts] == [habit["id"] for habit in habits]
    for row, habit in zip(impacts, habits, strict=True):
        assert row["goal"] == habit["goal"]
        assert [outcome["metric"] for outcome in row["outcomes"]] == list(LEVER_OUTCOMES[row["lever"]])
        for outcome in row["outcomes"]:
            assert outcome["done_vs_not_done"]["status"] == ImpactStatus.INSUFFICIENT_DATA
