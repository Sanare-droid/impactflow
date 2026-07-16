import { api } from "@/lib/api";
import { getMeta, setMeta } from "@/lib/db";
import * as repo from "@/lib/db/repo";

export type SyncResult = {
  pushed: number;
  failed: number;
  pulled: number;
  lastSyncAt: string | null;
};

let syncing = false;

async function pullAllPages<T>(
  fetchPage: (page: number, updated_after?: string) => Promise<{
    items: T[];
    meta: { total: number; page: number; page_size: number };
  }>,
  updated_after?: string | null,
): Promise<T[]> {
  const items: T[] = [];
  let page = 1;
  for (;;) {
    const res = await fetchPage(page, updated_after || undefined);
    items.push(...res.items);
    const loaded = page * res.meta.page_size;
    if (loaded >= res.meta.total || res.items.length === 0) break;
    page += 1;
    if (page > 50) break;
  }
  return items;
}

async function pushQueue(): Promise<{ pushed: number; failed: number }> {
  const mutations = await repo.listPendingMutations();
  let pushed = 0;
  let failed = 0;

  for (const mut of mutations) {
    try {
      const payload = JSON.parse(mut.payload_json) as Record<string, unknown>;
      if (mut.entity_type === "beneficiary" && mut.op === "create") {
        const created = await api.createBeneficiary(payload);
        await repo.markBeneficiarySynced(mut.local_id, {
          id: created.id,
          code: created.code,
          updated_at: created.updated_at,
        });
      } else if (mut.entity_type === "beneficiary" && mut.op === "update") {
        const local = await repo.getBeneficiary(mut.local_id);
        if (!local?.server_id) throw new Error("Missing server id for update");
        const updated = await api.updateBeneficiary(local.server_id, payload);
        await repo.markBeneficiarySynced(mut.local_id, {
          id: updated.id,
          code: updated.code,
          updated_at: updated.updated_at,
        });
      } else if (mut.entity_type === "community" && mut.op === "create") {
        await api.createCommunity(payload);
      } else if (mut.entity_type === "household" && mut.op === "create") {
        await api.createHousehold(payload);
      } else if (mut.entity_type === "survey_response" && mut.op === "create") {
        const surveyId = payload.survey_id as string | undefined;
        if (!surveyId) throw new Error("Survey has not synced yet — try again once online");
        const { survey_id: _drop, ...body } = payload;
        const created = await api.submitSurveyResponse(surveyId, body);
        await repo.markSurveyResponseSynced(mut.local_id, {
          id: created.id,
          survey_id: created.survey_id,
          updated_at: created.updated_at,
        });
      } else {
        throw new Error(`Unsupported mutation ${mut.entity_type}:${mut.op}`);
      }
      await repo.markMutationDone(mut.id);
      pushed += 1;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Sync failed";
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

async function pullDeltas(): Promise<number> {
  const last = await getMeta("last_sync_at");
  let pulled = 0;

  const communities = await pullAllPages(
    (page, updated_after) => api.listCommunities({ page, updated_after }),
    last,
  );
  for (const c of communities) {
    await repo.upsertServerCommunity(c);
    pulled += 1;
  }

  const households = await pullAllPages(
    (page, updated_after) => api.listHouseholds({ page, updated_after }),
    last,
  );
  for (const h of households) {
    await repo.upsertServerHousehold(h);
    pulled += 1;
  }

  const beneficiaries = await pullAllPages(
    (page, updated_after) => api.listBeneficiaries({ page, updated_after }),
    last,
  );
  for (const b of beneficiaries) {
    await repo.upsertServerBeneficiary(b);
    pulled += 1;
  }

  // Surveys: fetch published forms + their current schema so capture works offline.
  const surveys = await pullAllPages(
    (page, updated_after) => api.listSurveys({ page, updated_after, status: "published" }),
    last,
  );
  for (const s of surveys) {
    try {
      const detail = await api.getSurvey(s.id);
      await repo.upsertServerSurvey({ ...detail.survey, version: detail.version });
    } catch {
      // Schema fetch failed (e.g. permission change); keep prior cached copy.
      await repo.upsertServerSurvey({ ...s, version: null });
    }
    pulled += 1;
  }

  return pulled;
}

/** Push local queue then pull server changes (server-wins for synced rows). */
export async function runSync(): Promise<SyncResult> {
  if (syncing) {
    return {
      pushed: 0,
      failed: 0,
      pulled: 0,
      lastSyncAt: await getMeta("last_sync_at"),
    };
  }
  syncing = true;
  try {
    // Refresh auth before batch when possible
    if (api.refreshToken) {
      await api.refresh();
    }
    const { pushed, failed } = await pushQueue();
    const pulled = await pullDeltas();
    const lastSyncAt = new Date().toISOString();
    await setMeta("last_sync_at", lastSyncAt);
    return { pushed, failed, pulled, lastSyncAt };
  } finally {
    syncing = false;
  }
}

export async function getLastSyncAt(): Promise<string | null> {
  return getMeta("last_sync_at");
}
