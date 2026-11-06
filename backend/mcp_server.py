"""Bloom Oura MCP server: the web app's real Oura connector.

The published artifact cannot reach api.ouraring.com (its sandbox blocks outside
requests), so it calls this local server through the Claude app instead. With
OURA_TOKEN set the data is live; without it the server answers with the
synthetic persona and says so, so the page can label it honestly.

    OURA_TOKEN=... .venv/bin/python -m backend.mcp_server
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Literal

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import BaseModel

from backend.canonical.models import Activity, Readiness, SleepNight, Stress
from backend.canonical.oura_adapter import adapt_activity, adapt_readiness, adapt_sleep, adapt_stress
from backend.connectors.oura import OuraConnector
from backend.synthetic import oura_generator

MAX_DAYS = 120

Mode = Literal["live", "demo"]


class DayRow(BaseModel):
    """One day in the compact shape web/index.html renders (same keys as the embedded seed)."""

    day: date
    sleep: int | None = None
    sleepMin: int | None = None
    deep: int | None = None
    rem: int | None = None
    hrv: float | None = None
    rhr: float | None = None
    bed: str | None = None
    ready: int | None = None
    temp: float | None = None
    steps: int | None = None
    kcal: int | None = None
    stress: int | None = None
    recovery: int | None = None


class OuraStatus(BaseModel):
    mode: Mode
    message: str


class OuraDays(BaseModel):
    mode: Mode
    start: date
    end: date
    days: list[DayRow]


def merge_days(
    sleep: list[SleepNight], readiness: list[Readiness], activity: list[Activity], stress: list[Stress]
) -> list[DayRow]:
    rows: dict[date, DayRow] = {}
    for night in sleep:
        row = rows.setdefault(night.day, DayRow(day=night.day))
        row.sleep, row.sleepMin, row.deep, row.rem = night.score, night.total_sleep_min, night.deep_min, night.rem_min
        row.hrv, row.rhr, row.bed = night.avg_hrv_ms, night.resting_hr_bpm, night.bedtime_start.strftime("%H:%M")
    for ready in readiness:
        row = rows.setdefault(ready.day, DayRow(day=ready.day))
        row.ready, row.temp = ready.score, ready.temperature_deviation_c
    for act in activity:
        row = rows.setdefault(act.day, DayRow(day=act.day))
        row.steps, row.kcal = act.steps, act.active_kcal
    for load in stress:
        row = rows.setdefault(load.day, DayRow(day=load.day))
        row.stress, row.recovery = load.stress_high_min, load.recovery_high_min
    # Oura scores a night on the day she wakes; a day without a sleep row is still syncing.
    return [rows[day] for day in sorted(rows) if rows[day].sleep is not None]


server = MCPServer("bloom_oura")


@server.tool(annotations=ToolAnnotations(read_only_hint=True))
def oura_status() -> OuraStatus:
    """Whether Bloom is reading a real Oura account (live) or the demo persona (demo)."""
    if OuraConnector().is_live:
        return OuraStatus(mode="live", message="Reading your Oura account.")
    return OuraStatus(mode="demo", message="No Oura token on this computer, showing the demo persona.")


@server.tool(annotations=ToolAnnotations(read_only_hint=True))
def oura_daily(days: int = 90) -> OuraDays:
    """Daily sleep, HRV, readiness, temperature deviation, steps, and stress for the last `days` days (max 120)."""
    span = max(1, min(days, MAX_DAYS))
    end = date.today()
    start = end - timedelta(days=span - 1)
    connector = OuraConnector()
    if not connector.is_live:
        oura_generator.write(end)
    raw = connector.fetch_all(start, end)
    rows = merge_days(
        adapt_sleep(raw["daily_sleep"], raw["sleep"]),
        adapt_readiness(raw["daily_readiness"]),
        adapt_activity(raw["daily_activity"]),
        adapt_stress(raw["daily_stress"]),
    )
    return OuraDays(mode="live" if connector.is_live else "demo", start=start, end=end, days=rows)


if __name__ == "__main__":
    server.run()
