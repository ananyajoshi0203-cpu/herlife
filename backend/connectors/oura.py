"""Oura API v2 connector.

Live mode calls https://api.ouraring.com/v2/usercollection/* with a personal
access token. Mock mode reads the synthetic payloads written by
`backend.synthetic.oura_generator`, which share the exact response shape, so the
adapter cannot tell the two apart.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any, Literal

OuraEndpoint = Literal["daily_sleep", "sleep", "daily_readiness", "daily_activity", "daily_stress"]
ENDPOINTS: tuple[OuraEndpoint, ...] = (
    "daily_sleep",
    "sleep",
    "daily_readiness",
    "daily_activity",
    "daily_stress",
)

BASE_URL = "https://api.ouraring.com/v2/usercollection"
RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


class OuraConnector:
    def __init__(self, token: str | None = None, mock_dir: Path | None = None) -> None:
        self.token = token if token is not None else os.environ.get("OURA_TOKEN")
        self.mock_dir = mock_dir or RAW_DIR

    @property
    def is_live(self) -> bool:
        return bool(self.token)

    def fetch(self, endpoint: OuraEndpoint, start: date, end: date) -> list[dict[str, Any]]:
        if self.is_live:
            return self._fetch_live(endpoint, start, end)
        return self._fetch_mock(endpoint, start, end)

    def fetch_all(self, start: date, end: date) -> dict[OuraEndpoint, list[dict[str, Any]]]:
        return {endpoint: self.fetch(endpoint, start, end) for endpoint in ENDPOINTS}

    def _fetch_live(self, endpoint: OuraEndpoint, start: date, end: date) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        params: dict[str, str] = {"start_date": start.isoformat(), "end_date": end.isoformat()}
        while True:
            url = f"{BASE_URL}/{endpoint}?{urllib.parse.urlencode(params)}"
            request = urllib.request.Request(url, headers={"Authorization": f"Bearer {self.token}"})
            with urllib.request.urlopen(request, timeout=20) as response:
                page = json.load(response)
            rows.extend(page.get("data", []))
            next_token = page.get("next_token")
            if not next_token:
                return rows
            params["next_token"] = next_token

    def _fetch_mock(self, endpoint: OuraEndpoint, start: date, end: date) -> list[dict[str, Any]]:
        payload = json.loads((self.mock_dir / f"oura_{endpoint}.json").read_text())
        return [row for row in payload["data"] if start.isoformat() <= row["day"] <= end.isoformat()]
