"""The doctor record's numbers: her lifestyle trends first, then how her body moves with her cycle.

Reads only canonical models. Every field is None (never 0) when there isn't
enough data, so the app can say "not enough data yet" instead of a false zero.

    .venv/bin/python -m backend.insights      # reads web/seed.json, writes data/canonical/record.json
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Literal
from statistics import linear_regression, mean, quantiles

from pydantic import BaseModel

from backend.canonical.models import Activity, CanonicalDataset, CycleDay, CyclePhase, PeriodLog, SleepNight, Stress

ROOT = Path(__file__).resolve().parents[1]
SEED_PATH = ROOT / "web" / "seed.json"
RECORD_PATH = ROOT / "data" / "canonical" / "record.json"

PRE_PERIOD_WINDOW = timedelta(days=5)
# Cycles whose lengths spread by at most this much are commonly described as regular.
REGULAR_SPREAD = timedelta(days=7)
# The 90-day window starts and ends mid-week; thinner weeks are shown but kept out of the slope.
MIN_DAYS_FOR_TREND_WEEK = 4
MIN_NIGHTS_PER_WEEKDAY = 2
RECENT_WEEKS = 4
NOTABLE_SLEEP_MIN = 15.0
"""Sleep differences, and sleep slopes per week, at least this large are worth saying out loud."""
NOTABLE_STEPS_PER_WEEK = 750.0
"""Over 4 weeks that is about 3,000 fewer steps a day, roughly 40% of a typical baseline."""
NOTABLE_HRV_MS = 3.0
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


class WeeklyPoint(BaseModel):
    iso_week: str
    week_start: date
    days: int
    sleep_min: float | None
    steps: float | None
    hrv_ms: float | None
    stress_high_min: float | None


SlopeMetric = Literal["sleep_min", "steps", "hrv_ms"]


class WeeklySlopes(BaseModel):
    """Change per week from a straight-line fit; positive means rising."""

    weeks_used: int
    notable: list[SlopeMetric]
    sleep_min: float | None
    steps: float | None
    hrv_ms: float | None
    stress_high_min: float | None


class WeekdaySleep(BaseModel):
    weekday: str
    """The evening she went to bed, so "Sunday" is Sunday night."""
    nights: int
    sleep_min: float


class HeavyDayEffect(BaseModel):
    """Sleep the night after a high-stress day versus after any other day."""

    stress_threshold_min: float | None
    heavy_days: int
    sleep_after_heavy_min: float | None
    sleep_after_other_min: float | None
    difference_min: float | None
    """Positive means she sleeps less after heavy days."""
    is_notable: bool


class LifestyleInsights(BaseModel):
    weekly: list[WeeklyPoint]
    weekly_slopes: WeeklySlopes
    recent_slopes: WeeklySlopes
    """The same fit over only the last few full weeks, where a new habit or a slide shows up."""
    best_sleep_weekday: WeekdaySleep | None
    worst_sleep_weekday: WeekdaySleep | None
    sleep_weekday_gap_min: float | None
    sleep_weekday_gap_is_notable: bool
    heavy_day: HeavyDayEffect


class PhaseStats(BaseModel):
    phase: CyclePhase
    nights: int
    sleep_min: float | None
    hrv_ms: float | None
    readiness_score: float | None
    stress_high_min: float | None


class PrePeriodSleep(BaseModel):
    window_days: int
    periods_counted: int
    pre_period_sleep_min: float | None
    other_nights_sleep_min: float | None
    drop_min: float | None
    """Positive means she sleeps less in the days before her period."""
    is_notable: bool


class CycleRegularity(BaseModel):
    logged_period_starts: list[date]
    cycle_lengths_days: list[int]
    mean_length_days: float | None
    length_spread_days: int | None
    is_regular: bool | None


class OvulationConfirmation(BaseModel):
    completed_cycles: int
    confirmed_cycles: int
    confirmed_rate: float | None


class RecordInsights(BaseModel):
    generated_at: datetime
    first_day: date | None
    last_day: date | None
    lifestyle: LifestyleInsights
    by_phase: list[PhaseStats]
    pre_period_sleep: PrePeriodSleep
    regularity: CycleRegularity
    ovulation: OvulationConfirmation


def rounded_mean(values: Iterable[float | int | None]) -> float | None:
    present = [value for value in values if value is not None]
    return round(mean(present), 1) if present else None


def difference(baseline: float | None, compared: float | None) -> float | None:
    return round(baseline - compared, 1) if baseline is not None and compared is not None else None


def is_notable(value: float | None, threshold: float) -> bool:
    return value is not None and abs(value) >= threshold


def week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def weekly_points(dataset: CanonicalDataset) -> list[WeeklyPoint]:
    weeks = sorted(
        {week_start(row.day) for rows in (dataset.sleep, dataset.activity, dataset.stress) for row in rows}
    )

    def in_week[Row: (SleepNight, Activity, Stress)](rows: Iterable[Row], start: date) -> list[Row]:
        return [row for row in rows if week_start(row.day) == start]

    points: list[WeeklyPoint] = []
    for start in weeks:
        sleep, activity, stress = in_week(dataset.sleep, start), in_week(dataset.activity, start), in_week(dataset.stress, start)
        iso_year, iso_week, _ = start.isocalendar()
        points.append(
            WeeklyPoint(
                iso_week=f"{iso_year}-W{iso_week:02d}",
                week_start=start,
                days=len({row.day for row in [*sleep, *activity, *stress]}),
                sleep_min=rounded_mean(night.total_sleep_min for night in sleep),
                steps=rounded_mean(row.steps for row in activity),
                hrv_ms=rounded_mean(night.avg_hrv_ms for night in sleep),
                stress_high_min=rounded_mean(row.stress_high_min for row in stress),
            )
        )
    return points


def weekly_slopes(points: Sequence[WeeklyPoint], last_weeks: int | None = None) -> WeeklySlopes:
    full_weeks = [point for point in points if point.days >= MIN_DAYS_FOR_TREND_WEEK]
    if last_weeks is not None:
        full_weeks = full_weeks[-last_weeks:]

    def slope(values: Sequence[float | None]) -> float | None:
        pairs = [
            ((point.week_start - full_weeks[0].week_start).days / 7, value)
            for point, value in zip(full_weeks, values)
            if value is not None
        ]
        if len(pairs) < 2:
            return None
        weeks, measured = zip(*pairs)
        return round(linear_regression(weeks, measured).slope, 1)

    sleep_min = slope([point.sleep_min for point in full_weeks])
    steps = slope([point.steps for point in full_weeks])
    hrv_ms = slope([point.hrv_ms for point in full_weeks])
    thresholds: dict[SlopeMetric, tuple[float | None, float]] = {
        "sleep_min": (sleep_min, NOTABLE_SLEEP_MIN),
        "steps": (steps, NOTABLE_STEPS_PER_WEEK),
        "hrv_ms": (hrv_ms, NOTABLE_HRV_MS),
    }
    return WeeklySlopes(
        weeks_used=len(full_weeks),
        notable=[metric for metric, (value, threshold) in thresholds.items() if is_notable(value, threshold)],
        sleep_min=sleep_min,
        steps=steps,
        hrv_ms=hrv_ms,
        stress_high_min=slope([point.stress_high_min for point in full_weeks]),
    )


def sleep_by_weekday(sleep: Sequence[SleepNight]) -> list[WeekdaySleep]:
    by_evening: dict[int, list[int]] = {}
    for night in sleep:
        by_evening.setdefault((night.day - timedelta(days=1)).weekday(), []).append(night.total_sleep_min)
    return [
        WeekdaySleep(weekday=WEEKDAYS[weekday], nights=len(minutes), sleep_min=round(mean(minutes), 1))
        for weekday, minutes in sorted(by_evening.items())
        if len(minutes) >= MIN_NIGHTS_PER_WEEKDAY
    ]


def heavy_day_effect(dataset: CanonicalDataset) -> HeavyDayEffect:
    stress_minutes = [row.stress_high_min for row in dataset.stress]
    if len(stress_minutes) < 4:
        return HeavyDayEffect(
            stress_threshold_min=None, heavy_days=0, sleep_after_heavy_min=None,
            sleep_after_other_min=None, difference_min=None, is_notable=False,
        )
    threshold = quantiles(stress_minutes, n=4)[2]
    heavy_days = {row.day for row in dataset.stress if row.stress_high_min > threshold}
    # SleepNight.day is the morning she woke, so the night after day D is keyed D + 1.
    after_heavy = [night.total_sleep_min for night in dataset.sleep if night.day - timedelta(days=1) in heavy_days]
    after_other = [night.total_sleep_min for night in dataset.sleep if night.day - timedelta(days=1) not in heavy_days]
    heavy_mean, other_mean = rounded_mean(after_heavy), rounded_mean(after_other)
    effect = difference(other_mean, heavy_mean)
    return HeavyDayEffect(
        stress_threshold_min=round(threshold, 1),
        heavy_days=len(heavy_days),
        sleep_after_heavy_min=heavy_mean,
        sleep_after_other_min=other_mean,
        difference_min=effect,
        is_notable=is_notable(effect, NOTABLE_SLEEP_MIN),
    )


def lifestyle(dataset: CanonicalDataset) -> LifestyleInsights:
    points = weekly_points(dataset)
    weekdays = sleep_by_weekday(dataset.sleep)
    best = max(weekdays, key=lambda weekday: weekday.sleep_min, default=None)
    worst = min(weekdays, key=lambda weekday: weekday.sleep_min, default=None)
    gap = round(best.sleep_min - worst.sleep_min, 1) if best and worst else None
    return LifestyleInsights(
        weekly=points,
        weekly_slopes=weekly_slopes(points),
        recent_slopes=weekly_slopes(points, last_weeks=RECENT_WEEKS),
        best_sleep_weekday=best,
        worst_sleep_weekday=worst,
        sleep_weekday_gap_min=gap,
        sleep_weekday_gap_is_notable=is_notable(gap, NOTABLE_SLEEP_MIN),
        heavy_day=heavy_day_effect(dataset),
    )


def period_starts(periods: Iterable[PeriodLog]) -> list[date]:
    return sorted({period.start_day for period in periods})


def phase_stats(dataset: CanonicalDataset, phase_by_day: Mapping[date, CyclePhase]) -> list[PhaseStats]:
    stats: list[PhaseStats] = []
    for phase in CyclePhase:
        sleep = [night for night in dataset.sleep if phase_by_day.get(night.day) == phase]
        stats.append(
            PhaseStats(
                phase=phase,
                nights=len({night.day for night in sleep}),
                sleep_min=rounded_mean(night.total_sleep_min for night in sleep),
                hrv_ms=rounded_mean(night.avg_hrv_ms for night in sleep),
                readiness_score=rounded_mean(
                    row.score for row in dataset.readiness if phase_by_day.get(row.day) == phase
                ),
                stress_high_min=rounded_mean(
                    row.stress_high_min for row in dataset.stress if phase_by_day.get(row.day) == phase
                ),
            )
        )
    return stats


def pre_period_sleep(dataset: CanonicalDataset, starts: Sequence[date]) -> PrePeriodSleep:
    def window_before(start: date) -> set[date]:
        return {start - timedelta(days=offset) for offset in range(1, PRE_PERIOD_WINDOW.days + 1)}

    sleep_days = {night.day for night in dataset.sleep}
    pre_period_days = set().union(*map(window_before, starts))
    before = [night.total_sleep_min for night in dataset.sleep if night.day in pre_period_days]
    other = [night.total_sleep_min for night in dataset.sleep if night.day not in pre_period_days]
    before_mean, other_mean = rounded_mean(before), rounded_mean(other)
    drop = difference(other_mean, before_mean)
    return PrePeriodSleep(
        window_days=PRE_PERIOD_WINDOW.days,
        periods_counted=sum(bool(window_before(start) & sleep_days) for start in starts),
        pre_period_sleep_min=before_mean,
        other_nights_sleep_min=other_mean,
        drop_min=drop,
        is_notable=is_notable(drop, NOTABLE_SLEEP_MIN),
    )


def regularity(starts: Sequence[date]) -> CycleRegularity:
    lengths = [(later - earlier).days for earlier, later in zip(starts, starts[1:])]
    spread = max(lengths) - min(lengths) if len(lengths) >= 2 else None
    return CycleRegularity(
        logged_period_starts=list(starts),
        cycle_lengths_days=lengths,
        mean_length_days=rounded_mean(lengths),
        length_spread_days=spread,
        is_regular=spread <= REGULAR_SPREAD.days if spread is not None else None,
    )


def ovulation(cycle: Sequence[CycleDay], starts: Sequence[date]) -> OvulationConfirmation:
    completed = list(zip(starts, starts[1:]))
    confirmed = sum(
        any(row.ovulation_confirmed and start <= row.day < next_start for row in cycle)
        for start, next_start in completed
    )
    return OvulationConfirmation(
        completed_cycles=len(completed),
        confirmed_cycles=confirmed,
        confirmed_rate=round(confirmed / len(completed), 2) if completed else None,
    )


def compute(dataset: CanonicalDataset) -> RecordInsights:
    phase_by_day = {row.day: row.phase for row in dataset.cycle}
    starts = period_starts(dataset.periods)
    observed_days = sorted({night.day for night in dataset.sleep} | {row.day for row in dataset.readiness})
    return RecordInsights(
        generated_at=datetime.now(),
        first_day=observed_days[0] if observed_days else None,
        last_day=observed_days[-1] if observed_days else None,
        lifestyle=lifestyle(dataset),
        by_phase=phase_stats(dataset, phase_by_day),
        pre_period_sleep=pre_period_sleep(dataset, starts),
        regularity=regularity(starts),
        ovulation=ovulation(dataset.cycle, starts),
    )


def main() -> None:
    insights = compute(CanonicalDataset.model_validate_json(SEED_PATH.read_text()))
    RECORD_PATH.parent.mkdir(parents=True, exist_ok=True)
    RECORD_PATH.write_text(insights.model_dump_json(indent=1))
    print(insights.model_dump_json(indent=1))


if __name__ == "__main__":
    main()
