"""Request and response models: the typed boundary of the HTTP API."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, computed_field

from backend.api.guidance import AgeBand, Season, age_band_for
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

    @computed_field  # type: ignore[prop-decorator]
    @property
    def age_band(self) -> AgeBand:
        return age_band_for(self.age)


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


class DataSource(StrEnum):
    WEARABLE = "wearable"
    SELF_CHECK_IN = "self_check_in"
    NONE = "none"


class CheckinCreate(BaseModel):
    day: date | None = None
    sleep_hours: float = Field(ge=0, le=24)
    energy: int = Field(ge=1, le=5)
    stress: int = Field(ge=1, le=5)


class Checkin(BaseModel):
    day: date
    sleep_hours: float
    energy: int
    stress: int


class CheckinAverages(BaseModel):
    window_days: int
    days: int
    sleep_hours: float | None
    energy: float | None
    stress: float | None


class PlanText(BaseModel):
    sleep: str
    move: str
    eat: str
    mind: str


class TodayPlan(PlanText):
    day: date
    used_ai: bool
    data_source: DataSource
    ease_off: bool
    reasons: list[str]
    cycle: CycleContext | None
    age_band: AgeBand
    season: Season


class SignalLevel(StrEnum):
    STEADY = "steady"
    WATCH = "watch"
    FLAG = "flag"


class CycleSignal(BaseModel):
    level: SignalLevel
    title: str
    body: str
    clinician_question: str | None
    cycle_lengths_days: list[int]
    days_since_last_period: int


class Lever(StrEnum):
    SLEEP = "sleep"
    MOVEMENT = "movement"
    STRESS = "stress"
    NUTRITION = "nutrition"
    MOOD = "mood"


class OutcomeMetric(StrEnum):
    SLEEP_MIN = "sleep_min"
    HRV_MS = "hrv_ms"
    STEPS = "steps"
    READINESS = "readiness"


class ImpactStatus(StrEnum):
    NOTABLE = "notable"
    NO_CLEAR_DIFFERENCE = "no_clear_difference"
    INSUFFICIENT_DATA = "insufficient_data"


class Comparison(BaseModel):
    """Mean outcome with the habit against without it; means are withheld below the day minimum."""

    status: ImpactStatus
    with_habit_days: int
    without_habit_days: int
    with_habit_mean: float | None
    without_habit_mean: float | None
    difference: float | None
    summary: str


class OutcomeImpact(BaseModel):
    metric: OutcomeMetric
    lag_days: int
    notable_difference: float
    done_vs_not_done: Comparison
    before_vs_after: Comparison


class HabitImpact(BaseModel):
    habit_id: uuid.UUID
    title: str
    goal: str
    lever: Lever
    first_check: date | None
    outcomes: list[OutcomeImpact]


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
    data_source: DataSource
    self_check_ins: CheckinAverages | None
    cycle: RecordInsights | None
    cycle_signal: CycleSignal | None
    note: str
