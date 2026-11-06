# Evals

What can go wrong in front of a judge, and how we catch it before the demo.

## What we evaluate

| # | Surface | Failure that costs us | Kind | Gate |
|---|---|---|---|---|
| 1 | Cycle building (`cycle.build_cycle`) | Wrong phase, so the "ease off" card fires on the wrong day and the record says headaches cluster in the wrong phase | Deterministic, planted personas | Phase accuracy >= 85%, ovulation recall >= 90%, zero false ovulations |
| 2 | Voice-log sorter (Claude) | Latte filed as movement, headache dropped, invented symptom | LLM, golden set | Category recall >= 90%, zero invented items |
| 3 | Voice-log fallback (keyword sorter) | Dead end when `sample` fails | Deterministic, same golden set | Every ramble yields >= 1 card, recall >= 60% |
| 4 | Habit picker (Claude) | Habit conflicts with intake (gym habit for "no gym", meat for vegetarian) | LLM, persona matrix | Zero constraint violations, exactly 3 habits |
| 5 | Doctor record | Diagnostic language ("you have PCOS"), numbers that don't match the data | Deterministic numbers + LLM-judge for tone | Numbers match `insights.py` exactly; zero diagnosis phrases |
| 6 | All user-facing copy | Em dashes, British spelling, scary clinical tone | Deterministic lint + `womens-health-copy` agent | Zero lint hits |

## Tiers, cheapest first

1. **Deterministic (run every change, < 1s, no key).** Covers 1, 3, 5 (numbers), and 6 (lint). Plain
   Python with asserts, run with `.venv/bin/python -m evals.run`. We aren't adding pytest because it isn't
   worth a dependency during a 1h45m build.
2. **LLM golden set (run before each republish, needs `ANTHROPIC_API_KEY`).** Covers 2 and 4. Sends
   the same prompt the app uses to the Messages API, then scores the JSON output against labels with
   code, not with another model. About 20 rambles plus 6 personas, so roughly 30 calls per run.
3. **Judgment (run once before the pitch).** Covers 5 (tone) and the end-to-end flow:
   `womens-health-copy` and `judge-playtester` agents on the published URL.

## The one structural decision: prompts live in files

The app calls Claude through the artifact `sample` capability, which Python can't reach. If the
prompts are only inline in `web/index.html`, the eval tests a copy that drifts from what ships.

So: `evals/prompts/sort_log.txt` and `evals/prompts/pick_habits.txt` are the source of truth, and
`embed_seed.py` inlines them into `index.html` the same way it inlines `seed.json`. The output
contract (JSON shape) is a pydantic model in `evals/contracts.py`, and the app parses the same shape.

## Golden set design (voice-log sorter)

Each case is a ramble plus expected items per category, plus a list of things that must not appear:

```json
{"id": "latte-walk-headache",
 "ramble": "slept badly, had oatmeal and a latte, 20 min walk, headache after lunch, feeling anxious",
 "expect": {"sleep": ["poor"], "nutrition": ["oatmeal", "latte"], "movement": ["walk 20 min"],
            "symptom": ["headache"], "mood": ["anxious"]},
 "forbid": ["migraine", "caffeine withdrawal"]}
```

Matching is lenient on wording (lowercase substring on the key noun) and strict on category.
Cases cover: the demo script ramble verbatim (must pass, it's on stage), negation ("no headache today"),
ambiguity ("yoga then a smoothie"), period mentions ("cramps, day 2"), empty or off-topic input
("ugh mondays"), and a long 60-second ramble.

## Persona matrix (habit picker)

6 intakes crossing gym yes/no, vegetarian/vegan/none, and condition (migraines, PCOS, none), each with
2 goals. Checks: exactly 3 habits; no habit mentions gym/weights when gym is no; no animal food
for vegetarian/vegan; each habit maps to one of the 2 goals; copy lint passes.

## Copy lint rules (deterministic)

- No `—` or `–` in any user-facing string.
- British spellings blocklist: colour, behaviour, programme, optimise, centre, fibre.
- Diagnosis blocklist in AI output and record: "you have", "diagnos", "disorder", "abnormal", "you should see a doctor immediately".

## Cycle personas (`evals/cycle_personas.py`)

Targets `cycle.build_cycle(periods, readiness)`: phases come from the logged periods, temperature only
confirms ovulation. 11 personas x 10 seeds, scored against the cycle we planted.

Gated on days up to the last logged period (fully determined by the logs). Days after it are
predicted from her typical length and only reported, since nobody knows when an irregular period comes.

| Persona | Logged | Predicted | Note |
|---|---|---|---|
| maya, 25d, 35d, noisy sensor, ring gaps, pill | 100% | 100% | Pill: zero false ovulation confirmations |
| pcos (35 to 45d) | 100% | 88% | Each completed cycle uses its own length |
| perimenopause (24 to 45d) | 100% | 77% | Same |
| single logged period | n/a | 79% | Wraps on a 28-day default instead of counting to day 88 |
| forgets to log 1 in 3 | 84% | 92% | Known limit: few gaps in 90 days, a missed log looks like real variation |
| logs 2 days late | 73% | 73% | Known limit: the tracker UI lets her backdate |

Known-limit personas are printed but do not fail the run. Ovulation recall is 100% everywhere.

## Order of work (fits the time box)

1. `evals/cycle_personas.py`: tier 1, item 1. Done.
2. `evals/lint.py`: copy lint over `web/index.html` and AI outputs.
3. Golden set JSON + `evals/llm_eval.py`: tier 2, gated on the prompts moving to files.
4. Agents before the pitch.

Cut if behind: persona matrix shrinks to 3; LLM tier runs only the demo-script ramble.
