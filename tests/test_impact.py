from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import date, datetime, time, timedelta

import pytest

from backend.api.impact import (
    habit_impact,
    lever_for,
    outcome_series,
)
from backend.api.schemas import (
    Checkin,
    Habit,
    ImpactStatus,
    Lever,
    OutcomeImpact,
    OutcomeMetric,
)
from backend.canonical.models import Activity, CanonicalDataset, SleepNight, Source

# The spec, written out rather than imported, so changing a threshold in the code fails here.
MIN_DAYS_PER_SIDE = 5
NOTABLE_DIFFERENCE = {
    OutcomeMetric.SLEEP_MIN: 10,
    OutcomeMetric.HRV_MS: 3,
    OutcomeMetric.STEPS: 800,
    OutcomeMetric.READINESS: 3,
}
FIRST_DAY = date(2026, 9, 1)
HABIT_START = FIRST_DAY + timedelta(days=20)
TODAY = HABIT_START + timedelta(days=20)
BASE_SLEEP_MIN = 400
BASE_STEPS = 6000
SLEEP_HABIT = ("Screens off 30 minutes before bed", "sleep better")
MOVE_HABIT = ("A brisk 20 minute walk", "move every day")


def night(day: date, minutes: int) -> SleepNight:
    bedtime = datetime.combine(day - timedelta(days=1), time(23))
    return SleepNight(
        day=day,
        source=Source.OURA,
        bedtime_start=bedtime,
        bedtime_end=bedtime + timedelta(minutes=minutes),
        total_sleep_min=minutes,
        deep_min=0,
        rem_min=0,
        light_min=0,
        awake_min=0,
        efficiency_pct=90,
    )


def activity(day: date, steps: int) -> Activity:
    return Activity(
        day=day,
        source=Source.OURA,
        steps=steps,
        active_kcal=0,
        high_activity_min=0,
        medium_activity_min=0,
        low_activity_min=0,
    )


def days_between(first: date, last: date) -> list[date]:
    return [first + timedelta(days=offset) for offset in range((last - first).days + 1)]


def dataset(sleep_by_day: Mapping[date, int], steps_by_day: Mapping[date, int] | None = None) -> CanonicalDataset:
    return CanonicalDataset(
        user_id="test",
        generated_at=datetime(2026, 11, 6),
        sleep=[night(day, minutes) for day, minutes in sleep_by_day.items()],
        readiness=[],
        activity=[activity(day, steps) for day, steps in (steps_by_day or {}).items()],
        stress=[],
        periods=[],
        cycle=[],
    )


def habit(title: str, goal: str) -> Habit:
    return Habit(id=uuid.uuid4(), title=title, why="", goal=goal, created_on=HABIT_START)


def impact_on(
    metric: OutcomeMetric, title_goal: tuple[str, str], checked: set[date], data: CanonicalDataset
) -> OutcomeImpact:
    result = habit_impact(habit(*title_goal), checked, outcome_series(data, []), TODAY)
    return next(outcome for outcome in result.outcomes if outcome.metric == metric)


ALTERNATE_DAYS = {day for day in days_between(HABIT_START, TODAY) if (day - HABIT_START).days % 2 == 0}


@pytest.mark.parametrize(
    ("bump", "status"),
    [
        (NOTABLE_DIFFERENCE[OutcomeMetric.SLEEP_MIN], ImpactStatus.NOTABLE),
        (NOTABLE_DIFFERENCE[OutcomeMetric.SLEEP_MIN] - 1, ImpactStatus.NO_CLEAR_DIFFERENCE),
        (-3 * NOTABLE_DIFFERENCE[OutcomeMetric.SLEEP_MIN], ImpactStatus.NOTABLE),
    ],
)
def test_sleep_is_compared_on_the_night_after_the_habit(bump: float, status: ImpactStatus) -> None:
    sleep = {
        day: BASE_SLEEP_MIN + int(bump) * (day - timedelta(days=1) in ALTERNATE_DAYS)
        for day in days_between(FIRST_DAY, TODAY)
    }
    outcome = impact_on(OutcomeMetric.SLEEP_MIN, SLEEP_HABIT, ALTERNATE_DAYS, dataset(sleep))
    comparison = outcome.done_vs_not_done
    assert outcome.lag_days == 1
    assert comparison.status == status
    assert comparison.with_habit_mean == BASE_SLEEP_MIN + int(bump)
    assert comparison.without_habit_mean == BASE_SLEEP_MIN
    assert comparison.difference == int(bump)


@pytest.mark.parametrize(
    ("bump", "status"),
    [
        (NOTABLE_DIFFERENCE[OutcomeMetric.STEPS], ImpactStatus.NOTABLE),
        (NOTABLE_DIFFERENCE[OutcomeMetric.STEPS] - 1, ImpactStatus.NO_CLEAR_DIFFERENCE),
    ],
)
def test_steps_are_compared_on_the_same_day(bump: float, status: ImpactStatus) -> None:
    steps = {day: BASE_STEPS + int(bump) * (day in ALTERNATE_DAYS) for day in days_between(FIRST_DAY, TODAY)}
    outcome = impact_on(OutcomeMetric.STEPS, MOVE_HABIT, ALTERNATE_DAYS, dataset({}, steps))
    assert outcome.lag_days == 0
    assert outcome.done_vs_not_done.status == status
    assert outcome.done_vs_not_done.difference == int(bump)


def test_before_versus_after_splits_at_the_first_check() -> None:
    first_check = HABIT_START + timedelta(days=2)
    lift = 2 * int(NOTABLE_DIFFERENCE[OutcomeMetric.SLEEP_MIN])
    sleep = {
        day: BASE_SLEEP_MIN + lift * (day - timedelta(days=1) >= first_check) for day in days_between(FIRST_DAY, TODAY)
    }
    comparison = impact_on(OutcomeMetric.SLEEP_MIN, SLEEP_HABIT, {first_check}, dataset(sleep)).before_vs_after
    assert comparison.status == ImpactStatus.NOTABLE
    assert comparison.difference == lift
    assert comparison.with_habit_days == (TODAY - first_check).days
    assert comparison.without_habit_days == (first_check - FIRST_DAY).days + 1
    assert "moving together, not cause and effect" in comparison.summary
    assert not any(word in comparison.summary.lower() for word in ("because", "improv", "helped", "led to"))


@pytest.mark.parametrize(
    ("checked_days", "status"),
    [(MIN_DAYS_PER_SIDE - 1, ImpactStatus.INSUFFICIENT_DATA), (MIN_DAYS_PER_SIDE, ImpactStatus.NO_CLEAR_DIFFERENCE)],
)
def test_fewer_than_5_days_on_a_side_is_insufficient(checked_days: int, status: ImpactStatus) -> None:
    checked = set(days_between(HABIT_START, HABIT_START + timedelta(days=checked_days - 1)))
    sleep = dict.fromkeys(days_between(FIRST_DAY, TODAY), BASE_SLEEP_MIN)
    comparison = impact_on(OutcomeMetric.SLEEP_MIN, SLEEP_HABIT, checked, dataset(sleep)).done_vs_not_done
    assert comparison.status == status
    assert comparison.with_habit_days == checked_days
    assert (comparison.with_habit_mean is None) == (status == ImpactStatus.INSUFFICIENT_DATA)


def test_self_reported_sleep_counts_when_there_is_no_wearable() -> None:
    hours = 7.5
    checkins = [Checkin(day=day, sleep_hours=hours, energy=3, stress=3) for day in days_between(FIRST_DAY, TODAY)]
    series = outcome_series(dataset({}), checkins)
    assert series[OutcomeMetric.SLEEP_MIN] == dict.fromkeys(days_between(FIRST_DAY, TODAY), hours * 60)


def test_outcomes_report_the_notable_threshold() -> None:
    result = habit_impact(habit(*SLEEP_HABIT), set(), outcome_series(dataset({}), []), TODAY)
    assert {outcome.metric: outcome.notable_difference for outcome in result.outcomes} == {
        metric: NOTABLE_DIFFERENCE[metric]
        for metric in (OutcomeMetric.SLEEP_MIN, OutcomeMetric.HRV_MS, OutcomeMetric.READINESS)
    }


@pytest.mark.parametrize(
    ("title", "goal", "lever"),
    [
        (*SLEEP_HABIT, Lever.SLEEP),
        (*MOVE_HABIT, Lever.MOVEMENT),
        ("Five slow breaths before lunch", "less stress", Lever.STRESS),
        ("Protein with breakfast", "more energy", Lever.NUTRITION),
        ("Message one friend", "better mood", Lever.MOOD),
        ("Something new", "sleep better", Lever.SLEEP),
    ],
)
def test_lever_comes_from_the_habit_then_its_goal(title: str, goal: str, lever: Lever) -> None:
    assert lever_for(title, goal) == lever
