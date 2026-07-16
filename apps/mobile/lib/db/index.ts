import * as SQLite from "expo-sqlite";

let dbPromise: Promise<SQLite.SQLiteDatabase> | null = null;

/**
 * Bump this whenever a migration below adds/alters tables. Existing installs
 * run only the migrations newer than their stored `schema_version` meta key,
 * so upgrades are additive and never drop local data.
 */
const SCHEMA_VERSION = 3;

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

/** schema_version 3: tasks, notifications, media queue, sync logs, search, settings. */
const MIGRATION_V3 = `
CREATE TABLE IF NOT EXISTS tasks (
  local_id TEXT PRIMARY KEY NOT NULL,
  server_id TEXT,
  organization_id TEXT,
  project_id TEXT,
  title TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL DEFAULT 'open',
  priority TEXT,
  assignee_id TEXT,
  due_date TEXT,
  completed_at TEXT,
  payload_json TEXT NOT NULL DEFAULT '{}',
  sync_status TEXT NOT NULL DEFAULT 'synced',
  last_error TEXT,
  updated_at_local TEXT NOT NULL,
  updated_at_server TEXT
);

CREATE TABLE IF NOT EXISTS notifications (
  local_id TEXT PRIMARY KEY NOT NULL,
  server_id TEXT,
  organization_id TEXT,
  user_id TEXT,
  event_type TEXT,
  title TEXT NOT NULL,
  body TEXT,
  link TEXT,
  severity TEXT,
  status TEXT,
  read_at TEXT,
  payload_json TEXT NOT NULL DEFAULT '{}',
  sync_status TEXT NOT NULL DEFAULT 'synced',
  updated_at_local TEXT NOT NULL,
  updated_at_server TEXT
);

CREATE TABLE IF NOT EXISTS media_queue (
  local_id TEXT PRIMARY KEY NOT NULL,
  server_id TEXT,
  client_mutation_id TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_local_id TEXT,
  entity_server_id TEXT,
  file_uri TEXT NOT NULL,
  file_name TEXT NOT NULL,
  mime_type TEXT,
  file_size INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'pending',
  last_error TEXT,
  payload_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sync_logs (
  id TEXT PRIMARY KEY NOT NULL,
  session_id TEXT,
  status TEXT NOT NULL,
  pushed_count INTEGER NOT NULL DEFAULT 0,
  pulled_count INTEGER NOT NULL DEFAULT 0,
  failed_count INTEGER NOT NULL DEFAULT 0,
  conflict_count INTEGER NOT NULL DEFAULT 0,
  error_message TEXT,
  started_at TEXT NOT NULL,
  completed_at TEXT,
  payload_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS search_index (
  id TEXT PRIMARY KEY NOT NULL,
  entity_type TEXT NOT NULL,
  entity_local_id TEXT NOT NULL,
  entity_server_id TEXT,
  title TEXT NOT NULL,
  subtitle TEXT,
  keywords TEXT NOT NULL DEFAULT '',
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_profile (
  key TEXT PRIMARY KEY NOT NULL,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY NOT NULL,
  value TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_tasks_server ON tasks(server_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_notifications_server ON notifications(server_id);
CREATE INDEX IF NOT EXISTS idx_notifications_read ON notifications(read_at);
CREATE INDEX IF NOT EXISTS idx_media_queue_status ON media_queue(status);
CREATE INDEX IF NOT EXISTS idx_sync_logs_started ON sync_logs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_search_keywords ON search_index(keywords);
CREATE INDEX IF NOT EXISTS idx_search_entity ON search_index(entity_type, entity_local_id);
`;

/** Ordered by target version; each entry runs once per install. */
const MIGRATIONS: Record<number, string> = {
  2: MIGRATION_V2,
  3: MIGRATION_V3,
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
