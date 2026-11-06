"""Cycle-change signal from logged period starts, ported from cycleSignal in web/index.html.

The rules follow docs/RESEARCH.md sections 4 to 6. STRAW+10 stages reproductive
aging by bleeding pattern alone, so the triggers are the same at every age; only
the wording changes with age:

- under 40, output never names menopause or the transition, because early or
  premature menopause is a clinical diagnosis made with blood tests;
- 40 to 44, early perimenopause is offered as one possibility among equals;
- 45 and over, the pattern is named as fitting the transition, never as a verdict.

No output names a condition in the body. Conditions belong in the question she
takes to a clinician.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date, timedelta
from itertools import pairwise

from backend.api.schemas import CycleSignal, LifeStage, SignalLevel

EARLY_TRANSITION_SWING = timedelta(days=7)
PERSISTENCE_WINDOW_CYCLES = 10
LATE_TRANSITION_GAP = timedelta(days=60)
NO_PERIOD_VISIT = timedelta(days=90)
SILENT_ON_MENOPAUSE_BELOW_AGE = 40
TRANSITION_AGE = 45

# A 90 day gap is expected, not a red flag, while pregnant, postpartum, or on a
# method that changes bleeding (RESEARCH.md rows R3, C1, C2).
EXPECTED_PATTERN_NOTES: dict[LifeStage, tuple[str, str]] = {
    LifeStage.PREGNANT_POSTPARTUM: (
        "Cycle changes are expected right now",
        "HerLife has paused cycle-change notes while you are pregnant or postpartum.",
    ),
    LifeStage.HORMONAL_BIRTH_CONTROL: (
        "Your bleeding pattern reflects your method",
        "Hormonal birth control shapes your bleeding, so HerLife does not read changes as a cycle signal.",
    ),
}


def cycle_lengths(starts: Sequence[date]) -> list[int]:
    return [(later - earlier).days for earlier, later in pairwise(starts)]


def has_persistent_swing(lengths: Sequence[int]) -> bool:
    """Two swings of 7+ days between consecutive cycles, the second within 10 cycles of the first."""
    swing_at = [
        index
        for index, (earlier, later) in enumerate(pairwise(lengths))
        if abs(later - earlier) >= EARLY_TRANSITION_SWING.days
    ]
    return any(later - earlier <= PERSISTENCE_WINDOW_CYCLES for earlier, later in pairwise(swing_at))


def history_sentence(lengths: Sequence[int], since_last: timedelta) -> str:
    if not lengths:
        return f"It has been {since_last.days} days since your last logged period."
    return f"Recent cycles: {', '.join(str(length) for length in lengths)} days."


def cycle_signal(
    age: int, life_stage: LifeStage, period_starts: Iterable[date], today: date, stress_up: bool
) -> CycleSignal | None:
    starts = sorted(set(period_starts))
    if not starts:
        return None
    lengths = cycle_lengths(starts)
    since_last = today - starts[-1]
    history = history_sentence(lengths, since_last)

    def signal(level: SignalLevel, title: str, body: str, question: str | None) -> CycleSignal:
        return CycleSignal(
            level=level,
            title=title,
            body=body,
            clinician_question=question,
            cycle_lengths_days=lengths,
            days_since_last_period=since_last.days,
        )

    if life_stage in EXPECTED_PATTERN_NOTES:
        title, body = EXPECTED_PATTERN_NOTES[life_stage]
        return signal(SignalLevel.STEADY, title, body, None)
    if since_last >= NO_PERIOD_VISIT:
        return signal(
            SignalLevel.FLAG,
            "No period for 3 months",
            "That is worth a visit soon, whatever the reason. Many things can pause periods, "
            "and a clinician can help find which one it is.",
            "I have not had a period in 3 months. What should we check first?",
        )

    early = has_persistent_swing(lengths)
    late = max([*lengths, since_last.days]) >= LATE_TRANSITION_GAP.days
    if not early and not late:
        if not lengths:
            return None
        return signal(
            SignalLevel.STEADY,
            "Your cycles look steady",
            f"{history} Your cycle looks steady compared with your recent history.",
            None,
        )

    if age < SILENT_ON_MENOPAUSE_BELOW_AGE:
        stress_note = (
            " Your stress load has climbed lately, and stress and cycle changes often go together." if stress_up else ""
        )
        return signal(
            SignalLevel.WATCH,
            "Your cycles are changing",
            f"{history} Stress, short sleep, and eating too little for your training can all go along "
            f"with cycle changes.{stress_note}",
            "My cycles have been irregular for a few months. Could stress, training, or my thyroid explain it, "
            "and should anything be checked?",
        )
    if age < TRANSITION_AGE:
        return signal(
            SignalLevel.WATCH,
            "Your cycles are changing",
            f"{history} Early perimenopause is possible in your early 40s, but stress, sleep, "
            "and other causes are just as likely.",
            "My cycles have changed in my early 40s. Could hormones, stress, or something else be involved?",
        )
    if late:
        return signal(
            SignalLevel.WATCH,
            "This pattern fits the later menopause transition",
            f"{history} A gap of 60 days or more between periods is common in midlife, and it is how "
            "clinicians describe the later stage of the transition.",
            "I am having longer gaps between periods. What should I watch for?",
        )
    return signal(
        SignalLevel.WATCH,
        "This pattern fits the early menopause transition",
        f"{history} Your cycles have varied by a week or more a few times. This is common in midlife.",
        "My cycle lengths keep changing by a week or more. Could this be the menopause transition?",
    )
