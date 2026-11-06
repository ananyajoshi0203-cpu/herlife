---
name: publish-demo
description: Regenerate the Oura synthetic data, embed web/seed.json into web/index.html, and republish the judges' artifact. Use when the user says "republish", "ship the demo", "refresh data", or after editing web/index.html.
---

1. Run `.venv/bin/python -m backend.pipeline` from the repo root. It must print row counts for all five tables.
2. Run `.venv/bin/python -m backend.embed_seed` to replace the `<script id="seed" type="application/json">` block in `web/index.html` with the fresh seed.
3. Publish `web/index.html` with the Artifact tool, same file path as before so the judges' URL stays stable. Keep `capabilities: {sample: {}}`.
4. Reply with the link and the current cycle day and phase from the pipeline output.

Never publish a page with an em dash in visible copy; grep for it first.
