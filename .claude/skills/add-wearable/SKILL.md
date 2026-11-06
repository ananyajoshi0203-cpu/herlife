---
name: add-wearable
description: Add a new wearable source (Apple Health, Whoop, Garmin, Fitbit) by writing a connector and an adapter into the canonical models. Use when the user says "add Whoop", "connect Apple Health", or "new wearable".
---

The canonical models in `backend/canonical/models.py` are the contract. Do not change them to fit a vendor.

1. Add a `Source` enum member.
2. `backend/connectors/<vendor>.py`: same shape as `OuraConnector` (`is_live`, `fetch`, `fetch_all`, mock mode reading `data/raw/<vendor>_*.json`).
3. `backend/canonical/<vendor>_adapter.py`: one `adapt_<table>` per table the vendor covers; convert units at the edge (seconds to minutes, kJ to kcal).
4. If the vendor has no temperature signal, do not infer cycle; leave `cycle` to self report.
5. Wire into `backend/pipeline.py` and run it. Ask the `canonical-reviewer` agent to check the adapter.
