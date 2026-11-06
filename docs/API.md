# Bloom API

FastAPI service in `backend/api/`. SQLite at `data/bloom_api.db`. Reads and writes only canonical models.

```
.venv/bin/uvicorn backend.api.app:app --reload
```

Interactive docs at http://localhost:8000/docs. Tests: `.venv/bin/python -m pytest tests/test_api.py`.

## Environment

| Variable | Needed for | Without it |
|---|---|---|
| `ANTHROPIC_API_KEY` | Voice log sorting and habit suggestions via Claude (`claude-sonnet-5-5`) | Rule-based fallback; responses carry `used_ai: false` |
| `OURA_CLIENT_ID`, `OURA_CLIENT_SECRET` | Oura OAuth connect | `/oura/authorize` returns 503; sync runs in mock mode |
| `OURA_REDIRECT_URI` | Callback registered in the Oura developer app | Defaults to `http://localhost:8000/oura/callback` |

## Endpoints

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/users` | `name, age, gym_access (gym\|home\|none), diet[], conditions[], life_stage, goals[2]` | User profile with `id` |
| GET | `/oura/authorize?user_id=` | | 307 redirect to Oura consent (scopes `daily heartrate personal`) |
| GET | `/oura/callback?code=&state=` | | Stores the user's access and refresh tokens; `{user_id, connected}` |
| POST | `/users/{id}/sync` | | Pulls 90 days from Oura (live with a stored token, else mock data) and stores sleep, readiness, activity, stress; returns counts and `live` |
| POST | `/users/{id}/periods` | `start_day, end_day?, flow (light\|medium\|heavy)` | The self-reported period log entry |
| GET | `/users/{id}/cycle` | | Logged periods, today's cycle day, and every cycle day (`build_cycle`) |
| POST | `/users/{id}/logs/voice` | `text` | Entries sorted into `sleep\|movement\|nutrition\|mood\|symptoms` with `text` and `detail`, saved as `self_report` |
| POST | `/users/{id}/habits/suggest` | | 3 habits tied to her 2 goals, profile, and last 30 days of data |
| POST | `/users/{id}/habits/{habit_id}/checks` | `day?` (defaults to today) | The check-in; idempotent per day |
| GET | `/users/{id}/habits/consistency` | | Per habit, per ISO week: days checked, days possible, rate |
| GET | `/users/{id}/plan/today` | | `sleep, move, eat, mind`, `ease_off` with `reasons`, and `cycle` context only for `cycling` or `irregular` life stages |
| GET | `/users/{id}/record` | | Doctor summary: profile, 30 day lifestyle averages, self-report counts and recent entries, habit consistency, and cycle insights (`backend.insights.compute`) for cycle-aware life stages |

`life_stage` is one of `cycling, irregular, hormonal_birth_control, pregnant_postpartum, perimenopause_menopause, prefer_not`.

## Notes

- Claude calls use structured outputs (`client.beta.messages.parse` with a pydantic `output_format`) and the server-side refusal fallback (`fallbacks: "default"`). Any missing key, API error, refusal, or invalid output falls back to rules.
- Sync with no stored Oura token runs in mock mode against `data/raw/`; it never uses a process-wide `OURA_TOKEN`, so one ring cannot leak into every user's record.
- Bloom is not a medical device. The plan is lifestyle suggestions and the record is a record, not a diagnosis.
