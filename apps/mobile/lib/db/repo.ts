import { newLocalId, nowIso } from "@/lib/id";
import { getDb } from "@/lib/db";
import type {
  LocalBeneficiary,
  LocalCommunity,
  LocalHousehold,
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
       CASE entity_type WHEN 'community' THEN 0 WHEN 'household' THEN 1 ELSE 2 END,
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
