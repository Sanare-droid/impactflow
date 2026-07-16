import * as SQLite from "expo-sqlite";

let dbPromise: Promise<SQLite.SQLiteDatabase> | null = null;

/**
 * Bump this whenever a migration below adds/alters tables. Existing installs
 * run only the migrations newer than their stored `schema_version` meta key,
 * so upgrades are additive and never drop local data.
 */
const SCHEMA_VERSION = 2;

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

/** schema_version 2: published surveys cache + offline survey responses. */
const MIGRATION_V2 = `
CREATE TABLE IF NOT EXISTS surveys (
  local_id TEXT PRIMARY KEY NOT NULL,
  server_id TEXT,
  organization_id TEXT,
  name TEXT NOT NULL,
  code TEXT,
  category TEXT,
  status TEXT NOT NULL DEFAULT 'published',
  current_version INTEGER NOT NULL DEFAULT 1,
  payload_json TEXT NOT NULL DEFAULT '{}',
  schema_json TEXT NOT NULL DEFAULT '{}',
  sync_status TEXT NOT NULL DEFAULT 'synced',
  last_error TEXT,
  updated_at_local TEXT NOT NULL,
  updated_at_server TEXT
);

CREATE TABLE IF NOT EXISTS survey_responses (
  local_id TEXT PRIMARY KEY NOT NULL,
  server_id TEXT,
  survey_local_id TEXT,
  survey_server_id TEXT,
  organization_id TEXT,
  beneficiary_local_id TEXT,
  beneficiary_server_id TEXT,
  status TEXT NOT NULL DEFAULT 'draft',
  answers_json TEXT NOT NULL DEFAULT '{}',
  client_mutation_id TEXT NOT NULL,
  payload_json TEXT NOT NULL DEFAULT '{}',
  sync_status TEXT NOT NULL DEFAULT 'pending',
  last_error TEXT,
  updated_at_local TEXT NOT NULL,
  updated_at_server TEXT
);

CREATE INDEX IF NOT EXISTS idx_surveys_server ON surveys(server_id);
CREATE INDEX IF NOT EXISTS idx_surveys_status ON surveys(status);
CREATE INDEX IF NOT EXISTS idx_survey_responses_server ON survey_responses(server_id);
CREATE INDEX IF NOT EXISTS idx_survey_responses_survey ON survey_responses(survey_local_id);
CREATE INDEX IF NOT EXISTS idx_survey_responses_sync ON survey_responses(sync_status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_survey_responses_client_mutation ON survey_responses(client_mutation_id);
`;

/** Ordered by target version; each entry runs once per install. */
const MIGRATIONS: Record<number, string> = {
  2: MIGRATION_V2,
};

async function runMigrations(db: SQLite.SQLiteDatabase): Promise<void> {
  const row = await db.getFirstAsync<{ value: string }>(
    "SELECT value FROM sync_meta WHERE key = 'schema_version'",
  );
  let current = row ? parseInt(row.value, 10) || 1 : 1;
  for (let version = current + 1; version <= SCHEMA_VERSION; version += 1) {
    const statements = MIGRATIONS[version];
    if (statements) {
      await db.execAsync(statements);
    }
    current = version;
  }
  await db.runAsync(
    "INSERT INTO sync_meta (key, value) VALUES ('schema_version', ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
    [String(current)],
  );
}

export async function getDb(): Promise<SQLite.SQLiteDatabase> {
  if (!dbPromise) {
    dbPromise = (async () => {
      const db = await SQLite.openDatabaseAsync("impactflow_field.db");
      await db.execAsync(SCHEMA);
      await runMigrations(db);
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
