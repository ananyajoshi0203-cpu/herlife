# Bloom for iOS

Expo (SDK 58, Expo Router, TypeScript) app in `mobile/`. It talks only to the FastAPI service in `backend/api/` (see `docs/API.md`); it never reads a vendor field.

## Run it

```
.venv/bin/uvicorn backend.api.app:app --reload --host 0.0.0.0   # the API
cd mobile && npm install
EXPO_PUBLIC_API_URL=http://<your-mac-LAN-ip>:8000 npx expo start
```

`EXPO_PUBLIC_API_URL` defaults to `http://localhost:8000`, which works in the iOS simulator but not on a phone. Expo inlines `EXPO_PUBLIC_*` at bundle time, so restart the dev server after changing it. Type-check with `npm run typecheck`.

Dependencies are pinned to exact versions published at least two weeks before they were added (`npm install --before=<date>`), so `npx expo-doctor` reports patch drift against the newest SDK 58 release. That is expected; bump deliberately with `npx expo install --check`.

## Why native

The web artifact proves the story; the phone is where the record actually fills itself in.

| Unlocks | Why it matters for Bloom | Seam |
|---|---|---|
| **HealthKit** | Most iPhone owners already have sleep, steps, HRV, resting heart rate, and often cycle data in Apple Health. No ring required. | `mobile/src/health/healthkit.ts` (interface plus TODO for `react-native-health`) |
| **Background Oura sync** | Today's plan should be ready when she wakes, without opening the app. Background fetch calls `POST /users/{id}/sync`. | Next step |
| **Notifications** | A gentle evening nudge for the mood check-in is the difference between a 3 day and a 90 day record. | Next step (`expo-notifications`) |
| **On-device speech** | Voice notes are transcribed on the phone, so audio never leaves it; only text goes to `POST /logs/voice`. | `mobile/src/speech/dictation.ts` (TODO for `expo-speech-recognition`) |

HealthKit, background tasks, and speech all need a development build (`npx expo run:ios` or `eas build --profile development`); Expo Go cannot load them.

## Architecture

```
mobile/src/
  api.ts               typed client; types mirror backend/api/schemas.py by hand
  session.tsx          user and last habit suggestions in the keychain (expo-secure-store), today's phase
  theme.ts             light and dark tokens and phase colors copied from web/index.html
  copy.ts              goals, life stages, phase and category copy from web/index.html
  useRemote.ts         load, error, reload for one API call
  components/ui.tsx    Screen, Card, Button, Chip, Title, Body
  components/SwipeDeck.tsx   check-in deck: gesture-handler v3 usePanGesture plus Reanimated, with button fallbacks
  health/healthkit.ts  HealthKit seam
  speech/dictation.ts  on-device speech seam
  app/
    index.tsx          redirects to onboarding or Today
    onboarding.tsx     profile, life stage, two goals; creates the user, runs a mock sync, asks for habits
    (tabs)/today.tsx   plan/today: cycle note, ease-off card with reasons, four pillars
    (tabs)/habits.tsx  swipe right for done (POST checks), left for not today; weekly consistency
    (tabs)/log.tsx     text now, dictation later; logs/voice sorts into categories
    (tabs)/record.tsx  doctor summary from /record, shared via the iOS share sheet
```

The accent color follows her cycle phase, as on the web: Today sets the phase from `plan.cycle`, and every screen reads it through `usePhaseTheme()`. Life stages without cycle tracking keep follicular green.

## Known gaps and next steps

1. **API: add `GET /users/{id}/habits`.** There is no way to list habits, so the phone caches the last `habits/suggest` response. A reinstall loses the deck even though the server still has the habits.
2. **API: report today's checks.** Consistency is per week, so the deck cannot tell which habits were already checked today after an app restart.
3. **Auth.** The API has no authentication; the user id in the keychain is the only credential. This must land before any real user data leaves a simulator.
4. **HealthKit**: implement `healthkit.ts`, then add a backend Apple Health adapter (the `add-wearable` skill) and an ingest endpoint so mapping happens server side into canonical models.
5. **Oura OAuth** in-app via `expo-web-browser` against `/oura/authorize`, then background sync.
6. **Mood check-in** screen plus a daily local notification.
7. **Period logging** (`POST /periods`) and a cycle view (`GET /cycle`); both are in `api.ts` but have no screen yet.
8. Generate `api.ts` types from `/openapi.json` once the schema settles, instead of mirroring by hand.
