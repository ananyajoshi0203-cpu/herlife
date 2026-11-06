# HerLife web app

One UI, two hosts. `web/index.html` runs as the claude.ai artifact (judges) and as a real web app
served by `backend/webapp/server.py`. On the web app, `backend/webapp/static/bloom-platform.js`
answers the page's `window.claude.use(...)` calls with HerLife's own server:

| Page asks for | claude.ai artifact | HerLife web app |
|---|---|---|
| `sample` (Claude) | claude.ai sampling | `POST /api/ai/json`, Anthropic SDK (haiku for quick, sonnet for default) |
| `db` + `user` (saved record) | artifact private store | `GET/PUT/DELETE /api/state`, SQLite, per-browser person cookie |
| `mcp` Oura | local `bloom_oura` MCP server | `GET /api/oura/daily`, Oura OAuth per person |
| `calendar` | sample day | `GET/POST /api/calendar/events`, Google OAuth per person |
| Voice | sample dictation | browser speech recognition (Chrome, Safari) |

## Run locally
```
OURA... see below
.venv/bin/uvicorn backend.webapp.server:app --port 8080
open http://localhost:8080
```

| Env var | For | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | Claude habits, log sorting, plan, summary | Without it every feature uses HerLife's built-in fallback |
| `OURA_CLIENT_ID`, `OURA_CLIENT_SECRET` | Oura sign in | Register at cloud.ouraring.com/oauth/applications, redirect `http://localhost:8080/oura/callback` |
| `OURA_REDIRECT_URI` | Oura | Set to `https://<host>/oura/callback` when deployed |
| `BLOOM_DEV_OURA_TOKEN` | Local only | Your own Oura token, read for every visitor. Never set on a shared deploy |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Google Calendar | Google Cloud console, OAuth web client, scope `calendar.events`, redirect `http://localhost:8080/google/callback` |
| `GOOGLE_REDIRECT_URI` | Calendar | `https://<host>/google/callback` when deployed |

## Deploy to Vercel
1. Database: create a Postgres database (Vercel Storage → Neon, or neon.tech). Copy its connection string.
2. vercel.com → Add New Project → import `ananyajoshi0203-cpu/herlife`. Framework preset: Other. No build command.
3. Environment variables: `DATABASE_URL` (required on Vercel), `ANTHROPIC_API_KEY`, `BLOOM_SECURE_COOKIES=1`.
   Later, for real sign in: `OURA_CLIENT_ID`/`OURA_CLIENT_SECRET`/`OURA_REDIRECT_URI=https://<app>.vercel.app/oura/callback`,
   `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`/`GOOGLE_REDIRECT_URI=https://<app>.vercel.app/google/callback`.
4. Deploy. `api/index.py` exposes the FastAPI app; `vercel.json` routes every path to it. Tables are created on first request.

The server refuses to start on Vercel without `DATABASE_URL`, because Vercel's filesystem does not persist SQLite.
`Dockerfile` + `render.yaml` remain for any container host.
