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

from backend.canonical.daily_rows import DayRow, merge_days
from backend.canonical.oura_adapter import adapt_activity, adapt_readiness, adapt_sleep, adapt_stress
from backend.connectors.oura import OuraConnector
from backend.synthetic import oura_generator

MAX_DAYS = 120

Mode = Literal["live", "demo"]


class OuraStatus(BaseModel):
    mode: Mode
    message: str


class OuraDays(BaseModel):
    mode: Mode
    start: date
    end: date
    days: list[DayRow]


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
