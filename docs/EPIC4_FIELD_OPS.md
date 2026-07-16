# Epic 4 — Field Operations, Offline Intelligence & Mobile Experience Revamp

**API version:** 0.16.0 · **Migration:** `0015_phase15`

## Architecture (extends, does not rewrite)

| Layer | Approach |
|-------|----------|
| **Survey Engine (Epic 1)** | Reused — published schemas cached locally; responses submitted via sync queue with `client_mutation_id` |
| **AI Copilot (Epic 2)** | Online assist on mobile; offline requests queued in `ai_request_queue` (processed after sync) |
| **Workflow Engine (Epic 3)** | Tasks pulled via delta sync; completion pushed as `task:update` mutations |
| **Notifications** | Reused — inbox cached locally; read status synced back via batch push |
| **Sync transport** | New `POST /sync/run` batch endpoint; extends existing CRUD + `updated_after` filters |
| **Devices** | New `field_devices`, `sync_sessions`, `sync_mutation_logs` models |

## Backend endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/devices/register` | Register or re-activate field device |
| POST | `/devices/{id}/heartbeat` | Last seen, storage, pending uploads |
| GET | `/devices` | Admin device list |
| PATCH | `/devices/{id}` | Deactivate / revoke |
| POST | `/sync/push` | Batch push mutations (idempotent) |
| POST | `/sync/pull` | Multi-entity delta pull |
| POST | `/sync/run` | Combined push + pull session |
| GET | `/sync/sessions` | Sync history |
| GET | `/field-ops/metrics` | Dashboard KPIs |
| POST/GET | `/media/uploads` | Media queue registration + monitoring |

## Mobile (apps/mobile v1.0.0)

- **Design system:** Manrope typography, teal enterprise palette, light/dark theme, reusable UI components
- **Navigation:** Auth login + 5-tab layout (Home, Beneficiaries, Surveys, Tasks, More)
- **SQLite v3:** beneficiaries, surveys, tasks, notifications, media_queue, sync_logs, search_index, settings
- **Sync:** Batch `POST /sync/run`, device registration, server-wins conflicts logged locally
- **Offline:** Beneficiary register/edit, survey capture, task completion, notification inbox

## Web

- **Field Operations Dashboard:** `/app/field-operations` — devices, sync sessions, pending media

## Conflict resolution (v1)

Server wins. Local copy preserved on device. Conflicts logged in `sync_conflict_logs` + local `sync_logs`.

## Permissions

- `sync:push`, `sync:pull`, `devices:register` — field officers
- `devices:read`, `devices:manage` — org admins / managers

## Delivered status (Definition of Done)

- [x] Offline beneficiary registration and update
- [x] Offline survey completion (existing engine extended)
- [x] Offline task list and completion sync
- [x] Batch synchronization with idempotency
- [x] Device registration and heartbeat
- [x] Sync sessions and monitoring on web
- [x] Media upload queue (local + server registration)
- [x] Mobile design system revamp (Manrope, components, tabs, dashboard)
- [x] Existing notification service reused (cache + read sync)
- [x] Tenant isolation + RBAC tests
- [x] API **0.16.0** · migration **0015_phase15**
- [x] Tests in `tests/test_field_ops.py`

## Deferred

- Encrypted SQLite, biometric/PIN unlock
- Push notifications (FCM/APNs)
- Full offline maps / geofencing
- Binary media upload to object storage (queue metadata only v1)
- SMS/Teams channels
