"""Synthetic HerLife period log for persona Maya, aligned with the Oura generator.

Starts use the same cycle length and offset as `oura_generator`, so her logged
periods land exactly where the ring sees the temperature drop. One log precedes
the 90 day window, as a real tracker would hold history from before the ring.
"""

from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path

from backend.canonical.models import Flow, PeriodLog
from backend.connectors.oura import RAW_DIR
from backend.synthetic.oura_generator import CYCLE_LENGTH, DAYS, FIRST_PERIOD_OFFSET, SEED

PERIOD_LENGTH = timedelta(days=5)
PERIOD_LOG_FILE = "bloom_period_log.json"
FLOW_WEIGHTS: dict[Flow, int] = {Flow.LIGHT: 1, Flow.MEDIUM: 3, Flow.HEAVY: 2}


def _logged_end(start: date, today: date) -> date | None:
    """A period still running today has no end logged yet."""
    last_day = start + PERIOD_LENGTH - timedelta(days=1)
    return last_day if last_day < today else None


def generate(end: date, rng: random.Random) -> list[PeriodLog]:
    window_start = end - timedelta(days=DAYS - 1)
    first_start = window_start - timedelta(days=FIRST_PERIOD_OFFSET)
    starts = [
        first_start + timedelta(days=offset)
        for offset in range(0, DAYS + FIRST_PERIOD_OFFSET, CYCLE_LENGTH)
    ]
    return [
        PeriodLog(
            start_day=start,
            end_day=_logged_end(start, end),
            flow=rng.choices(list(FLOW_WEIGHTS), weights=list(FLOW_WEIGHTS.values()))[0],
        )
        for start in starts
    ]


def write(end: date, out_dir: Path = RAW_DIR) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / PERIOD_LOG_FILE
    logs = generate(end, random.Random(SEED))
    path.write_text(json.dumps([log.model_dump(mode="json") for log in logs], indent=1))
    return path


if __name__ == "__main__":
    write(date.today())
