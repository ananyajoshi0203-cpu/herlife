"""Generate 90 days of Oura-shaped payloads for one persona, with a real cycle signal.

Persona: Maya, 32, 29-day cycle. Luteal nights run warmer with lower HRV and
lighter sleep; the first two period days drag readiness down. This is what lets
the app show judges that cycle context changes the plan.
"""

from __future__ import annotations

import json
import random
import uuid
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

from backend.connectors.oura import RAW_DIR, OuraEndpoint

CYCLE_LENGTH = 29
DAYS = 90
SEED = 7
FIRST_PERIOD_OFFSET = 9
# Lifestyle effects draw from their own generator so every draw on the main one,
# and with it the cycle's temperature signal, stays identical.
LIFESTYLE_SEED = 11
HEAVY_STRESS_MIN = 130
HEAVY_DAY_SLEEP_COST_MIN = (30, 40)
SUNDAY_NIGHT_SLEEP_COST_MIN = (30, 45)
STEPS_DRIFT = timedelta(days=28)
STEPS_DRIFT_FLOOR = 0.45
HRV_RISE = timedelta(days=14)
HRV_RISE_MS = 9.0


def _cycle_day(day_index: int, first_period_offset: int) -> int:
    return (day_index + first_period_offset) % CYCLE_LENGTH + 1


def _phase_effects(cycle_day: int) -> tuple[float, float, float]:
    """Returns (temperature deviation C, HRV multiplier, readiness delta)."""
    ovulation = CYCLE_LENGTH - 14
    if cycle_day <= 2:
        return -0.05, 0.85, -14
    if cycle_day <= 5:
        return -0.08, 0.93, -6
    if cycle_day <= ovulation:
        return -0.1, 1.08, 5
    if cycle_day >= CYCLE_LENGTH - 4:
        return 0.38, 0.84, -10
    return 0.3, 0.92, -3


def _lifestyle_sleep_cost(day: date, previous_stress_high: int | None, lifestyle_rng: random.Random) -> int:
    """Minutes lost on the night that ends on `day`: after a heavy day, and on Sunday nights."""
    cost = 0
    if previous_stress_high is not None and previous_stress_high >= HEAVY_STRESS_MIN:
        cost += lifestyle_rng.randint(*HEAVY_DAY_SLEEP_COST_MIN)
    if day.weekday() == 0:
        cost += lifestyle_rng.randint(*SUNDAY_NIGHT_SLEEP_COST_MIN)
    return cost


def _ramp(days_left: int, span: timedelta) -> float:
    """0 before the final `span`, rising to 1 on the last day."""
    return max(0.0, 1 - days_left / span.days)


def generate(end: date, rng: random.Random) -> dict[OuraEndpoint, list[dict[str, Any]]]:
    payloads: dict[OuraEndpoint, list[dict[str, Any]]] = {
        "daily_sleep": [],
        "sleep": [],
        "daily_readiness": [],
        "daily_activity": [],
        "daily_stress": [],
    }
    start = end - timedelta(days=DAYS - 1)
    lifestyle_rng = random.Random(LIFESTYLE_SEED)
    previous_stress_high: int | None = None
    for i in range(DAYS):
        day = start + timedelta(days=i)
        days_left = DAYS - 1 - i
        cd = _cycle_day(i, FIRST_PERIOD_OFFSET)
        temp, hrv_mult, readiness_delta = _phase_effects(cd)
        weekend = day.weekday() >= 5

        bedtime = datetime.combine(day - timedelta(days=1), time(22, 45)) + timedelta(
            minutes=rng.randint(-30, 70) + (40 if weekend else 0)
        )
        total = int(rng.gauss(445, 30) * (0.94 if temp > 0.2 else 1.0))
        total -= _lifestyle_sleep_cost(day, previous_stress_high, lifestyle_rng)
        deep = int(total * rng.uniform(0.15, 0.21) * hrv_mult)
        rem = int(total * rng.uniform(0.19, 0.24))
        awake = rng.randint(18, 45) + (15 if temp > 0.3 else 0)
        light = total - deep - rem
        efficiency = round(100 * total / (total + awake))
        hrv = round(rng.gauss(52, 5) * hrv_mult + HRV_RISE_MS * _ramp(days_left, HRV_RISE), 1)
        sleep_score = max(40, min(97, round(62 + (total - 400) / 5 + (efficiency - 88) + rng.gauss(0, 3))))
        readiness = max(35, min(98, round(78 + readiness_delta + rng.gauss(0, 4))))
        steps = int(rng.gauss(8200 if not weekend else 6400, 1800) * (0.8 if cd <= 2 else 1.0))
        steps = int(steps * (1 - (1 - STEPS_DRIFT_FLOOR) * _ramp(days_left, STEPS_DRIFT)))

        day_s = day.isoformat()
        payloads["sleep"].append(
            {
                "id": str(uuid.UUID(int=rng.getrandbits(128))),
                "day": day_s,
                "type": "long_sleep",
                "bedtime_start": bedtime.isoformat() + "-07:00",
                "bedtime_end": (bedtime + timedelta(minutes=total + awake)).isoformat() + "-07:00",
                "total_sleep_duration": total * 60,
                "deep_sleep_duration": deep * 60,
                "rem_sleep_duration": rem * 60,
                "light_sleep_duration": light * 60,
                "awake_time": awake * 60,
                "efficiency": efficiency,
                "average_hrv": hrv,
                "average_heart_rate": round(rng.gauss(58, 2) + (2 if temp > 0.2 else 0), 1),
                "lowest_heart_rate": round(rng.gauss(52, 2) + (2 if temp > 0.2 else 0)),
            }
        )
        payloads["daily_sleep"].append(
            {
                "id": str(uuid.UUID(int=rng.getrandbits(128))),
                "day": day_s,
                "score": sleep_score,
                "contributors": {"total_sleep": min(100, total // 5), "efficiency": efficiency},
                "timestamp": f"{day_s}T00:00:00+00:00",
            }
        )
        payloads["daily_readiness"].append(
            {
                "id": str(uuid.UUID(int=rng.getrandbits(128))),
                "day": day_s,
                "score": readiness,
                "temperature_deviation": round(temp + rng.gauss(0, 0.06), 2),
                "temperature_trend_deviation": round(temp, 2),
                "contributors": {
                    "hrv_balance": max(30, min(100, round(80 * hrv_mult))),
                    "recovery_index": max(30, min(100, round(75 + readiness_delta))),
                    "body_temperature": max(40, round(95 - abs(temp) * 80)),
                },
                "timestamp": f"{day_s}T00:00:00+00:00",
            }
        )
        payloads["daily_activity"].append(
            {
                "id": str(uuid.UUID(int=rng.getrandbits(128))),
                "day": day_s,
                "score": max(40, min(99, round(70 + (steps - 7000) / 250))),
                "steps": max(1500, steps),
                "active_calories": max(120, round(steps * 0.045)),
                "total_calories": 1850 + max(120, round(steps * 0.045)),
                "high_activity_time": rng.choice([0, 0, 900, 1800, 2700]),
                "medium_activity_time": rng.randint(900, 3600),
                "low_activity_time": rng.randint(7200, 14400),
            }
        )
        stress_high = rng.randint(30, 150) + (45 if temp > 0.3 else 0)
        recovery_high = rng.randint(40, 160)
        previous_stress_high = stress_high
        payloads["daily_stress"].append(
            {
                "id": str(uuid.UUID(int=rng.getrandbits(128))),
                "day": day_s,
                "stress_high": stress_high * 60,
                "recovery_high": recovery_high * 60,
                "day_summary": "stressful" if stress_high > recovery_high + 40 else "normal" if stress_high > recovery_high else "restored",
            }
        )
    return payloads


def write(end: date, out_dir: Path = RAW_DIR) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for endpoint, rows in generate(end, random.Random(SEED)).items():
        (out_dir / f"oura_{endpoint}.json").write_text(json.dumps({"data": rows, "next_token": None}, indent=1))


if __name__ == "__main__":
    write(date.today())
