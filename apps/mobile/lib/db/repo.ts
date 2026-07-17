import { newLocalId, nowIso } from "@/lib/id";
import { getDb } from "@/lib/db";
import type {
  LocalBeneficiary,
  LocalCommunity,
  LocalHousehold,
  LocalNotification,
  LocalSurvey,
  LocalSurveyResponse,
  LocalTask,
  MediaQueueRow,
  MutationRow,
  SearchIndexRow,
  SyncLogRow,
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
  await indexSearchEntry({
    entity_type: "beneficiary",
    entity_local_id: local_id,
    title: `${input.first_name} ${input.last_name}`,
    subtitle: input.phone,
    keywords: [input.first_name, input.last_name, input.phone].filter(Boolean).join(" "),
  });
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
    await logSyncConflict({
      entity_type: "beneficiary",
      local_id: existing.local_id,
      server_id: remote.id,
      local_snapshot: JSON.parse(existing.payload_json),
      server_snapshot: remote as Record<string, unknown>,
    });
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

export async function searchBeneficiaries(query: string): Promise<LocalBeneficiary[]> {
  const db = await getDb();
  const q = `%${query.trim().toLowerCase()}%`;
  if (!q || q === "%%") return listLocalBeneficiaries();
  return db.getAllAsync<LocalBeneficiary>(
    `SELECT * FROM beneficiaries
     WHERE LOWER(first_name || ' ' || last_name) LIKE ?
        OR LOWER(COALESCE(code, '')) LIKE ?
        OR LOWER(COALESCE(phone, '')) LIKE ?
     ORDER BY updated_at_local DESC`,
    [q, q, q],
  );
}

export async function updateLocalBeneficiary(
  local_id: string,
  input: { first_name?: string; last_name?: string; phone?: string | null },
): Promise<void> {
  const db = await getDb();
  const existing = await getBeneficiary(local_id);
  if (!existing) throw new Error("Beneficiary not found");

  const payload = {
    ...JSON.parse(existing.payload_json),
    ...input,
  };
  await db.runAsync(
    `UPDATE beneficiaries SET first_name = COALESCE(?, first_name),
      last_name = COALESCE(?, last_name), phone = COALESCE(?, phone),
      payload_json = ?, sync_status = 'pending', updated_at_local = ?
     WHERE local_id = ?`,
    [
      input.first_name ?? null,
      input.last_name ?? null,
      input.phone ?? null,
      JSON.stringify(payload),
      nowIso(),
      local_id,
    ],
  );
  if (existing.server_id) {
    await enqueueMutation({
      entity_type: "beneficiary",
      local_id,
      op: "update",
      payload: {
        server_id: existing.server_id,
        first_name: input.first_name ?? existing.first_name,
        last_name: input.last_name ?? existing.last_name,
        phone: input.phone ?? existing.phone,
      },
    });
  } else {
    // Edit before first sync — refresh pending create payload
    const db2 = await getDb();
    const pending = await db2.getFirstAsync<{ id: string; payload_json: string }>(
      `SELECT id, payload_json FROM mutation_queue
       WHERE local_id = ? AND entity_type = 'beneficiary' AND op = 'create'
         AND status IN ('pending', 'failed')
       ORDER BY created_at DESC LIMIT 1`,
      [local_id],
    );
    if (pending) {
      const next = {
        ...JSON.parse(pending.payload_json),
        first_name: input.first_name ?? existing.first_name,
        last_name: input.last_name ?? existing.last_name,
        phone: input.phone ?? existing.phone,
      };
      await db2.runAsync(
        `UPDATE mutation_queue SET payload_json = ?, updated_at = ?, status = 'pending' WHERE id = ?`,
        [JSON.stringify(next), nowIso(), pending.id],
      );
    }
  }
  await indexSearchEntry({
    entity_type: "beneficiary",
    entity_local_id: local_id,
    entity_server_id: existing.server_id,
    title: `${input.first_name ?? existing.first_name} ${input.last_name ?? existing.last_name}`,
    subtitle: existing.code ?? existing.phone,
    keywords: [existing.first_name, existing.last_name, existing.code, existing.phone]
      .filter(Boolean)
      .join(" "),
  });
}

// -------- Tasks (server-wins cache from sync pull) --------

export async function upsertServerTask(remote: {
  id: string;
  organization_id?: string;
  project_id?: string;
  title: string;
  description?: string | null;
  status?: string;
  priority?: string | null;
  assignee_id?: string | null;
  due_date?: string | null;
  completed_at?: string | null;
  updated_at?: string;
}): Promise<void> {
  const db = await getDb();
  const existing = await db.getFirstAsync<LocalTask>(
    "SELECT * FROM tasks WHERE server_id = ?",
    [remote.id],
  );
  const updated_at_local = nowIso();
  const payload = JSON.stringify(remote);
  if (existing) {
    await db.runAsync(
      `UPDATE tasks SET title = ?, description = ?, status = ?, priority = ?,
        assignee_id = ?, due_date = ?, completed_at = ?, payload_json = ?,
        sync_status = 'synced', last_error = NULL, updated_at_local = ?,
        updated_at_server = ?, organization_id = COALESCE(organization_id, ?),
        project_id = COALESCE(?, project_id)
       WHERE local_id = ?`,
      [
        remote.title,
        remote.description ?? null,
        remote.status ?? "open",
        remote.priority ?? null,
        remote.assignee_id ?? null,
        remote.due_date ?? null,
        remote.completed_at ?? null,
        payload,
        updated_at_local,
        remote.updated_at ?? null,
        remote.organization_id ?? null,
        remote.project_id ?? null,
        existing.local_id,
      ],
    );
    await indexSearchEntry({
      entity_type: "task",
      entity_local_id: existing.local_id,
      entity_server_id: remote.id,
      title: remote.title,
      subtitle: remote.status ?? undefined,
      keywords: [remote.title, remote.description, remote.status].filter(Boolean).join(" "),
    });
  } else {
    const local_id = newLocalId();
    await db.runAsync(
      `INSERT INTO tasks (
        local_id, server_id, organization_id, project_id, title, description,
        status, priority, assignee_id, due_date, completed_at, payload_json,
        sync_status, last_error, updated_at_local, updated_at_server
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'synced', NULL, ?, ?)`,
      [
        local_id,
        remote.id,
        remote.organization_id ?? null,
        remote.project_id ?? null,
        remote.title,
        remote.description ?? null,
        remote.status ?? "open",
        remote.priority ?? null,
        remote.assignee_id ?? null,
        remote.due_date ?? null,
        remote.completed_at ?? null,
        payload,
        updated_at_local,
        remote.updated_at ?? null,
      ],
    );
    await indexSearchEntry({
      entity_type: "task",
      entity_local_id: local_id,
      entity_server_id: remote.id,
      title: remote.title,
      subtitle: remote.status ?? undefined,
      keywords: [remote.title, remote.description, remote.status].filter(Boolean).join(" "),
    });
  }
}

export async function listLocalTasks(status?: string): Promise<LocalTask[]> {
  const db = await getDb();
  if (status) {
    return db.getAllAsync<LocalTask>(
      "SELECT * FROM tasks WHERE status = ? ORDER BY due_date ASC, updated_at_local DESC",
      [status],
    );
  }
  return db.getAllAsync<LocalTask>(
    "SELECT * FROM tasks ORDER BY CASE status WHEN 'open' THEN 0 WHEN 'in_progress' THEN 1 ELSE 2 END, due_date ASC",
  );
}

export async function getLocalTask(local_id: string): Promise<LocalTask | null> {
  const db = await getDb();
  return (await db.getFirstAsync<LocalTask>("SELECT * FROM tasks WHERE local_id = ?", [local_id])) ?? null;
}

export async function countOpenTasks(): Promise<number> {
  const db = await getDb();
  const row = await db.getFirstAsync<{ c: number }>(
    "SELECT COUNT(*) as c FROM tasks WHERE status IN ('open', 'in_progress')",
  );
  return row?.c ?? 0;
}

export async function updateLocalTaskStatus(
  local_id: string,
  status: string,
): Promise<void> {
  const db = await getDb();
  const existing = await getLocalTask(local_id);
  if (!existing) throw new Error("Task not found");
  if (!existing.server_id) throw new Error("Task is not synced yet");
  const now = nowIso();
  const completed_at = status === "done" ? now : null;
  await db.runAsync(
    `UPDATE tasks SET status = ?, completed_at = ?, sync_status = 'pending',
      last_error = NULL, updated_at_local = ? WHERE local_id = ?`,
    [status, completed_at, now, local_id],
  );
  await enqueueMutation({
    entity_type: "task",
    local_id,
    op: "update",
    payload: {
      server_id: existing.server_id,
      status,
      ...(status === "done" ? { completed_at } : {}),
    },
  });
}

export async function markTaskSynced(
  local_id: string,
  remote?: { status?: string; completed_at?: string | null; updated_at?: string },
): Promise<void> {
  const db = await getDb();
  await db.runAsync(
    `UPDATE tasks SET sync_status = 'synced', last_error = NULL,
      status = COALESCE(?, status),
      completed_at = CASE WHEN ? IS NOT NULL THEN ? ELSE completed_at END,
      updated_at_server = COALESCE(?, updated_at_server),
      updated_at_local = ?
     WHERE local_id = ?`,
    [
      remote?.status ?? null,
      remote?.completed_at ?? null,
      remote?.completed_at ?? null,
      remote?.updated_at ?? null,
      nowIso(),
      local_id,
    ],
  );
}

export async function markTaskFailed(local_id: string, message: string): Promise<void> {
  const db = await getDb();
  await db.runAsync(
    `UPDATE tasks SET sync_status = 'failed', last_error = ?, updated_at_local = ? WHERE local_id = ?`,
    [message, nowIso(), local_id],
  );
}

/** Remove local tasks that are no longer assigned to this user on the server. */
export async function purgeTasksNotIn(serverIds: string[]): Promise<number> {
  const db = await getDb();
  const keep = new Set(serverIds);
  const rows = await db.getAllAsync<LocalTask>(
    "SELECT * FROM tasks WHERE server_id IS NOT NULL AND sync_status = 'synced'",
  );
  let removed = 0;
  for (const row of rows) {
    if (row.server_id && !keep.has(row.server_id)) {
      await db.runAsync("DELETE FROM tasks WHERE local_id = ?", [row.local_id]);
      await db.runAsync(
        "DELETE FROM search_index WHERE entity_type = 'task' AND entity_local_id = ?",
        [row.local_id],
      );
      removed += 1;
    }
  }
  return removed;
}

// -------- Notifications (cache from sync pull only) --------

export async function upsertServerNotification(remote: {
  id: string;
  organization_id?: string;
  user_id?: string;
  event_type?: string;
  title: string;
  body?: string | null;
  link?: string | null;
  severity?: string | null;
  status?: string | null;
  read_at?: string | null;
  created_at?: string;
  updated_at?: string;
}): Promise<void> {
  const db = await getDb();
  const existing = await db.getFirstAsync<LocalNotification>(
    "SELECT * FROM notifications WHERE server_id = ?",
    [remote.id],
  );
  const updated_at_local = nowIso();
  const payload = JSON.stringify(remote);
  if (existing) {
    await db.runAsync(
      `UPDATE notifications SET title = ?, body = ?, link = ?, severity = ?,
        status = ?, read_at = ?, event_type = ?, payload_json = ?,
        sync_status = 'synced', updated_at_local = ?, updated_at_server = ?
       WHERE local_id = ?`,
      [
        remote.title,
        remote.body ?? null,
        remote.link ?? null,
        remote.severity ?? null,
        remote.status ?? null,
        remote.read_at ?? null,
        remote.event_type ?? null,
        payload,
        updated_at_local,
        remote.updated_at ?? remote.created_at ?? null,
        existing.local_id,
      ],
    );
  } else {
    await db.runAsync(
      `INSERT INTO notifications (
        local_id, server_id, organization_id, user_id, event_type, title, body,
        link, severity, status, read_at, payload_json, sync_status,
        updated_at_local, updated_at_server
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'synced', ?, ?)`,
      [
        newLocalId(),
        remote.id,
        remote.organization_id ?? null,
        remote.user_id ?? null,
        remote.event_type ?? null,
        remote.title,
        remote.body ?? null,
        remote.link ?? null,
        remote.severity ?? null,
        remote.status ?? null,
        remote.read_at ?? null,
        payload,
        updated_at_local,
        remote.updated_at ?? remote.created_at ?? null,
      ],
    );
  }
}

export async function listLocalNotifications(unreadOnly = false): Promise<LocalNotification[]> {
  const db = await getDb();
  if (unreadOnly) {
    return db.getAllAsync<LocalNotification>(
      "SELECT * FROM notifications WHERE read_at IS NULL ORDER BY updated_at_local DESC",
    );
  }
  return db.getAllAsync<LocalNotification>(
    "SELECT * FROM notifications ORDER BY updated_at_local DESC LIMIT 100",
  );
}

export async function countUnreadNotifications(): Promise<number> {
  const db = await getDb();
  const row = await db.getFirstAsync<{ c: number }>(
    "SELECT COUNT(*) as c FROM notifications WHERE read_at IS NULL",
  );
  return row?.c ?? 0;
}

export async function markNotificationRead(local_id: string): Promise<void> {
  const db = await getDb();
  const existing = await db.getFirstAsync<LocalNotification>(
    "SELECT * FROM notifications WHERE local_id = ?",
    [local_id],
  );
  await db.runAsync(
    "UPDATE notifications SET read_at = ?, updated_at_local = ?, sync_status = 'pending' WHERE local_id = ?",
    [nowIso(), nowIso(), local_id],
  );
  if (existing?.server_id) {
    await enqueueMutation({
      entity_type: "notification",
      local_id,
      op: "update",
      payload: { server_id: existing.server_id },
    });
  }
}

// -------- Media queue --------

export async function enqueueMediaUpload(input: {
  entity_type: string;
  entity_local_id?: string;
  entity_server_id?: string;
  file_uri: string;
  file_name: string;
  mime_type?: string;
  file_size?: number;
}): Promise<MediaQueueRow> {
  const db = await getDb();
  const local_id = newLocalId();
  const client_mutation_id = newLocalId();
  const now = nowIso();
  await db.runAsync(
    `INSERT INTO media_queue (
      local_id, server_id, client_mutation_id, entity_type, entity_local_id,
      entity_server_id, file_uri, file_name, mime_type, file_size, status,
      last_error, payload_json, created_at, updated_at
    ) VALUES (?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', NULL, '{}', ?, ?)`,
    [
      local_id,
      client_mutation_id,
      input.entity_type,
      input.entity_local_id ?? null,
      input.entity_server_id ?? null,
      input.file_uri,
      input.file_name,
      input.mime_type ?? null,
      input.file_size ?? 0,
      now,
      now,
    ],
  );
  const row = await db.getFirstAsync<MediaQueueRow>(
    "SELECT * FROM media_queue WHERE local_id = ?",
    [local_id],
  );
  if (!row) throw new Error("Failed to enqueue media");
  return row;
}

export async function listPendingMedia(): Promise<MediaQueueRow[]> {
  const db = await getDb();
  return db.getAllAsync<MediaQueueRow>(
    "SELECT * FROM media_queue WHERE status IN ('pending', 'failed') ORDER BY created_at ASC",
  );
}

export async function markMediaSynced(local_id: string, server_id: string): Promise<void> {
  const db = await getDb();
  await db.runAsync(
    "UPDATE media_queue SET status = 'synced', server_id = ?, updated_at = ? WHERE local_id = ?",
    [server_id, nowIso(), local_id],
  );
}

export async function markMediaFailed(local_id: string, error: string): Promise<void> {
  const db = await getDb();
  await db.runAsync(
    "UPDATE media_queue SET status = 'failed', last_error = ?, updated_at = ? WHERE local_id = ?",
    [error.slice(0, 500), nowIso(), local_id],
  );
}

// -------- Sync logs & conflicts --------

export async function logSyncSession(input: {
  session_id?: string | null;
  status: string;
  pushed_count: number;
  pulled_count: number;
  failed_count: number;
  conflict_count?: number;
  error_message?: string | null;
  started_at: string;
  completed_at?: string | null;
  payload?: Record<string, unknown>;
}): Promise<void> {
  const db = await getDb();
  await db.runAsync(
    `INSERT INTO sync_logs (
      id, session_id, status, pushed_count, pulled_count, failed_count,
      conflict_count, error_message, started_at, completed_at, payload_json
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    [
      newLocalId(),
      input.session_id ?? null,
      input.status,
      input.pushed_count,
      input.pulled_count,
      input.failed_count,
      input.conflict_count ?? 0,
      input.error_message ?? null,
      input.started_at,
      input.completed_at ?? null,
      JSON.stringify(input.payload ?? {}),
    ],
  );
}

export async function logSyncConflict(input: {
  entity_type: string;
  local_id: string;
  server_id?: string | null;
  local_snapshot: Record<string, unknown>;
  server_snapshot: Record<string, unknown>;
}): Promise<void> {
  await logSyncSession({
    status: "conflict",
    pushed_count: 0,
    pulled_count: 0,
    failed_count: 0,
    conflict_count: 1,
    started_at: nowIso(),
    completed_at: nowIso(),
    payload: input,
  });
}

export async function listSyncLogs(limit = 20): Promise<SyncLogRow[]> {
  const db = await getDb();
  return db.getAllAsync<SyncLogRow>(
    "SELECT * FROM sync_logs ORDER BY started_at DESC LIMIT ?",
    [limit],
  );
}

// -------- Search index --------

export async function indexSearchEntry(input: {
  entity_type: string;
  entity_local_id: string;
  entity_server_id?: string | null;
  title: string;
  subtitle?: string | null;
  keywords?: string;
}): Promise<void> {
  const db = await getDb();
  const id = `${input.entity_type}:${input.entity_local_id}`;
  const updated_at = nowIso();
  await db.runAsync(
    `INSERT INTO search_index (id, entity_type, entity_local_id, entity_server_id, title, subtitle, keywords, updated_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?)
     ON CONFLICT(id) DO UPDATE SET
       title = excluded.title, subtitle = excluded.subtitle,
       keywords = excluded.keywords, updated_at = excluded.updated_at,
       entity_server_id = COALESCE(excluded.entity_server_id, search_index.entity_server_id)`,
    [
      id,
      input.entity_type,
      input.entity_local_id,
      input.entity_server_id ?? null,
      input.title,
      input.subtitle ?? null,
      input.keywords ?? input.title,
      updated_at,
    ],
  );
}

export async function searchAll(query: string, limit = 30): Promise<SearchIndexRow[]> {
  const db = await getDb();
  const q = `%${query.trim().toLowerCase()}%`;
  if (!query.trim()) return [];
  return db.getAllAsync<SearchIndexRow>(
    `SELECT * FROM search_index
     WHERE LOWER(title || ' ' || COALESCE(subtitle, '') || ' ' || keywords) LIKE ?
     ORDER BY updated_at DESC LIMIT ?`,
    [q, limit],
  );
}

// -------- Settings & profile --------

export async function getSetting(key: string): Promise<string | null> {
  const db = await getDb();
  const row = await db.getFirstAsync<{ value: string }>(
    "SELECT value FROM settings WHERE key = ?",
    [key],
  );
  return row?.value ?? null;
}

export async function setSetting(key: string, value: string): Promise<void> {
  const db = await getDb();
  await db.runAsync(
    "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
    [key, value],
  );
}

export async function getProfileField(key: string): Promise<string | null> {
  const db = await getDb();
  const row = await db.getFirstAsync<{ value: string }>(
    "SELECT value FROM user_profile WHERE key = ?",
    [key],
  );
  return row?.value ?? null;
}

export async function setProfileField(key: string, value: string): Promise<void> {
  const db = await getDb();
  await db.runAsync(
    "INSERT INTO user_profile (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
    [key, value],
  );
}

export async function countBeneficiaries(): Promise<number> {
  const db = await getDb();
  const row = await db.getFirstAsync<{ c: number }>("SELECT COUNT(*) as c FROM beneficiaries");
  return row?.c ?? 0;
}

export async function countLocalSurveys(): Promise<number> {
  const db = await getDb();
  const row = await db.getFirstAsync<{ c: number }>(
    "SELECT COUNT(*) as c FROM surveys WHERE status = 'published'",
  );
  return row?.c ?? 0;
}

export type { SyncStatus };
