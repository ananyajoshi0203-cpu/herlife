<p align="center"><img src="docs/assets/herlife-wordmark.svg" alt="HerLife" width="300"></p>

<p align="center"><b>Health that fits into her life.</b><br>
An AI health coordinator for busy women: it plans small, realistic health actions around her calendar, adapts to her body and cycle, learns what works for her, and turns it all into a record her doctor can use.</p>

<p align="center"><a href="https://herlife-six.vercel.app"><b>Try the live app: herlife-six.vercel.app</b></a><br>
<a href="https://github.com/ananyajoshi0203-cpu/herlife/actions/workflows/tests.yml"><img src="https://github.com/ananyajoshi0203-cpu/herlife/actions/workflows/tests.yml/badge.svg" alt="tests"></a></p>

---

## The problem

Women carry careers, families, and social lives, and their own health slides to the bottom of the list. Today's health apps track metrics or hand out recommendations, then leave her to turn insights into daily action. She ends up stitching together a fitness tracker, a calendar, a period app, and notes for her doctor, and doing the planning in her head.

When she does see a doctor, the visit is 15 minutes and starts from zero. The doctor has no record of how she sleeps, moves, eats, copes with stress, or how any of that shifts across her cycle, so care starts from the standard protocol. That is Medicine 2.0: wait for symptoms, then treat them.

## What HerLife does

HerLife coordinates her health instead of just measuring it.

| | What she gets |
|---|---|
| **Health that fits her calendar** | HerLife reads her day and finds the realistic gap: a 10 minute walk between meetings, a wind-down before dinner. "Book it" drops it into a free slot; "Up next" nudges her as it gets close. |
| **Small actions, long-term impact** | Three tiny habits from goals she writes in her own words. Claude suggests six, she swipes to keep three. Consistency, not perfection. |
| **Adapts to women's biology** | Her own period tracker, cycle predictions, conditions (PCOS, endometriosis, migraines, PMDD, thyroid, perimenopause), age band, and life stage. Poor sleep, a heavy calendar, or the days before her period trigger "Ease off today" with a lighter plan. Cycle advice is based on her logged pattern and is switched off on hormonal birth control or after menopause. |
| **A health profile that keeps evolving** | 90 days of sleep, HRV, stress, activity, cycle, symptoms, mood, and nutrition become patterns ("after high-stress days she sleeps 34 min less", "headaches cluster in the 5 days before her period") and a one-page summary to share with her doctor. |
| **Learns what works for her** | A weekly check-in shows a hill of her consistency with a flag per week and what moved since she started. HerLife learns when she slips (a weekday, busy days, her pre-period week) and which habits actually move her outcomes, then picks the next move: shrink a habit, add a nudge, swap the lever, or level up. |
| **Minimal effort** | Oura sync, a 10 second morning check-in when she has no wearable, voice logging that Claude sorts into sleep, movement, nutrition, mood, and symptoms, and a mood check-in asked at most once a day. |

Every number explains itself: tap the info icon to see how it is calculated. Seasonal advice cites its sources (CDC, NIH, NIMH, peer-reviewed sleep research) with clickable links.

## Who it is for

Busy women who put everyone else first: the student juggling midterms, clubs, research, and an internship; the working mother in tech with two kids and back-to-back meetings; the night-shift nurse with no wearable at all. They do not have 20 minutes a day to enter health data, and they should not need it.

## Why nothing on the market does this

| | Apple Health / Oura | Google Calendar | Period trackers | **HerLife** |
|---|---|---|---|---|
| Collects body data | Yes | No | Cycle only | Yes, plus check-ins and voice |
| Plans health actions into her actual day | No | She does it | No | **Yes, finds the gap and books it** |
| Adapts the plan to sleep, stress, cycle, conditions, life stage | No | No | Cycle phase only | **Yes, every day** |
| Learns which habits work for her and adjusts | No | No | No | **Yes, weekly** |
| Produces a record her doctor can use | Raw charts | No | Cycle log | **Patterns plus a written summary** |

**Why not just use Apple Health, Google Calendar, and a period tracker?** HerLife is not a bundle of the three. It actively coordinates them, understands her changing health needs, and takes the cognitive load of planning preventive health off her shoulders.

## Impact

Small actions done daily compound into better sleep, steadier energy, and fewer bad weeks. That is Medicine 3.0: preventive, personal, and focused on longevity and quality of life. When she does see a clinician, she walks in with the story instead of starting from zero.

## Try it (3 minute demo)

Open **https://herlife-six.vercel.app**. The first page offers two ways in:

1. **Create my account**: answer the onboarding questions yourself (life stage, cycle, the shape of your days, conditions, goals), connect a simulated Oura ring and calendar, and swipe to pick your habits.
2. **Sign in to a demo profile**: pick one of the women below. Each still walks through onboarding with her answers prefilled and a banner explaining who she is.

**To test another profile, tap Switch** (top right of every screen in the app). It returns to this first page without deleting anything, so you can create an account or pick a different demo profile.

| Persona | Shows |
|---|---|
| **Maya, 32**, busy working woman, migraines | Full onboarding, cycle map and prediction, Today's plan, Book it, voice log, doctor summary |
| **Dana, 41**, one week in, "lose 10 pounds", "high energy all day" | Weekly check-in: consistency hill with flags, what moved, what HerLife learned, next move |
| **Hana, 27**, student, endometriosis and anemia | Period day 2, heavy flow, ease-off plan |
| **Ines, 30**, freelancer, PCOS | Longer cycles, strength goals |
| **Sofia, 35**, stay-at-home parent, PMDD | The week before her period |
| **Ava, 24**, student athlete, cycles stretching | Cycle-change card that never suggests menopause under 40 |
| **Lena, 48**, working, perimenopause | Menopause transition signal and a question for her doctor |
| **Priya, 29**, night-shift nurse, no wearable, no calendar | Everything from a morning check-in and voice notes |

Shortcut for presenters: `https://herlife-six.vercel.app/?profile=dana` (or `maya`, `priya`, `hana`, `ines`, `sofia`, `ava`, `lena`) skips onboarding and opens that profile's app directly.

A browser that has used HerLife before reopens where it left off; tap **Switch** to get back to the first page. Oura and calendar connections are simulated in this build; real sign in is implemented and turns on once the providers approve the app.

## How it is built

```
web/index.html            One UI for the hosted app (and a claude.ai artifact)
backend/webapp/           FastAPI server for Vercel: page, AI, saved records, Oura and Google OAuth
  static/bloom-platform.js  Answers the page's window.claude calls with our own server
backend/api/              Production API: users, sync, cycle signal, habits, impact, plan, record
backend/canonical/        Vendor-neutral health models, Oura adapter, cycle builder
backend/insights.py       90-day patterns for the doctor record
backend/mcp_server.py     Local MCP server for live Oura in the Claude desktop app
mobile/                   Expo iOS app scaffold (HealthKit and on-device speech seams)
evals/                    Cycle persona evals and Claude evals
tests/                    API, web server, and web app tests
docs/                     Pitch, research (28 citations), data model, API, demo script
```

- **Claude** (Anthropic API) writes habits from free-text goals, sorts voice logs, maps any goal to the signals and outcomes to track, personalizes the daily plan, and writes the doctor summary. Every call has a timeout and a deterministic fallback, so the app never dead-ends.
- **Data**: Oura API v2 through a canonical adapter (any wearable next), Bloom's own period log for the cycle, Oura temperature only to confirm ovulation, and Postgres (Neon) for each person's record.
- **Research-backed rules**: cycle staging follows STRAW+10, normal ranges follow FIGO and ACOG, and seasonal advice cites the CDC, NIH, and NIMH. See [docs/RESEARCH.md](docs/RESEARCH.md).
- **Not a medical device.** HerLife offers lifestyle suggestions and keeps a record; it never diagnoses.

## Run it locally

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env              # add ANTHROPIC_API_KEY; everything else is optional
.venv/bin/uvicorn backend.webapp.server:app --port 8080
open http://localhost:8080
```

Deploying: see [docs/WEBAPP.md](docs/WEBAPP.md) (Vercel plus Neon Postgres; every push to `main` redeploys).

## Tests and evals

Run everything from the repo root after setup (`python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`). Every command below passes; GitHub Actions runs them on each push.

| Command | What it checks | Result |
|---|---|---|
| `.venv/bin/python -m pytest -q tests` | Production API (cycle signal, habit impact, seasons, age bands, check-ins) and the hosted web server (page, per-person records, delete, AI and connector fallbacks, health) | 85 passed |
| `node --test tests/web/app.test.mjs` | Every demo persona renders every onboarding step and tab with zero errors; phase boundaries; temperature cycle estimate; never menopause under 40; stress load; adaptive next move | 7 passed |
| `.venv/bin/python -m evals.cycle_personas` | Cycle prediction across 11 body types x 10 seeds, logged periods and temperature only | exits 0 |
| `.venv/bin/python -m evals.claude_evals` | AI features against the real models: log sorting, habit suggestions, goal to signal mapping, doctor summary; no diagnosis, no em dashes, no cycle talk on the pill, never menopause under 40 (needs `ANTHROPIC_API_KEY`) | 51/51 checks |

All four in one go:

```bash
.venv/bin/python -m pytest -q tests && node --test tests/web/app.test.mjs && .venv/bin/python -m evals.cycle_personas && .venv/bin/python -m evals.claude_evals
```

Details in [docs/TESTING.md](docs/TESTING.md).

## What's next

- An AI chat that hears a discomfort description and suggests self-care or whether to see a doctor
- Automatic preventive scheduling (screenings and vaccines by age and conditions), linked to her insurance plan and nearby clinics
- Medications and supplements, including their effects on hormones, sleep, and stress, plus lab results and biomarkers
- Apple Health and Google Fit integrations, and live activities that check in on her phone
- Local signals such as weather, season, and outbreaks that prompt timely preventive actions
- A mood index and short, trustworthy health education
