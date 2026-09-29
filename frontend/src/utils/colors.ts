export function severityColor(sev?: string | null): string {
  switch ((sev || "").toUpperCase()) {
    case "CRITICAL":
      return "text-red-700 dark:text-sev-critical bg-red-100 dark:bg-sev-critical/10 border-red-300 dark:border-sev-critical/40 font-bold";
    case "HIGH":
      return "text-orange-800 dark:text-sev-high bg-orange-100 dark:bg-sev-high/10 border-orange-300 dark:border-sev-high/40 font-bold";
    case "MEDIUM":
      return "text-amber-900 dark:text-sev-medium bg-amber-100 dark:bg-sev-medium/10 border-amber-300 dark:border-sev-medium/40 font-bold";
    case "LOW":
      return "text-emerald-800 dark:text-sev-low bg-emerald-100 dark:bg-sev-low/10 border-emerald-300 dark:border-sev-low/40 font-bold";
    default:
      return "text-slate-800 dark:text-sev-info bg-slate-200/80 dark:bg-sev-info/10 border-slate-300 dark:border-sev-info/40 font-bold";
  }
}

export function severityHex(sev?: string | null): string {
  switch ((sev || "").toUpperCase()) {
    case "CRITICAL":
      return "#dc2626";
    case "HIGH":
      return "#ea580c";
    case "MEDIUM":
      return "#d97706";
    case "LOW":
      return "#16a34a";
    default:
      return "#475569";
  }
}

export function statusColor(status?: string | null): string {
  switch ((status || "").toUpperCase()) {
    case "PROCESSED":
      return "text-emerald-800 dark:text-emerald-400 bg-emerald-100 dark:bg-emerald-500/10 border-emerald-300 dark:border-emerald-500/40 font-bold";
    case "WARNING":
      return "text-amber-900 dark:text-amber-300 bg-amber-100 dark:bg-amber-500/10 border-amber-300 dark:border-amber-500/40 font-bold";
    case "QUARANTINED":
    case "FAILED":
      return "text-red-800 dark:text-red-400 bg-red-100 dark:bg-red-500/10 border-red-300 dark:border-red-500/40 font-bold";
    case "RECEIVED":
      return "text-sky-800 dark:text-sky-400 bg-sky-100 dark:bg-sky-500/10 border-sky-300 dark:border-sky-500/40 font-bold";
    default:
      return "text-soc-text font-bold bg-soc-panelAlt border-soc-borderStrong";
  }
}

export function riskColor(score?: number | null): string {
  const s = score ?? 0;
  if (s >= 85) return "text-red-700 dark:text-sev-critical font-bold";
  if (s >= 60) return "text-orange-800 dark:text-sev-high font-bold";
  if (s >= 35) return "text-amber-900 dark:text-sev-medium font-bold";
  if (s >= 15) return "text-emerald-800 dark:text-sev-low font-bold";
  return "text-soc-textMuted font-semibold";
}

export function providerStatusColor(status?: string | null): string {
  switch (status) {
    case "OK":
      return "text-emerald-700 dark:text-emerald-400 font-bold";
    case "NOT_CONFIGURED":
      return "text-slate-600 dark:text-soc-textDim font-medium";
    case "RATE_LIMITED":
      return "text-amber-800 dark:text-amber-400 font-bold";
    case "TIMEOUT":
    case "UNAVAILABLE":
    case "ERROR":
      return "text-red-700 dark:text-red-400 font-bold";
    default:
      return "text-soc-textMuted font-medium";
  }
}