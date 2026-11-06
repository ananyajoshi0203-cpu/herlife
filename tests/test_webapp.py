"""Hosted web app: the endpoints the page's platform shim relies on."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

os.environ["BLOOM_WEB_DB"] = f"sqlite:///{Path(tempfile.mkdtemp()) / 'web_test.db'}"

from fastapi.testclient import TestClient  # noqa: E402

from backend.webapp.server import app  # noqa: E402


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def test_page_is_served_with_the_platform_shim_before_the_app(client: TestClient) -> None:
    html = client.get("/").text
    assert html.startswith("<!doctype html>")
    assert "<title>HerLife</title>" in html
    assert html.index("/static/bloom-platform.js") < html.index('"use strict";')


def test_each_browser_gets_its_own_private_record(client: TestClient) -> None:
    other = TestClient(app)
    client.put("/api/state", json={"json": '{"step":"app"}', "updatedAt": 5})
    assert client.get("/api/state").json() == {"exists": True, "json": '{"step":"app"}', "updatedAt": 5}
    assert other.get("/api/state").json()["exists"] is False
    assert client.get("/api/me").json()["id"] != other.get("/api/me").json()["id"]


def test_deleting_the_record_erases_it(client: TestClient) -> None:
    client.put("/api/state", json={"json": "{}", "updatedAt": 1})
    assert client.delete("/api/state").status_code == 204
    assert client.get("/api/state").json()["exists"] is False


def test_ai_without_a_key_returns_a_code_the_page_falls_back_on(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    response = client.post("/api/ai/json", json={"prompt": "hi", "tier": "quick"})
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "not_configured"


def test_oversized_prompts_are_rejected(client: TestClient) -> None:
    assert client.post("/api/ai/json", json={"prompt": "x" * 20_000}).status_code == 422


def test_oura_and_calendar_say_not_configured_instead_of_failing(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("OURA_CLIENT_ID", "OURA_CLIENT_SECRET", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "BLOOM_DEV_OURA_TOKEN", "DEV_OURA_TOKEN"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr("backend.webapp.server.DEV_OURA_TOKEN", None)
    assert client.get("/api/oura/daily").json()["detail"]["code"] == "oura_not_configured"
    assert client.get("/api/calendar/events", params={"start": "2026-11-06T00:00:00Z", "end": "2026-11-07T00:00:00Z"}).json()["detail"]["code"] == "calendar_not_configured"
    assert client.get("/api/oura/connect", follow_redirects=False).headers["location"].endswith("oura=not_configured")


def test_health_reports_the_database_kind(client: TestClient) -> None:
    assert client.get("/healthz").json() == {"status": "ok", "database": "sqlite"}
