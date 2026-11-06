"""Compact daily rows: the shape web/index.html renders, built from canonical Oura tables."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from backend.canonical.models import Activity, Readiness, SleepNight, Stress


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
