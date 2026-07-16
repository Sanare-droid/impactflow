# ImpactFlow Field (Expo)

Phase 5/Track D field app: offline-first beneficiary registration against the ImpactFlow API.

## Requirements

- **Expo SDK 54** (matches current Expo Go)
- Node 20+

## Setup

```bash
cd apps/mobile
npm install --legacy-peer-deps
npx expo start -c
```

Set `EXPO_PUBLIC_API_URL` to your API base (use your machine LAN IP for a physical device), e.g. `http://192.168.1.20:8000`.

## Current capability

- Secure token storage + refresh on reconnect / 401
- Sign in via `/api/v1/auth/login`
- **SQLite** local store: communities, households, beneficiaries, mutation queue
- Offline create beneficiary (`sync_status: pending`) → push on reconnect
- Pull deltas via `updated_after` (server-wins for synced rows)
- Online/offline banner, last sync time, retry failed queue

## Offline test (exit criteria)

1. Sign in while online (pulls caseload).
2. Enable airplane mode.
3. Register a beneficiary — appears locally as **pending**.
4. Disable airplane mode — Sync banner pushes queue; badge clears.
5. Confirm the person appears in the web Beneficiaries list.
