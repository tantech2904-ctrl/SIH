import { useState } from "react";
import { useAudit } from "@/hooks/useApi";
import { Loading, ErrorBox, EmptyState } from "@/components/Loading";
import { formatTime } from "@/utils/format";

export default function AuditLogs() {
  const [action, setAction] = useState("");
  const [actor, setActor] = useState("");
  const { data, isLoading, error } = useAudit({
    action: action || undefined,
    actor: actor || undefined,
    size: 200, page: 1,
  });

  return (
    <div className="p-4 space-y-3">
      <div>
        <h1 className="text-lg font-semibold tracking-wide">Audit Log</h1>
        <div className="text-2xs text-soc-textDim">
          Hash-chained. Every entry commits to the previous entry's integrity hash.
        </div>
      </div>
      <div className="panel p-3 grid grid-cols-1 md:grid-cols-3 gap-2">
        <div>
          <label className="label">Actor</label>
          <input className="input" value={actor} onChange={(e) => setActor(e.target.value)} />
        </div>
        <div>
          <label className="label">Action</label>
          <input className="input" value={action} onChange={(e) => setAction(e.target.value)} />
        </div>
      </div>
      <div className="panel overflow-hidden">
        {isLoading ? <Loading /> : error ? <ErrorBox error={error} /> :
          !data || data.items.length === 0 ? <EmptyState message="No audit entries" /> : (
            <div className="overflow-x-auto">
              <table className="table">
                <thead>
                  <tr>
                    <th>Time</th><th>Actor</th><th>Action</th><th>Resource</th>
                    <th>Resource ID</th><th>Source IP</th><th>Integrity Hash</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((r) => (
                    <tr key={r.audit_id} className="text-xs">
                      <td className="whitespace-nowrap font-mono">{formatTime(r.timestamp)}</td>
                      <td>{r.actor}</td>
                      <td className="text-soc-accent">{r.action}</td>
                      <td>{r.resource}</td>
                      <td className="font-mono text-soc-textMuted truncate max-w-[160px]">{r.resource_id || "—"}</td>
                      <td className="font-mono">{r.source_ip || "—"}</td>
                      <td className="font-mono text-soc-textDim truncate max-w-[160px]">{r.integrity_hash.slice(0, 16)}…</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
      </div>
    </div>
  );
}