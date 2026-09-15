import { useState, useEffect } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ChevronRight, RefreshCw, Check, X } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useQuarantine } from "@/hooks/useApi";
import { api } from "@/services/api";
import { Loading, ErrorBox, EmptyState } from "@/components/Loading";
import { formatTime } from "@/utils/format";

export default function Quarantine() {
  const [status, setStatus] = useState("");
  const [reason, setReason] = useState("");
  const params = { status: status || undefined, reason: reason || undefined, size: 100, page: 1 };
  const { data, isLoading, error } = useQuarantine(params);
  const [searchParams, setSearchParams] = useSearchParams();
  const [selected, setSelected] = useState<string | null>(searchParams.get("sel") || null);

  useEffect(() => {
    const sel = searchParams.get("sel");
    setSelected(sel || null);
  }, [searchParams]);

  function handleClose() {
    setSelected(null);
    const next = new URLSearchParams(searchParams);
    next.delete("sel");
    setSearchParams(next, { replace: true });
  }

  return (
    <div className="p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-wide">Quarantine Center</h1>
          <div className="text-2xs text-soc-textDim">
            No event is silently dropped. Every quarantined event has preserved raw evidence.
          </div>
        </div>
      </div>

      <div className="panel p-3 grid grid-cols-1 md:grid-cols-3 gap-2">
        <div>
          <label className="label">Status</label>
          <select className="input" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All</option>
            {["OPEN", "APPROVED", "REPLAYED", "DISCARDED"].map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="label">Reason</label>
          <select className="input" value={reason} onChange={(e) => setReason(e.target.value)}>
            <option value="">All</option>
            {["UNKNOWN_FORMAT", "PARSER_FAILED", "VALIDATION_FAILED", "DETECTION_FAILED", "PARSER_NOT_FOUND"].map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 panel overflow-hidden">
          {isLoading ? <Loading /> : error ? <ErrorBox error={error} /> :
            !data || data.items.length === 0 ? <EmptyState message="Quarantine is empty" /> : (
              <table className="table">
                <thead>
                  <tr><th>Time</th><th>Reason</th><th>Stage</th><th>Event</th><th>Detail</th><th>Status</th><th></th></tr>
                </thead>
                <tbody>
                  {data.items.map((q) => (
                    <tr key={q.id} className="text-xs cursor-pointer" onClick={() => setSelected(q.id)}>
                      <td className="whitespace-nowrap">{formatTime(q.created_at)}</td>
                      <td className="text-amber-400">{q.reason}</td>
                      <td>{q.stage}</td>
                      <td className="font-mono">{q.event_id.slice(0, 8)}</td>
                      <td className="text-soc-textMuted max-w-[280px] truncate">{q.detail}</td>
                      <td>{q.status}</td>
                      <td><ChevronRight className="w-3.5 h-3.5 text-soc-textDim" /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
        </div>

        <div className="panel p-3">
          {!selected ? (
            <EmptyState message="Select a quarantine entry" />
          ) : (
            <QuarantineDetail id={selected} onClose={handleClose} />
          )}
        </div>
      </div>
    </div>
  );
}

function QuarantineDetail({ id, onClose }: { id: string; onClose: () => void }) {
  const qc = useQueryClient();
  const { data: entry } = useQuery({
    queryKey: ["quarantine", id],
    queryFn: () => api.getQuarantine(id),
  });
  const { data: analysis, isLoading: analysisLoading } = useQuery({
    queryKey: ["quarantine-analysis", id],
    queryFn: () => api.getQuarantineAnalysis(id),
  });
  const [approved, setApproved] = useState<Record<string, boolean>>({});

  const approveMutation = useMutation({
    mutationFn: async () => {
      const mappings = (analysis?.candidates || [])
        .filter((c) => approved[c.name] && c.suggested_canonical)
        .map((c) => ({
          original_field: c.name,
          canonical_field: c.suggested_canonical!,
          confidence: c.confidence,
        }));
      return api.approveQuarantineMapping(id, mappings);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["quarantine"] });
      qc.invalidateQueries({ queryKey: ["mappings"] });
    },
  });

  const replayMutation = useMutation({
    mutationFn: () => api.replayQuarantine(id, entry?.parser_id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["quarantine"] });
      qc.invalidateQueries({ queryKey: ["events"] });
    },
  });

  if (!entry) return <Loading />;

  return (
    <div className="space-y-3 text-xs">
      <div className="flex items-center justify-between">
        <div className="panel-title">Detail</div>
        <button className="btn text-2xs !py-0.5 !px-2" onClick={onClose}>
          <X className="w-3 h-3" />
        </button>
      </div>
      <div className="grid grid-cols-[110px_1fr] gap-x-3 gap-y-1">
        <div className="text-soc-textDim">Event</div>
        <Link to={`/events/${entry.event_id}`} className="font-mono text-soc-accent truncate">
          {entry.event_id}
        </Link>
        <div className="text-soc-textDim">Reason</div>
        <div>{entry.reason}</div>
        <div className="text-soc-textDim">Stage</div>
        <div>{entry.stage}</div>
        <div className="text-soc-textDim">Format</div>
        <div>{entry.detected_format || "—"}</div>
        <div className="text-soc-textDim">Confidence</div>
        <div>{entry.detection_confidence?.toFixed(3) ?? "—"}</div>
        <div className="text-soc-textDim">Detail</div>
        <div className="text-soc-textMuted">{entry.detail}</div>
      </div>

      <div className="border-t border-soc-border pt-3">
        <div className="panel-title mb-2">Structural Analysis</div>
        {analysisLoading ? <Loading /> : !analysis ? (
          <EmptyState message="No analysis available" />
        ) : (
          <>
            <div className="text-2xs text-soc-textDim mb-2">
              Delimiter: <span className="font-mono">{analysis.delimiter ?? "none"}</span> ·
              Fields detected: <span className="font-mono">{analysis.field_count}</span>
            </div>
            {analysis.notes.map((n, i) => (
              <div key={i} className="text-2xs text-soc-textDim">· {n}</div>
            ))}
            <table className="table mt-2">
              <thead>
                <tr><th>Field</th><th>Value</th><th>Suggested</th><th>Conf.</th><th>Approve</th></tr>
              </thead>
              <tbody>
                {analysis.candidates.map((c, i) => (
                  <tr key={i} className="text-2xs">
                    <td className="font-mono">{c.name}</td>
                    <td className="font-mono text-soc-textMuted max-w-[140px] truncate">{c.value}</td>
                    <td className="font-mono text-soc-accent">
                      {c.suggested_canonical || "—"}
                    </td>
                    <td className="font-mono">{c.confidence.toFixed(2)}</td>
                    <td>
                      {c.suggested_canonical ? (
                        <input
                          type="checkbox"
                          checked={!!approved[c.name]}
                          onChange={(e) => setApproved({ ...approved, [c.name]: e.target.checked })}
                        />
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="flex gap-2 mt-2">
              <button
                className="btn text-2xs"
                onClick={() => approveMutation.mutate()}
                disabled={approveMutation.isPending || !Object.values(approved).some(Boolean)}
              >
                <Check className="w-3 h-3" /> Approve selected mappings
              </button>
              <button
                className="btn btn-primary text-2xs"
                onClick={() => replayMutation.mutate()}
                disabled={replayMutation.isPending}
              >
                <RefreshCw className={`w-3 h-3 ${replayMutation.isPending ? "animate-spin" : ""}`} />
                Replay
              </button>
            </div>
            {replayMutation.data ? (
              <div className="text-2xs mt-2">
                Result: <span className={replayMutation.data.result === "SUCCESS" ? "text-emerald-400" : "text-red-400"}>
                  {replayMutation.data.result}
                </span> → {replayMutation.data.new_status}
              </div>
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}