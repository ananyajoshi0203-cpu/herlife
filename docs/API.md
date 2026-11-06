# HerLife API

FastAPI service in `backend/api/`. SQLite at `data/bloom_api.db`. Reads and writes only canonical models.

```
.venv/bin/uvicorn backend.api.app:app --reload
```

Interactive docs at http://localhost:8000/docs. Tests: `.venv/bin/python -m pytest tests/test_api.py`.

## Environment

| Variable | Needed for | Without it |
|---|---|---|
| `ANTHROPIC_API_KEY` | Voice log sorting, habit suggestions, and plan wording via Claude (`claude-sonnet-5-5`) | Rule-based fallback; responses carry `used_ai: false` |
| `OURA_CLIENT_ID`, `OURA_CLIENT_SECRET` | Oura OAuth connect | `/oura/authorize` returns 503; sync runs in mock mode |
| `OURA_REDIRECT_URI` | Callback registered in the Oura developer app | Defaults to `http://localhost:8000/oura/callback` |

## Endpoints

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/users` | `name, age, gym_access (gym\|home\|none), diet[], conditions[], life_stage, goals[2]` | User profile with `id` and `age_band` (`label`, `focus[]`, `tip`) |
| GET | `/oura/authorize?user_id=` | | 307 redirect to Oura consent (scopes `daily heartrate personal`) |
| GET | `/oura/callback?code=&state=` | | Stores the user's access and refresh tokens; `{user_id, connected}` |
| POST | `/users/{id}/sync` | | Pulls 90 days from Oura (live with a stored token, else mock data) and stores sleep, readiness, activity, stress; returns counts and `live` |
| POST | `/users/{id}/periods` | `start_day, end_day?, flow (light\|medium\|heavy)` | The self-reported period log entry |
| GET | `/users/{id}/cycle` | | Logged periods, today's cycle day, and every cycle day (`build_cycle`) |
| GET | `/users/{id}/cycle/signal` | | Cycle-change signal: `level (steady\|watch\|flag), title, body, clinician_question, cycle_lengths_days, days_since_last_period`, or `null` before there is enough history |
| POST | `/users/{id}/checkins` | `day?, sleep_hours (0-24), energy (1-5), stress (1-5)` | The morning check-in; one per day, a repeat replaces it. Future days return 422 |
| POST | `/users/{id}/logs/voice` | `text` | Entries sorted into `sleep\|movement\|nutrition\|mood\|symptoms` with `text` and `detail`, saved as `self_report` |
| POST | `/users/{id}/habits/suggest` | | 3 habits tied to her 2 goals, profile, and last 30 days of data |
| POST | `/users/{id}/habits/{habit_id}/checks` | `day?` (defaults to today) | The check-in; idempotent per day |
| GET | `/users/{id}/habits/consistency` | | Per habit, per ISO week: days checked, days possible, rate |
| GET | `/users/{id}/habits/impact` | | Per habit: `goal`, `lever`, `first_check`, and per outcome metric a `done_vs_not_done` and a `before_vs_after` comparison |
| GET | `/users/{id}/plan/today` | | `sleep, move, eat, mind`, `ease_off` with `reasons`, `cycle` context only for `cycling` or `irregular` life stages, `age_band`, `season` (`name, label, recs[{title, body, source}]`), `data_source`, `used_ai` |
| GET | `/users/{id}/record` | | Doctor summary: profile, 30 day lifestyle averages, self-report counts and recent entries, habit consistency, cycle insights (`backend.insights.compute`) for cycle-aware life stages, `cycle_signal`, `data_source`, and 30 day `self_check_ins` averages |

`life_stage` is one of `cycling, irregular, hormonal_birth_control, pregnant_postpartum, perimenopause_menopause, prefer_not`.

## Age bands and seasons

`backend/api/guidance.py`, ported from `AGE_BANDS` and `SEASONS` in `web/index.html`. Bands are 18 to 25, 26 to 34, 35 to 44, 45 to 55, and 56 and up; ages under 18 fall in the first band. Seasons go by calendar month (Northern Hemisphere): winter is December to February. Both feed the plan and the Claude habit and plan prompts. Season recs carry their source; see the seasonal addendum in `docs/RESEARCH.md`.

## Cycle signal

`backend/api/cycle_signal.py`, following `docs/RESEARCH.md` sections 4 to 6. Triggers use STRAW+10 bleeding criteria at every age:

- **flag**: 90 or more days since the last logged period. Pregnant or postpartum and hormonal birth control users get a `steady` note instead, since long gaps are expected for them (rows R3, C1, C2).
- **watch**, early pattern: two swings of 7 or more days between consecutive cycle lengths, the second within 10 cycles of the first.
- **watch**, late pattern: any cycle, or the current gap, of 60 or more days.
- **steady**: neither pattern, with at least one completed cycle.

Wording depends on age. Under 40, no field says "menopause", "perimenopause", or "transition". From 40 to 44, the body says early perimenopause is possible but other causes are just as likely. At 45 and up, the title says the pattern fits the early or later transition. No body names a condition; the clinician question may. `stress_up` (heavy stress days, rising stress minutes, or self-rated stress of 4 or more over 14 days) adds a correlation-only note under 40.

## Habit impact

`backend/api/impact.py`. Each habit gets a `lever` (sleep, movement, stress, nutrition, mood) from its title, then its goal. The lever picks the outcomes: sleep habits track `sleep_min`, `hrv_ms`, `readiness`; movement tracks `steps`, `readiness`; and so on (`LEVER_OUTCOMES`).

- `done_vs_not_done`: mean outcome on days from the habit's start that she checked it against days she didn't.
- `before_vs_after`: mean outcome from the first check on against every earlier day of data.
- Sleep, HRV, and readiness are lagged one day (`lag_days: 1`): a habit done on day D is matched to the night stamped D + 1, the morning she woke. Steps use the same day.
- `status` is `notable` when the difference reaches the threshold (sleep 10 min, HRV 3 ms, steps 800, readiness 3 points), `no_clear_difference` below it, and `insufficient_data` (means withheld) with fewer than 5 days on either side.
- Summaries describe the two moving together, never cause and effect.

## Without a wearable

When no Oura sync exists, the plan's `ease_off` reasons come from the latest check-in (under 6 hours of sleep, energy 2 or less, stress 4 or more), `data_source` is `self_check_in`, and cycle days are walked over the calendar from her first logged period so cycle context still works. The record reports `self_check_ins` averages, and check-in sleep fills habit impact's `sleep_min` on nights without a wearable.

## Notes

- `GET /plan/today` builds the plan from rules, then asks Claude to rewrite its four lines for her season and age band. Without Claude it returns the rule plan with `used_ai: false`.
- Claude calls use structured outputs (`client.beta.messages.parse` with a pydantic `output_format`) and the server-side refusal fallback (`fallbacks: "default"`). Any missing key, API error, refusal, or invalid output falls back to rules.
- Sync with no stored Oura token runs in mock mode against `data/raw/`; it never uses a process-wide `OURA_TOKEN`, so one ring cannot leak into every user's record.
- HerLife is not a medical device. The plan is lifestyle suggestions and the record is a record, not a diagnosis.
