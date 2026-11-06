# Tests and evals

| Command | What it checks | Needs |
|---|---|---|
| `.venv/bin/python -m pytest -q tests` | 85 tests: production API (cycle signal, habit impact, seasons, age bands, check-ins) and the hosted web server (page + shim, per-person records, delete, AI and connector fallbacks, health) | nothing |
| `node --test tests/web/app.test.mjs` | Web app: every demo persona renders every onboarding step and tab, mood and info sheets, with zero errors; phase boundaries; temperature cycle estimate; never menopause under 40; stress load; cue times; adaptive next move | Node 20+ |
| `.venv/bin/python -m evals.cycle_personas` | Cycle prediction across 11 body types x 10 seeds, logged and temperature-only | nothing |
| `.venv/bin/python -m evals.claude_evals` | Claude features against the real models: log sorting, habit suggestions (count, length, no diagnosis, no cycle talk on the pill), goal to signal mapping, doctor summary (3 paragraphs, no diagnosis, no menopause under 40), no em dashes. Gate: every check passes; a case that fails is retried once with a fresh answer, since sampling varies | `ANTHROPIC_API_KEY` |

The web render test was checked by reintroducing a real bug (a shadowed helper that blanked Today): it fails and names the error for every persona.
The Claude evals caught a production bug on their first run: answers were cut off because the models think before answering, so habit suggestions silently fell back to the built-in library. Output tokens were raised to 4,000.
