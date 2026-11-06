"""Domain logic behind the endpoints. Reads and writes canonical models only."""

from __future__ import annotations

import uuid
from collections import Counter
from collections.abc import Iterable, Sequence
from datetime import date, datetime, time, timedelta
from enum import StrEnum
from statistics import median

from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.api.db import (
    HabitCheckRow,
    HabitRow,
    PeriodRow,
    SelfReportRow,
    UserRow,
    WearableDayRow,
)
from backend.api.schemas import (
    CYCLE_AWARE_STAGES,
    CycleContext,
    DoctorRecord,
    GymAccess,
    Habit,
    HabitConsistency,
    LifestyleAverages,
    LogCategory,
    LogEntry,
    SelfReportSummary,
    TodayPlan,
    User,
    WeekConsistency,
)
from backend.canonical.cycle import build_cycle
from backend.canonical.models import (
    Activity,
    CanonicalDataset,
    CycleDay,
    CyclePhase,
    Flow,
    PeriodLog,
    Readiness,
    SleepNight,
    Source,
    Stress,
)
from backend.insights import compute, rounded_mean

LIFESTYLE_WINDOW = timedelta(days=30)
BASELINE_WINDOW = timedelta(days=14)
RECENT_REPORTS = 20
SHORT_NIGHT = timedelta(hours=6)
LOW_READINESS = 65
READINESS_DROP = 10
STRESS_SPIKE_RATIO = 1.5
WARM_TEMPERATURE_C = 0.5
EASE_OFF_BEDTIME_SHIFT = timedelta(minutes=30)
RECORD_NOTE = (
    "A lifestyle record kept by the patient in Bloom and her wearable. "
    "It is a record to support the conversation, not a diagnosis."
)


class WearableKind(StrEnum):
    SLEEP = "sleep"
    READINESS = "readiness"
    ACTIVITY = "activity"
    STRESS = "stress"


type DailyRecord = SleepNight | Readiness | Activity | Stress


def to_user(row: UserRow) -> User:
    return User.model_validate(row, from_attributes=True)


def replace_wearable_days(
    session: Session, user_id: uuid.UUID, kind: WearableKind, records: Iterable[DailyRecord], source: Source
) -> int:
    session.execute(
        delete(WearableDayRow).where(
            WearableDayRow.user_id == user_id, WearableDayRow.kind == kind, WearableDayRow.source == source
        )
    )
    rows = [
        WearableDayRow(
            user_id=user_id, kind=kind, day=record.day, source=record.source, payload=record.model_dump(mode="json")
        )
        for record in {record.day: record for record in records}.values()
    ]
    session.add_all(rows)
    return len(rows)


def load_wearable[T: BaseModel](session: Session, user_id: uuid.UUID, kind: WearableKind, model: type[T]) -> list[T]:
    rows = session.scalars(
        select(WearableDayRow)
        .where(WearableDayRow.user_id == user_id, WearableDayRow.kind == kind)
        .order_by(WearableDayRow.day)
    )
    return [model.model_validate(row.payload) for row in rows]


def load_periods(session: Session, user_id: uuid.UUID) -> list[PeriodLog]:
    rows = session.scalars(select(PeriodRow).where(PeriodRow.user_id == user_id).order_by(PeriodRow.start_day))
    return [
        PeriodLog(start_day=row.start_day, end_day=row.end_day, flow=Flow(row.flow), source=Source(row.source))
        for row in rows
    ]


def load_dataset(session: Session, user_id: uuid.UUID) -> CanonicalDataset:
    readiness = load_wearable(session, user_id, WearableKind.READINESS, Readiness)
    periods = load_periods(session, user_id)
    return CanonicalDataset(
        user_id=str(user_id),
        generated_at=datetime.now(),
        sleep=load_wearable(session, user_id, WearableKind.SLEEP, SleepNight),
        readiness=readiness,
        activity=load_wearable(session, user_id, WearableKind.ACTIVITY, Activity),
        stress=load_wearable(session, user_id, WearableKind.STRESS, Stress),
        periods=periods,
        cycle=build_cycle(periods, readiness),
    )


def within[T: DailyRecord | CycleDay](records: Iterable[T], end: date, window: timedelta) -> list[T]:
    return [record for record in records if end - window < record.day <= end]


def last_observed_day(dataset: CanonicalDataset) -> date | None:
    days = [night.day for night in dataset.sleep] + [row.day for row in dataset.readiness]
    return max(days, default=None)


def lifestyle_averages(
    dataset: CanonicalDataset, end: date | None, window: timedelta = LIFESTYLE_WINDOW
) -> LifestyleAverages:
    end = end or date.today()
    sleep = within(dataset.sleep, end, window)
    activity = within(dataset.activity, end, window)
    return LifestyleAverages(
        window_days=window.days,
        sleep_min=rounded_mean(night.total_sleep_min for night in sleep),
        sleep_efficiency_pct=rounded_mean(night.efficiency_pct for night in sleep),
        hrv_ms=rounded_mean(night.avg_hrv_ms for night in sleep),
        resting_hr_bpm=rounded_mean(night.resting_hr_bpm for night in sleep),
        readiness_score=rounded_mean(row.score for row in within(dataset.readiness, end, window)),
        steps=rounded_mean(row.steps for row in activity),
        active_min=rounded_mean(row.high_activity_min + row.medium_activity_min for row in activity),
        stress_high_min=rounded_mean(row.stress_high_min for row in within(dataset.stress, end, window)),
    )


def latest[T: DailyRecord | CycleDay](records: Sequence[T], today: date) -> T | None:
    return max((record for record in records if record.day <= today), key=lambda record: record.day, default=None)


def to_habit(row: HabitRow) -> Habit:
    return Habit.model_validate(row, from_attributes=True)


def to_log_entry(row: SelfReportRow) -> LogEntry:
    return LogEntry(id=row.id, day=row.day, category=LogCategory(row.category), text=row.text, detail=row.detail)


def week_consistency(created_on: date, checked: set[date], monday: date, today: date) -> WeekConsistency:
    first, last = max(created_on, monday), min(today, monday + timedelta(days=6))
    possible = (last - first).days + 1
    days_checked = sum(first <= day <= last for day in checked)
    iso = monday.isocalendar()
    return WeekConsistency(
        iso_week=f"{iso.year}-W{iso.week:02d}",
        week_start=monday,
        days_checked=days_checked,
        days_possible=possible,
        rate=round(days_checked / possible, 2) if possible > 0 else None,
    )


def habit_consistency(session: Session, user_id: uuid.UUID, today: date) -> list[HabitConsistency]:
    habits = session.scalars(select(HabitRow).where(HabitRow.user_id == user_id).order_by(HabitRow.created_on))
    consistency: list[HabitConsistency] = []
    for habit in habits:
        checked = set(session.scalars(select(HabitCheckRow.day).where(HabitCheckRow.habit_id == habit.id)))
        monday = habit.created_on - timedelta(days=habit.created_on.weekday())
        weeks: list[WeekConsistency] = []
        while monday <= today:
            weeks.append(week_consistency(habit.created_on, checked, monday, today))
            monday += timedelta(weeks=1)
        consistency.append(HabitConsistency(habit_id=habit.id, title=habit.title, weeks=weeks))
    return consistency


def clock(moment: time) -> str:
    return f"{moment.hour % 12 or 12}:{moment.minute:02d} {'AM' if moment.hour < 12 else 'PM'}"


def typical_bedtime(nights: Sequence[SleepNight]) -> time | None:
    if not nights:
        return None
    # Minutes after noon, so 11 PM and 12:30 AM sit next to each other instead of 22 hours apart.
    offsets = [((night.bedtime_start.hour - 12) % 24) * 60 + night.bedtime_start.minute for night in nights]
    middle = round(median(offsets))
    return time(hour=(middle // 60 + 12) % 24, minute=middle % 60)


def ease_off_reasons(dataset: CanonicalDataset, today: date) -> list[str]:
    reasons: list[str] = []
    night, readiness, stress = (
        latest(dataset.sleep, today),
        latest(dataset.readiness, today),
        latest(dataset.stress, today),
    )
    if night and timedelta(minutes=night.total_sleep_min) < SHORT_NIGHT:
        reasons.append(f"You slept {night.total_sleep_min // 60}h {night.total_sleep_min % 60}m last night.")
    if readiness:
        baseline = rounded_mean(row.score for row in within(dataset.readiness, today, BASELINE_WINDOW))
        if readiness.score < LOW_READINESS or (baseline is not None and readiness.score <= baseline - READINESS_DROP):
            reasons.append(f"Your readiness is {readiness.score}, lower than your recent average.")
        if (readiness.temperature_deviation_c or 0) >= WARM_TEMPERATURE_C:
            reasons.append("Your body temperature is running warmer than usual.")
    if stress:
        baseline = rounded_mean(row.stress_high_min for row in within(dataset.stress, today, BASELINE_WINDOW))
        if baseline and stress.stress_high_min >= STRESS_SPIKE_RATIO * baseline:
            reasons.append("Yesterday carried more stress than a typical day for you.")
    return reasons


PHASE_NOTES: dict[CyclePhase, str] = {
    CyclePhase.MENSTRUAL: "Period days. Many women like gentler movement and extra rest now.",
    CyclePhase.FOLLICULAR: "Energy often builds in this phase, a good window for harder sessions.",
    CyclePhase.OVULATORY: "Around ovulation. Energy is often at its peak.",
    CyclePhase.LUTEAL: "Second half of your cycle. Sleep and cravings can shift, so steady meals help.",
}


def cycle_context(user: User, dataset: CanonicalDataset, today: date) -> CycleContext | None:
    if user.life_stage not in CYCLE_AWARE_STAGES:
        return None
    day = latest(dataset.cycle, today)
    if day is None:
        return None
    return CycleContext(
        cycle_day=day.cycle_day,
        phase=day.phase,
        ovulation_confirmed=day.ovulation_confirmed,
        note=PHASE_NOTES[day.phase],
    )


MOVE_PLAN: dict[GymAccess, tuple[str, str]] = {
    GymAccess.GYM: (
        "A full strength or cardio session at the gym.",
        "Swap the gym for an easy walk or gentle stretching.",
    ),
    GymAccess.HOME: (
        "20 to 30 minutes of strength or a workout video at home.",
        "10 minutes of gentle yoga or stretching at home.",
    ),
    GymAccess.NONE: ("A brisk 30 minute walk, with a few hills if you can.", "An easy 15 minute walk, no pace goal."),
}
PLANT_DIETS = ("vegetarian", "vegan", "plant")


def eat_plan(user: User, ease_off: bool, cycle: CycleContext | None) -> str:
    protein = (
        "beans, lentils, or tofu"
        if any(word in item.lower() for item in user.diet for word in PLANT_DIETS)
        else "eggs, fish, or chicken"
    )
    if cycle and cycle.phase == CyclePhase.MENSTRUAL:
        return f"Iron-rich foods today, like leafy greens with {protein}, plus plenty of water."
    if ease_off:
        return f"Warm, simple meals with {protein}, and go easy on caffeine after noon."
    return f"Build each meal around {protein} and a vegetable, and keep water nearby."


def build_plan(user: User, dataset: CanonicalDataset, today: date) -> TodayPlan:
    reasons = ease_off_reasons(dataset, today)
    cycle = cycle_context(user, dataset, today)
    if cycle and cycle.phase == CyclePhase.MENSTRUAL and cycle.cycle_day <= 2:
        reasons.append("You are early in your period.")
    ease_off = bool(reasons)
    bedtime = typical_bedtime(within(dataset.sleep, today, BASELINE_WINDOW))
    if bedtime is None:
        sleep = "Aim for 7 to 9 hours, with a wind down 30 minutes before bed."
    elif ease_off:
        earlier = (datetime.combine(today, bedtime) - EASE_OFF_BEDTIME_SHIFT).time()
        sleep = f"Aim to be in bed by {clock(earlier)}, about 30 minutes earlier than usual."
    else:
        sleep = f"Keep your usual bedtime, around {clock(bedtime)}."
    steady_move, easy_move = MOVE_PLAN[user.gym_access]
    return TodayPlan(
        day=today,
        sleep=sleep,
        move=easy_move if ease_off else steady_move,
        eat=eat_plan(user, ease_off, cycle),
        mind="10 minutes of slow breathing or a quiet walk outside."
        if ease_off
        else "Two minutes to note one thing that went well today.",
        ease_off=ease_off,
        reasons=reasons,
        cycle=cycle,
    )


def self_report_summary(session: Session, user_id: uuid.UUID) -> SelfReportSummary:
    rows = list(
        session.scalars(
            select(SelfReportRow).where(SelfReportRow.user_id == user_id).order_by(SelfReportRow.created_at.desc())
        )
    )
    counts = Counter(LogCategory(row.category) for row in rows)
    return SelfReportSummary(
        counts={category: counts[category] for category in LogCategory},
        recent=[to_log_entry(row) for row in rows[:RECENT_REPORTS]],
    )


def build_record(session: Session, user: User, today: date) -> DoctorRecord:
    dataset = load_dataset(session, user.id)
    insights = compute(dataset)
    show_cycle = user.life_stage in CYCLE_AWARE_STAGES and bool(dataset.periods)
    return DoctorRecord(
        generated_at=datetime.now(),
        patient=user,
        first_day=insights.first_day,
        last_day=insights.last_day,
        lifestyle=lifestyle_averages(dataset, last_observed_day(dataset)),
        self_reports=self_report_summary(session, user.id),
        habits=habit_consistency(session, user.id, today),
        cycle=insights if show_cycle else None,
        note=RECORD_NOTE,
    )
