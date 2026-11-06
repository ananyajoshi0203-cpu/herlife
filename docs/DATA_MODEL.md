# Data model

```
Oura API v2 ──► OuraConnector ──► oura_adapter ──► sleep, readiness, ──┐
(daily_sleep,     (live or mock)    (units, enums)   activity, stress    │
 sleep, daily_                                                          │ temperature
 readiness, ...)                                                        ▼ (confirms ovulation)
HerLife period tracker ──► bloom_period_log.json ──► periods ──► cycle.build_cycle ──► cycle
(self-reported starts,                                         (cycle day + phase
 ends, flow)                                                    from logged starts)
                                                                        │
                                          all tables ──► SQLite / data/canonical / web seed
Voice log ──► Claude sorter ──► self_report entries (sleep, movement, nutrition, mood, symptom)
```

| Table | Key | Fields | Oura origin |
|---|---|---|---|
| sleep | day, source | score, bedtime_start/end, total/deep/rem/light/awake min, efficiency, HRV, resting HR | `sleep` (long_sleep) + `daily_sleep.score` |
| readiness | day, source | score, temperature_deviation_c, hrv_balance, recovery_index | `daily_readiness` |
| activity | day, source | score, steps, active_kcal, high/medium/low activity min | `daily_activity` (seconds -> min) |
| stress | day, source | stress_high_min, recovery_high_min, summary | `daily_stress` |
| periods | start_day, source | start_day, end_day (null while ongoing), flow (light/medium/heavy) | none: self-reported in HerLife, Oura does not sync periods |
| cycle | day, source | cycle_day, phase, is_period, ovulation_confirmed | built from `periods` (cycle length = average gap between starts, 28 if only one). `ovulation_confirmed` turns on after 3 straight nights >= +0.18 C on `readiness.temperature_deviation_c` and stays on until the next logged start. Source is `self_report` |

`source` is part of every key so self-reported and wearable rows coexist for the same day.
Adding Apple Health or Whoop means writing one adapter; nothing downstream changes.
