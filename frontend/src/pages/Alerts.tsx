import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAlerts } from "@/hooks/useApi";
import { api } from "@/services/api";
import { Loading, ErrorBox, EmptyState } from "@/components/Loading";
import { SeverityBadge } from "@/components/SeverityBadge";
import { formatTime } from "@/utils/format";

export default function Alerts() {
  const [severity, setSeverity] = useState("");
  const [status, setStatus] = useState("");
  const { data, isLoading, error } = useAlerts({
    severity: severity || undefined,
    status: status || undefined,
    size: 100, page: 1,
  });
  const qc = useQueryClient();
  const update = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => api.setAlertStatus(id, status),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
  });

  return (
    <div className="p-4 space-y-3">
      <div>
        <h1 className="text-lg font-semibold tracking-wide">Alerts</h1>
        <div className="text-2xs text-soc-textDim">
          Fired by the deterministic detection engine. Every alert is auditable.
        </div>
      </div>
      <div className="panel p-3 grid grid-cols-1 md:grid-cols-3 gap-2">
        <div>
          <label className="label">Severity</label>
          <select className="input" value={severity} onChange={(e) => setSeverity(e.target.value)}>
            <option value="">All</option>
            {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="label">Status</label>
          <select className="input" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All</option>
            {["OPEN", "ACKNOWLEDGED", "CLOSED", "FALSE_POSITIVE"].map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
      </div>
      <div className="panel overflow-hidden">
        {isLoading ? <Loading /> : error ? <ErrorBox error={error} /> :
          !data || data.items.length === 0 ? <EmptyState message="No alerts" /> : (
            <table className="table">
              <thead>
                <tr>
                  <th>Time</th><th>Rule</th><th>Severity</th><th>Risk</th>
                  <th>Event</th><th>MITRE</th><th>Status</th><th></th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((a) => (
                  <tr key={a.alert_id} className="text-xs">
                    <td className="whitespace-nowrap">{formatTime(a.created_at)}</td>
                    <td>{a.rule_name}</td>
                    <td><SeverityBadge severity={a.severity} small /></td>
                    <td className="font-mono">{a.risk_score}</td>
                    <td className="font-mono">
                      <Link to={`/events/${a.event_id}`} className="text-soc-accent hover:underline">
                        {a.event_id.slice(0, 8)}
                      </Link>
                    </td>
                    <td className="font-mono">{a.mitre.join(", ") || "—"}</td>
                    <td>{a.status}</td>
                    <td>
                      <select
                        className="input !py-0.5 !px-1 !text-2xs"
                        value={a.status}
                        onChange={(e) => update.mutate({ id: a.alert_id, status: e.target.value })}
                      >
                        {["OPEN", "ACKNOWLEDGED", "CLOSED", "FALSE_POSITIVE"].map((s) => (
                          <option key={s} value={s}>{s}</option>
                        ))}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
      </div>
    </div>
  );
}