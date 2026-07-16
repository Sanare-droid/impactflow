import * as SQLite from "expo-sqlite";

let dbPromise: Promise<SQLite.SQLiteDatabase> | null = null;

const SCHEMA = `
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sync_meta (
  key TEXT PRIMARY KEY NOT NULL,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS communities (
  local_id TEXT PRIMARY KEY NOT NULL,
  server_id TEXT,
  organization_id TEXT,
  name TEXT NOT NULL,
  code TEXT,
  community_type TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  payload_json TEXT NOT NULL DEFAULT '{}',
  sync_status TEXT NOT NULL DEFAULT 'synced',
  last_error TEXT,
  updated_at_local TEXT NOT NULL,
  updated_at_server TEXT
);

CREATE TABLE IF NOT EXISTS households (
  local_id TEXT PRIMARY KEY NOT NULL,
  server_id TEXT,
  organization_id TEXT,
  community_local_id TEXT,
  community_server_id TEXT,
  name TEXT NOT NULL,
  code TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  payload_json TEXT NOT NULL DEFAULT '{}',
  sync_status TEXT NOT NULL DEFAULT 'synced',
  last_error TEXT,
  updated_at_local TEXT NOT NULL,
  updated_at_server TEXT
);

CREATE TABLE IF NOT EXISTS beneficiaries (
  local_id TEXT PRIMARY KEY NOT NULL,
  server_id TEXT,
  organization_id TEXT,
  household_local_id TEXT,
  household_server_id TEXT,
  community_local_id TEXT,
  community_server_id TEXT,
  first_name TEXT NOT NULL,
  last_name TEXT NOT NULL,
  code TEXT,
  phone TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  consent_data_use INTEGER NOT NULL DEFAULT 1,
  payload_json TEXT NOT NULL DEFAULT '{}',
  sync_status TEXT NOT NULL DEFAULT 'synced',
  last_error TEXT,
  updated_at_local TEXT NOT NULL,
  updated_at_server TEXT
);

CREATE TABLE IF NOT EXISTS mutation_queue (
  id TEXT PRIMARY KEY NOT NULL,
  entity_type TEXT NOT NULL,
  local_id TEXT NOT NULL,
  op TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  attempts INTEGER NOT NULL DEFAULT 0,
  last_error TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_beneficiaries_sync ON beneficiaries(sync_status);
CREATE INDEX IF NOT EXISTS idx_queue_status ON mutation_queue(status, created_at);
CREATE INDEX IF NOT EXISTS idx_communities_server ON communities(server_id);
CREATE INDEX IF NOT EXISTS idx_households_server ON households(server_id);
CREATE INDEX IF NOT EXISTS idx_beneficiaries_server ON beneficiaries(server_id);
`;

export async function getDb(): Promise<SQLite.SQLiteDatabase> {
  if (!dbPromise) {
    dbPromise = (async () => {
      const db = await SQLite.openDatabaseAsync("impactflow_field.db");
      await db.execAsync(SCHEMA);
      return db;
    })();
  }
  return dbPromise;
}

export async function getMeta(key: string): Promise<string | null> {
  const db = await getDb();
  const row = await db.getFirstAsync<{ value: string }>(
    "SELECT value FROM sync_meta WHERE key = ?",
    [key],
  );
  return row?.value ?? null;
}

export async function setMeta(key: string, value: string): Promise<void> {
  const db = await getDb();
  await db.runAsync(
    "INSERT INTO sync_meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
    [key, value],
  );
}
