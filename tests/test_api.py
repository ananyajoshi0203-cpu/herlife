from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.api.app import create_app
from backend.api.db import Database
from backend.api.schemas import GymAccess, LifeStage, LogCategory
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
    with TestClient(create_app(Database(f"sqlite:///{tmp_path / 'bloom.db'}"))) as test_client:
        yield test_client


def onboard(client: TestClient, life_stage: LifeStage) -> str:
    response = client.post(
        "/users",
        json={
            "name": "Maya",
            "age": 32,
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

    periods = json.loads((RAW_DIR / "bloom_period_log.json").read_text())
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
