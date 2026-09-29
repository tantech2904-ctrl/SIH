import { severityColor, statusColor } from "@/utils/colors";

export function SeverityBadge({ severity, small }: { severity?: string | null; small?: boolean }) {
  const cls = severityColor(severity);
  return (
    <span className={`badge border ${cls} ${small ? "text-2xs px-1 py-0" : ""}`}>
      {severity || "INFO"}
    </span>
  );
}

export function StatusBadge({ status }: { status?: string | null }) {
  const cls = statusColor(status);
  return <span className={`badge border ${cls}`}>{status || "UNKNOWN"}</span>;
}