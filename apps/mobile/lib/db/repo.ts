import { newLocalId, nowIso } from "@/lib/id";
import { getDb } from "@/lib/db";
import type {
  LocalBeneficiary,
  LocalCommunity,
  LocalHousehold,
  LocalSurvey,
  LocalSurveyResponse,
  MutationRow,
  SyncStatus,
} from "@/lib/db/types";

export async function listLocalBeneficiaries(): Promise<LocalBeneficiary[]> {
  const db = await getDb();
  return db.getAllAsync<LocalBeneficiary>(
    "SELECT * FROM beneficiaries ORDER BY updated_at_local DESC",
  );
}

export async function createLocalBeneficiary(input: {
  organization_id?: string | null;
  first_name: string;
  last_name: string;
  phone?: string;
}): Promise<LocalBeneficiary> {
  const db = await getDb();
  const local_id = newLocalId();
  const updated_at_local = nowIso();
  const payload = {
    first_name: input.first_name,
    last_name: input.last_name,
    phone: input.phone || null,
    consent_data_use: true,
    status: "active",
  };
  await db.runAsync(
    `INSERT INTO beneficiaries (
      local_id, server_id, organization_id, household_local_id, household_server_id,
      community_local_id, community_server_id, first_name, last_name, code, phone,
      status, consent_data_use, payload_json, sync_status, last_error,
      updated_at_local, updated_at_server
    ) VALUES (?, NULL, ?, NULL, NULL, NULL, NULL, ?, ?, NULL, ?, 'active', 1, ?, 'pending', NULL, ?, NULL)`,
    [
      local_id,
      input.organization_id ?? null,
      input.first_name,
      input.last_name,
      input.phone ?? null,
      JSON.stringify(payload),
      updated_at_local,
    ],
  );
  await enqueueMutation({
    entity_type: "beneficiary",
    local_id,
    op: "create",
    payload,
  });
  const row = await db.getFirstAsync<LocalBeneficiary>(
    "SELECT * FROM beneficiaries WHERE local_id = ?",
    [local_id],
  );
  if (!row) throw new Error("Failed to create local beneficiary");
  return row;
}

export async function upsertServerBeneficiary(remote: {
  id: string;
  organization_id?: string;
  first_name: string;
  last_name: string;
  code?: string | null;
  phone?: string | null;
  status?: string;
  household_id?: string | null;
  community_id?: string | null;
  updated_at?: string;
}): Promise<void> {
  const db = await getDb();
  const existing = await db.getFirstAsync<LocalBeneficiary>(
    "SELECT * FROM beneficiaries WHERE server_id = ?",
    [remote.id],
  );
  // Server-wins only for synced rows; preserve pending local edits
  if (existing && existing.sync_status !== "synced") {
    return;
  }
  const updated_at_local = nowIso();
  const payload = JSON.stringify(remote);
  if (existing) {
    await db.runAsync(
      `UPDATE beneficiaries SET
        first_name = ?, last_name = ?, code = ?, phone = ?, status = ?,
        household_server_id = ?, community_server_id = ?, payload_json = ?,
        sync_status = 'synced', last_error = NULL, updated_at_local = ?,
        updated_at_server = ?, organization_id = COALESCE(organization_id, ?)
       WHERE local_id = ?`,
      [
        remote.first_name,
        remote.last_name,
        remote.code ?? null,
        remote.phone ?? null,
        remote.status ?? "active",
        remote.household_id ?? null,
        remote.community_id ?? null,
        payload,
        updated_at_local,
        remote.updated_at ?? null,
        remote.organization_id ?? null,
        existing.local_id,
      ],
    );
  } else {
    await db.runAsync(
      `INSERT INTO beneficiaries (
        local_id, server_id, organization_id, household_local_id, household_server_id,
        community_local_id, community_server_id, first_name, last_name, code, phone,
        status, consent_data_use, payload_json, sync_status, last_error,
        updated_at_local, updated_at_server
      ) VALUES (?, ?, ?, NULL, ?, NULL, ?, ?, ?, ?, ?, ?, 1, ?, 'synced', NULL, ?, ?)`,
      [
        newLocalId(),
        remote.id,
        remote.organization_id ?? null,
        remote.household_id ?? null,
        remote.community_id ?? null,
        remote.first_name,
        remote.last_name,
        remote.code ?? null,
        remote.phone ?? null,
        remote.status ?? "active",
        payload,
        updated_at_local,
        remote.updated_at ?? null,
      ],
    );
  }
}

export async function markBeneficiarySynced(
  local_id: string,
  server: { id: string; code?: string | null; updated_at?: string },
): Promise<void> {
  const db = await getDb();
  await db.runAsync(
    `UPDATE beneficiaries SET server_id = ?, code = COALESCE(?, code),
      sync_status = 'synced', last_error = NULL, updated_at_server = ?,
      updated_at_local = ? WHERE local_id = ?`,
    [server.id, server.code ?? null, server.updated_at ?? null, nowIso(), local_id],
  );
}

export async function markBeneficiaryFailed(local_id: string, error: string): Promise<void> {
  const db = await getDb();
  await db.runAsync(
    `UPDATE beneficiaries SET sync_status = 'failed', last_error = ?, updated_at_local = ? WHERE local_id = ?`,
    [error.slice(0, 500), nowIso(), local_id],
  );
}

export async function upsertServerCommunity(remote: {
  id: string;
  organization_id?: string;
  name: string;
  code?: string | null;
  community_type?: string | null;
  status?: string;
  updated_at?: string;
}): Promise<void> {
  const db = await getDb();
  const existing = await db.getFirstAsync<LocalCommunity>(
    "SELECT * FROM communities WHERE server_id = ?",
    [remote.id],
  );
  if (existing && existing.sync_status !== "synced") return;
  const updated_at_local = nowIso();
  const payload = JSON.stringify(remote);
  if (existing) {
    await db.runAsync(
      `UPDATE communities SET name = ?, code = ?, community_type = ?, status = ?,
        payload_json = ?, sync_status = 'synced', last_error = NULL,
        updated_at_local = ?, updated_at_server = ? WHERE local_id = ?`,
      [
        remote.name,
        remote.code ?? null,
        remote.community_type ?? null,
        remote.status ?? "active",
        payload,
        updated_at_local,
        remote.updated_at ?? null,
        existing.local_id,
      ],
    );
  } else {
    await db.runAsync(
      `INSERT INTO communities (
        local_id, server_id, organization_id, name, code, community_type, status,
        payload_json, sync_status, last_error, updated_at_local, updated_at_server
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'synced', NULL, ?, ?)`,
      [
        newLocalId(),
        remote.id,
        remote.organization_id ?? null,
        remote.name,
        remote.code ?? null,
        remote.community_type ?? null,
        remote.status ?? "active",
        payload,
        updated_at_local,
        remote.updated_at ?? null,
      ],
    );
  }
}

export async function upsertServerHousehold(remote: {
  id: string;
  organization_id?: string;
  community_id?: string | null;
  name: string;
  code?: string | null;
  status?: string;
  updated_at?: string;
}): Promise<void> {
  const db = await getDb();
  const existing = await db.getFirstAsync<LocalHousehold>(
    "SELECT * FROM households WHERE server_id = ?",
    [remote.id],
  );
  if (existing && existing.sync_status !== "synced") return;
  const updated_at_local = nowIso();
  const payload = JSON.stringify(remote);
  if (existing) {
    await db.runAsync(
      `UPDATE households SET name = ?, code = ?, status = ?, community_server_id = ?,
        payload_json = ?, sync_status = 'synced', last_error = NULL,
        updated_at_local = ?, updated_at_server = ? WHERE local_id = ?`,
      [
        remote.name,
        remote.code ?? null,
        remote.status ?? "active",
        remote.community_id ?? null,
        payload,
        updated_at_local,
        remote.updated_at ?? null,
        existing.local_id,
      ],
    );
  } else {
    await db.runAsync(
      `INSERT INTO households (
        local_id, server_id, organization_id, community_local_id, community_server_id,
        name, code, status, payload_json, sync_status, last_error,
        updated_at_local, updated_at_server
      ) VALUES (?, ?, ?, NULL, ?, ?, ?, ?, ?, 'synced', NULL, ?, ?)`,
      [
        newLocalId(),
        remote.id,
        remote.organization_id ?? null,
        remote.community_id ?? null,
        remote.name,
        remote.code ?? null,
        remote.status ?? "active",
        payload,
        updated_at_local,
        remote.updated_at ?? null,
      ],
    );
  }
}

// -------- Surveys (server-wins, v1 conflict policy — see docstring below) --------

/**
 * Conflict policy (v1): surveys are read-only on the device, so pulled
 * versions always overwrite the local cache — server wins unconditionally.
 * Survey *responses* are append-only from the device (create only), so there
 * is nothing to reconcile there either; retries are deduped server-side by
 * `client_mutation_id`.
 */
export async function upsertServerSurvey(remote: {
  id: string;
  organization_id?: string;
  name: string;
  code?: string | null;
  category?: string | null;
  status: string;
  current_version: number;
  updated_at?: string;
  version?: {
    id: string;
    survey_id: string;
    version: number;
    title: string;
    schema: Record<string, unknown>;
    published_at?: string | null;
    created_at?: string;
  } | null;
}): Promise<void> {
  const db = await getDb();
  const existing = await db.getFirstAsync<LocalSurvey>(
    "SELECT * FROM surveys WHERE server_id = ?",
    [remote.id],
  );
  const updated_at_local = nowIso();
  const payload = JSON.stringify(remote);
  // Preserve the previously cached schema if this pull didn't include one
  // (e.g. the schema fetch failed) so an offline form doesn't go blank.
  const schemaJson = remote.version
    ? JSON.stringify(remote.version.schema ?? {})
    : existing?.schema_json ?? "{}";
  if (existing) {
    await db.runAsync(
      `UPDATE surveys SET name = ?, code = ?, category = ?, status = ?,
        current_version = ?, payload_json = ?, schema_json = ?,
        sync_status = 'synced', last_error = NULL, updated_at_local = ?,
        updated_at_server = ?, organization_id = COALESCE(organization_id, ?)
       WHERE local_id = ?`,
      [
        remote.name,
        remote.code ?? null,
        remote.category ?? null,
        remote.status,
        remote.current_version,
        payload,
        schemaJson,
        updated_at_local,
        remote.updated_at ?? null,
        remote.organization_id ?? null,
        existing.local_id,
      ],
    );
  } else {
    await db.runAsync(
      `INSERT INTO surveys (
        local_id, server_id, organization_id, name, code, category, status,
        current_version, payload_json, schema_json, sync_status, last_error,
        updated_at_local, updated_at_server
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'synced', NULL, ?, ?)`,
      [
        newLocalId(),
        remote.id,
        remote.organization_id ?? null,
        remote.name,
        remote.code ?? null,
        remote.category ?? null,
        remote.status,
        remote.current_version,
        payload,
        schemaJson,
        updated_at_local,
        remote.updated_at ?? null,
      ],
    );
  }
}

export async function listLocalSurveys(): Promise<LocalSurvey[]> {
  const db = await getDb();
  return db.getAllAsync<LocalSurvey>(
    "SELECT * FROM surveys WHERE status = 'published' ORDER BY name ASC",
  );
}

export async function getLocalSurvey(local_id: string): Promise<LocalSurvey | null> {
  const db = await getDb();
  return (
    (await db.getFirstAsync<LocalSurvey>("SELECT * FROM surveys WHERE local_id = ?", [
      local_id,
    ])) ?? null
  );
}

export async function createLocalSurveyResponse(input: {
  survey_local_id: string;
  survey_server_id: string | null;
  organization_id?: string | null;
  beneficiary_local_id?: string | null;
  beneficiary_server_id?: string | null;
  status: "draft" | "submitted";
  answers: Record<string, unknown>;
}): Promise<LocalSurveyResponse> {
  const db = await getDb();
  const local_id = newLocalId();
  const client_mutation_id = newLocalId();
  const updated_at_local = nowIso();
  const answersJson = JSON.stringify(input.answers);
  await db.runAsync(
    `INSERT INTO survey_responses (
      local_id, server_id, survey_local_id, survey_server_id, organization_id,
      beneficiary_local_id, beneficiary_server_id, status, answers_json,
      client_mutation_id, payload_json, sync_status, last_error,
      updated_at_local, updated_at_server
    ) VALUES (?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, '{}', 'pending', NULL, ?, NULL)`,
    [
      local_id,
      input.survey_local_id,
      input.survey_server_id ?? null,
      input.organization_id ?? null,
      input.beneficiary_local_id ?? null,
      input.beneficiary_server_id ?? null,
      input.status,
      answersJson,
      client_mutation_id,
      updated_at_local,
    ],
  );
  if (input.status === "submitted") {
    await enqueueMutation({
      entity_type: "survey_response",
      local_id,
      op: "create",
      payload: {
        survey_id: input.survey_server_id,
        answers: input.answers,
        status: "submitted",
        beneficiary_id: input.beneficiary_server_id ?? undefined,
        client_mutation_id,
      },
    });
  }
  const row = await db.getFirstAsync<LocalSurveyResponse>(
    "SELECT * FROM survey_responses WHERE local_id = ?",
    [local_id],
  );
  if (!row) throw new Error("Failed to create local survey response");
  return row;
}

export async function listLocalSurveyResponses(
  survey_local_id?: string,
): Promise<LocalSurveyResponse[]> {
  const db = await getDb();
  if (survey_local_id) {
    return db.getAllAsync<LocalSurveyResponse>(
      "SELECT * FROM survey_responses WHERE survey_local_id = ? ORDER BY updated_at_local DESC",
      [survey_local_id],
    );
  }
  return db.getAllAsync<LocalSurveyResponse>(
    "SELECT * FROM survey_responses ORDER BY updated_at_local DESC",
  );
}

export async function listPendingSurveyResponses(): Promise<LocalSurveyResponse[]> {
  const db = await getDb();
  return db.getAllAsync<LocalSurveyResponse>(
    "SELECT * FROM survey_responses WHERE sync_status IN ('pending', 'failed') AND status = 'submitted'",
  );
}

export async function markSurveyResponseSynced(
  local_id: string,
  server: { id: string; survey_id?: string; updated_at?: string },
): Promise<void> {
  const db = await getDb();
  await db.runAsync(
    `UPDATE survey_responses SET server_id = ?, survey_server_id = COALESCE(?, survey_server_id),
      sync_status = 'synced', last_error = NULL, updated_at_server = ?,
      updated_at_local = ? WHERE local_id = ?`,
    [server.id, server.survey_id ?? null, server.updated_at ?? null, nowIso(), local_id],
  );
}

export async function markSurveyResponseFailed(local_id: string, error: string): Promise<void> {
  const db = await getDb();
  await db.runAsync(
    `UPDATE survey_responses SET sync_status = 'failed', last_error = ?, updated_at_local = ? WHERE local_id = ?`,
    [error.slice(0, 500), nowIso(), local_id],
  );
}

export async function getSurveyResponse(local_id: string): Promise<LocalSurveyResponse | null> {
  const db = await getDb();
  return (
    (await db.getFirstAsync<LocalSurveyResponse>(
      "SELECT * FROM survey_responses WHERE local_id = ?",
      [local_id],
    )) ?? null
  );
}

export async function enqueueMutation(input: {
  entity_type: MutationRow["entity_type"];
  local_id: string;
  op: MutationRow["op"];
  payload: Record<string, unknown>;
}): Promise<void> {
  const db = await getDb();
  const now = nowIso();
  await db.runAsync(
    `INSERT INTO mutation_queue (
      id, entity_type, local_id, op, payload_json, status, attempts, last_error, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, 'pending', 0, NULL, ?, ?)`,
    [
      newLocalId(),
      input.entity_type,
      input.local_id,
      input.op,
      JSON.stringify(input.payload),
      now,
      now,
    ],
  );
}

export async function listPendingMutations(): Promise<MutationRow[]> {
  const db = await getDb();
  return db.getAllAsync<MutationRow>(
    `SELECT * FROM mutation_queue
     WHERE status IN ('pending', 'failed')
     ORDER BY
       CASE entity_type
         WHEN 'community' THEN 0
         WHEN 'household' THEN 1
         WHEN 'beneficiary' THEN 2
         ELSE 3
       END,
       created_at ASC`,
  );
}

export async function markMutationDone(id: string): Promise<void> {
  const db = await getDb();
  await db.runAsync(
    `UPDATE mutation_queue SET status = 'done', updated_at = ? WHERE id = ?`,
    [nowIso(), id],
  );
}

export async function markMutationFailed(id: string, error: string): Promise<void> {
  const db = await getDb();
  await db.runAsync(
    `UPDATE mutation_queue SET status = 'failed', attempts = attempts + 1,
      last_error = ?, updated_at = ? WHERE id = ?`,
    [error.slice(0, 500), nowIso(), id],
  );
}

export async function retryFailedMutations(): Promise<number> {
  const db = await getDb();
  const result = await db.runAsync(
    `UPDATE mutation_queue SET status = 'pending', updated_at = ? WHERE status = 'failed'`,
    [nowIso()],
  );
  await db.runAsync(
    `UPDATE beneficiaries SET sync_status = 'pending', last_error = NULL WHERE sync_status = 'failed'`,
  );
  await db.runAsync(
    `UPDATE communities SET sync_status = 'pending', last_error = NULL WHERE sync_status = 'failed'`,
  );
  await db.runAsync(
    `UPDATE households SET sync_status = 'pending', last_error = NULL WHERE sync_status = 'failed'`,
  );
  await db.runAsync(
    `UPDATE survey_responses SET sync_status = 'pending', last_error = NULL WHERE sync_status = 'failed'`,
  );
  return result.changes;
}

export async function queueCounts(): Promise<{
  pending: number;
  failed: number;
}> {
  const db = await getDb();
  const pending = await db.getFirstAsync<{ c: number }>(
    `SELECT COUNT(*) as c FROM mutation_queue WHERE status IN ('pending', 'processing')`,
  );
  const failed = await db.getFirstAsync<{ c: number }>(
    `SELECT COUNT(*) as c FROM mutation_queue WHERE status = 'failed'`,
  );
  return { pending: pending?.c ?? 0, failed: failed?.c ?? 0 };
}

export async function getBeneficiary(local_id: string): Promise<LocalBeneficiary | null> {
  const db = await getDb();
  return (
    (await db.getFirstAsync<LocalBeneficiary>(
      "SELECT * FROM beneficiaries WHERE local_id = ?",
      [local_id],
    )) ?? null
  );
}

export type { SyncStatus };
