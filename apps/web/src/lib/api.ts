export const APP_NAME = process.env.NEXT_PUBLIC_APP_NAME ?? "ImpactFlow AI";
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const API_V1 = `${API_URL}/api/v1`;

export type UserBrief = {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  display_name?: string | null;
  avatar_url?: string | null;
  is_active: boolean;
  mfa_enabled: boolean;
  must_change_password?: boolean;
  primary_organization_id?: string | null;
};

export type Organization = {
  id: string;
  name: string;
  slug: string;
  organization_type: string;
  country_code?: string | null;
  timezone: string;
  locale: string;
  logo_url?: string | null;
  website?: string | null;
  email?: string | null;
  is_active: boolean;
  is_verified: boolean;
  settings: Record<string, unknown>;
  created_at: string;
};

export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  mfa_required: boolean;
  user: UserBrief;
};

export type DashboardStats = {
  users_count: number;
  active_memberships: number;
  roles_count: number;
  recent_audit_events: number;
  organization: Organization;
  programs_count: number;
  projects_count: number;
  activities_count: number;
  tasks_count: number;
  open_tasks_count: number;
  donors_count: number;
  grants_count: number;
  active_grants_count: number;
  budgets_count: number;
  grants_awarded_total: string;
  grants_received_total: string;
  expenses_total: string;
  theories_of_change_count: number;
  logframes_count: number;
  indicators_count: number;
  active_indicators_count: number;
  monitoring_results_count: number;
  evaluations_count: number;
  communities_count: number;
  households_count: number;
  beneficiaries_count: number;
  active_beneficiaries_count: number;
  beneficiary_memberships_count: number;
  reports_count: number;
  published_reports_count: number;
  saved_dashboards_count: number;
  map_layers_count: number;
  map_features_count: number;
  evidence_count: number;
  verified_evidence_count: number;
  ai_conversations_count: number;
  ai_predictions_count: number;
  open_predictions_count: number;
  ai_narratives_count: number;
  knowledge_documents_count: number;
  marketplace_installs_count: number;
  integrations_count: number;
  api_keys_count: number;
  branding_enabled_count: number;
  notifications_count?: number;
  unread_notifications_count?: number;
  webhook_pending_count?: number;
  webhook_failed_count?: number;
  surveys_count?: number;
  published_surveys_count?: number;
  survey_responses_count?: number;
};

export type Role = {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  is_system: boolean;
  is_default: boolean;
  permissions: string[];
};

export type OrgMembership = {
  id: string;
  organization_id: string;
  user_id: string;
  role_id: string;
  status: string;
  user?: UserBrief | null;
  role?: Role | null;
};

export type InviteUserResponse = {
  user: UserBrief;
  message: string;
  email_delivery?: { status?: string; provider?: string };
  temporary_password?: string;
};

export type Paginated<T> = {
  items: T[];
  meta: {
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
  };
};

export type Program = {
  id: string;
  organization_id: string;
  name: string;
  code: string;
  description?: string | null;
  status: string;
  start_date?: string | null;
  end_date?: string | null;
  manager_id?: string | null;
  goal?: string | null;
  tags: string[];
  created_at: string;
  updated_at: string;
};

export type Project = {
  id: string;
  organization_id: string;
  program_id: string;
  name: string;
  code: string;
  description?: string | null;
  status: string;
  start_date?: string | null;
  end_date?: string | null;
  country_code?: string | null;
  location?: string | null;
  manager_id?: string | null;
  priority: string;
  tags: string[];
  created_at: string;
  updated_at: string;
};

export type ActivityItem = {
  id: string;
  organization_id: string;
  project_id: string;
  name: string;
  code?: string | null;
  description?: string | null;
  status: string;
  start_date?: string | null;
  end_date?: string | null;
  sort_order: number;
  owner_id?: string | null;
  location?: string | null;
  created_at: string;
  updated_at: string;
};

export type WorkPlan = {
  id: string;
  organization_id: string;
  project_id: string;
  name: string;
  description?: string | null;
  status: string;
  period_start?: string | null;
  period_end?: string | null;
  fiscal_year?: number | null;
  period_label?: string | null;
  created_at: string;
  updated_at: string;
};

export type TaskItem = {
  id: string;
  organization_id: string;
  project_id: string;
  activity_id?: string | null;
  work_plan_id?: string | null;
  title: string;
  description?: string | null;
  status: string;
  priority: string;
  assignee_id?: string | null;
  due_date?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type Donor = {
  id: string;
  organization_id: string;
  name: string;
  code: string;
  donor_type: string;
  status: string;
  country_code?: string | null;
  contact_name?: string | null;
  contact_email?: string | null;
  contact_phone?: string | null;
  website?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
};

export type Grant = {
  id: string;
  organization_id: string;
  donor_id: string;
  program_id?: string | null;
  project_id?: string | null;
  name: string;
  code: string;
  description?: string | null;
  status: string;
  currency: string;
  amount_awarded: number | string;
  amount_received: number | string;
  start_date?: string | null;
  end_date?: string | null;
  agreement_reference?: string | null;
  created_at: string;
  updated_at: string;
};

export type BudgetLine = {
  id: string;
  budget_id: string;
  category: string;
  code?: string | null;
  description?: string | null;
  amount: number | string;
  sort_order: number;
};

export type Budget = {
  id: string;
  organization_id: string;
  grant_id?: string | null;
  project_id?: string | null;
  program_id?: string | null;
  name: string;
  fiscal_year?: number | null;
  currency: string;
  status: string;
  total_amount: number | string;
  notes?: string | null;
  lines?: BudgetLine[];
  created_at: string;
  updated_at: string;
};

export type FinanceTxn = {
  id: string;
  organization_id: string;
  grant_id?: string | null;
  project_id?: string | null;
  budget_id?: string | null;
  transaction_type: string;
  status: string;
  amount: number | string;
  currency: string;
  transaction_date: string;
  description?: string | null;
  reference?: string | null;
  category?: string | null;
  created_at: string;
  updated_at: string;
};

export type TheoryOfChange = {
  id: string;
  organization_id: string;
  program_id?: string | null;
  project_id?: string | null;
  name: string;
  code: string;
  status: string;
  goal_statement?: string | null;
  problem_statement?: string | null;
  assumptions?: string | null;
  success_criteria?: string | null;
  pathways?: unknown[];
  created_at: string;
  updated_at: string;
};

export type LogframeResult = {
  id: string;
  logframe_id: string;
  parent_id?: string | null;
  level: string;
  code?: string | null;
  statement: string;
  assumptions?: string | null;
  means_of_verification?: string | null;
  sort_order: number;
};

export type Logframe = {
  id: string;
  organization_id: string;
  theory_of_change_id?: string | null;
  program_id?: string | null;
  project_id?: string | null;
  name: string;
  code: string;
  description?: string | null;
  status: string;
  results?: LogframeResult[];
  created_at: string;
  updated_at: string;
};

export type IndicatorTarget = {
  id: string;
  indicator_id: string;
  period_label: string;
  start_date?: string | null;
  end_date?: string | null;
  target_value: number | string;
  notes?: string | null;
  status: string;
};

export type Indicator = {
  id: string;
  organization_id: string;
  program_id?: string | null;
  project_id?: string | null;
  logframe_result_id?: string | null;
  name: string;
  code: string;
  description?: string | null;
  level: string;
  measure_type: string;
  unit?: string | null;
  direction: string;
  collection_method?: string | null;
  frequency?: string | null;
  baseline_value?: number | string | null;
  baseline_date?: string | null;
  status: string;
  targets?: IndicatorTarget[];
  created_at: string;
  updated_at: string;
};

export type MonitoringResult = {
  id: string;
  organization_id: string;
  indicator_id: string;
  target_id?: string | null;
  project_id?: string | null;
  reporting_date: string;
  period_start?: string | null;
  period_end?: string | null;
  actual_value?: number | string | null;
  qualitative_value?: string | null;
  status: string;
  data_source?: string | null;
  location_label?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
};

export type Evaluation = {
  id: string;
  organization_id: string;
  program_id?: string | null;
  project_id?: string | null;
  name: string;
  code: string;
  evaluation_type: string;
  status: string;
  start_date?: string | null;
  end_date?: string | null;
  evaluator_name?: string | null;
  objectives?: string | null;
  methodology?: string | null;
  key_findings?: string | null;
  recommendations?: string | null;
  lessons_learned?: string | null;
  created_at: string;
  updated_at: string;
};

export type Community = {
  id: string;
  organization_id: string;
  parent_id?: string | null;
  name: string;
  code: string;
  community_type: string;
  status: string;
  country_code?: string | null;
  region?: string | null;
  district?: string | null;
  population_estimate?: number | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
};

export type Household = {
  id: string;
  organization_id: string;
  community_id?: string | null;
  name: string;
  code: string;
  status: string;
  address?: string | null;
  household_size?: number | null;
  poverty_status?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
};

export type BeneficiaryMembership = {
  id: string;
  beneficiary_id: string;
  program_id?: string | null;
  project_id?: string | null;
  activity_id?: string | null;
  membership_role: string;
  status: string;
  start_date?: string | null;
  end_date?: string | null;
};

export type Beneficiary = {
  id: string;
  organization_id: string;
  household_id?: string | null;
  community_id?: string | null;
  code: string;
  first_name: string;
  last_name: string;
  middle_name?: string | null;
  sex?: string | null;
  date_of_birth?: string | null;
  national_id?: string | null;
  phone?: string | null;
  email?: string | null;
  status: string;
  registration_date?: string | null;
  consent_data_use: boolean;
  is_household_head: boolean;
  memberships?: BeneficiaryMembership[];
  created_at: string;
  updated_at: string;
};

export type Report = {
  id: string;
  organization_id: string;
  program_id?: string | null;
  project_id?: string | null;
  grant_id?: string | null;
  name: string;
  code: string;
  report_type: string;
  status: string;
  period_start?: string | null;
  period_end?: string | null;
  summary?: string | null;
  content?: string | null;
  sections?: unknown[];
  created_at: string;
  updated_at: string;
};

/** Epic 5 — executive analytics & donor reporting */

export type PortfolioHealth = {
  score: number;
  band: "healthy" | "watch" | "at_risk" | string;
  components: {
    delivery: number;
    indicators: number;
    budget: number;
    grants: number;
    risk_penalty: number;
  };
};

export type ExecutiveKpis = {
  active_programs: number;
  active_projects: number;
  open_tasks: number;
  grant_pipeline: number;
  active_grants: number;
  budget_utilization_pct: number;
  grants_awarded_total: number;
  expenses_total: number;
  indicator_on_track: number;
  indicator_total: number;
  beneficiary_reach: number;
  active_beneficiaries: number;
  communities_reached: number;
  project_completion_pct: number;
  surveys_count: number;
  published_surveys_count: number;
  indicators_count: number;
  female?: number;
  male?: number;
  other?: number;
  unknown?: number;
  youth_reach?: number;
  persons_with_disabilities?: number;
  evidence_verified?: number | null;
};

export type RiskHeatItem = {
  type?: string;
  title?: string;
  severity?: string;
  summary?: string;
  suggested_action?: string;
};

export type ExecutiveDeadlineGrant = {
  id: string;
  name: string;
  code: string;
  end_date?: string | null;
  status: string;
};

export type ExecutiveDeadlineTask = {
  id: string;
  title: string;
  due_date?: string | null;
  priority?: string;
  status: string;
};

export type ExecutiveReportBrief = {
  id: string;
  name: string;
  code: string;
  report_type: string;
  status: string;
  updated_at?: string | null;
};

export type ExecutiveQuickAction = {
  label: string;
  href: string;
  action: string;
};

export type ExecutiveDashboard = {
  generated_at: string;
  filters: { program_id?: string | null; project_id?: string | null };
  portfolio_health: PortfolioHealth;
  kpis: ExecutiveKpis;
  indicator_performance: IndicatorProgressRow[];
  indicators_behind: IndicatorProgressRow[];
  upcoming_deadlines: {
    grants_expiring: ExecutiveDeadlineGrant[];
    overdue_tasks: ExecutiveDeadlineTask[];
  };
  risk_heat: RiskHeatItem[];
  field_operations?: Record<string, unknown>;
  ai_insights: {
    summary?: string | null;
    key_risks?: RiskHeatItem[];
    recommendations?: string[];
    wins?: string[];
  };
  latest_reports: ExecutiveReportBrief[];
  quick_actions: ExecutiveQuickAction[];
  citations: { source: string; metric?: string }[];
};

export type ChartBar = { label: string; value: number };

export type ExecutivePortfolio = {
  generated_at: string;
  filters: Record<string, string | null | undefined>;
  program_performance: Record<string, number>;
  grant_performance: Record<string, number>;
  beneficiary_trends: {
    total: number;
    active: number;
    gender: Record<string, number>;
  };
  indicator_trends: {
    id?: string;
    name?: string;
    progress_pct?: number | null;
    actual?: unknown;
    target?: unknown;
    on_track?: boolean;
  }[];
  survey_completion: { surveys: number; submitted_responses: number };
  evidence_collection: {
    total: number;
    verified: number;
    verification_pct: number;
  };
  efficiency: {
    cost_per_beneficiary: number;
    budget_utilization_pct: number;
  };
  charts: {
    indicator_progress_bar: ChartBar[];
    gender_donut: ChartBar[];
    budget_utilization: ChartBar[];
  };
  citations: { source: string }[];
};

export type ExecutiveImpact = {
  generated_at: string;
  outputs_tracked: number;
  outcomes_tracked: number;
  indicators_on_track: number;
  indicators_total: number;
  cost_per_beneficiary: number;
  program_efficiency_pct: number;
  grant_efficiency_pct: number;
  beneficiary_reach: number;
  variances: {
    id?: string;
    name?: string;
    baseline?: unknown;
    target?: number;
    actual?: number;
    variance?: number;
    progress_pct?: number | null;
  }[];
  citations: { source: string }[];
};

export type ComplianceRecommendation = {
  why: string;
  action: string;
  severity: string;
  href?: string;
};

export type ComplianceIssue = {
  category: string;
  title: string;
  severity: string;
  detail?: string | null;
};

export type ExecutiveCompliance = {
  generated_at: string;
  summary: {
    draft_reports: number;
    reports_in_review: number;
    missing_indicator_actuals: number;
    indicators_behind: number;
    survey_gaps: number;
    evidence_pending: number;
    grants_ending_soon: number;
    open_risk_signals: number;
  };
  issues: ComplianceIssue[];
  recommendations: ComplianceRecommendation[];
  risk_signals: RiskHeatItem[];
  citations: { source: string }[];
};

export type ExecutiveRiskItem = {
  type?: string;
  title?: string;
  severity?: string;
  summary?: string;
  reason?: string;
  suggested_action?: string;
  responsible_role?: string;
  recommended_deadline_days?: number;
};

export type ExecutiveRisks = {
  generated_at: string;
  total: number;
  by_severity: Record<string, number>;
  items: ExecutiveRiskItem[];
  citations: { source: string }[];
};

export type ExecutiveBriefResponse = {
  audience: string;
  narrative: AiReport | Record<string, unknown>;
  report: Report | null;
};

export type ReportTemplate = {
  id?: string;
  organization_id?: string | null;
  name: string;
  code: string;
  description?: string | null;
  category: string;
  report_type: string;
  narrative_style?: string;
  sections?: { id: string; title: string; required?: boolean }[];
  required_metrics?: string[];
  branding?: Record<string, unknown>;
  export_preferences?: Record<string, unknown>;
  is_system?: boolean;
  status?: string;
  cloned_from_id?: string | null;
};

export type ClonedReportTemplate = {
  id: string;
  name: string;
  code: string;
  category: string;
  sections?: unknown[];
};

export type ReportVersion = {
  id: string;
  organization_id: string;
  report_id: string;
  version: number;
  title: string;
  summary?: string | null;
  content?: string | null;
  sections?: unknown[];
  changelog?: string | null;
  status: string;
  citations?: unknown[];
  created_at?: string | null;
};

export type ReportExportFormat =
  | "markdown"
  | "html"
  | "pdf"
  | "csv"
  | "xlsx"
  | "excel"
  | "docx"
  | "pptx";

export type SavedDashboard = {
  id: string;
  organization_id: string;
  name: string;
  code: string;
  description?: string | null;
  status: string;
  is_default: boolean;
  layout?: Record<string, unknown>;
  widgets?: unknown[];
  filters?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type MapFeature = {
  id: string;
  layer_id: string;
  name: string;
  feature_type: string;
  latitude?: number | string | null;
  longitude?: number | string | null;
  properties?: Record<string, unknown>;
  sort_order: number;
};

export type MapLayer = {
  id: string;
  organization_id: string;
  name: string;
  code: string;
  layer_type: string;
  status: string;
  description?: string | null;
  features?: MapFeature[];
  created_at: string;
  updated_at: string;
};

export type EvidenceItem = {
  id: string;
  organization_id: string;
  title: string;
  code: string;
  evidence_type: string;
  status: string;
  description?: string | null;
  collected_on?: string | null;
  source?: string | null;
  file_url?: string | null;
  tags?: unknown[];
  created_at: string;
  updated_at: string;
};

export type AnalyticsOverview = {
  delivery: Record<string, unknown>;
  finance: Record<string, unknown>;
  meal: Record<string, unknown>;
  field: Record<string, unknown>;
  insights: Record<string, unknown>;
  reports_by_status: Record<string, number>;
  evidence_by_type: Record<string, number>;
};

export type Citation = {
  type: string;
  id: string;
  label: string;
  href?: string;
};

export type AiConversation = {
  id: string;
  organization_id: string;
  user_id: string;
  title: string;
  status: string;
  pinned?: boolean;
  share_token?: string | null;
  context?: Record<string, unknown>;
  metadata?: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
};

export type AiMessageMetadata = {
  citations?: Citation[];
  tools_used?: string[];
  feedback?: string;
  [key: string]: unknown;
};

export type AiMessage = {
  id: string;
  organization_id: string;
  conversation_id: string;
  role: string;
  content: string;
  model?: string | null;
  provider: string;
  token_count?: number | null;
  metadata?: AiMessageMetadata | null;
  created_at: string;
  updated_at: string;
};

export type AiStreamEvent =
  | { event: "tool_start"; tool: string }
  | { event: "tool_result"; tool: string; ok: boolean }
  | { event: "token"; text: string }
  | {
      event: "done";
      conversation_id: string;
      message_id: string;
      citations?: Citation[];
      tools_used?: string[];
    }
  | { event: "error"; error: string; detail?: string };

export type AiInsightRisk = {
  type: string;
  title: string;
  summary?: string;
  severity: string;
  recommendation?: string;
  [key: string]: unknown;
};

export type AiInsightWin = {
  title: string;
  detail?: string;
  indicator_id?: string;
  [key: string]: unknown;
};

export type AiInsightAction = {
  title: string;
  severity?: string;
  action?: string | null;
};

export type AiDashboardInsights = {
  summary: string;
  key_risks: AiInsightRisk[];
  key_wins: AiInsightWin[];
  recommendations: string[];
  upcoming_actions: AiInsightAction[];
  predictions: AiInsightRisk[];
  generated_at: string;
};

export type AiReport = {
  report_type: string;
  title: string;
  content: string;
  provider: string;
  model?: string | null;
  generated_at: string;
  narrative_id?: string | null;
};

export type AiConversationDetail = AiConversation & {
  messages: AiMessage[];
};

export type AiPrediction = {
  id: string;
  organization_id: string;
  program_id?: string | null;
  project_id?: string | null;
  prediction_type: string;
  title: string;
  summary: string;
  severity: string;
  score: string | number;
  status: string;
  recommendations: string[];
  provider: string;
  model?: string | null;
  created_at: string;
  updated_at: string;
};

export type AiNarrative = {
  id: string;
  organization_id: string;
  name: string;
  code: string;
  narrative_type: string;
  status: string;
  prompt?: string | null;
  content: string;
  provider: string;
  model?: string | null;
  created_at: string;
  updated_at: string;
};

export type KnowledgeDocument = {
  id: string;
  organization_id: string;
  name: string;
  code: string;
  category: string;
  status: string;
  summary?: string | null;
  content: string;
  source?: string | null;
  tags?: unknown[];
  created_at: string;
  updated_at: string;
};

export type MarketplaceApp = {
  id: string;
  name: string;
  code: string;
  category: string;
  summary?: string | null;
  description?: string | null;
  publisher: string;
  pricing_tier: string;
  status: string;
  is_featured: boolean;
  icon_key?: string | null;
  created_at: string;
  updated_at: string;
};

export type MarketplaceInstallation = {
  id: string;
  organization_id: string;
  app_id: string;
  status: string;
  config?: Record<string, unknown>;
  notes?: string | null;
  created_at: string;
  updated_at: string;
};

export type OrgApiKey = {
  id: string;
  organization_id: string;
  name: string;
  key_prefix: string;
  status: string;
  scopes: string[];
  created_at: string;
  updated_at: string;
};

export type OrgApiKeyCreated = OrgApiKey & { secret: string };

export type IntegrationConnection = {
  id: string;
  organization_id: string;
  name: string;
  provider: string;
  status: string;
  direction: string;
  endpoint_url?: string | null;
  secret_hint?: string | null;
  events?: string[];
  last_sync_at?: string | null;
  last_error?: string | null;
  created_at: string;
  updated_at: string;
};

export type ConnectorConfigField = {
  key: string;
  label: string;
  required?: boolean;
  secret?: boolean;
  type?: string;
};

export type ConnectorDefinition = {
  code: string;
  name: string;
  category: string;
  auth_type: string;
  sync_modes?: string[];
  directions?: string[];
  description?: string;
  config_schema?: { fields?: ConnectorConfigField[] };
  oauth?: Record<string, unknown>;
  health_check?: string;
  version?: string;
  status?: string;
};

export type ConnectorCatalogResponse = {
  items: ConnectorDefinition[];
  total: number;
};

export type EnabledConnector = {
  id: string;
  name: string;
  provider: string;
  status: string;
  direction: string;
  config?: Record<string, unknown>;
};

export type ConnectorHealthResult = {
  healthy: boolean;
  check?: string;
  message?: string;
  connector?: string;
  checked_at?: string;
};

export type ConnectorSyncJob = {
  id: string;
  organization_id: string;
  integration_id: string;
  connector_code: string;
  status: string;
  direction: string;
  mode: string;
  records_processed: number;
  records_failed: number;
  error_message?: string | null;
  result?: Record<string, unknown>;
  started_at?: string | null;
  completed_at?: string | null;
  created_at?: string | null;
};

export type IntegrationExport = {
  name: string;
  provider: string;
  direction: string;
  endpoint_url?: string | null;
  events?: string[];
  config?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  exported_at?: string;
};

export type IntegrationMonitoring = {
  connected_systems: number;
  healthy_connectors: number;
  errored_connectors: number;
  webhook_pending: number;
  webhook_delivered: number;
  webhook_dead: number;
  queue_depth: number;
  sync_completed: number;
  sync_failed: number;
  api_keys_active: number;
  success_rate: number;
  failure_rate: number;
  generated_at?: string;
};

export type FieldMappingProfile = {
  id: string;
  name: string;
  code: string;
  entity_type: string;
  connector_code?: string | null;
  mappings: { source: string; target: string; transform?: string }[];
  defaults?: Record<string, unknown>;
  validation_rules?: { field: string; required?: boolean }[];
  status: string;
};

export type FieldMappingPreview = {
  mapped: Record<string, unknown>;
  errors: string[];
  valid: boolean;
};

export type WebhookDelivery = {
  id: string;
  organization_id: string;
  integration_id: string;
  event_type: string;
  status: string;
  attempt_count: number;
  max_attempts: number;
  next_attempt_at?: string | null;
  delivered_at?: string | null;
  last_error?: string | null;
  response_status?: number | null;
  endpoint_url?: string | null;
  created_at: string;
  updated_at: string;
};

export type PlatformEventDef = {
  code: string;
  description: string;
};

export type PluginManifest = {
  id: string;
  code: string;
  name: string;
  version: string;
  status: string;
  events?: string[];
  ui_panels?: string[];
  workflow_actions?: string[];
  ai_tools?: string[];
  description?: string | null;
};

export type DeveloperPortal = {
  api_version: string;
  openapi_url: string;
  docs_url: string;
  authentication: {
    jwt: string;
    api_key: string;
    organization_header: string;
  };
  webhooks: {
    outbound: string;
    inbound: string;
    signing_header: string;
    retry: string;
  };
  events: PlatformEventDef[];
  connectors: {
    code: string;
    name: string;
    category: string;
    auth_type: string;
    version?: string;
    status?: string;
  }[];
  code_samples: Record<string, string>;
  postman?: { hint?: string };
  changelog: { version: string; notes: string }[];
};

export type OrgBranding = {
  id: string;
  organization_id: string;
  product_name?: string | null;
  tagline?: string | null;
  primary_color: string;
  secondary_color: string;
  accent_color?: string | null;
  logo_url?: string | null;
  favicon_url?: string | null;
  login_background_url?: string | null;
  custom_domain?: string | null;
  support_email?: string | null;
  support_url?: string | null;
  hide_powered_by: boolean;
  is_enabled: boolean;
  metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type SubscriptionPlan = {
  id: string;
  code: string;
  name: string;
  description?: string | null;
  tier: string;
  billing_period: string;
  price_monthly?: number | null;
  price_annual?: number | null;
  monthly_price?: number | null;
  annual_price?: number | null;
  currency: string;
  seat_limit?: number | null;
  max_users?: number | null;
  storage_gb?: number | null;
  max_storage?: number | null;
  max_projects?: number | null;
  api_limit?: number | null;
  ai_credits?: number | null;
  trial_days: number;
  features: string[];
  feature_flags?: string[];
  is_public: boolean;
  recommended?: boolean;
  sort_order: number;
  display_order?: number;
  active?: boolean;
  contact_sales?: boolean;
};

export type OrganizationSubscription = {
  id: string;
  organization_id: string;
  status: string;
  billing_period: string;
  seats: number;
  trial_ends_at?: string | null;
  days_remaining?: number | null;
  current_period_start?: string | null;
  current_period_end?: string | null;
  grace_ends_at?: string | null;
  canceled_at?: string | null;
  cancel_at_period_end?: boolean;
  provider: string;
  coupon_code?: string | null;
  discount_percent: number;
  plan?: SubscriptionPlan | null;
};

export type BillingInvoice = {
  id: string;
  organization_id: string;
  subscription_id: string;
  plan_id?: string | null;
  number: string;
  amount: number;
  currency: string;
  status: string;
  billing_period: string;
  period_start?: string | null;
  period_end?: string | null;
  paystack_reference?: string | null;
  receipt_url?: string | null;
  paid_at?: string | null;
  created_at?: string | null;
};

export type BillingUsage = {
  subscription: OrganizationSubscription;
  users: { used: number; limit?: number | null };
  projects: { used: number; limit?: number | null };
  storage_gb: { used: number; limit?: number | null };
  ai_credits: { used: number; limit?: number | null };
  api_calls: { used: number; limit?: number | null };
  projected_renewal: { amount: number; currency: string; at?: string | null };
};

export type PlatformBillingAnalytics = {
  mrr: number;
  arr: number;
  revenue: number;
  active_organizations: number;
  trials: number;
  conversions: number;
  failed_payments: number;
  grace_period_accounts: number;
  expired_accounts: number;
  government_accounts: number;
  enterprise_contracts: number;
  most_popular_plan?: string | null;
  average_revenue_per_organization: number;
  churn: number;
  growth: number;
  plan_distribution: Record<string, number>;
  currency: string;
};

export type OrgDomain = {
  id: string;
  organization_id: string;
  hostname: string;
  is_primary: boolean;
  status: string;
  verification_token: string;
  ssl_status: string;
  dns_records: { type: string; name: string; value: string }[];
  last_error?: string | null;
};

export type OnboardingState = {
  id: string;
  organization_id: string;
  status: string;
  current_step: string;
  checklist: Record<string, boolean>;
  sector?: string | null;
  country_code?: string | null;
  theme_preset?: string | null;
  completed_at?: string | null;
};

export type CustomerSuccessMetrics = {
  health_score: number;
  adoption_pct: number;
  active_users: number;
  projects: number;
  beneficiaries: number;
  integrations: number;
  api_keys: number;
  onboarding_status: string;
  recommendations: { why: string; action: string; href: string }[];
  generated_at: string;
};

export type NotificationItem = {
  id: string;
  organization_id: string;
  user_id: string;
  event_type: string;
  title: string;
  body?: string | null;
  link?: string | null;
  severity: string;
  status: string;
  read_at?: string | null;
  resource_type?: string | null;
  resource_id?: string | null;
  created_at: string;
  updated_at: string;
};

export type SurveyFieldOption = { value: string; label: string };

export type SurveyFieldValidation = {
  min?: number;
  max?: number;
  min_length?: number;
  max_length?: number;
  regex?: string;
};

export type SurveyShowIf = {
  field: string;
  op: "eq" | "neq" | "in" | "not_in" | "truthy" | "falsy";
  value?: unknown;
};

export type SurveyFieldLogic = {
  show_if?: SurveyShowIf;
};

export type SurveyFieldCalculate = {
  op: "sum";
  fields: string[];
};

export type SurveyField = {
  id: string;
  type: string;
  label: string;
  required?: boolean;
  hidden?: boolean;
  read_only?: boolean;
  placeholder?: string;
  help_text?: string;
  options?: SurveyFieldOption[];
  validation?: SurveyFieldValidation;
  default?: unknown;
  logic?: SurveyFieldLogic;
  calculate?: SurveyFieldCalculate;
  [key: string]: unknown;
};

export type SurveySection = {
  id: string;
  title?: string;
  fields: SurveyField[];
};

export type SurveyPage = {
  id: string;
  title?: string;
  sections: SurveySection[];
};

export type SurveySchemaSettings = {
  progress_bar?: boolean;
  allow_draft?: boolean;
  auto_save?: boolean;
  randomize_questions?: boolean;
  anonymous?: boolean;
  [key: string]: unknown;
};

export type SurveySchema = {
  schema_version?: number;
  settings?: SurveySchemaSettings;
  pages?: SurveyPage[];
  /** Legacy flat field list — either the authoring format (no pages) or a
   * flattened convenience copy the API appends alongside `pages`. */
  fields?: SurveyField[];
};

export type FieldTypeInfo = { code: string; label: string; category: string };

export type Survey = {
  id: string;
  organization_id: string;
  name: string;
  code: string;
  description?: string | null;
  category?: string | null;
  status: string;
  current_version: number;
  program_id?: string | null;
  project_id?: string | null;
  activity_id?: string | null;
  is_anonymous: boolean;
  response_limit?: number | null;
  starts_at?: string | null;
  ends_at?: string | null;
  cloned_from_id?: string | null;
  created_by_id?: string | null;
  created_at: string;
  updated_at: string;
};

export type SurveyVersionDetail = {
  id: string;
  survey_id: string;
  version: number;
  title: string;
  schema: SurveySchema;
  changelog?: string | null;
  published_at?: string | null;
  created_at: string;
};

export type SurveyDetail = {
  survey: Survey;
  version: SurveyVersionDetail;
};

export type SurveyAssignment = {
  id: string;
  organization_id: string;
  survey_id: string;
  target_type: string;
  target_id: string;
  status: string;
  due_at?: string | null;
  assigned_by_id?: string | null;
  created_at: string;
  updated_at: string;
};

export type SurveyAnalytics = {
  survey_id: string;
  total_responses: number;
  status_counts: Record<string, number>;
  field_histograms: Record<
    string,
    { label: string; type: string; counts: Record<string, number> }
  >;
};

export type SurveySubmission = {
  id: string;
  organization_id: string;
  survey_id: string;
  survey_version_id: string;
  version: number;
  status: string;
  answers: Record<string, unknown>;
  respondent_name?: string | null;
  beneficiary_id?: string | null;
  community_id?: string | null;
  household_id?: string | null;
  program_id?: string | null;
  project_id?: string | null;
  activity_id?: string | null;
  assignment_id?: string | null;
  client_mutation_id?: string | null;
  location?: Record<string, unknown> | null;
  submitted_at?: string | null;
  submitted_by_id?: string | null;
  created_at: string;
  updated_at: string;
};

export type PublicBranding = {
  organization_name: string;
  organization_slug: string;
  product_name?: string | null;
  tagline?: string | null;
  is_enabled: boolean;
  primary_color: string;
  secondary_color: string;
  accent_color?: string | null;
  logo_url?: string | null;
  favicon_url?: string | null;
  login_background_url?: string | null;
  support_email?: string | null;
  support_url?: string | null;
  hide_powered_by: boolean;
};

export type IndicatorProgressRow = {
  indicator_id: string;
  code: string;
  name: string;
  unit?: string | null;
  target_value?: number | null;
  actual_value?: number | null;
  progress_pct?: number | null;
  period_end?: string | null;
};

// --------------------------------------------------------------------------- //
// Workflow engine (Epic 3)
// --------------------------------------------------------------------------- //

export type WorkflowCatalogItem = {
  code: string;
  label: string;
  category?: string;
};

export type WorkflowOperator = { code: string; label: string };

export type WorkflowConditionLeaf = {
  field: string;
  cmp: string;
  value?: unknown;
};

export type WorkflowConditionGroup = {
  op: "and" | "or";
  rules: WorkflowConditionNode[];
};

export type WorkflowConditionNode =
  | WorkflowConditionLeaf
  | WorkflowConditionGroup;

export type WorkflowTrigger = {
  type: string;
  conditions?: WorkflowConditionGroup | null;
  [key: string]: unknown;
};

export type WorkflowAction = {
  id: string;
  type: string;
  name?: string;
  config: Record<string, unknown>;
  conditions?: WorkflowConditionGroup | null;
};

export type WorkflowSettings = {
  max_attempts?: number;
  stop_on_error?: boolean;
  [key: string]: unknown;
};

export type WorkflowDefinition = {
  trigger: WorkflowTrigger;
  actions: WorkflowAction[];
  settings: WorkflowSettings;
};

export type Workflow = {
  id: string;
  organization_id: string;
  name: string;
  code: string;
  description?: string | null;
  category?: string | null;
  status: string;
  current_version: number;
  is_template: boolean;
  cloned_from_id?: string | null;
  created_by_id?: string | null;
  created_at: string;
  updated_at: string;
};

export type WorkflowDetail = Workflow & {
  definition: WorkflowDefinition;
  metadata?: Record<string, unknown>;
};

export type WorkflowVersion = {
  id: string;
  workflow_id: string;
  version: number;
  title: string;
  changelog?: string | null;
  published_at?: string | null;
  created_by_id?: string | null;
  created_at: string;
};

export type WorkflowVersionDetail = WorkflowVersion & {
  definition: WorkflowDefinition;
};

export type WorkflowRun = {
  id: string;
  organization_id: string;
  workflow_id: string;
  workflow_version_id: string;
  status: string;
  trigger_type: string;
  trigger_event?: string | null;
  error_message?: string | null;
  attempt_count: number;
  max_attempts: number;
  next_attempt_at?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  created_by_id?: string | null;
  created_at: string;
  updated_at: string;
};

export type WorkflowRunStep = {
  id: string;
  run_id: string;
  step_index: number;
  action_id: string;
  action_type: string;
  status: string;
  input_json: Record<string, unknown>;
  output_json: Record<string, unknown>;
  error_message?: string | null;
  attempt_count: number;
  started_at?: string | null;
  finished_at?: string | null;
};

export type WorkflowRunDetail = WorkflowRun & {
  steps: WorkflowRunStep[];
  trigger_payload: Record<string, unknown>;
  context: Record<string, unknown>;
};

export type WorkflowApproval = {
  id: string;
  organization_id: string;
  run_id: string;
  step_id: string;
  status: string;
  assignee_id?: string | null;
  comments?: string | null;
  decided_at?: string | null;
  decided_by_id?: string | null;
  due_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type WorkflowSchedule = {
  id: string;
  organization_id: string;
  workflow_id: string;
  cadence: string;
  cron_expr?: string | null;
  timezone: string;
  enabled: boolean;
  next_run_at?: string | null;
  last_run_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type WorkflowTemplate = {
  code: string;
  name: string;
  category?: string | null;
  description?: string | null;
  definition: WorkflowDefinition;
  workflow_id?: string;
};

export type WorkflowMetrics = {
  workflow_status_counts: Record<string, number>;
  run_status_counts: Record<string, number>;
  runs_last_7d: number;
  success_rate_7d: number;
  failure_rate_7d: number;
  queue_depth: number;
  pending_approvals: number;
};

export type FieldDevice = {
  id: string;
  organization_id: string;
  user_id: string;
  device_key: string;
  name: string;
  platform: string;
  app_version?: string | null;
  status: string;
  last_seen_at?: string | null;
  last_sync_at?: string | null;
  storage_bytes: number;
  pending_uploads: number;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type SyncSession = {
  id: string;
  organization_id: string;
  device_id: string;
  user_id: string;
  status: string;
  started_at: string;
  completed_at?: string | null;
  pushed_count: number;
  pulled_count: number;
  failed_count: number;
  error_message?: string | null;
  sync_token?: string | null;
  client_version?: string | null;
  created_at: string;
  updated_at: string;
};

export type MediaUploadRecord = {
  id: string;
  organization_id: string;
  device_id?: string | null;
  client_mutation_id: string;
  entity_type: string;
  entity_id?: string | null;
  file_name: string;
  mime_type?: string | null;
  file_size: number;
  status: string;
  remote_url?: string | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
};

export type FieldOpsMetrics = {
  active_devices: number;
  failed_mutations: number;
  sync_sessions: number;
  conflicts: number;
};

export type WorkflowDefinitionExport = {
  name?: string;
  code?: string;
  category?: string | null;
  definition: WorkflowDefinition;
  [key: string]: unknown;
};

export type AiWorkflowDraft = {
  definition: WorkflowDefinition;
  explanation: string;
  provider: string;
  workflow_id?: string | null;
};

type ApiError = {
  message?: string;
  code?: string;
  details?: Record<string, unknown>;
  detail?: string | { message?: string; code?: string } | Array<{ msg?: string }>;
};

function humanApiError(body: ApiError, status: number): string {
  if (typeof body.message === "string" && body.message.trim()) {
    return body.message.trim();
  }
  if (typeof body.detail === "string" && body.detail.trim()) {
    return body.detail.trim();
  }
  if (body.detail && typeof body.detail === "object" && !Array.isArray(body.detail)) {
    const nested = body.detail.message;
    if (typeof nested === "string" && nested.trim()) return nested.trim();
  }
  if (Array.isArray(body.detail) && body.detail.length > 0) {
    const first = body.detail[0]?.msg;
    if (typeof first === "string" && first.trim()) return first.trim();
  }
  if (status === 401) return "Invalid email or password";
  if (status === 403) return "You do not have permission to do that";
  if (status === 404) return "Not found";
  if (status === 429) return "Too many requests. Please try again later.";
  if (status >= 500) return "Something went wrong. Please try again.";
  return "Request failed. Please try again.";
}

class ApiClient {
  private accessToken: string | null = null;
  private refreshToken: string | null = null;
  private organizationId: string | null = null;

  hydrateFromStorage() {
    if (typeof window === "undefined") return;
    this.accessToken = localStorage.getItem("if_access_token");
    this.refreshToken = localStorage.getItem("if_refresh_token");
    this.organizationId = localStorage.getItem("if_organization_id");
  }

  setSession(tokens: {
    access_token: string;
    refresh_token: string;
    organization_id?: string | null;
  }) {
    this.accessToken = tokens.access_token;
    this.refreshToken = tokens.refresh_token;
    if (tokens.organization_id) {
      this.organizationId = tokens.organization_id;
    }
    if (typeof window !== "undefined") {
      localStorage.setItem("if_access_token", tokens.access_token);
      localStorage.setItem("if_refresh_token", tokens.refresh_token);
      if (tokens.organization_id) {
        localStorage.setItem("if_organization_id", tokens.organization_id);
      }
    }
  }

  clearSession() {
    this.accessToken = null;
    this.refreshToken = null;
    this.organizationId = null;
    if (typeof window !== "undefined") {
      localStorage.removeItem("if_access_token");
      localStorage.removeItem("if_refresh_token");
      localStorage.removeItem("if_organization_id");
      localStorage.removeItem("if_user");
    }
  }

  get hasSession() {
    return Boolean(this.accessToken);
  }

  private async request<T>(
    path: string,
    options: RequestInit = {},
    retry = true,
  ): Promise<T> {
    this.hydrateFromStorage();
    const headers = new Headers(options.headers);
    headers.set("Content-Type", "application/json");
    if (this.accessToken) {
      headers.set("Authorization", `Bearer ${this.accessToken}`);
    }
    if (this.organizationId) {
      headers.set("X-Organization-Id", this.organizationId);
    }

    try {
      const res = await fetch(`${API_V1}${path}`, {
        ...options,
        headers,
      });

      if (res.status === 401 && retry && this.refreshToken) {
        const refreshed = await this.refresh();
        if (refreshed) {
          return this.request<T>(path, options, false);
        }
        this.clearSession();
      }

      if (!res.ok) {
        let error: ApiError = {};
        try {
          error = await res.json();
        } catch {
          /* ignore */
        }
        throw new Error(humanApiError(error, res.status));
      }

      if (res.status === 204) {
        return undefined as T;
      }
      return res.json() as Promise<T>;
    } catch (err) {
      const msg = err instanceof Error ? err.message : "";
      const unreachable =
        err instanceof TypeError ||
        /failed to fetch|networkerror|load failed|network request failed/i.test(msg);
      if (unreachable) {
        throw new Error(
          "Unable to reach the server. Check your connection and try again.",
        );
      }
      throw err;
    }
  }

  async refresh(): Promise<boolean> {
    if (!this.refreshToken) return false;
    try {
      const data = await fetch(`${API_V1}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: this.refreshToken }),
      }).then(async (res) => {
        if (!res.ok) return null;
        return res.json() as Promise<TokenResponse>;
      });
      if (!data?.access_token) return false;
      this.setSession({
        access_token: data.access_token,
        refresh_token: data.refresh_token,
        organization_id: data.user.primary_organization_id,
      });
      return true;
    } catch {
      return false;
    }
  }

  register(body: Record<string, unknown>) {
    return this.request<TokenResponse>(
      "/auth/register",
      {
        method: "POST",
        body: JSON.stringify(body),
      },
      false,
    );
  }

  login(body: Record<string, unknown>) {
    return this.request<TokenResponse>(
      "/auth/login",
      {
        method: "POST",
        body: JSON.stringify(body),
      },
      false,
    );
  }

  logout() {
    const token = this.refreshToken;
    this.clearSession();
    if (!token) return Promise.resolve();
    return this.request("/auth/logout", {
      method: "POST",
      body: JSON.stringify({ refresh_token: token }),
    }).catch(() => undefined);
  }

  me() {
    return this.request<UserBrief>("/auth/me");
  }

  changePassword(body: { current_password: string; new_password: string }) {
    return this.request<{ message: string }>("/auth/change-password", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  forgotPassword(email: string) {
    return this.request<{ message: string }>("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    });
  }

  resetPassword(body: { token: string; new_password: string }) {
    return this.request<{ message: string }>("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  currentOrganization() {
    return this.request<Organization>("/organizations/current");
  }

  dashboardStats() {
    return this.request<DashboardStats>("/dashboard/stats");
  }

  roles() {
    return this.request<Role[]>("/roles");
  }

  listUsers(params: { page?: number; page_size?: number } = {}) {
    const q = new URLSearchParams();
    q.set("page", String(params.page ?? 1));
    q.set("page_size", String(params.page_size ?? 100));
    return this.request<Paginated<OrgMembership>>(`/users?${q}`);
  }

  inviteUser(body: {
    email: string;
    first_name: string;
    last_name: string;
    role_id: string;
    job_title?: string | null;
    send_invite?: boolean;
  }) {
    return this.request<InviteUserResponse>("/users/invite", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  updateMembershipRole(membershipId: string, role_id: string) {
    return this.request<OrgMembership>(`/users/memberships/${membershipId}`, {
      method: "PATCH",
      body: JSON.stringify({ role_id }),
    });
  }

  permissions() {
    return this.request<{ roles: string[]; permissions: string[] }>(
      "/me/permissions",
    );
  }

  listPrograms(params: { page?: number; search?: string; status?: string } = {}) {
    const q = new URLSearchParams();
    if (params.page) q.set("page", String(params.page));
    if (params.search) q.set("search", params.search);
    if (params.status) q.set("status", params.status);
    const qs = q.toString();
    return this.request<Paginated<Program>>(`/programs${qs ? `?${qs}` : ""}`);
  }

  createProgram(body: Record<string, unknown>) {
    return this.request<Program>("/programs", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  getProgram(id: string) {
    return this.request<Program>(`/programs/${id}`);
  }

  updateProgram(id: string, body: Record<string, unknown>) {
    return this.request<Program>(`/programs/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  deleteProgram(id: string) {
    return this.request<{ message: string }>(`/programs/${id}`, {
      method: "DELETE",
    });
  }

  listProjects(
    params: {
      page?: number;
      program_id?: string;
      search?: string;
      status?: string;
    } = {},
  ) {
    const q = new URLSearchParams();
    if (params.page) q.set("page", String(params.page));
    if (params.program_id) q.set("program_id", params.program_id);
    if (params.search) q.set("search", params.search);
    if (params.status) q.set("status", params.status);
    const qs = q.toString();
    return this.request<Paginated<Project>>(`/projects${qs ? `?${qs}` : ""}`);
  }

  createProject(body: Record<string, unknown>) {
    return this.request<Project>("/projects", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  getProject(id: string) {
    return this.request<Project>(`/projects/${id}`);
  }

  updateProject(id: string, body: Record<string, unknown>) {
    return this.request<Project>(`/projects/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  deleteProject(id: string) {
    return this.request<{ message: string }>(`/projects/${id}`, {
      method: "DELETE",
    });
  }

  listActivities(projectId: string) {
    return this.request<Paginated<ActivityItem>>(
      `/activities?project_id=${projectId}&page_size=100`,
    );
  }

  createActivity(body: Record<string, unknown>) {
    return this.request<ActivityItem>("/activities", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  updateActivity(id: string, body: Record<string, unknown>) {
    return this.request<ActivityItem>(`/activities/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  listWorkPlans(projectId: string) {
    return this.request<Paginated<WorkPlan>>(
      `/work-plans?project_id=${projectId}&page_size=50`,
    );
  }

  createWorkPlan(body: Record<string, unknown>) {
    return this.request<WorkPlan>("/work-plans", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  listTasks(params: { project_id?: string; status?: string } = {}) {
    const q = new URLSearchParams();
    if (params.project_id) q.set("project_id", params.project_id);
    if (params.status) q.set("status", params.status);
    q.set("page_size", "100");
    return this.request<Paginated<TaskItem>>(`/tasks?${q.toString()}`);
  }

  createTask(body: Record<string, unknown>) {
    return this.request<TaskItem>("/tasks", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  updateTask(id: string, body: Record<string, unknown>) {
    return this.request<TaskItem>(`/tasks/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  listDonors(params: { search?: string; status?: string } = {}) {
    const q = new URLSearchParams({ page_size: "100" });
    if (params.search) q.set("search", params.search);
    if (params.status) q.set("status", params.status);
    return this.request<Paginated<Donor>>(`/donors?${q}`);
  }

  createDonor(body: Record<string, unknown>) {
    return this.request<Donor>("/donors", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  listGrants(params: { donor_id?: string; status?: string } = {}) {
    const q = new URLSearchParams({ page_size: "100" });
    if (params.donor_id) q.set("donor_id", params.donor_id);
    if (params.status) q.set("status", params.status);
    return this.request<Paginated<Grant>>(`/grants?${q}`);
  }

  createGrant(body: Record<string, unknown>) {
    return this.request<Grant>("/grants", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  updateGrant(id: string, body: Record<string, unknown>) {
    return this.request<Grant>(`/grants/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  listBudgets(params: { grant_id?: string } = {}) {
    const q = new URLSearchParams({ page_size: "100" });
    if (params.grant_id) q.set("grant_id", params.grant_id);
    return this.request<Paginated<Budget>>(`/budgets?${q}`);
  }

  createBudget(body: Record<string, unknown>) {
    return this.request<Budget>("/budgets", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  getBudget(id: string) {
    return this.request<Budget>(`/budgets/${id}`);
  }

  addBudgetLine(budgetId: string, body: Record<string, unknown>) {
    return this.request<BudgetLine>(`/budgets/${budgetId}/lines`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  listTransactions(params: { grant_id?: string; transaction_type?: string } = {}) {
    const q = new URLSearchParams({ page_size: "100" });
    if (params.grant_id) q.set("grant_id", params.grant_id);
    if (params.transaction_type) q.set("transaction_type", params.transaction_type);
    return this.request<Paginated<FinanceTxn>>(`/finance/transactions?${q}`);
  }

  createTransaction(body: Record<string, unknown>) {
    return this.request<FinanceTxn>("/finance/transactions", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  listTheoriesOfChange(params: { status?: string } = {}) {
    const q = new URLSearchParams({ page_size: "100" });
    if (params.status) q.set("status", params.status);
    return this.request<Paginated<TheoryOfChange>>(`/theories-of-change?${q}`);
  }

  createTheoryOfChange(body: Record<string, unknown>) {
    return this.request<TheoryOfChange>("/theories-of-change", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  listLogframes(params: { status?: string } = {}) {
    const q = new URLSearchParams({ page_size: "100" });
    if (params.status) q.set("status", params.status);
    return this.request<Paginated<Logframe>>(`/logframes?${q}`);
  }

  createLogframe(body: Record<string, unknown>) {
    return this.request<Logframe>("/logframes", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  addLogframeResult(logframeId: string, body: Record<string, unknown>) {
    return this.request<LogframeResult>(`/logframes/${logframeId}/results`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  listIndicators(params: { status?: string; level?: string } = {}) {
    const q = new URLSearchParams({ page_size: "100" });
    if (params.status) q.set("status", params.status);
    if (params.level) q.set("level", params.level);
    return this.request<Paginated<Indicator>>(`/indicators?${q}`);
  }

  createIndicator(body: Record<string, unknown>) {
    return this.request<Indicator>("/indicators", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  addIndicatorTarget(indicatorId: string, body: Record<string, unknown>) {
    return this.request<IndicatorTarget>(`/indicators/${indicatorId}/targets`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  listMonitoringResults(params: { indicator_id?: string; status?: string } = {}) {
    const q = new URLSearchParams({ page_size: "100" });
    if (params.indicator_id) q.set("indicator_id", params.indicator_id);
    if (params.status) q.set("status", params.status);
    return this.request<Paginated<MonitoringResult>>(`/monitoring-results?${q}`);
  }

  createMonitoringResult(body: Record<string, unknown>) {
    return this.request<MonitoringResult>("/monitoring-results", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  updateMonitoringResult(id: string, body: Record<string, unknown>) {
    return this.request<MonitoringResult>(`/monitoring-results/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  listEvaluations(params: { status?: string; evaluation_type?: string } = {}) {
    const q = new URLSearchParams({ page_size: "100" });
    if (params.status) q.set("status", params.status);
    if (params.evaluation_type) q.set("evaluation_type", params.evaluation_type);
    return this.request<Paginated<Evaluation>>(`/evaluations?${q}`);
  }

  createEvaluation(body: Record<string, unknown>) {
    return this.request<Evaluation>("/evaluations", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  listCommunities(params: { status?: string } = {}) {
    const q = new URLSearchParams({ page_size: "100" });
    if (params.status) q.set("status", params.status);
    return this.request<Paginated<Community>>(`/communities?${q}`);
  }

  createCommunity(body: Record<string, unknown>) {
    return this.request<Community>("/communities", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  listHouseholds(params: { community_id?: string; status?: string } = {}) {
    const q = new URLSearchParams({ page_size: "100" });
    if (params.community_id) q.set("community_id", params.community_id);
    if (params.status) q.set("status", params.status);
    return this.request<Paginated<Household>>(`/households?${q}`);
  }

  createHousehold(body: Record<string, unknown>) {
    return this.request<Household>("/households", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  listBeneficiaries(params: {
    household_id?: string;
    community_id?: string;
    status?: string;
    search?: string;
  } = {}) {
    const q = new URLSearchParams({ page_size: "100" });
    if (params.household_id) q.set("household_id", params.household_id);
    if (params.community_id) q.set("community_id", params.community_id);
    if (params.status) q.set("status", params.status);
    if (params.search) q.set("search", params.search);
    return this.request<Paginated<Beneficiary>>(`/beneficiaries?${q}`);
  }

  createBeneficiary(body: Record<string, unknown>) {
    return this.request<Beneficiary>("/beneficiaries", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  addBeneficiaryMembership(beneficiaryId: string, body: Record<string, unknown>) {
    return this.request<BeneficiaryMembership>(
      `/beneficiaries/${beneficiaryId}/memberships`,
      {
        method: "POST",
        body: JSON.stringify(body),
      },
    );
  }

  listBeneficiaryMemberships(params: { beneficiary_id?: string; status?: string } = {}) {
    const q = new URLSearchParams({ page_size: "100" });
    if (params.beneficiary_id) q.set("beneficiary_id", params.beneficiary_id);
    if (params.status) q.set("status", params.status);
    return this.request<Paginated<BeneficiaryMembership>>(`/beneficiary-memberships?${q}`);
  }

  analyticsOverview() {
    return this.request<AnalyticsOverview>("/analytics/overview");
  }

  listReports(params: { status?: string; report_type?: string } = {}) {
    const q = new URLSearchParams({ page_size: "100" });
    if (params.status) q.set("status", params.status);
    if (params.report_type) q.set("report_type", params.report_type);
    return this.request<Paginated<Report>>(`/reports?${q}`);
  }

  createReport(body: Record<string, unknown>) {
    return this.request<Report>("/reports", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  listSavedDashboards() {
    return this.request<Paginated<SavedDashboard>>("/saved-dashboards?page_size=100");
  }

  createSavedDashboard(body: Record<string, unknown>) {
    return this.request<SavedDashboard>("/saved-dashboards", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  listMapLayers() {
    return this.request<Paginated<MapLayer>>("/map-layers?page_size=100");
  }

  createMapLayer(body: Record<string, unknown>) {
    return this.request<MapLayer>("/map-layers", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  addMapFeature(layerId: string, body: Record<string, unknown>) {
    return this.request<MapFeature>(`/map-layers/${layerId}/features`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  listEvidence(params: { status?: string; evidence_type?: string } = {}) {
    const q = new URLSearchParams({ page_size: "100" });
    if (params.status) q.set("status", params.status);
    if (params.evidence_type) q.set("evidence_type", params.evidence_type);
    return this.request<Paginated<EvidenceItem>>(`/evidence?${q}`);
  }

  createEvidence(body: Record<string, unknown>) {
    return this.request<EvidenceItem>("/evidence", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  updateEvidence(id: string, body: Record<string, unknown>) {
    return this.request<EvidenceItem>(`/evidence/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  listAiConversations(params: { status?: string } = {}) {
    const q = new URLSearchParams({ page_size: "50" });
    if (params.status) q.set("status", params.status);
    return this.request<Paginated<AiConversation>>(`/ai/conversations?${q}`);
  }

  createAiConversation(body: Record<string, unknown> = {}) {
    return this.request<AiConversation>("/ai/conversations", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  getAiConversation(id: string) {
    return this.request<AiConversationDetail>(`/ai/conversations/${id}`);
  }

  updateAiConversation(
    id: string,
    body: { title?: string; pinned?: boolean },
  ) {
    return this.request<AiConversation>(`/ai/conversations/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  archiveAiConversation(id: string) {
    return this.request<AiConversation>(`/ai/conversations/${id}/archive`, {
      method: "POST",
    });
  }

  shareAiConversation(id: string) {
    return this.request<{ share_token: string; url_path: string }>(
      `/ai/conversations/${id}/share`,
      { method: "POST" },
    );
  }

  sendAiMessage(
    conversationId: string,
    content: string,
    pageContext?: Record<string, unknown>,
  ) {
    return this.request<AiConversationDetail>(
      `/ai/conversations/${conversationId}/messages`,
      {
        method: "POST",
        body: JSON.stringify({
          content,
          ...(pageContext ? { page_context: pageContext } : {}),
        }),
      },
    );
  }

  async streamAiMessage(
    conversationId: string,
    content: string,
    onEvent: (event: AiStreamEvent) => void,
    pageContext?: Record<string, unknown>,
  ): Promise<void> {
    this.hydrateFromStorage();
    const headers = new Headers();
    headers.set("Content-Type", "application/json");
    headers.set("Accept", "text/event-stream");
    if (this.accessToken) {
      headers.set("Authorization", `Bearer ${this.accessToken}`);
    }
    if (this.organizationId) {
      headers.set("X-Organization-Id", this.organizationId);
    }

    const res = await fetch(
      `${API_V1}/ai/conversations/${conversationId}/messages/stream`,
      {
        method: "POST",
        headers,
        body: JSON.stringify({
          content,
          ...(pageContext ? { page_context: pageContext } : {}),
        }),
      },
    );

    if (!res.ok || !res.body) {
      throw new Error("Stream failed");
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    const flush = (chunk: string) => {
      buffer += chunk;
      let idx: number;
      // SSE events are separated by a blank line.
      while ((idx = buffer.indexOf("\n\n")) !== -1) {
        const raw = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        for (const line of raw.split("\n")) {
          const trimmed = line.trim();
          if (!trimmed.startsWith("data:")) continue;
          const payload = trimmed.slice(5).trim();
          if (!payload) continue;
          try {
            onEvent(JSON.parse(payload) as AiStreamEvent);
          } catch {
            /* ignore malformed event */
          }
        }
      }
    };

    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      flush(decoder.decode(value, { stream: true }));
    }
    // Flush any trailing buffered event without a terminating blank line.
    if (buffer.trim()) {
      flush("\n\n");
    }
  }

  messageFeedback(messageId: string, feedback: "up" | "down") {
    return this.request<AiMessage>(`/ai/messages/${messageId}/feedback`, {
      method: "POST",
      body: JSON.stringify({ feedback }),
    });
  }

  regenerateAiMessage(conversationId: string) {
    return this.request<AiConversationDetail>(
      `/ai/conversations/${conversationId}/regenerate`,
      { method: "POST" },
    );
  }

  suggestedQuestions() {
    return this.request<{ questions: string[] }>("/ai/suggested-questions");
  }

  dashboardInsights() {
    return this.request<AiDashboardInsights>("/ai/insights/dashboard");
  }

  scanInsights(persist = false) {
    return this.request<Record<string, unknown>>("/ai/insights/scan", {
      method: "POST",
      body: JSON.stringify({ persist }),
    });
  }

  generateAiReport(body: {
    report_type: string;
    program_id?: string;
    project_id?: string;
    save_narrative?: boolean;
  }) {
    return this.request<AiReport>("/ai/reports/generate", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  async exportAiConversation(id: string): Promise<string> {
    const headers = new Headers();
    if (this.accessToken) headers.set("Authorization", `Bearer ${this.accessToken}`);
    if (this.organizationId) headers.set("X-Organization-Id", this.organizationId);
    const res = await fetch(`${API_V1}/ai/conversations/${id}/export`, {
      headers,
    });
    if (!res.ok) throw new Error("Export failed");
    return res.text();
  }

  listAiPredictions(params: { status?: string; severity?: string } = {}) {
    const q = new URLSearchParams({ page_size: "100" });
    if (params.status) q.set("status", params.status);
    if (params.severity) q.set("severity", params.severity);
    return this.request<Paginated<AiPrediction>>(`/ai/predictions?${q}`);
  }

  generateAiPrediction(body: Record<string, unknown> = {}) {
    return this.request<AiPrediction>("/ai/predictions", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  updateAiPrediction(id: string, body: Record<string, unknown>) {
    return this.request<AiPrediction>(`/ai/predictions/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  listAiNarratives() {
    return this.request<Paginated<AiNarrative>>("/ai/narratives?page_size=100");
  }

  generateAiNarrative(body: Record<string, unknown>) {
    return this.request<AiNarrative>("/ai/narratives", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  listKnowledge(params: { search?: string; category?: string } = {}) {
    const q = new URLSearchParams({ page_size: "100" });
    if (params.search) q.set("search", params.search);
    if (params.category) q.set("category", params.category);
    return this.request<Paginated<KnowledgeDocument>>(`/knowledge?${q}`);
  }

  createKnowledge(body: Record<string, unknown>) {
    return this.request<KnowledgeDocument>("/knowledge", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  listMarketplaceApps(params: { category?: string; search?: string } = {}) {
    const q = new URLSearchParams({ page_size: "100" });
    if (params.category) q.set("category", params.category);
    if (params.search) q.set("search", params.search);
    return this.request<Paginated<MarketplaceApp>>(`/marketplace/apps?${q}`);
  }

  listMarketplaceInstallations() {
    return this.request<Paginated<MarketplaceInstallation>>(
      "/marketplace/installations?page_size=100"
    );
  }

  installMarketplaceApp(body: Record<string, unknown>) {
    return this.request<MarketplaceInstallation>("/marketplace/installations", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  updateMarketplaceInstallation(id: string, body: Record<string, unknown>) {
    return this.request<MarketplaceInstallation>(`/marketplace/installations/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  listApiKeys() {
    return this.request<Paginated<OrgApiKey>>("/api-keys?page_size=100");
  }

  createApiKey(body: Record<string, unknown>) {
    return this.request<OrgApiKeyCreated>("/api-keys", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  revokeApiKey(id: string) {
    return this.request<OrgApiKey>(`/api-keys/${id}/revoke`, { method: "POST" });
  }

  rotateApiKey(id: string) {
    return this.request<OrgApiKeyCreated>(`/api-keys/${id}/rotate`, {
      method: "POST",
    });
  }

  listIntegrations() {
    return this.request<Paginated<IntegrationConnection>>("/integrations?page_size=100");
  }

  createIntegration(body: Record<string, unknown>) {
    return this.request<IntegrationConnection>("/integrations", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  testIntegration(id: string) {
    return this.request<IntegrationConnection>(`/integrations/${id}/test`, {
      method: "POST",
    });
  }

  listConnectors(params: { category?: string; include_future?: boolean } = {}) {
    const q = new URLSearchParams();
    if (params.category) q.set("category", params.category);
    if (params.include_future === false) q.set("include_future", "false");
    const qs = q.toString();
    return this.request<ConnectorCatalogResponse>(
      `/connectors${qs ? `?${qs}` : ""}`,
    );
  }

  getConnector(code: string) {
    return this.request<ConnectorDefinition>(
      `/connectors/${encodeURIComponent(code)}`,
    );
  }

  enableConnector(body: {
    connector_code: string;
    name?: string;
    config?: Record<string, unknown>;
    secret?: string;
    endpoint_url?: string;
    events?: string[];
  }) {
    return this.request<EnabledConnector>("/connectors/enable", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  integrationHealth(id: string) {
    return this.request<ConnectorHealthResult>(`/integrations/${id}/health`, {
      method: "POST",
    });
  }

  syncIntegration(
    id: string,
    body: {
      mode?: "full" | "incremental" | "dry_run";
      direction?: "pull" | "push";
      dry_run?: boolean;
    } = {},
  ) {
    return this.request<ConnectorSyncJob>(`/integrations/${id}/sync`, {
      method: "POST",
      body: JSON.stringify({
        mode: body.mode ?? "incremental",
        direction: body.direction ?? "pull",
        dry_run: body.dry_run ?? false,
      }),
    });
  }

  listSyncJobs(
    params: {
      page?: number;
      page_size?: number;
      integration_id?: string;
      status?: string;
    } = {},
  ) {
    const q = new URLSearchParams();
    if (params.page) q.set("page", String(params.page));
    if (params.page_size) q.set("page_size", String(params.page_size));
    if (params.integration_id) q.set("integration_id", params.integration_id);
    if (params.status) q.set("status", params.status);
    const qs = q.toString();
    return this.request<Paginated<ConnectorSyncJob>>(
      `/integrations/sync-jobs${qs ? `?${qs}` : ""}`,
    );
  }

  cloneIntegration(id: string, name?: string) {
    const q = name ? `?name=${encodeURIComponent(name)}` : "";
    return this.request<{ id: string; name: string; status: string }>(
      `/integrations/${id}/clone${q}`,
      { method: "POST" },
    );
  }

  exportIntegration(id: string) {
    return this.request<IntegrationExport>(`/integrations/${id}/export`);
  }

  startIntegrationOAuth(
    id: string,
    body: { redirect_uri: string; connector_code?: string },
  ) {
    return this.request<{ authorize_url: string; state: string }>(
      `/integrations/${id}/oauth/start`,
      { method: "POST", body: JSON.stringify(body) },
    );
  }

  integrationMonitoring() {
    return this.request<IntegrationMonitoring>("/integrations/monitoring");
  }

  listFieldMappings(params: { entity_type?: string; page_size?: number } = {}) {
    const q = new URLSearchParams({
      page_size: String(params.page_size ?? 100),
    });
    if (params.entity_type) q.set("entity_type", params.entity_type);
    return this.request<Paginated<FieldMappingProfile>>(
      `/field-mappings?${q}`,
    );
  }

  createFieldMapping(body: {
    name: string;
    code?: string;
    entity_type?: string;
    connector_code?: string;
    integration_id?: string;
    mappings?: { source: string; target: string; transform?: string }[];
    transformations?: Record<string, unknown>;
    defaults?: Record<string, unknown>;
    validation_rules?: { field: string; required?: boolean }[];
  }) {
    return this.request<{ id: string; code: string; name: string }>(
      "/field-mappings",
      { method: "POST", body: JSON.stringify(body) },
    );
  }

  previewFieldMapping(id: string, sample: Record<string, unknown>) {
    return this.request<FieldMappingPreview>(
      `/field-mappings/${id}/preview`,
      { method: "POST", body: JSON.stringify({ sample }) },
    );
  }

  listWebhookDeliveries(params: { status?: string; page?: number } = {}) {
    const q = new URLSearchParams({ page_size: "50" });
    if (params.status) q.set("status", params.status);
    if (params.page) q.set("page", String(params.page));
    return this.request<Paginated<WebhookDelivery>>(
      `/webhook-deliveries?${q}`,
    );
  }

  redriveDeadWebhooks(limit = 25) {
    return this.request<{ redriven: number }>(
      `/webhooks/dead/redrive?limit=${limit}`,
      { method: "POST" },
    );
  }

  getDeveloperPortal() {
    return this.request<DeveloperPortal>("/developer/portal");
  }

  listDeveloperEvents() {
    return this.request<{ items: PlatformEventDef[] }>("/developer/events");
  }

  async downloadDeveloperOpenApi(filename = "impactflow-openapi.json") {
    const headers = new Headers();
    if (this.accessToken) headers.set("Authorization", `Bearer ${this.accessToken}`);
    if (this.organizationId) headers.set("X-Organization-Id", this.organizationId);
    const res = await fetch(`${API_V1}/developer/openapi`, { headers });
    if (!res.ok) throw new Error("OpenAPI download failed");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  listPlugins() {
    return this.request<{ items: PluginManifest[] }>("/plugins");
  }

  getBranding() {
    return this.request<OrgBranding>("/branding");
  }

  updateBranding(body: Record<string, unknown>) {
    return this.request<OrgBranding>("/branding", {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  listBillingPlans() {
    return this.request<Paginated<SubscriptionPlan>>("/billing/plans");
  }

  listPublicBillingPlans() {
    return fetch(`${API_V1}/public/billing/plans`)
      .then(async (res) => {
        if (!res.ok) {
          throw new Error("Unable to load pricing. Please try again.");
        }
        return res.json() as Promise<Paginated<SubscriptionPlan>>;
      })
      .catch((err: unknown) => {
        if (err instanceof TypeError) {
          throw new Error(
            "Unable to reach the server. Check your connection and try again.",
          );
        }
        throw err;
      });
  }

  getSubscription() {
    return this.request<OrganizationSubscription>("/billing/subscription");
  }

  changeSubscription(body: {
    plan_code: string;
    billing_period?: string;
    seats?: number;
    coupon_code?: string;
  }) {
    return this.request<
      | OrganizationSubscription
      | {
          mode: string;
          authorization_url?: string | null;
          reference?: string | null;
          subscription?: OrganizationSubscription;
        }
    >("/billing/subscription/change", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  verifyPaystack(reference: string) {
    return this.request<{ mode: string; subscription?: OrganizationSubscription }>(
      `/billing/paystack/verify?reference=${encodeURIComponent(reference)}`,
    );
  }

  getBillingUsage() {
    return this.request<BillingUsage>("/billing/usage");
  }

  listBillingInvoices() {
    return this.request<{ items: BillingInvoice[] }>("/billing/invoices");
  }

  cancelSubscription(at_period_end = true) {
    return this.request<OrganizationSubscription>("/billing/subscription/cancel", {
      method: "POST",
      body: JSON.stringify({ at_period_end }),
    });
  }

  getPlatformBillingAnalytics() {
    return this.request<PlatformBillingAnalytics>("/platform/billing/analytics");
  }

  assignPlatformPlan(body: {
    organization_id: string;
    plan_code: string;
    billing_period?: string;
  }) {
    return this.request<OrganizationSubscription>("/platform/billing/assign", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  verifyEmail(token: string) {
    return this.request<{ message: string }>("/auth/verify-email", {
      method: "POST",
      body: JSON.stringify({ token }),
    });
  }

  getFeatures(environment = "production") {
    return this.request<{ features: Record<string, boolean>; environment: string }>(
      `/features?environment=${encodeURIComponent(environment)}`,
    );
  }

  listDomains() {
    return this.request<Paginated<OrgDomain>>("/domains");
  }

  createDomain(body: { hostname: string; is_primary?: boolean }) {
    return this.request<OrgDomain>("/domains", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  verifyDomain(domainId: string) {
    return this.request<OrgDomain>(`/domains/${domainId}/verify`, { method: "POST" });
  }

  getOnboarding() {
    return this.request<OnboardingState>("/onboarding");
  }

  updateOnboarding(body: Record<string, unknown>) {
    return this.request<OnboardingState>("/onboarding", {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  listThemePresets() {
    return this.request<{ items: { code: string; name: string; primary: string; secondary: string; accent: string }[] }>(
      "/onboarding/theme-presets",
    );
  }

  patchAdminSettings(settings: Record<string, unknown>) {
    return this.request<{ id: string; settings: Record<string, unknown> }>("/admin/settings", {
      method: "PATCH",
      body: JSON.stringify({ settings }),
    });
  }

  listBackups() {
    return this.request<Paginated<{ id: string; label: string; status: string; checksum?: string; completed_at?: string; size_bytes: number }>>("/backups");
  }

  createBackup(body: { label?: string } = {}) {
    return this.request<{ id: string; label: string; status: string; checksum?: string }>("/backups", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  exportTenantData() {
    return this.request<Record<string, unknown>>("/backups/export");
  }

  listLocales() {
    return this.request<Paginated<{ locale: string; name: string; native_name: string; direction: string; coverage_pct: number }>>("/locales");
  }

  getCustomerSuccess() {
    return this.request<CustomerSuccessMetrics>("/customer-success");
  }

  getOpsObservability() {
    return this.request<{
      organizations: number;
      users: number;
      api_health: string;
      components: { name: string; status: string }[];
      generated_at: string;
    }>("/ops/observability");
  }

  getPluginSdkManifest() {
    return this.request<{
      sdk_version: string;
      registration_points: string[];
      rules: string[];
      example_manifest: Record<string, unknown>;
    }>("/plugin-sdk/manifest");
  }

  upsertSso(body: {
    provider: string;
    config: Record<string, unknown>;
    client_secret?: string;
    enforce_sso?: boolean;
    scim_enabled?: boolean;
    allowed_domains?: string[];
  }) {
    return this.request<{ id: string; provider: string; status: string; enforce_sso: boolean }>(
      "/sso",
      { method: "PUT", body: JSON.stringify(body) },
    );
  }

  listNotifications(params: { page?: number; status?: string } = {}) {
    const q = new URLSearchParams();
    if (params.page) q.set("page", String(params.page));
    if (params.status) q.set("status", params.status);
    const qs = q.toString();
    return this.request<Paginated<NotificationItem>>(
      `/notifications${qs ? `?${qs}` : ""}`,
    );
  }

  notificationsUnreadCount() {
    return this.request<{ unread_count: number }>("/notifications/unread-count");
  }

  markNotificationRead(id: string) {
    return this.request<NotificationItem>(`/notifications/${id}/read`, {
      method: "POST",
    });
  }

  markAllNotificationsRead() {
    return this.request<{ message: string }>("/notifications/read-all", {
      method: "POST",
    });
  }

  listSurveys(
    params: {
      status?: string;
      category?: string;
      program_id?: string;
      project_id?: string;
      search?: string;
    } = {},
  ) {
    const q = new URLSearchParams({ page_size: "100" });
    if (params.status) q.set("status", params.status);
    if (params.category) q.set("category", params.category);
    if (params.program_id) q.set("program_id", params.program_id);
    if (params.project_id) q.set("project_id", params.project_id);
    if (params.search) q.set("search", params.search);
    return this.request<Paginated<Survey>>(`/surveys?${q}`);
  }

  createSurvey(body: Record<string, unknown>) {
    return this.request<Survey>("/surveys", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  getSurvey(id: string) {
    return this.request<SurveyDetail>(`/surveys/${id}`);
  }

  updateSurvey(id: string, body: Record<string, unknown>) {
    return this.request<Survey>(`/surveys/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  cloneSurvey(id: string) {
    return this.request<Survey>(`/surveys/${id}/clone`, { method: "POST" });
  }

  archiveSurvey(id: string) {
    return this.request<Survey>(`/surveys/${id}/archive`, { method: "POST" });
  }

  listFieldTypes() {
    return this.request<FieldTypeInfo[]>("/surveys/field-types");
  }

  listSurveyVersions(id: string) {
    return this.request<SurveyVersionDetail[]>(`/surveys/${id}/versions`);
  }

  getSurveyVersion(id: string, version: number) {
    return this.request<SurveyVersionDetail>(`/surveys/${id}/versions/${version}`);
  }

  exportSurveySchema(id: string) {
    return this.request<{
      name: string;
      code: string;
      category?: string | null;
      schema: SurveySchema;
    }>(`/surveys/${id}/export-schema`);
  }

  importSurveySchema(id: string, schema: SurveySchema, changelog?: string) {
    return this.request<SurveyDetail>(`/surveys/${id}/import-schema`, {
      method: "POST",
      body: JSON.stringify({ schema, changelog }),
    });
  }

  listAssignments(surveyId: string) {
    return this.request<SurveyAssignment[]>(`/surveys/${surveyId}/assignments`);
  }

  createAssignment(surveyId: string, body: Record<string, unknown>) {
    return this.request<SurveyAssignment>(`/surveys/${surveyId}/assignments`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  deleteAssignment(surveyId: string, assignmentId: string) {
    return this.request<void>(`/surveys/${surveyId}/assignments/${assignmentId}`, {
      method: "DELETE",
    });
  }

  submitSurveyResponse(id: string, body: Record<string, unknown>) {
    return this.request<SurveySubmission>(`/surveys/${id}/responses`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  updateSurveyResponse(id: string, body: Record<string, unknown>) {
    return this.request<SurveySubmission>(`/survey-responses/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  listSurveyResponses(
    params: { survey_id?: string; status?: string; page?: number; page_size?: number } = {},
  ) {
    const q = new URLSearchParams({ page_size: String(params.page_size ?? 50) });
    if (params.survey_id) q.set("survey_id", params.survey_id);
    if (params.status) q.set("status", params.status);
    if (params.page) q.set("page", String(params.page));
    return this.request<Paginated<SurveySubmission>>(`/survey-responses?${q}`);
  }

  getSurveyAnalytics(id: string) {
    return this.request<SurveyAnalytics>(`/surveys/${id}/analytics`);
  }

  async exportSurveyResponses(
    id: string,
    format: "csv" | "html" | "xlsx" = "csv",
  ): Promise<string> {
    const headers = new Headers();
    if (this.accessToken) headers.set("Authorization", `Bearer ${this.accessToken}`);
    if (this.organizationId) headers.set("X-Organization-Id", this.organizationId);
    const res = await fetch(`${API_V1}/surveys/${id}/export?format=${format}`, {
      headers,
    });
    if (!res.ok) throw new Error("Export failed");
    return res.text();
  }

  async exportSurveyResponsesCsv(id: string): Promise<string> {
    return this.exportSurveyResponses(id, "csv");
  }

  getPublicBranding(slug: string) {
    return this.request<PublicBranding>(`/public/branding/${encodeURIComponent(slug)}`);
  }

  indicatorProgress() {
    return this.request<{ items: IndicatorProgressRow[] }>("/indicators/progress");
  }

  async exportReportMarkdown(id: string): Promise<string> {
    const headers = new Headers();
    if (this.accessToken) headers.set("Authorization", `Bearer ${this.accessToken}`);
    if (this.organizationId) headers.set("X-Organization-Id", this.organizationId);
    const res = await fetch(`${API_V1}/reports/${id}/export?format=markdown`, {
      headers,
    });
    if (!res.ok) throw new Error("Export failed");
    return res.text();
  }

  // ------------------------------------------------------------------------- //
  // Workflow engine (Epic 3)
  // ------------------------------------------------------------------------- //

  listWorkflowTriggers() {
    return this.request<{ triggers: WorkflowCatalogItem[] }>(
      "/workflows/triggers",
    );
  }

  listWorkflowActions() {
    return this.request<{ actions: WorkflowCatalogItem[] }>("/workflows/actions");
  }

  listWorkflowOperators() {
    return this.request<{ operators: WorkflowOperator[] }>(
      "/workflows/operators",
    );
  }

  listWorkflowTemplates() {
    return this.request<{ templates: WorkflowTemplate[] }>(
      "/workflows/templates",
    );
  }

  cloneWorkflowTemplate(templateCode: string) {
    return this.request<Workflow>(
      `/workflows/templates/${encodeURIComponent(templateCode)}/clone`,
      { method: "POST" },
    );
  }

  workflowMetrics() {
    return this.request<WorkflowMetrics>("/workflows/metrics");
  }

  listWorkflows(
    params: {
      page?: number;
      status?: string;
      category?: string;
      is_template?: boolean;
      search?: string;
    } = {},
  ) {
    const q = new URLSearchParams({ page_size: "100" });
    if (params.page) q.set("page", String(params.page));
    if (params.status) q.set("status", params.status);
    if (params.category) q.set("category", params.category);
    if (typeof params.is_template === "boolean")
      q.set("is_template", String(params.is_template));
    if (params.search) q.set("search", params.search);
    return this.request<Paginated<Workflow>>(`/workflows?${q}`);
  }

  createWorkflow(body: Record<string, unknown>) {
    return this.request<Workflow>("/workflows", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  getWorkflow(id: string) {
    return this.request<WorkflowDetail>(`/workflows/${id}`);
  }

  updateWorkflow(id: string, body: Record<string, unknown>) {
    return this.request<WorkflowDetail>(`/workflows/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  cloneWorkflow(id: string, name?: string) {
    return this.request<Workflow>(`/workflows/${id}/clone`, {
      method: "POST",
      body: JSON.stringify({ name }),
    });
  }

  archiveWorkflow(id: string) {
    return this.request<Workflow>(`/workflows/${id}/archive`, { method: "POST" });
  }

  enableWorkflow(id: string) {
    return this.request<Workflow>(`/workflows/${id}/enable`, { method: "POST" });
  }

  disableWorkflow(id: string) {
    return this.request<Workflow>(`/workflows/${id}/disable`, { method: "POST" });
  }

  activateWorkflow(id: string) {
    return this.request<Workflow>(`/workflows/${id}/activate`, { method: "POST" });
  }

  listWorkflowVersions(id: string) {
    return this.request<WorkflowVersion[]>(`/workflows/${id}/versions`);
  }

  getWorkflowVersion(id: string, version: number) {
    return this.request<WorkflowVersionDetail>(
      `/workflows/${id}/versions/${version}`,
    );
  }

  exportWorkflowDefinition(id: string) {
    return this.request<WorkflowDefinitionExport>(
      `/workflows/${id}/export-definition`,
    );
  }

  importWorkflowDefinition(
    id: string,
    definition: WorkflowDefinition,
    changelog?: string,
  ) {
    return this.request<WorkflowVersion>(`/workflows/${id}/import-definition`, {
      method: "POST",
      body: JSON.stringify({ definition, changelog }),
    });
  }

  runWorkflow(id: string, inputs?: Record<string, unknown>) {
    return this.request<WorkflowRun>(`/workflows/${id}/run`, {
      method: "POST",
      body: JSON.stringify({ inputs }),
    });
  }

  listWorkflowRuns(
    params: { workflow_id?: string; status?: string; page?: number } = {},
  ) {
    const q = new URLSearchParams({ page_size: "50" });
    if (params.workflow_id) q.set("workflow_id", params.workflow_id);
    if (params.status) q.set("status", params.status);
    if (params.page) q.set("page", String(params.page));
    return this.request<Paginated<WorkflowRun>>(`/workflow-runs?${q}`);
  }

  getWorkflowRun(id: string) {
    return this.request<WorkflowRunDetail>(`/workflow-runs/${id}`);
  }

  cancelWorkflowRun(id: string) {
    return this.request<WorkflowRun>(`/workflow-runs/${id}/cancel`, {
      method: "POST",
    });
  }

  listWorkflowApprovals(
    params: { status?: string; mine?: boolean; page?: number } = {},
  ) {
    const q = new URLSearchParams({ page_size: "50" });
    if (params.status) q.set("status", params.status);
    if (params.mine) q.set("mine", "true");
    if (params.page) q.set("page", String(params.page));
    return this.request<Paginated<WorkflowApproval>>(`/workflow-approvals?${q}`);
  }

  decideWorkflowApproval(
    id: string,
    decision: "approved" | "rejected" | "returned",
    comments?: string,
  ) {
    return this.request<WorkflowApproval>(
      `/workflow-approvals/${id}/decide`,
      {
        method: "POST",
        body: JSON.stringify({ decision, comments }),
      },
    );
  }

  listWorkflowSchedules(workflowId: string) {
    return this.request<WorkflowSchedule[]>(
      `/workflows/${workflowId}/schedules`,
    );
  }

  createWorkflowSchedule(workflowId: string, body: Record<string, unknown>) {
    return this.request<WorkflowSchedule>(`/workflows/${workflowId}/schedules`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  updateWorkflowSchedule(
    workflowId: string,
    scheduleId: string,
    body: Record<string, unknown>,
  ) {
    return this.request<WorkflowSchedule>(
      `/workflows/${workflowId}/schedules/${scheduleId}`,
      {
        method: "PATCH",
        body: JSON.stringify(body),
      },
    );
  }

  deleteWorkflowSchedule(workflowId: string, scheduleId: string) {
    return this.request<{ message: string }>(
      `/workflows/${workflowId}/schedules/${scheduleId}`,
      { method: "DELETE" },
    );
  }

  draftAiWorkflow(prompt: string, save = false) {
    return this.request<AiWorkflowDraft>("/ai/workflows/draft", {
      method: "POST",
      body: JSON.stringify({ prompt, save }),
    });
  }

  // Field operations (Epic 4)
  fieldOpsMetrics() {
    return this.request<FieldOpsMetrics>("/field-ops/metrics");
  }

  listFieldDevices(params: { page?: number; status?: string } = {}) {
    const q = new URLSearchParams({ page_size: "50" });
    if (params.page) q.set("page", String(params.page));
    if (params.status) q.set("status", params.status);
    return this.request<Paginated<FieldDevice>>(`/devices?${q}`);
  }

  updateFieldDeviceStatus(id: string, status: "active" | "deactivated" | "revoked") {
    return this.request<FieldDevice>(`/devices/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
  }

  listSyncSessions(params: { page?: number; device_id?: string } = {}) {
    const q = new URLSearchParams({ page_size: "50" });
    if (params.page) q.set("page", String(params.page));
    if (params.device_id) q.set("device_id", params.device_id);
    return this.request<Paginated<SyncSession>>(`/sync/sessions?${q}`);
  }

  listMediaUploads(params: { page?: number; status?: string } = {}) {
    const q = new URLSearchParams({ page_size: "50" });
    if (params.page) q.set("page", String(params.page));
    if (params.status) q.set("status", params.status);
    return this.request<Paginated<MediaUploadRecord>>(`/media/uploads?${q}`);
  }

  // ------------------------------------------------------------------------- //
  // Executive analytics & donor reporting (Epic 5)
  // ------------------------------------------------------------------------- //

  executiveDashboard(params: { program_id?: string; project_id?: string } = {}) {
    const q = new URLSearchParams();
    if (params.program_id) q.set("program_id", params.program_id);
    if (params.project_id) q.set("project_id", params.project_id);
    const qs = q.toString();
    return this.request<ExecutiveDashboard>(
      `/executive/dashboard${qs ? `?${qs}` : ""}`,
    );
  }

  executivePortfolio(
    params: {
      program_id?: string;
      project_id?: string;
      grant_id?: string;
    } = {},
  ) {
    const q = new URLSearchParams();
    if (params.program_id) q.set("program_id", params.program_id);
    if (params.project_id) q.set("project_id", params.project_id);
    if (params.grant_id) q.set("grant_id", params.grant_id);
    const qs = q.toString();
    return this.request<ExecutivePortfolio>(
      `/executive/portfolio${qs ? `?${qs}` : ""}`,
    );
  }

  executiveImpact() {
    return this.request<ExecutiveImpact>("/executive/impact");
  }

  executiveCompliance() {
    return this.request<ExecutiveCompliance>("/executive/compliance");
  }

  executiveRisks() {
    return this.request<ExecutiveRisks>("/executive/risks");
  }

  createExecutiveBrief(body: {
    audience?: string;
    program_id?: string;
    project_id?: string;
    save_as_report?: boolean;
  }) {
    return this.request<ExecutiveBriefResponse>("/executive/briefs", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  listReportTemplates(params: { category?: string; page?: number } = {}) {
    const q = new URLSearchParams({ page_size: "50" });
    if (params.category) q.set("category", params.category);
    if (params.page) q.set("page", String(params.page));
    return this.request<Paginated<ReportTemplate>>(`/report-templates?${q}`);
  }

  cloneReportTemplate(body: {
    code?: string;
    template_id?: string;
    name?: string;
  }) {
    return this.request<ClonedReportTemplate>("/report-templates/clone", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  buildReport(body: {
    name: string;
    template_code?: string;
    template_id?: string;
    report_type?: string;
    program_id?: string;
    project_id?: string;
    grant_id?: string;
    period_start?: string;
    period_end?: string;
    generate_narrative?: boolean;
    narrative_type?: string;
    save_version?: boolean;
  }) {
    return this.request<Report>("/reports/build", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  listReportVersions(reportId: string) {
    return this.request<{ items: ReportVersion[] }>(
      `/reports/${reportId}/versions`,
    );
  }

  createReportVersion(
    reportId: string,
    body: { changelog?: string; citations?: Record<string, unknown>[] } = {},
  ) {
    return this.request<ReportVersion>(`/reports/${reportId}/versions`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  approveReport(reportId: string) {
    return this.request<Report>(`/reports/${reportId}/approve`, {
      method: "POST",
    });
  }

  publishReport(reportId: string) {
    return this.request<Report>(`/reports/${reportId}/publish`, {
      method: "POST",
    });
  }

  async downloadReportExport(
    reportId: string,
    format: ReportExportFormat,
    filename?: string,
  ): Promise<void> {
    const headers = new Headers();
    if (this.accessToken) headers.set("Authorization", `Bearer ${this.accessToken}`);
    if (this.organizationId) headers.set("X-Organization-Id", this.organizationId);
    const res = await fetch(
      `${API_V1}/reports/${reportId}/export/download?format=${encodeURIComponent(format)}`,
      { headers },
    );
    if (!res.ok) throw new Error("Export download failed");
    const blob = await res.blob();
    const cd = res.headers.get("Content-Disposition");
    const match = cd?.match(/filename="?([^"]+)"?/i);
    const name = filename ?? match?.[1] ?? `report.${format === "markdown" ? "md" : format}`;
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    a.click();
    URL.revokeObjectURL(url);
  }
}

export const api = new ApiClient();
