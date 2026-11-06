"""Build the canonical cycle from self-reported period logs.

The logged period starts define cycle day and phase. Wearable temperature never
moves a period start; it only confirms that ovulation happened, using the
classic sustained-rise rule: once the nightly deviation stays at or above the
luteal threshold for several nights in a row, ovulation is behind her.

A cycle with a logged next start uses its own length, so ovulation sits 14 days
before the next period even when cycles vary (PCOS, perimenopause). Past the
last log, and inside a gap so long it must hide an unlogged period, days wrap
onto predicted cycles of her typical length, matching `currentCd` in the app.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from statistics import median

from backend.canonical.models import CycleDay, CyclePhase, PeriodLog, Readiness, Source

DEFAULT_CYCLE_LENGTH = 28
DEFAULT_PERIOD_LENGTH = timedelta(days=5)
LUTEAL_TEMP_RISE_C = 0.18
SUSTAINED_RISE_NIGHTS = 3
# A gap this many times her median cycle almost certainly hides a period she didn't log.
# 1.75 rather than 1.6: perimenopausal cycles of 24 then 45 days are real, a missed log is about 2x.
MISSED_LOG_GAP_RATIO = 1.75


def _phase_for(cycle_day: int, cycle_length: int) -> CyclePhase:
    """Mirrors `phaseOf` in web/index.html; keep the two in lockstep."""
    ovulation_day = cycle_length - 14
    if cycle_day <= 5:
        return CyclePhase.MENSTRUAL
    if cycle_day < ovulation_day - 1:
        return CyclePhase.FOLLICULAR
    if cycle_day <= ovulation_day + 1:
        return CyclePhase.OVULATORY
    return CyclePhase.LUTEAL


def _gaps(starts: Sequence[date]) -> list[int]:
    return [(later - earlier).days for earlier, later in zip(starts, starts[1:])]


def _is_missed_log_gap(gap: int, typical_gaps: Sequence[int]) -> bool:
    return bool(typical_gaps) and gap > MISSED_LOG_GAP_RATIO * median(typical_gaps)


def _typical_length(starts: Sequence[date]) -> int:
    gaps = _gaps(starts)
    kept = [gap for gap in gaps if not _is_missed_log_gap(gap, gaps)]
    return round(sum(kept) / len(kept)) if kept else DEFAULT_CYCLE_LENGTH


def _period_end(log: PeriodLog) -> date:
    return log.end_day or log.start_day + DEFAULT_PERIOD_LENGTH - timedelta(days=1)


@dataclass(frozen=True)
class _CycleSpan:
    start: date
    length: int
    logged: PeriodLog | None
    """The period log that opened this cycle; None for a predicted cycle."""


def _span_for(day: date, logs: Sequence[PeriodLog], typical_length: int) -> _CycleSpan | None:
    index = next((i for i in reversed(range(len(logs))) if logs[i].start_day <= day), None)
    if index is None:
        return None
    log = logs[index]
    if index + 1 < len(logs):
        own_length = (logs[index + 1].start_day - log.start_day).days
        if not _is_missed_log_gap(own_length, _gaps([entry.start_day for entry in logs])):
            return _CycleSpan(log.start_day, own_length, log)
    laps = (day - log.start_day).days // typical_length
    if laps == 0:
        return _CycleSpan(log.start_day, typical_length, log)
    return _CycleSpan(log.start_day + timedelta(days=laps * typical_length), typical_length, None)


def build_cycle(periods: Iterable[PeriodLog], readiness: Iterable[Readiness]) -> list[CycleDay]:
    logs = sorted({log.start_day: log for log in periods}.values(), key=lambda log: log.start_day)
    if not logs:
        return []
    typical_length = _typical_length([log.start_day for log in logs])

    cycle: list[CycleDay] = []
    current_start: date | None = None
    warm_streak = 0
    ovulation_confirmed = False
    for row in sorted(readiness, key=lambda reading: reading.day):
        span = _span_for(row.day, logs, typical_length)
        if span is None:
            continue
        if span.start != current_start:
            current_start, warm_streak, ovulation_confirmed = span.start, 0, False

        warm = (row.temperature_deviation_c or 0) >= LUTEAL_TEMP_RISE_C
        warm_streak = warm_streak + 1 if warm else 0
        ovulation_confirmed = ovulation_confirmed or warm_streak >= SUSTAINED_RISE_NIGHTS
        cycle_day = (row.day - span.start).days + 1
        cycle.append(
            CycleDay(
                day=row.day,
                source=Source.SELF_REPORT,
                cycle_day=cycle_day,
                phase=_phase_for(cycle_day, span.length),
                is_period=span.logged is not None and row.day <= _period_end(span.logged),
                ovulation_confirmed=ovulation_confirmed,
            )
        )
    return cycle
