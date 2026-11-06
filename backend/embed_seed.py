"""Inline web/seed.json into web/index.html so the published artifact is self-contained."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "web" / "index.html"
SEED = ROOT / "web" / "seed.json"
RECORD = ROOT / "data" / "canonical" / "record.json"
SEED_BLOCK = re.compile(r'(<script id="seed" type="application/json">)(.*?)(</script>)', re.DOTALL)


def compact_seed() -> str:
    dataset = json.loads(SEED.read_text())
    days: dict[str, dict[str, object]] = {}
    for row in dataset["sleep"]:
        days.setdefault(row["day"], {}).update(
            sleep=row["score"], sleepMin=row["total_sleep_min"], deep=row["deep_min"], rem=row["rem_min"],
            hrv=row["avg_hrv_ms"], rhr=row["resting_hr_bpm"], bed=row["bedtime_start"][11:16],
        )
    for row in dataset["readiness"]:
        days.setdefault(row["day"], {}).update(ready=row["score"], temp=row["temperature_deviation_c"])
    for row in dataset["activity"]:
        days.setdefault(row["day"], {}).update(steps=row["steps"], kcal=row["active_kcal"])
    for row in dataset["stress"]:
        days.setdefault(row["day"], {}).update(stress=row["stress_high_min"], recovery=row["recovery_high_min"])
    for row in dataset["cycle"]:
        days.setdefault(row["day"], {}).update(cd=row["cycle_day"], phase=row["phase"], ov=row["ovulation_confirmed"])
    rows = [{"day": day, **values} for day, values in sorted(days.items()) if "sleep" in values]
    periods = [row["start_day"] for row in dataset["periods"]]
    record = json.loads(RECORD.read_text()) if RECORD.exists() else None
    return json.dumps({"days": rows, "periods": periods, "record": record}, separators=(",", ":"))


def main() -> None:
    page = PAGE.read_text()
    updated, count = SEED_BLOCK.subn(lambda m: m.group(1) + compact_seed() + m.group(3), page)
    if count != 1:
        raise SystemExit("web/index.html needs exactly one <script id=\"seed\"> block")
    PAGE.write_text(updated)
    print(f"embedded {len(compact_seed())} bytes of seed")


if __name__ == "__main__":
    main()
