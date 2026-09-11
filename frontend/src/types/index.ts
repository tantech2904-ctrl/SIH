export interface Role {
  name: string;
}

export interface Me {
  id: string;
  email: string;
  full_name: string;
  roles: string[];
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface EventListItem {
  event_id: string;
  timestamp: string;
  event_type: string;
  category: string;
  severity: string;
  source_ip: string | null;
  destination_ip: string | null;
  user_name: string | null;
  vendor: string | null;
  product: string | null;
  message: string | null;
  risk_score: number | null;
  threat_malicious?: boolean | null;
  threat_context?: Record<string, any> | null;
  processing_status: string;
  detected_format: string | null;
  parser_id: string | null;
}

export interface EventDetail {
  event_id: string;
  ingestion_id: string;
  correlation_id: string;
  ingested_at: string | null;
  source: string;
  source_type: string;
  filename: string;
  content_type: string;
  raw_size: number;
  detected_format: string | null;
  detection_confidence: number | null;
  parser_id: string | null;
  parser_version: string | null;
  processing_status: string;
  error_message: string | null;
  severity: string | null;
  risk_score: number | null;
  sha256: string | null;
  canonical: any | null;
}

export interface RawEvent {
  event_id: string;
  content_type: string;
  raw_size: number;
  sha256: string;
  content: string;
}

export interface TimelineStage {
  stage: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  duration_ms: number;
  component: string;
  error: string | null;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages?: number;
}

export interface DashboardData {
  totals: {
    events: number;
    canonical_events: number;
    quarantined: number;
    high_risk_events: number;
    critical_alerts: number;
    open_alerts: number;
  };
  throughput: {
    events_last_minute: number;
    events_per_second: number;
  };
  status_counts: Record<string, number>;
  severity_counts: Record<string, number>;
  category_counts: Record<string, number>;
  format_counts: Record<string, number>;
  top_vendors: Record<string, number>;
  top_source_ips: { ip: string; count: number }[];
  top_destination_ips: { ip: string; count: number }[];
  hourly_throughput: { hour: string; count: number }[];
}

export interface QuarantineItem {
  id: string;
  event_id: string;
  reason: string;
  stage: string;
  detail: string;
  detected_format: string | null;
  detection_confidence: number | null;
  parser_id: string | null;
  retry_count: number;
  status: string;
  created_at: string;
}

export interface QuarantineAnalysisCandidate {
  name: string;
  value: string;
  inferred_types: string[];
  suggested_canonical: string | null;
  confidence: number;
  reason: string;
}

export interface QuarantineAnalysis {
  delimiter: string | null;
  field_count: number;
  notes: string[];
  candidates: QuarantineAnalysisCandidate[];
}

export interface AlertItem {
  alert_id: string;
  event_id: string;
  rule_id: string;
  rule_name: string;
  severity: string;
  risk_score: number;
  description: string;
  mitre: string[];
  details: Record<string, any>;
  status: string;
  incident_id: string | null;
  created_at: string;
}

export interface IncidentItem {
  incident_id: string;
  title: string;
  description: string;
  severity: string;
  status: string;
  first_seen: string;
  last_seen: string;
  source: string;
  affected_assets: string[];
  indicators: string[];
  related_events: string[];
  mitre: string[];
  notes: { author: string; text: string; at: string }[];
}

export interface ParserItem {
  parser_id: string;
  name: string;
  vendor: string;
  format: string;
  version: string;
  enabled: boolean;
  success_count: number;
  failure_count: number;
  last_used_at: string | null;
  metadata?: Record<string, any>;
}

export interface DriftItem {
  id: string;
  vendor: string;
  parser_id: string;
  expected_field: string;
  observed_field: string;
  suggested_canonical: string | null;
  affected_events: number;
  confidence: number;
  reason: string;
  approved: boolean;
  sample_event_id: string | null;
  created_at: string;
}

export interface MappingItem {
  id: string;
  parser_id: string;
  parser_version: string;
  original_field: string;
  canonical_field: string;
  transformation: string;
  confidence: number;
  source: string;
  approved: boolean;
  notes: string;
  created_at: string;
}

export interface AuditItem {
  audit_id: string;
  timestamp: string;
  actor: string;
  action: string;
  resource: string;
  resource_id: string | null;
  source_ip: string | null;
  correlation_id: string | null;
  previous_state: any;
  new_state: any;
  integrity_hash: string;
  prev_hash: string;
}

export interface IntegrityResult {
  evidence_id: string;
  original_hash: string;
  recalculated_hash: string | null;
  integrity_status: "VERIFIED" | "MISMATCH" | "UNAVAILABLE";
  verification_timestamp: string;
}

export interface ProviderStatus {
  provider: string;
  configured: boolean;
  indicator_types: string[];
}

export interface ReplayResult {
  replay_id: string;
  previous_status: string;
  new_status: string;
  result: string;
  error?: string | null;
}