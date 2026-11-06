"""Habit impact: how her outcomes look on days she did a habit against days she didn't.

Everything here is association. A habit checked on good days may simply be
easier on good days, so the summaries describe things moving together and never
say the habit changed anything.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date, timedelta
from statistics import fmean

from backend.api.schemas import (
    Checkin,
    Comparison,
    Habit,
    HabitImpact,
    ImpactStatus,
    Lever,
    OutcomeImpact,
    OutcomeMetric,
)
from backend.canonical.models import CanonicalDataset

MIN_DAYS_PER_SIDE = 5
NOTABLE_DIFFERENCE: dict[OutcomeMetric, float] = {
    OutcomeMetric.SLEEP_MIN: 10.0,
    OutcomeMetric.HRV_MS: 3.0,
    OutcomeMetric.STEPS: 800.0,
    OutcomeMetric.READINESS: 3.0,
}
# Sleep rows are dated by the morning she woke, so a habit done on day D shows up
# in the night stamped D + 1. HRV is measured during that same night, and the
# readiness score is computed from it the next morning.
OUTCOME_LAG: dict[OutcomeMetric, timedelta] = {
    OutcomeMetric.SLEEP_MIN: timedelta(days=1),
    OutcomeMetric.HRV_MS: timedelta(days=1),
    OutcomeMetric.READINESS: timedelta(days=1),
    OutcomeMetric.STEPS: timedelta(0),
}
OUTCOME_WORDS: dict[OutcomeMetric, tuple[str, str]] = {
    OutcomeMetric.SLEEP_MIN: ("sleep the next night", "min"),
    OutcomeMetric.HRV_MS: ("HRV the next night", "ms"),
    OutcomeMetric.READINESS: ("readiness the next morning", "points"),
    OutcomeMetric.STEPS: ("steps that day", "steps"),
}
LEVER_OUTCOMES: dict[Lever, tuple[OutcomeMetric, ...]] = {
    Lever.SLEEP: (OutcomeMetric.SLEEP_MIN, OutcomeMetric.HRV_MS, OutcomeMetric.READINESS),
    Lever.MOVEMENT: (OutcomeMetric.STEPS, OutcomeMetric.READINESS),
    Lever.STRESS: (OutcomeMetric.HRV_MS, OutcomeMetric.SLEEP_MIN, OutcomeMetric.READINESS),
    Lever.NUTRITION: (OutcomeMetric.READINESS, OutcomeMetric.SLEEP_MIN),
    Lever.MOOD: (OutcomeMetric.READINESS, OutcomeMetric.SLEEP_MIN),
}
# Ordered: the habit's own words decide before its goal does, and sleep words
# come first because "wake" and "bed" also turn up in movement habits' cues.
LEVER_WORDS: tuple[tuple[Lever, tuple[str, ...]], ...] = (
    (Lever.SLEEP, ("sleep", "bed", "screens off", "lights out", "wake", "waking", "rest")),
    (Lever.MOVEMENT, ("walk", "strength", "stretch", "steps", "gym", "yoga", "workout", "run", "move", "fit")),
    (Lever.STRESS, ("breath", "stress", "calm", "phone", "meditat", "anxi", "burnout")),
    (Lever.NUTRITION, ("protein", "water", "vegetable", "meal", "breakfast", "lunch", "dinner", "eat", "energy")),
    (Lever.MOOD, ("mood", "friend", "write", "journal", "happy")),
)
INSUFFICIENT_SUMMARY = f"Not enough days yet to compare. Bloom needs at least {MIN_DAYS_PER_SIDE} days on each side."

type OutcomeSeries = Mapping[OutcomeMetric, Mapping[date, float]]


def lever_for(title: str, goal: str) -> Lever:
    for text in (title.lower(), goal.lower()):
        for lever, words in LEVER_WORDS:
            if any(word in text for word in words):
                return lever
    return Lever.MOOD


def outcome_series(dataset: CanonicalDataset, checkins: Iterable[Checkin]) -> dict[OutcomeMetric, dict[date, float]]:
    """Daily outcomes from the wearable, with self-reported sleep filling nights the wearable missed."""
    sleep = {checkin.day: checkin.sleep_hours * 60 for checkin in checkins}
    sleep |= {night.day: float(night.total_sleep_min) for night in dataset.sleep}
    return {
        OutcomeMetric.SLEEP_MIN: sleep,
        OutcomeMetric.HRV_MS: {night.day: night.avg_hrv_ms for night in dataset.sleep if night.avg_hrv_ms is not None},
        OutcomeMetric.READINESS: {row.day: float(row.score) for row in dataset.readiness},
        OutcomeMetric.STEPS: {row.day: float(row.steps) for row in dataset.activity},
    }


def describe_difference(metric: OutcomeMetric, difference: float, with_label: str, without_label: str) -> str:
    noun, unit = OUTCOME_WORDS[metric]
    direction = "higher" if difference > 0 else "lower"
    amount = f"{abs(difference):,.0f}" if metric == OutcomeMetric.STEPS else f"{abs(difference):g}"
    return (
        f"Your {noun} ran {amount} {unit} {direction} {with_label} than {without_label}. "
        "This shows the two moving together, not cause and effect."
    )


def compare(
    metric: OutcomeMetric, with_habit: list[float], without_habit: list[float], with_label: str, without_label: str
) -> Comparison:
    if min(len(with_habit), len(without_habit)) < MIN_DAYS_PER_SIDE:
        return Comparison(
            status=ImpactStatus.INSUFFICIENT_DATA,
            with_habit_days=len(with_habit),
            without_habit_days=len(without_habit),
            with_habit_mean=None,
            without_habit_mean=None,
            difference=None,
            summary=INSUFFICIENT_SUMMARY,
        )
    with_mean, without_mean = round(fmean(with_habit), 1), round(fmean(without_habit), 1)
    difference = round(with_mean - without_mean, 1)
    notable = abs(difference) >= NOTABLE_DIFFERENCE[metric]
    return Comparison(
        status=ImpactStatus.NOTABLE if notable else ImpactStatus.NO_CLEAR_DIFFERENCE,
        with_habit_days=len(with_habit),
        without_habit_days=len(without_habit),
        with_habit_mean=with_mean,
        without_habit_mean=without_mean,
        difference=difference,
        summary=describe_difference(metric, difference, with_label, without_label)
        if notable
        else f"No clear difference in your {OUTCOME_WORDS[metric][0]} yet.",
    )


def outcome_impact(
    metric: OutcomeMetric, created_on: date, checked: set[date], series: Mapping[date, float], today: date
) -> OutcomeImpact:
    lag = OUTCOME_LAG[metric]
    outcomes_by_action_day = {day - lag: value for day, value in series.items() if day - lag <= today}

    done = [value for day, value in outcomes_by_action_day.items() if day >= created_on and day in checked]
    not_done = [value for day, value in outcomes_by_action_day.items() if day >= created_on and day not in checked]
    first_check = min(checked, default=None)
    after = [value for day, value in outcomes_by_action_day.items() if first_check is not None and day >= first_check]
    before = [value for day, value in outcomes_by_action_day.items() if first_check is not None and day < first_check]
    return OutcomeImpact(
        metric=metric,
        lag_days=lag.days,
        notable_difference=NOTABLE_DIFFERENCE[metric],
        done_vs_not_done=compare(metric, done, not_done, "on days you did it", "on days you didn't"),
        before_vs_after=compare(metric, after, before, "since you started", "before"),
    )


def habit_impact(habit: Habit, checked: set[date], series: OutcomeSeries, today: date) -> HabitImpact:
    lever = lever_for(habit.title, habit.goal)
    return HabitImpact(
        habit_id=habit.id,
        title=habit.title,
        goal=habit.goal,
        lever=lever,
        first_check=min(checked, default=None),
        outcomes=[
            outcome_impact(metric, habit.created_on, checked, series[metric], today)
            for metric in LEVER_OUTCOMES[lever]
        ],
    )
