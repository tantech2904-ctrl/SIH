import type {
  AlertItem,
  AuditItem,
  AuditVerifyResult,
  DashboardData,
  DriftItem,
  EventDetail,
  EventListItem,
  IncidentItem,
  IntegrityResult,
  MappingItem,
  Me,
  Page,
  ParserItem,
  ProviderStatus,
  QuarantineAnalysis,
  QuarantineItem,
  RawEvent,
  ReplayResult,
  TimelineStage,
  TokenResponse,
} from "@/types";

const API_BASE = "/api/v1";

let accessToken: string | null = localStorage.getItem("ulpf.access_token");
let refreshToken: string | null = localStorage.getItem("ulpf.refresh_token");

export function setTokens(access: string, refresh: string) {
  accessToken = access;
  refreshToken = refresh;
  localStorage.setItem("ulpf.access_token", access);
  localStorage.setItem("ulpf.refresh_token", refresh);
}

export function clearTokens() {
  accessToken = null;
  refreshToken = null;
  localStorage.removeItem("ulpf.access_token");
  localStorage.removeItem("ulpf.refresh_token");
}

export function getAccessToken() {
  return accessToken;
}

export class ApiError extends Error {
  code: string;
  correlationId?: string;
  status: number;
  details?: any;
  constructor(message: string, code: string, status: number, correlationId?: string, details?: any) {
    super(message);
    this.code = code;
    this.status = status;
    this.correlationId = correlationId;
    this.details = details;
  }
}

async function tryRefresh(): Promise<boolean> {
  if (!refreshToken) return false;
  try {
    const r = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!r.ok) return false;
    const data = await r.json();
    setTokens(data.access_token, data.refresh_token);
    return true;
  } catch {
    return false;
  }
}

async function request<T>(
  path: string,
  opts: RequestInit = {},
  retry = true,
): Promise<T> {
  const headers = new Headers(opts.headers || {});
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  if (!(opts.body instanceof FormData) && opts.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${API_BASE}${path}`, { ...opts, headers });

  if (res.status === 401 && retry) {
    const ok = await tryRefresh();
    if (ok) return request<T>(path, opts, false);
    clearTokens();
    window.dispatchEvent(new CustomEvent("ulpf:logout"));
  }

  const text = await res.text();
  const data = text ? safeJson(text) : null;

  if (!res.ok) {
    const err = (data && data.error) || {};
    throw new ApiError(
      err.message || `HTTP ${res.status}`,
      err.code || `HTTP_${res.status}`,
      res.status,
      err.correlation_id,
      err.details,
    );
  }
  return data as T;
}

function safeJson(text: string) {
  try {
    return JSON.parse(text);
  } catch {
    return { raw: text };
  }
}

export const api = {
  // Auth
  login: (email: string, password: string) =>
    request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  logout: () => request<{ status: string }>("/auth/logout", { method: "POST" }),
  me: () => request<Me>("/auth/me"),

  // Dashboard
  dashboard: () => request<DashboardData>("/dashboard"),

  // Events
  listEvents: (params: Record<string, string | number | undefined> = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
    });
    return request<Page<EventListItem>>(`/events?${qs.toString()}`);
  },
  getEvent: (id: string) => request<EventDetail>(`/events/${id}`),
  getRaw: (id: string) => request<RawEvent>(`/events/${id}/raw`),
  getNormalized: (id: string) => request<any>(`/events/${id}/normalized`),
  getIntegrity: (id: string) => request<IntegrityResult>(`/events/${id}/integrity`),
  getTimeline: (id: string) =>
    request<{ event_id: string; stages: TimelineStage[] }>(`/events/${id}/timeline`),
  getReplayHistory: (id: string) =>
    request<{ items: any[] }>(`/events/${id}/replay-history`),
  replay: (id: string, parserId?: string) =>
    request<ReplayResult>(
      `/events/${id}/replay${parserId ? `?parser_id=${parserId}` : ""}`,
      { method: "POST" },
    ),

  // Ingest
  ingestRaw: (raw: string, opts?: { source?: string; filename?: string; contentType?: string }) =>
    request<any>("/ingest", {
      method: "POST",
      body: JSON.stringify({
        raw,
        source: opts?.source ?? "ui",
        source_type: "ui",
        filename: opts?.filename ?? "inline.log",
        content_type: opts?.contentType ?? "text/plain",
      }),
    }),
  ingestFile: (file: File, source = "ui") => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("source", source);
    fd.append("source_type", "upload");
    fd.append("filename", file.name);
    fd.append("content_type", file.type || "text/plain");
    return request<any>("/ingest/raw", { method: "POST", body: fd });
  },
  ingestBatch: (file: File, source = "ui") => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("source", source);
    fd.append("source_type", "batch");
    return request<any>("/ingest/batch", { method: "POST", body: fd });
  },

  // Quarantine
  listQuarantine: (params: Record<string, string | number | undefined> = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
    });
    return request<Page<QuarantineItem>>(`/quarantine?${qs.toString()}`);
  },
  getQuarantine: (id: string) => request<any>(`/quarantine/${id}`),
  getQuarantineAnalysis: (id: string) =>
    request<QuarantineAnalysis>(`/quarantine/${id}/analysis`),
  approveQuarantineMapping: (
    id: string,
    mappings: { original_field: string; canonical_field: string; confidence?: number }[],
  ) =>
    request<{ approved: string[] }>(`/quarantine/${id}/approve-mapping`, {
      method: "POST",
      body: JSON.stringify({ mappings }),
    }),
  replayQuarantine: (id: string, parserId?: string) =>
    request<ReplayResult>(
      `/quarantine/${id}/replay${parserId ? `?parser_id=${parserId}` : ""}`,
      { method: "POST" },
    ),

  // Parsers
  listParsers: () => request<{ items: ParserItem[] }>("/parsers"),
  getParser: (id: string) => request<ParserItem & { loaded: boolean }>(`/parsers/${id}`),
  createParser: (body: {
    parser_id: string;
    name?: string;
    vendor?: string;
    format?: string;
    version?: string;
    enabled?: boolean;
    metadata?: Record<string, any>;
  }) => request<any>("/parsers", { method: "POST", body: JSON.stringify(body) }),
  enableParser: (id: string) =>
    request<{ enabled: boolean }>(`/parsers/${id}/enable`, { method: "POST" }),
  disableParser: (id: string) =>
    request<{ enabled: boolean }>(`/parsers/${id}/disable`, { method: "POST" }),

  // Enrichment
  getEnrichment: (eventId: string) => request<any>(`/enrichment/${eventId}`),
  providersStatus: () =>
    request<{ providers: ProviderStatus[] }>("/enrichment/providers/status"),

  // Threat Intel
  tiLookup: (indicator: string, type?: string) =>
    request<any>(
      `/threat-intel/${encodeURIComponent(indicator)}${type ? `?type=${type}` : ""}`,
    ),
  tiHistory: (indicator: string) =>
    request<{ items: any[] }>(`/threat-intel/history/${encodeURIComponent(indicator)}`),

  // ATT&CK
  attckList: () => request<{ techniques: any[] }>("/attck"),
  attckForEvent: (eventId: string) =>
    request<{ items: any[] }>(`/attck/events/${eventId}`),

  // Audit
  listAudit: (params: Record<string, string | number | undefined> = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
    });
    return request<Page<AuditItem>>(`/audit?${qs.toString()}`);
  },
  verifyAuditChain: () => request<AuditVerifyResult>("/audit/verify"),

  // Alerts / Incidents
  listAlerts: (params: Record<string, string | number | undefined> = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
    });
    return request<Page<AlertItem>>(`/alerts?${qs.toString()}`);
  },
  getAlert: (id: string) => request<AlertItem>(`/alerts/${id}`),
  setAlertStatus: (id: string, status: string) =>
    request<{ status: string }>(`/alerts/${id}/status`, {
      method: "POST",
      body: JSON.stringify({ status }),
    }),

  listIncidents: (params: Record<string, string | number | undefined> = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
    });
    return request<Page<IncidentItem>>(`/incidents?${qs.toString()}`);
  },
  getIncident: (id: string) => request<IncidentItem>(`/incidents/${id}`),
  createIncident: (body: Partial<IncidentItem>) =>
    request<IncidentItem>("/incidents", { method: "POST", body: JSON.stringify(body) }),
  setIncidentStatus: (id: string, status: string) =>
    request<IncidentItem>(`/incidents/${id}/status`, {
      method: "POST",
      body: JSON.stringify({ status }),
    }),
  addIncidentNote: (id: string, text: string) =>
    request<IncidentItem>(`/incidents/${id}/notes`, {
      method: "POST",
      body: JSON.stringify({ text }),
    }),

  // Schema / Mappings / Drift
  cseSchema: () => request<{ fields: any[]; version: string }>("/schema/cse"),
  listMappings: (parserId?: string) =>
    request<{ items: MappingItem[] }>(
      `/mappings${parserId ? `?parser_id=${parserId}` : ""}`,
    ),
  upsertMapping: (body: Partial<MappingItem>) =>
    request<{ id: string }>("/mappings", { method: "POST", body: JSON.stringify(body) }),
  deleteMapping: (id: string) =>
    request<{ deleted: boolean }>(`/mappings/${id}`, { method: "DELETE" }),
  listDrift: (approved?: boolean) =>
    request<{ items: DriftItem[] }>(
      `/drift${approved !== undefined ? `?approved=${approved}` : ""}`,
    ),
  approveDrift: (id: string) =>
    request<{ approved: boolean }>(`/drift/${id}/approve`, { method: "POST" }),

  // Test Lab
  testlabScenarios: () => request<{ scenarios: string[] }>("/testlab/scenarios"),
  testlabGenerate: (scenario: string, count: number) =>
    request<any>("/testlab/generate", {
      method: "POST",
      body: JSON.stringify({ scenario, count }),
    }),

  // Reports
  eventReport: (eventId: string) => request<any>(`/reports/event/${eventId}`),

  // Health
  health: () => request<any>("/health"),
  ready: () => request<any>("/health/ready"),
  metrics: () => request<any>("/metrics"),
};