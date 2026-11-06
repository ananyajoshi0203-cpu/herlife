from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta

import pytest

from backend.api.cycle_signal import cycle_signal
from backend.api.schemas import CycleSignal, LifeStage, SignalLevel

TODAY = date(2026, 11, 6)
MENOPAUSE_WORDS = ("menopause", "perimenopause", "transition")
STEADY = [29, 30, 29, 28]
EARLY_TRANSITION = [27, 36, 26, 35]
LATE_TRANSITION = [28, 29, 65]


def starts_from(lengths: Sequence[int], days_since_last: int) -> list[date]:
    last = TODAY - timedelta(days=days_since_last)
    starts = [last]
    for length in reversed(lengths):
        starts.insert(0, starts[0] - timedelta(days=length))
    return starts


def signal(
    age: int,
    lengths: Sequence[int],
    days_since_last: int = 10,
    life_stage: LifeStage = LifeStage.IRREGULAR,
    stress_up: bool = False,
) -> CycleSignal:
    result = cycle_signal(age, life_stage, starts_from(lengths, days_since_last), TODAY, stress_up)
    assert result is not None
    return result


def all_text(result: CycleSignal) -> str:
    return " ".join((result.title, result.body, result.clinician_question or "")).lower()


@pytest.mark.parametrize("age", [18, 25, 32, 39])
@pytest.mark.parametrize(
    ("lengths", "days_since_last", "level"),
    [
        (STEADY, 10, SignalLevel.STEADY),
        (EARLY_TRANSITION, 10, SignalLevel.WATCH),
        (LATE_TRANSITION, 10, SignalLevel.WATCH),
        (STEADY, 70, SignalLevel.WATCH),
        (STEADY, 95, SignalLevel.FLAG),
    ],
)
def test_under_40_never_mentions_menopause(
    age: int, lengths: list[int], days_since_last: int, level: SignalLevel
) -> None:
    result = signal(age, lengths, days_since_last, stress_up=True)
    assert result.level == level
    assert not any(word in all_text(result) for word in MENOPAUSE_WORDS), all_text(result)


def test_early_40s_offers_perimenopause_as_one_possibility() -> None:
    result = signal(42, EARLY_TRANSITION)
    assert result.level == SignalLevel.WATCH
    assert "early perimenopause is possible" in result.body.lower()
    assert "just as likely" in result.body


@pytest.mark.parametrize(
    ("lengths", "days_since_last", "title"),
    [
        (EARLY_TRANSITION, 10, "This pattern fits the early menopause transition"),
        (LATE_TRANSITION, 10, "This pattern fits the later menopause transition"),
        (STEADY, 60, "This pattern fits the later menopause transition"),
    ],
)
def test_45_and_over_names_the_straw_stage(lengths: list[int], days_since_last: int, title: str) -> None:
    assert signal(48, lengths, days_since_last).title == title


@pytest.mark.parametrize(
    ("lengths", "level"),
    [
        ([28, 35, 28], SignalLevel.WATCH),
        ([28, 34, 28], SignalLevel.STEADY),
        ([28, 35, 35, 35], SignalLevel.STEADY),
        ([28, 35, *[35] * 10, 28], SignalLevel.STEADY),
        ([28, 35, *[35] * 9, 28], SignalLevel.WATCH),
    ],
    ids=["two-7-day-swings", "6-day-swings", "one-swing", "second-swing-after-10-cycles", "within-10-cycles"],
)
def test_early_transition_needs_a_persistent_7_day_swing(lengths: list[int], level: SignalLevel) -> None:
    assert signal(48, lengths).level == level


@pytest.mark.parametrize("age", [24, 42, 52])
def test_90_days_without_a_period_flags_a_visit_at_any_age(age: int) -> None:
    flagged = signal(age, STEADY, days_since_last=90)
    assert flagged.level == SignalLevel.FLAG
    assert flagged.clinician_question
    assert signal(age, STEADY, days_since_last=89).level == SignalLevel.WATCH


def test_one_logged_period_flags_after_90_days() -> None:
    assert signal(30, [], days_since_last=100).level == SignalLevel.FLAG
    assert cycle_signal(30, LifeStage.CYCLING, [TODAY - timedelta(days=10)], TODAY, False) is None


def test_expected_gaps_are_not_flagged_while_pregnant_or_postpartum() -> None:
    result = signal(30, STEADY, days_since_last=120, life_stage=LifeStage.PREGNANT_POSTPARTUM)
    assert result.level == SignalLevel.STEADY
    assert result.clinician_question is None


def test_no_periods_means_no_signal() -> None:
    assert cycle_signal(30, LifeStage.CYCLING, [], TODAY, False) is None
