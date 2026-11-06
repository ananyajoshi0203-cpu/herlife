"""End to end: Oura + Bloom period log -> canonical tables -> SQLite + web seed.

Oura supplies sleep, readiness, activity, and stress. The cycle comes from the
self-reported period log, with Oura temperature used only to confirm ovulation.

    .venv/bin/python -m backend.pipeline            # mock mode, regenerates synthetic data
    OURA_TOKEN=... .venv/bin/python -m backend.pipeline   # live Oura account
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel, TypeAdapter

from backend.canonical.cycle import build_cycle
from backend.canonical.models import CanonicalDataset, PeriodLog
from backend.canonical.oura_adapter import adapt_all
from backend.connectors.oura import RAW_DIR, OuraConnector
from backend.synthetic import oura_generator, period_log_generator

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_DIR = ROOT / "data" / "canonical"
DB_PATH = ROOT / "data" / "health.db"
WEB_SEED = ROOT / "web" / "seed.json"
PERIOD_LOG_PATH = RAW_DIR / period_log_generator.PERIOD_LOG_FILE
DAILY_KEY = ("day", "source")
TABLE_KEYS: dict[str, tuple[str, ...]] = {
    "sleep": DAILY_KEY,
    "readiness": DAILY_KEY,
    "activity": DAILY_KEY,
    "stress": DAILY_KEY,
    "periods": ("start_day", "source"),
    "cycle": DAILY_KEY,
}


def _write_table(conn: sqlite3.Connection, name: str, rows: Sequence[BaseModel], key: tuple[str, ...]) -> None:
    if not rows:
        return
    records = [row.model_dump(mode="json") for row in rows]
    columns = list(records[0])
    conn.execute(f"DROP TABLE IF EXISTS {name}")
    conn.execute(f"CREATE TABLE {name} ({', '.join(columns)}, PRIMARY KEY ({', '.join(key)}))")
    conn.executemany(
        f"INSERT INTO {name} VALUES ({', '.join('?' for _ in columns)})",
        [tuple(r[c] for c in columns) for r in records],
    )


def load_period_log(path: Path = PERIOD_LOG_PATH) -> list[PeriodLog]:
    if not path.exists():
        return []
    return TypeAdapter(list[PeriodLog]).validate_json(path.read_text())


def run(today: date) -> CanonicalDataset:
    connector = OuraConnector()
    if not connector.is_live:
        oura_generator.write(today)
        period_log_generator.write(today)
    raw = connector.fetch_all(today - timedelta(days=oura_generator.DAYS - 1), today)
    periods = load_period_log()
    dataset = CanonicalDataset(
        user_id="maya-demo", generated_at=datetime.now(), periods=periods, cycle=[], **adapt_all(raw)
    )
    dataset.cycle = build_cycle(dataset.periods, dataset.readiness)

    CANONICAL_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        for table, key in TABLE_KEYS.items():
            rows: list[BaseModel] = getattr(dataset, table)
            _write_table(conn, table, rows, key)
            (CANONICAL_DIR / f"{table}.json").write_text(
                json.dumps([r.model_dump(mode="json") for r in rows], indent=1)
            )
    WEB_SEED.write_text(dataset.model_dump_json())
    return dataset


if __name__ == "__main__":
    result = run(date.today())
    print(
        f"sleep={len(result.sleep)} readiness={len(result.readiness)} activity={len(result.activity)} "
        f"stress={len(result.stress)} periods={len(result.periods)} cycle={len(result.cycle)} "
        f"ovulation_confirmed={sum(day.ovulation_confirmed for day in result.cycle)} "
        f"today={result.cycle[-1] if result.cycle else None}"
    )
