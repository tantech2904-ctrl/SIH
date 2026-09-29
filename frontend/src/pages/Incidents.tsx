import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useIncidents } from "@/hooks/useApi";
import { api } from "@/services/api";
import { Loading, ErrorBox, EmptyState } from "@/components/Loading";
import { SeverityBadge } from "@/components/SeverityBadge";
import { formatTime } from "@/utils/format";

export default function Incidents() {
  const [status, setStatus] = useState("");
  const { data, isLoading, error } = useIncidents({
    status: status || undefined, size: 100, page: 1,
  });
  const [showNew, setShowNew] = useState(false);
  const [title, setTitle] = useState("");
  const [sev, setSev] = useState("MEDIUM");
  const [desc, setDesc] = useState("");
  const qc = useQueryClient();
  const create = useMutation({
    mutationFn: () => api.createIncident({ title, severity: sev, description: desc } as any),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["incidents"] });
      setShowNew(false); setTitle(""); setDesc("");
    },
  });
  const setIncStatus = useMutation({
    mutationFn: ({ id, s }: { id: string; s: string }) => api.setIncidentStatus(id, s),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["incidents"] }),
  });

  return (
    <div className="p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-wide">Incidents</h1>
          <div className="text-2xs text-soc-textDim">Investigation tracking with full audit history.</div>
        </div>
        <button className="btn text-xs" onClick={() => setShowNew((s) => !s)}>
          <Plus className="w-3.5 h-3.5" /> New incident
        </button>
      </div>

      {showNew ? (
        <div className="panel p-3 grid grid-cols-1 md:grid-cols-3 gap-2">
          <div>
            <label className="label">Title</label>
            <input className="input" value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <div>
            <label className="label">Severity</label>
            <select className="input" value={sev} onChange={(e) => setSev(e.target.value)}>
              {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <button className="btn btn-primary text-xs" disabled={!title} onClick={() => create.mutate()}>
              Create
            </button>
          </div>
          <div className="md:col-span-3">
            <label className="label">Description</label>
            <textarea className="input h-20" value={desc} onChange={(e) => setDesc(e.target.value)} />
          </div>
        </div>
      ) : null}

      <div className="panel p-3">
        <label className="label">Status</label>
        <select className="input !w-64" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All</option>
          {["OPEN", "INVESTIGATING", "CONTAINED", "RESOLVED", "FALSE_POSITIVE"].map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      <div className="panel overflow-hidden">
        {isLoading ? <Loading /> : error ? <ErrorBox error={error} /> :
          !data || data.items.length === 0 ? <EmptyState message="No incidents" /> : (
            <table className="table">
              <thead>
                <tr><th>ID</th><th>Title</th><th>Severity</th><th>Status</th><th>Source</th><th>Last seen</th><th>Actions</th></tr>
              </thead>
              <tbody>
                {data.items.map((i) => (
                  <tr key={i.incident_id} className="text-xs">
                    <td className="font-mono">{i.incident_id.slice(0, 8)}</td>
                    <td>{i.title}</td>
                    <td><SeverityBadge severity={i.severity} small /></td>
                    <td>{i.status}</td>
                    <td>{i.source}</td>
                    <td>{formatTime(i.last_seen)}</td>
                    <td>
                      <select
                        className="input !py-0.5 !px-1 !text-2xs"
                        value={i.status}
                        onChange={(e) => setIncStatus.mutate({ id: i.incident_id, s: e.target.value })}
                      >
                        {["OPEN", "INVESTIGATING", "CONTAINED", "RESOLVED", "FALSE_POSITIVE"].map((s) => (
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