# Build plan (1h45m)

Decision: **web app**, laid out like a phone screen, published as a claude.ai artifact. Zero install for
judges, Claude available in-page via the `sample` capability, no API key to leak.

| Time | Slice | Done when |
|---|---|---|
| 0:00-0:15 | venv, Oura connector, canonical models, adapter, synthetic generator, pipeline | `python -m backend.pipeline` writes db + seed |
| 0:15-0:20 | CLAUDE.md, docs, `.claude/` skills + agents | files in place |
| 0:20-1:15 | App: onboarding, privacy, goals, AI habits, Today, log composer, period tab, record | published link works on phone |
| 1:15-1:30 | Polish: mood check-in, ease-off card, calendar, animations | judge walkthrough has no dead end |
| 1:30-1:45 | Pitch rehearsal with `docs/DEMO_SCRIPT.md` | 2 minute run-through |

## App surfaces
1. **Onboarding**: name, age, gym access, food restrictions, medical conditions (Preffect-style intake).
2. **Health privacy**: plain-language promises, per-category consent toggles.
3. **Goals**: pick 2. Claude suggests 3 habits, each becomes a tracker with weekly consistency.
4. **Today**: cycle phase + Oura readiness -> plan of the day, one small win, recipe, movement, "ease off" when signals say so, calendar-aware timing.
5. **Log composer**: speak or type one long ramble; Claude sorts it into sleep, movement, nutrition, mood, symptoms.
6. **Cycle**: ring of phases, predicted next period and fertile window, phase-specific guidance.
7. **Record**: doctor-ready summary of 90 days: trends, symptom patterns by phase, habit adherence.
8. **Random mood check-in**: animated bubble, appears mid-session.

## Cut list if behind
Calendar becomes a static mock; voice falls back to typing (dictation from phone keyboard still works).
