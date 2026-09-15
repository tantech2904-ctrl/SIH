export function severityColor(sev?: string | null): string {
  switch ((sev || "").toUpperCase()) {
    case "CRITICAL":
      return "text-sev-critical bg-sev-critical/10 border-sev-critical/40";
    case "HIGH":
      return "text-sev-high bg-sev-high/10 border-sev-high/40";
    case "MEDIUM":
      return "text-sev-medium bg-sev-medium/10 border-sev-medium/40";
    case "LOW":
      return "text-sev-low bg-sev-low/10 border-sev-low/40";
    default:
      return "text-sev-info bg-sev-info/10 border-sev-info/40";
  }
}

export function severityHex(sev?: string | null): string {
  switch ((sev || "").toUpperCase()) {
    case "CRITICAL":
      return "#dc2626";
    case "HIGH":
      return "#ea580c";
    case "MEDIUM":
      return "#eab308";
    case "LOW":
      return "#22c55e";
    default:
      return "#64748b";
  }
}

export function statusColor(status?: string | null): string {
  switch ((status || "").toUpperCase()) {
    case "PROCESSED":
      return "text-emerald-400 bg-emerald-500/10 border-emerald-500/40";
    case "WARNING":
      return "text-amber-400 bg-amber-500/10 border-amber-500/40";
    case "QUARANTINED":
    case "FAILED":
      return "text-red-400 bg-red-500/10 border-red-500/40";
    case "RECEIVED":
      return "text-sky-400 bg-sky-500/10 border-sky-500/40";
    default:
      return "text-soc-textMuted bg-soc-panelAlt border-soc-border";
  }
}

export function riskColor(score?: number | null): string {
  const s = score ?? 0;
  if (s >= 85) return "text-sev-critical";
  if (s >= 60) return "text-sev-high";
  if (s >= 35) return "text-sev-medium";
  if (s >= 15) return "text-sev-low";
  return "text-soc-textMuted";
}

export function providerStatusColor(status?: string | null): string {
  switch (status) {
    case "OK":
      return "text-emerald-400";
    case "NOT_CONFIGURED":
      return "text-soc-textDim";
    case "RATE_LIMITED":
      return "text-amber-400";
    case "TIMEOUT":
    case "UNAVAILABLE":
    case "ERROR":
      return "text-red-400";
    default:
      return "text-soc-textMuted";
  }
}