export type SyncStatus = "synced" | "pending" | "failed";

export type LocalBeneficiary = {
  local_id: string;
  server_id: string | null;
  organization_id: string | null;
  household_local_id: string | null;
  household_server_id: string | null;
  community_local_id: string | null;
  community_server_id: string | null;
  first_name: string;
  last_name: string;
  code: string | null;
  phone: string | null;
  status: string;
  consent_data_use: number;
  payload_json: string;
  sync_status: SyncStatus;
  last_error: string | null;
  updated_at_local: string;
  updated_at_server: string | null;
};

export type LocalCommunity = {
  local_id: string;
  server_id: string | null;
  organization_id: string | null;
  name: string;
  code: string | null;
  community_type: string | null;
  status: string;
  payload_json: string;
  sync_status: SyncStatus;
  last_error: string | null;
  updated_at_local: string;
  updated_at_server: string | null;
};

export type LocalHousehold = {
  local_id: string;
  server_id: string | null;
  organization_id: string | null;
  community_local_id: string | null;
  community_server_id: string | null;
  name: string;
  code: string | null;
  status: string;
  payload_json: string;
  sync_status: SyncStatus;
  last_error: string | null;
  updated_at_local: string;
  updated_at_server: string | null;
};

export type LocalSurvey = {
  local_id: string;
  server_id: string | null;
  organization_id: string | null;
  name: string;
  code: string | null;
  category: string | null;
  status: string;
  current_version: number;
  payload_json: string;
  schema_json: string;
  sync_status: SyncStatus;
  last_error: string | null;
  updated_at_local: string;
  updated_at_server: string | null;
};

export type LocalSurveyResponse = {
  local_id: string;
  server_id: string | null;
  survey_local_id: string | null;
  survey_server_id: string | null;
  organization_id: string | null;
  beneficiary_local_id: string | null;
  beneficiary_server_id: string | null;
  status: "draft" | "submitted";
  answers_json: string;
  client_mutation_id: string;
  payload_json: string;
  sync_status: SyncStatus;
  last_error: string | null;
  updated_at_local: string;
  updated_at_server: string | null;
};

export type MutationRow = {
  id: string;
  entity_type: "community" | "household" | "beneficiary" | "survey_response";
  local_id: string;
  op: "create" | "update" | "delete";
  payload_json: string;
  status: "pending" | "processing" | "failed" | "done";
  attempts: number;
  last_error: string | null;
  created_at: string;
  updated_at: string;
};

export type LocalTask = {
  local_id: string;
  server_id: string | null;
  organization_id: string | null;
  project_id: string | null;
  title: string;
  description: string | null;
  status: string;
  priority: string | null;
  assignee_id: string | null;
  due_date: string | null;
  completed_at: string | null;
  payload_json: string;
  sync_status: SyncStatus;
  last_error: string | null;
  updated_at_local: string;
  updated_at_server: string | null;
};

export type LocalNotification = {
  local_id: string;
  server_id: string | null;
  organization_id: string | null;
  user_id: string | null;
  event_type: string | null;
  title: string;
  body: string | null;
  link: string | null;
  severity: string | null;
  status: string | null;
  read_at: string | null;
  payload_json: string;
  sync_status: SyncStatus;
  updated_at_local: string;
  updated_at_server: string | null;
};

export type MediaQueueRow = {
  local_id: string;
  server_id: string | null;
  client_mutation_id: string;
  entity_type: string;
  entity_local_id: string | null;
  entity_server_id: string | null;
  file_uri: string;
  file_name: string;
  mime_type: string | null;
  file_size: number;
  status: "pending" | "uploading" | "synced" | "failed";
  last_error: string | null;
  payload_json: string;
  created_at: string;
  updated_at: string;
};

export type SyncLogRow = {
  id: string;
  session_id: string | null;
  status: string;
  pushed_count: number;
  pulled_count: number;
  failed_count: number;
  conflict_count: number;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
  payload_json: string;
};

export type SearchIndexRow = {
  id: string;
  entity_type: string;
  entity_local_id: string;
  entity_server_id: string | null;
  title: string;
  subtitle: string | null;
  keywords: string;
  updated_at: string;
};
