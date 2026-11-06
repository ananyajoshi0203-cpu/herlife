"""Request and response models: the typed boundary of the HTTP API."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from backend.canonical.models import CycleDay, Flow, PeriodLog
from backend.insights import RecordInsights


class GymAccess(StrEnum):
    GYM = "gym"
    HOME = "home"
    NONE = "none"


class LifeStage(StrEnum):
    CYCLING = "cycling"
    IRREGULAR = "irregular"
    HORMONAL_BIRTH_CONTROL = "hormonal_birth_control"
    PREGNANT_POSTPARTUM = "pregnant_postpartum"
    PERIMENOPAUSE_MENOPAUSE = "perimenopause_menopause"
    PREFER_NOT = "prefer_not"


CYCLE_AWARE_STAGES = frozenset({LifeStage.CYCLING, LifeStage.IRREGULAR})


class LogCategory(StrEnum):
    SLEEP = "sleep"
    MOVEMENT = "movement"
    NUTRITION = "nutrition"
    MOOD = "mood"
    SYMPTOMS = "symptoms"


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    age: int = Field(ge=13, le=120)
    gym_access: GymAccess
    diet: list[str] = []
    conditions: list[str] = []
    life_stage: LifeStage
    goals: list[str] = Field(min_length=2, max_length=2)


class User(UserCreate):
    id: uuid.UUID
    created_at: datetime


class OuraConnected(BaseModel):
    user_id: uuid.UUID
    connected: bool


class SyncResult(BaseModel):
    user_id: uuid.UUID
    live: bool
    start: date
    end: date
    sleep: int
    readiness: int
    activity: int
    stress: int


class PeriodCreate(BaseModel):
    start_day: date
    end_day: date | None = None
    flow: Flow


class CycleView(BaseModel):
    periods: list[PeriodLog]
    today: CycleDay | None
    days: list[CycleDay]


class VoiceLogRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)


class LogEntry(BaseModel):
    id: uuid.UUID
    day: date
    category: LogCategory
    text: str
    detail: str


class VoiceLogResult(BaseModel):
    used_ai: bool
    entries: list[LogEntry]


class Habit(BaseModel):
    id: uuid.UUID
    title: str
    why: str
    goal: str
    created_on: date


class HabitSuggestions(BaseModel):
    used_ai: bool
    habits: list[Habit]


class HabitCheckCreate(BaseModel):
    day: date | None = None


class HabitCheck(BaseModel):
    habit_id: uuid.UUID
    day: date


class WeekConsistency(BaseModel):
    iso_week: str
    week_start: date
    days_checked: int
    days_possible: int
    rate: float | None


class HabitConsistency(BaseModel):
    habit_id: uuid.UUID
    title: str
    weeks: list[WeekConsistency]


class CycleContext(BaseModel):
    cycle_day: int
    phase: str
    ovulation_confirmed: bool
    note: str


class TodayPlan(BaseModel):
    day: date
    sleep: str
    move: str
    eat: str
    mind: str
    ease_off: bool
    reasons: list[str]
    cycle: CycleContext | None


class LifestyleAverages(BaseModel):
    window_days: int
    sleep_min: float | None
    sleep_efficiency_pct: float | None
    hrv_ms: float | None
    resting_hr_bpm: float | None
    readiness_score: float | None
    steps: float | None
    active_min: float | None
    stress_high_min: float | None


class SelfReportSummary(BaseModel):
    counts: dict[LogCategory, int]
    recent: list[LogEntry]


class DoctorRecord(BaseModel):
    generated_at: datetime
    patient: User
    first_day: date | None
    last_day: date | None
    lifestyle: LifestyleAverages
    self_reports: SelfReportSummary
    habits: list[HabitConsistency]
    cycle: RecordInsights | None
    note: str
