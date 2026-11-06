# Bloom: women's lifestyle record

Hackathon build (1h45m, 2026-11-06). Judges play through a published claude.ai artifact.

## The problem we pitch
Women walk into a doctor's office with no lifestyle record. The doctor sees a 15 minute
snapshot and starts standard treatment. Bloom builds the "cookie trail" (sleep, food,
movement, mood, cycle) every day with near-zero effort, and hands the doctor a one-page
summary. See `docs/PITCH.md`.

## Layout
- `backend/connectors/oura.py`: Oura API v2 client. Live with `OURA_TOKEN`, otherwise mock mode reading `data/raw/`.
- `backend/canonical/models.py`: vendor-neutral pydantic models. Everything downstream reads only these.
- `backend/canonical/oura_adapter.py`: raw Oura -> canonical sleep, readiness, activity, stress. Produces no cycle rows: Oura does not sync periods.
- `backend/canonical/cycle.py`: `build_cycle(periods, readiness)`. Cycle day and phase come from Bloom's self-reported period log; Oura temperature only sets `ovulation_confirmed`. `_phase_for` must match `phaseOf` in `web/index.html`.
- `backend/synthetic/oura_generator.py`: 90 days of Oura-shaped payloads with a real cycle signal (persona "Maya").
- `backend/synthetic/period_log_generator.py`: Maya's period log (`data/raw/bloom_period_log.json`), aligned with the Oura generator's cycle.
- `backend/pipeline.py`: generate -> adapt Oura + load period log -> build cycle -> `data/health.db` + `data/canonical/*.json` (incl. `periods`, `cycle`) + `web/seed.json`.
- `web/index.html`: the whole app, published as an artifact. Claude calls go through the artifact `sample` capability.
- `docs/`: plan, pitch, data model, demo script.

## Commands
- Regenerate data: `.venv/bin/python -m backend.pipeline`
- Embed seed in the app and republish: `/publish-demo` skill

## Rules for this repo
- New wearable = new adapter producing canonical models. Never let a vendor field reach `web/`.
- Copy is American English, warm, never clinical-scary, no em dashes in user-facing text.
- Every AI call in the app has a deterministic fallback so the demo never dead-ends.
- We are not a medical device. Recommendations are lifestyle suggestions; the doctor summary is a record, not a diagnosis.
