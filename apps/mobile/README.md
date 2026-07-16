# ImpactFlow Field (Expo)

Phase 5 field app for beneficiary registration against the ImpactFlow API.

## Requirements

- **Expo SDK 54** (matches current Expo Go)
- Node 20+

## Setup

```bash
cd apps/mobile
npm install
npx expo start -c
```

Set `EXPO_PUBLIC_API_URL` to your API base (use your machine LAN IP for a physical device), e.g. `http://192.168.1.20:8000`.

## Current capability

- Secure token storage
- Sign in via `/api/v1/auth/login`
- List beneficiaries
- Register beneficiaries

Offline SQLite queue + sync lands in a follow-up iteration; the domain APIs already support field enrollment.
