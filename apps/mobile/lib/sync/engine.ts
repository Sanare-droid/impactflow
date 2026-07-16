import { api } from "@/lib/api";
import {
  getAppVersion,
  getDeviceId,
  getDeviceName,
  getOrCreateDeviceKey,
  getPlatform,
  setDeviceId,
} from "@/lib/device";
import { getMeta, setMeta } from "@/lib/db";
import * as repo from "@/lib/db/repo";
import { nowIso } from "@/lib/id";

export type SyncResult = {
  pushed: number;
  failed: number;
  pulled: number;
  conflicts: number;
  lastSyncAt: string | null;
  sessionId?: string;
};

let syncing = false;

async function ensureDeviceRegistered(): Promise<string> {
  const existing = await getDeviceId();
  if (existing) return existing;

  const device = await api.registerDevice({
    device_key: await getOrCreateDeviceKey(),
    name: getDeviceName(),
    platform: getPlatform(),
    app_version: getAppVersion(),
  });
  await setDeviceId(device.id);
  return device.id;
}

function buildPushMutations(
  mutations: Awaited<ReturnType<typeof repo.listPendingMutations>>,
) {
  return mutations.map((mut) => ({
    client_mutation_id: mut.id,
    entity_type: mut.entity_type,
    op: mut.op,
    local_id: mut.local_id,
    payload: JSON.parse(mut.payload_json) as Record<string, unknown>,
    created_at: mut.created_at,
  }));
}

async function applyPushResults(
  mutations: Awaited<ReturnType<typeof repo.listPendingMutations>>,
  results: Array<{
    client_mutation_id: string;
    status: string;
    server_id?: string;
    error?: string;
    record?: Record<string, unknown>;
  }>,
): Promise<{ pushed: number; failed: number }> {
  const byId = new Map(mutations.map((m) => [m.id, m]));
  let pushed = 0;
  let failed = 0;

  for (const result of results) {
    const mut = byId.get(result.client_mutation_id);
    if (!mut && result.status === "duplicate") {
      pushed += 1;
      continue;
    }
    if (!mut) continue;

    if (result.status === "applied" || result.status === "duplicate") {
      await repo.markMutationDone(mut.id);
      if (mut.entity_type === "beneficiary" && result.server_id) {
        await repo.markBeneficiarySynced(mut.local_id, {
          id: result.server_id,
          code: (result.record?.code as string) ?? undefined,
          updated_at: (result.record?.updated_at as string) ?? undefined,
        });
      } else if (mut.entity_type === "survey_response" && result.server_id) {
        await repo.markSurveyResponseSynced(mut.local_id, {
          id: result.server_id,
          survey_id: (result.record?.survey_id as string) ?? undefined,
          updated_at: (result.record?.updated_at as string) ?? undefined,
        });
      }
      pushed += 1;
    } else {
      const message = result.error ?? "Sync failed";
      await repo.markMutationFailed(mut.id, message);
      if (mut.entity_type === "beneficiary") {
        await repo.markBeneficiaryFailed(mut.local_id, message);
      } else if (mut.entity_type === "survey_response") {
        await repo.markSurveyResponseFailed(mut.local_id, message);
      }
      failed += 1;
    }
  }
  return { pushed, failed };
}

async function applyPullResults(pull: Record<string, unknown>): Promise<number> {
  let pulled = 0;

  for (const c of (pull.communities as Array<Record<string, unknown>>) ?? []) {
    await repo.upsertServerCommunity(c as Parameters<typeof repo.upsertServerCommunity>[0]);
    pulled += 1;
  }

  for (const h of (pull.households as Array<Record<string, unknown>>) ?? []) {
    await repo.upsertServerHousehold(h as Parameters<typeof repo.upsertServerHousehold>[0]);
    pulled += 1;
  }

  for (const b of (pull.beneficiaries as Array<Record<string, unknown>>) ?? []) {
    await repo.upsertServerBeneficiary(b as Parameters<typeof repo.upsertServerBeneficiary>[0]);
    pulled += 1;
    const row = (await repo.listLocalBeneficiaries()).find((x) => x.server_id === b.id);
    if (row) {
      await repo.indexSearchEntry({
        entity_type: "beneficiary",
        entity_local_id: row.local_id,
        entity_server_id: row.server_id,
        title: `${row.first_name} ${row.last_name}`,
        subtitle: row.code ?? row.phone,
        keywords: [row.first_name, row.last_name, row.code, row.phone].filter(Boolean).join(" "),
      });
    }
  }

  for (const s of (pull.surveys as Array<Record<string, unknown>>) ?? []) {
    const version = s.version as Record<string, unknown> | undefined;
    await repo.upsertServerSurvey({
      ...(s as Parameters<typeof repo.upsertServerSurvey>[0]),
      version: version
        ? {
            id: String(version.id),
            survey_id: String(version.survey_id),
            version: Number(version.version),
            title: String(version.title ?? ""),
            schema: (version.schema as Record<string, unknown>) ?? {},
            published_at: (version.published_at as string) ?? null,
          }
        : null,
    });
    pulled += 1;
  }

  for (const t of (pull.tasks as Array<Record<string, unknown>>) ?? []) {
    await repo.upsertServerTask(t as Parameters<typeof repo.upsertServerTask>[0]);
    pulled += 1;
  }

  for (const n of (pull.notifications as Array<Record<string, unknown>>) ?? []) {
    await repo.upsertServerNotification(n as Parameters<typeof repo.upsertServerNotification>[0]);
    pulled += 1;
  }

  return pulled;
}

/** Batch push + pull via POST /sync/run with device registration and conflict logging. */
export async function runSync(): Promise<SyncResult> {
  if (syncing) {
    return {
      pushed: 0,
      failed: 0,
      pulled: 0,
      conflicts: 0,
      lastSyncAt: await getMeta("last_sync_at"),
    };
  }
  syncing = true;
  const startedAt = nowIso();
  try {
    if (api.refreshToken) {
      await api.refresh();
    }

    const deviceId = await ensureDeviceRegistered();
    const last = await getMeta("last_sync_at");
    const pendingMutations = await repo.listPendingMutations();
    const pendingMedia = await repo.listPendingMedia();

    const response = await api.syncRun({
      device_id: deviceId,
      client_version: getAppVersion(),
      push: {
        device_id: deviceId,
        mutations: buildPushMutations(pendingMutations),
      },
      pull: {
        since: last ?? undefined,
        entities: [
          "communities",
          "households",
          "beneficiaries",
          "surveys",
          "tasks",
          "notifications",
        ],
        page_size: 100,
      },
    });

    const pushResults = response.push?.results ?? [];
    const { pushed, failed } = await applyPushResults(pendingMutations, pushResults);
    const pulled = await applyPullResults(response.pull ?? {});

    const lastSyncAt = response.pull?.sync_token ?? new Date().toISOString();
    await setMeta("last_sync_at", lastSyncAt);

    await api.heartbeat(deviceId, {
      app_version: getAppVersion(),
      pending_uploads: pendingMedia.length + (await repo.queueCounts()).pending,
    });

    const conflictLogs = (await repo.listSyncLogs(50)).filter(
      (l) => l.status === "conflict" && l.started_at >= startedAt,
    ).length;

    await repo.logSyncSession({
      session_id: response.session_id,
      status: response.status,
      pushed_count: pushed,
      pulled_count: pulled,
      failed_count: failed,
      conflict_count: conflictLogs,
      started_at: startedAt,
      completed_at: nowIso(),
      payload: { device_id: deviceId },
    });

    return {
      pushed,
      failed,
      pulled,
      conflicts: conflictLogs,
      lastSyncAt,
      sessionId: response.session_id,
    };
  } catch (err) {
    const message = err instanceof Error ? err.message : "Sync failed";
    await repo.logSyncSession({
      status: "failed",
      pushed_count: 0,
      pulled_count: 0,
      failed_count: 1,
      error_message: message,
      started_at: startedAt,
      completed_at: nowIso(),
    });
    throw err;
  } finally {
    syncing = false;
  }
}

export async function getLastSyncAt(): Promise<string | null> {
  return getMeta("last_sync_at");
}
