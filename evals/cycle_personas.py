"""Cycle building across women whose cycles, bodies, and logging habits differ from Maya's.

Each persona plants a known cycle: the periods she actually had, the ones she
logged (maybe late, maybe not at all), and nightly temperature. build_cycle sees
only the logs and the temperature; we score phases and ovulation against the plant.

    .venv/bin/python -m evals.cycle_personas
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from backend.canonical.cycle import build_cycle
from backend.canonical.models import CycleDay, CyclePhase, Flow, PeriodLog, Readiness, Source

DAYS = 90
END = date(2026, 11, 6)
SEEDS = range(10)
LUTEAL_LENGTH = 14
FOLLICULAR_TEMP_C = -0.08
# Mirrors startsFromTemperature in web/index.html, the app's estimate when no period is logged.
ESTIMATE_MIN_SPREAD_C = 0.15
ESTIMATE_MIN_NIGHTS = 20
ESTIMATE_MIN_WARM_NIGHTS = 8
START_TOLERANCE = timedelta(days=1)
MIN_LUTEAL_NIGHTS_SEEN = 5


@dataclass(frozen=True)
class CyclePersona:
    name: str
    cycle_lengths: Sequence[int]
    ovulates: bool = True
    luteal_temp_c: float = 0.32
    noise_sd_c: float = 0.06
    missing_night_rate: float = 0.0
    skipped_log_rate: float = 0.0
    log_delay: timedelta = timedelta(0)
    max_logged_periods: int | None = None
    known_limit: str | None = None
    """Why this persona can't pass from data alone; reported, not gated."""
    min_phase_accuracy: float = 0.85
    min_ovulation_recall: float = 0.9


PERSONAS: tuple[CyclePersona, ...] = (
    CyclePersona("maya (29d, demo)", [29] * 5),
    CyclePersona("short-regular (25d)", [25] * 5),
    CyclePersona("long-regular (35d)", [35] * 4),
    CyclePersona("pcos (35 to 45d)", [38, 45, 35, 42]),
    CyclePersona("perimenopause", [24, 45, 30, 26], luteal_temp_c=0.22),
    CyclePersona("noisy-sensor", [29] * 5, noise_sd_c=0.12),
    CyclePersona("forgets-ring", [29] * 5, missing_night_rate=0.2),
    CyclePersona(
        "forgets-to-log", [29] * 5, skipped_log_rate=0.33,
        known_limit="with 2 or 3 gaps in 90 days, a missed log looks like real variation",
    ),
    CyclePersona(
        "logs-2-days-late", [29] * 5, log_delay=timedelta(days=2),
        known_limit="phases follow the logged day; the tracker UI lets her backdate",
    ),
    CyclePersona("single-logged-period", [29] * 5, max_logged_periods=1),
    CyclePersona("on-the-pill", [28] * 5, ovulates=False, luteal_temp_c=FOLLICULAR_TEMP_C),
)


def true_phase(cycle_day: int, cycle_length: int) -> CyclePhase:
    ovulation_day = cycle_length - LUTEAL_LENGTH
    if cycle_day <= 5:
        return CyclePhase.MENSTRUAL
    if cycle_day < ovulation_day - 1:
        return CyclePhase.FOLLICULAR
    if cycle_day <= ovulation_day + 1:
        return CyclePhase.OVULATORY
    return CyclePhase.LUTEAL


@dataclass(frozen=True)
class PlantedNight:
    day: date
    cycle_day: int
    cycle_length: int


@dataclass(frozen=True)
class PersonaScore:
    persona: CyclePersona
    phase_accuracy: float | None
    """Days up to the last logged period, which the logs fully determine."""
    predicted_accuracy: float | None
    """Days after the last log, wrapped onto her typical length; reported, not gated."""
    ovulation_recall: float | None
    false_ovulations: int
    crashed: str | None = None

    @property
    def passed(self) -> bool:
        if self.crashed:
            return False
        if not self.persona.ovulates:
            return self.false_ovulations == 0
        return (
            (self.phase_accuracy if self.phase_accuracy is not None else 1.0) >= self.persona.min_phase_accuracy
            and (self.ovulation_recall or 0) >= self.persona.min_ovulation_recall
        )


def plant(persona: CyclePersona, rng: random.Random) -> list[PlantedNight]:
    """Cycles back to back, entering the first partway through so day 1 of the window isn't a period."""
    lengths = list(persona.cycle_lengths) * 3
    nights: list[PlantedNight] = []
    day = END - timedelta(days=DAYS - 1)
    first_cycle_day = rng.randrange(lengths[0]) + 1
    for cycle_length in lengths:
        for cycle_day in range(first_cycle_day, cycle_length + 1):
            if len(nights) == DAYS:
                return nights
            nights.append(PlantedNight(day, cycle_day, cycle_length))
            day += timedelta(days=1)
        first_cycle_day = 1
    return nights


def temperature(night: PlantedNight, persona: CyclePersona, rng: random.Random) -> float:
    in_luteal = night.cycle_day > night.cycle_length - LUTEAL_LENGTH
    baseline = persona.luteal_temp_c if in_luteal else FOLLICULAR_TEMP_C
    return round(baseline + rng.gauss(0, persona.noise_sd_c), 2)


def readiness_rows(nights: Sequence[PlantedNight], persona: CyclePersona, rng: random.Random) -> list[Readiness]:
    return [
        Readiness(day=night.day, source=Source.OURA, score=75, temperature_deviation_c=temperature(night, persona, rng))
        for night in nights
        if rng.random() >= persona.missing_night_rate
    ]


def period_logs(nights: Sequence[PlantedNight], persona: CyclePersona, rng: random.Random) -> list[PeriodLog]:
    logs = [
        PeriodLog(start_day=night.day + persona.log_delay, flow=Flow.MEDIUM)
        for night in nights
        if night.cycle_day == 1 and rng.random() >= persona.skipped_log_rate
    ]
    return logs[: persona.max_logged_periods]


def starts_from_temperature(readiness: Sequence[Readiness]) -> list[PeriodLog]:
    """After 8+ warm nights, a period starts on the first of two cool nights in a row.

    Warm means above the midpoint of her own cool and warm levels (25th and 75th
    percentile); too little spread between them means no shift to find.
    """
    ordered = sorted(
        (row for row in readiness if row.temperature_deviation_c is not None), key=lambda reading: reading.day
    )
    temperatures = sorted(row.temperature_deviation_c for row in ordered if row.temperature_deviation_c is not None)
    if len(temperatures) < ESTIMATE_MIN_NIGHTS:
        return []
    cool_level, warm_level = temperatures[len(temperatures) // 4], temperatures[3 * len(temperatures) // 4]
    if warm_level - cool_level < ESTIMATE_MIN_SPREAD_C:
        return []
    warm_at = (cool_level + warm_level) / 2

    starts: list[PeriodLog] = []
    warm_nights = 0
    first_cool_day: date | None = None
    for row in ordered:
        if (row.temperature_deviation_c or 0) >= warm_at:
            warm_nights += 1
            first_cool_day = None
        elif warm_nights >= ESTIMATE_MIN_WARM_NIGHTS and first_cool_day is not None:
            starts.append(PeriodLog(start_day=first_cool_day, flow=Flow.MEDIUM))
            warm_nights, first_cool_day = 0, None
        elif warm_nights >= ESTIMATE_MIN_WARM_NIGHTS:
            first_cool_day = row.day
        else:
            warm_nights = 0
    return starts


@dataclass(frozen=True)
class EstimateScore:
    persona: CyclePersona
    coverage: float
    phase_accuracy: float | None
    start_recall: float | None
    false_starts: int

    @property
    def passed(self) -> bool:
        if not self.persona.ovulates:
            return self.false_starts == 0
        return (
            (self.phase_accuracy or 0) >= self.persona.min_phase_accuracy
            and (self.start_recall if self.start_recall is not None else 1.0) >= 0.66
            and self.false_starts == 0
        )


def score_estimate(persona: CyclePersona, seed: int) -> EstimateScore:
    """No period logged: starts estimated from Oura temperature, then phased by build_cycle."""
    rng = random.Random(seed)
    nights = plant(persona, rng)
    truth = {night.day: night for night in nights}
    readiness = readiness_rows(nights, persona, rng)
    estimated = starts_from_temperature(readiness)
    cycle = build_cycle(estimated, readiness)

    true_starts = [night.day for night in nights if night.cycle_day == 1]
    # A start needs 8 warm nights on record before it, so one in the first ~3 weeks can't be found.
    findable = [day for day in true_starts if (day - nights[0].day).days > ESTIMATE_MIN_WARM_NIGHTS + LUTEAL_LENGTH // 2]

    def near(day: date, candidates: Sequence[date]) -> bool:
        return any(abs(day - other) <= START_TOLERANCE for other in candidates)

    estimated_days = [log.start_day for log in estimated]
    correct = sum(row.phase == true_phase(truth[row.day].cycle_day, truth[row.day].cycle_length) for row in cycle)
    return EstimateScore(
        persona=persona,
        coverage=len(cycle) / len(nights),
        phase_accuracy=correct / len(cycle) if cycle else None,
        start_recall=sum(near(day, estimated_days) for day in findable) / len(findable) if findable else None,
        false_starts=sum(not near(day, true_starts) for day in estimated_days),
    )


def score(persona: CyclePersona, seed: int) -> PersonaScore:
    rng = random.Random(seed)
    nights = plant(persona, rng)
    truth = {night.day: night for night in nights}
    try:
        logs = period_logs(nights, persona, rng)
        cycle: list[CycleDay] = build_cycle(logs, readiness_rows(nights, persona, rng))
    except Exception as error:  # a crash is a finding, not a reason to stop the run
        return PersonaScore(persona, None, None, None, 0, crashed=f"{type(error).__name__}: {error}")

    def accuracy(rows: Sequence[CycleDay]) -> float | None:
        correct = sum(row.phase == true_phase(truth[row.day].cycle_day, truth[row.day].cycle_length) for row in rows)
        return correct / len(rows) if rows else None

    last_logged_start = max((log.start_day for log in logs), default=END)
    # A planted cycle counts once build_cycle has seen enough of its luteal phase; it is
    # recalled if ovulation was confirmed on any of its days. A pill cycle never should be.
    def cycle_start(night: PlantedNight) -> date:
        return night.day - timedelta(days=night.cycle_day - 1)

    covered_days = {row.day for row in cycle}
    luteal_nights_seen: dict[date, int] = {}
    for night in nights:
        if night.cycle_day > night.cycle_length - LUTEAL_LENGTH and night.day in covered_days:
            luteal_nights_seen[cycle_start(night)] = luteal_nights_seen.get(cycle_start(night), 0) + 1
    covered_cycles = {start for start, seen in luteal_nights_seen.items() if seen >= MIN_LUTEAL_NIGHTS_SEEN}
    confirmed_cycles = {cycle_start(truth[row.day]) for row in cycle if row.ovulation_confirmed}
    return PersonaScore(
        persona=persona,
        phase_accuracy=accuracy([row for row in cycle if row.day < last_logged_start]),
        predicted_accuracy=accuracy([row for row in cycle if row.day >= last_logged_start]),
        ovulation_recall=(
            len(covered_cycles & confirmed_cycles) / len(covered_cycles)
            if covered_cycles and persona.ovulates
            else None
        ),
        false_ovulations=0 if persona.ovulates else sum(row.ovulation_confirmed for row in cycle),
    )


def percent(values: Sequence[float | None]) -> str:
    present = [value for value in values if value is not None]
    return f"{sum(present) / len(present):.0%}" if present else "n/a"


def main() -> int:
    any_failed = False
    print(f"{'persona':<22} {'pass':>5} {'logged':>7} {'predicted':>9} {'ovulation':>9} {'false ov':>8}")
    for persona in PERSONAS:
        scores = [score(persona, seed) for seed in SEEDS]
        passed = sum(result.passed for result in scores)
        any_failed |= passed < len(scores) and persona.known_limit is None
        print(
            f"{persona.name:<22} {passed:>2}/{len(scores):<2} "
            f"{percent([result.phase_accuracy for result in scores]):>7} "
            f"{percent([result.predicted_accuracy for result in scores]):>9} "
            f"{percent([result.ovulation_recall for result in scores]):>9} "
            f"{sum(result.false_ovulations for result in scores):>8}"
            + (f"   limit: {persona.known_limit}" if persona.known_limit else "")
        )
        for crash in {result.crashed for result in scores if result.crashed}:
            print(f"    CRASH {crash}")

    body_personas = [persona for persona in PERSONAS if persona.max_logged_periods is None and not persona.skipped_log_rate and not persona.log_delay]
    print("\nno period logged, Oura only (estimate; reported, not gated)")
    print(f"{'persona':<22} {'pass':>5} {'coverage':>8} {'phase acc':>9} {'start recall':>12} {'false starts':>12}")
    for persona in body_personas:
        estimates = [score_estimate(persona, seed) for seed in SEEDS]
        print(
            f"{persona.name:<22} {sum(result.passed for result in estimates):>2}/{len(estimates):<2} "
            f"{percent([result.coverage for result in estimates]):>8} "
            f"{percent([result.phase_accuracy for result in estimates]):>9} "
            f"{percent([result.start_recall for result in estimates]):>12} "
            f"{sum(result.false_starts for result in estimates):>12}"
        )
    return 1 if any_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
