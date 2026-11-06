"""Morph raw Oura v2 payloads into canonical records.

Oura does not sync periods, so this adapter produces no cycle rows. The cycle is
built from Bloom's own period log in `backend.canonical.cycle`, which reads the
temperature deviation adapted here only to confirm ovulation.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from backend.canonical.models import (
    Activity,
    Readiness,
    SleepNight,
    Source,
    Stress,
)
from backend.connectors.oura import OuraEndpoint

SECONDS_PER_MINUTE = 60


def _minutes(seconds: int | None) -> int:
    return round((seconds or 0) / SECONDS_PER_MINUTE)


def adapt_sleep(daily: list[dict[str, Any]], periods: list[dict[str, Any]]) -> list[SleepNight]:
    score_by_day = {row["day"]: row.get("score") for row in daily}
    return [
        SleepNight(
            day=date.fromisoformat(period["day"]),
            source=Source.OURA,
            score=score_by_day.get(period["day"]),
            bedtime_start=datetime.fromisoformat(period["bedtime_start"]),
            bedtime_end=datetime.fromisoformat(period["bedtime_end"]),
            total_sleep_min=_minutes(period["total_sleep_duration"]),
            deep_min=_minutes(period["deep_sleep_duration"]),
            rem_min=_minutes(period["rem_sleep_duration"]),
            light_min=_minutes(period["light_sleep_duration"]),
            awake_min=_minutes(period["awake_time"]),
            efficiency_pct=period["efficiency"],
            avg_hrv_ms=period.get("average_hrv"),
            resting_hr_bpm=period.get("lowest_heart_rate"),
        )
        for period in periods
        if period.get("type", "long_sleep") == "long_sleep"
    ]


def adapt_readiness(rows: list[dict[str, Any]]) -> list[Readiness]:
    return [
        Readiness(
            day=date.fromisoformat(row["day"]),
            source=Source.OURA,
            score=row["score"],
            temperature_deviation_c=row.get("temperature_deviation"),
            hrv_balance=row["contributors"].get("hrv_balance"),
            recovery_index=row["contributors"].get("recovery_index"),
        )
        for row in rows
    ]


def adapt_activity(rows: list[dict[str, Any]]) -> list[Activity]:
    return [
        Activity(
            day=date.fromisoformat(row["day"]),
            source=Source.OURA,
            score=row.get("score"),
            steps=row["steps"],
            active_kcal=row["active_calories"],
            high_activity_min=_minutes(row["high_activity_time"]),
            medium_activity_min=_minutes(row["medium_activity_time"]),
            low_activity_min=_minutes(row["low_activity_time"]),
        )
        for row in rows
    ]


def adapt_stress(rows: list[dict[str, Any]]) -> list[Stress]:
    return [
        Stress(
            day=date.fromisoformat(row["day"]),
            source=Source.OURA,
            stress_high_min=_minutes(row["stress_high"]),
            recovery_high_min=_minutes(row["recovery_high"]),
            summary=row.get("day_summary"),
        )
        for row in rows
    ]


def adapt_all(raw: dict[OuraEndpoint, list[dict[str, Any]]]) -> dict[str, list[Any]]:
    return {
        "sleep": adapt_sleep(raw["daily_sleep"], raw["sleep"]),
        "readiness": adapt_readiness(raw["daily_readiness"]),
        "activity": adapt_activity(raw["daily_activity"]),
        "stress": adapt_stress(raw["daily_stress"]),
    }
