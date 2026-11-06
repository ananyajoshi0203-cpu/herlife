"""Canonical health record: the vendor-neutral shape every wearable adapter produces.

Oura today, Apple Health / Whoop / Garmin later. The app and the doctor summary
only ever read these models, never a vendor payload.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Source(StrEnum):
    OURA = "oura"
    SELF_REPORT = "self_report"


class CyclePhase(StrEnum):
    MENSTRUAL = "menstrual"
    FOLLICULAR = "follicular"
    OVULATORY = "ovulatory"
    LUTEAL = "luteal"


class Flow(StrEnum):
    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"


class PeriodLog(BaseModel):
    """One period as logged in Bloom's own tracker; wearables do not sync periods."""

    start_day: date
    end_day: date | None = None
    flow: Flow
    source: Source = Source.SELF_REPORT


class SleepNight(BaseModel):
    day: date
    source: Source
    score: int | None = Field(default=None, ge=0, le=100)
    bedtime_start: datetime
    bedtime_end: datetime
    total_sleep_min: int
    deep_min: int
    rem_min: int
    light_min: int
    awake_min: int
    efficiency_pct: int
    avg_hrv_ms: float | None = None
    resting_hr_bpm: float | None = None


class Readiness(BaseModel):
    day: date
    source: Source
    score: int = Field(ge=0, le=100)
    temperature_deviation_c: float | None = None
    hrv_balance: int | None = None
    recovery_index: int | None = None


class Activity(BaseModel):
    day: date
    source: Source
    score: int | None = Field(default=None, ge=0, le=100)
    steps: int
    active_kcal: int
    high_activity_min: int
    medium_activity_min: int
    low_activity_min: int


class Stress(BaseModel):
    day: date
    source: Source
    stress_high_min: int
    recovery_high_min: int
    summary: str | None = None


class CycleDay(BaseModel):
    day: date
    source: Source
    cycle_day: int = Field(ge=1)
    phase: CyclePhase
    is_period: bool
    ovulation_confirmed: bool = False


class CanonicalDataset(BaseModel):
    user_id: str
    generated_at: datetime
    sleep: list[SleepNight]
    readiness: list[Readiness]
    activity: list[Activity]
    stress: list[Stress]
    periods: list[PeriodLog]
    cycle: list[CycleDay]
