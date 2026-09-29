import { useState, useEffect, useRef } from "react";
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
  const detailRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const sel = searchParams.get("sel");
    setSelected(sel || null);
  }, [searchParams]);

  function handleSelect(id: string) {
    setSelected(id);
    const next = new URLSearchParams(searchParams);
    next.set("sel", id);
    setSearchParams(next, { replace: true });
    setTimeout(() => {
      detailRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }, 40);
  }

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

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 items-start">
        <div className="lg:col-span-2 panel overflow-hidden">
          {isLoading ? <Loading /> : error ? <ErrorBox error={error} /> :
            !data || data.items.length === 0 ? <EmptyState message="Quarantine is empty" /> : (
              <table className="table">
                <thead>
                  <tr><th>Time</th><th>Reason</th><th>Stage</th><th>Event</th><th>Detail</th><th>Status</th><th></th></tr>
                </thead>
                <tbody>
                  {data.items.map((q) => {
                    const isRowSelected = selected === q.id;
                    return (
                      <tr
                        key={q.id}
                        className={`text-xs cursor-pointer transition-colors ${
                          isRowSelected
                            ? "bg-soc-accent/15 border-l-4 border-soc-accent font-semibold"
                            : "hover:bg-soc-panelAlt/50"
                        }`}
                        onClick={() => handleSelect(q.id)}
                      >
                        <td className="whitespace-nowrap font-mono text-[11px]">{formatTime(q.created_at)}</td>
                        <td className="text-amber-500 font-medium">{q.reason}</td>
                        <td className="font-mono text-soc-text">{q.stage}</td>
                        <td className="font-mono text-soc-accent font-semibold">{q.event_id.slice(0, 8)}</td>
                        <td className="text-soc-textMuted max-w-[280px] truncate">{q.detail}</td>
                        <td>
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            q.status === "OPEN"
                              ? "bg-amber-500/10 text-amber-500 border border-amber-500/30"
                              : q.status === "REPLAYED"
                              ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/30"
                              : "bg-soc-panelAlt text-soc-textDim border border-soc-border"
                          }`}>
                            {q.status}
                          </span>
                        </td>
                        <td><ChevronRight className="w-3.5 h-3.5 text-soc-textDim" /></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
        </div>

        <div
          ref={detailRef}
          className="panel p-4 min-w-0 max-w-full shadow-md border border-soc-border sticky top-4 self-start max-h-[calc(100vh-5rem)] overflow-y-auto"
        >
          {!selected ? (
            <EmptyState message="Select a quarantine entry to inspect and map" />
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
    <div className="space-y-4 text-xs min-w-0 max-w-full overflow-hidden">
      <div className="flex items-center justify-between pb-2 border-b border-soc-border">
        <div className="panel-title flex items-center gap-2">
          <span>Quarantine Entry</span>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-500 font-bold border border-amber-500/30">
            {entry.status}
          </span>
        </div>
        <button
          className="btn text-2xs !py-1 !px-2 rounded-lg text-soc-textDim hover:text-soc-text"
          onClick={onClose}
          title="Close details"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="grid grid-cols-[90px_minmax(0,1fr)] gap-x-3 gap-y-2 text-xs">
        <div className="text-soc-textDim font-medium">Event ID</div>
        <Link
          to={`/events/${entry.event_id}`}
          className="font-mono text-soc-accent truncate block hover:underline"
          title={entry.event_id}
        >
          {entry.event_id}
        </Link>

        <div className="text-soc-textDim font-medium">Reason</div>
        <div className="font-semibold text-amber-500 break-words">{entry.reason}</div>

        <div className="text-soc-textDim font-medium">Pipeline Stage</div>
        <div className="font-mono text-soc-text">{entry.stage}</div>

        <div className="text-soc-textDim font-medium">Format</div>
        <div>
          <span className="px-2 py-0.5 rounded-full font-mono text-[10px] bg-soc-panelAlt border border-soc-border text-soc-text">
            {entry.detected_format || "UNKNOWN"}
          </span>
        </div>

        <div className="text-soc-textDim font-medium">Confidence</div>
        <div className="font-mono text-soc-text">
          {entry.detection_confidence !== null && entry.detection_confidence !== undefined
            ? (entry.detection_confidence * 100).toFixed(1) + "%"
            : "—"}
        </div>

        <div className="text-soc-textDim font-medium">Error Details</div>
        <div className="text-soc-textMuted font-mono text-[11px] break-words break-all bg-soc-panelAlt/60 p-2.5 rounded-xl border border-soc-border max-h-28 overflow-y-auto select-text leading-relaxed">
          {entry.detail || "No additional error message provided"}
        </div>
      </div>

      <div className="border-t border-soc-border pt-3 space-y-2">
        <div className="panel-title flex items-center justify-between">
          <span>Structural Analysis</span>
          {analysis && (
            <span className="text-[10px] font-mono text-soc-textDim">
              {analysis.field_count} candidate fields
            </span>
          )}
        </div>

        {analysisLoading ? (
          <div className="py-6"><Loading /></div>
        ) : !analysis ? (
          <EmptyState message="No structural analysis available" />
        ) : (
          <div className="space-y-2.5 min-w-0 max-w-full">
            <div className="text-2xs text-soc-textDim flex flex-wrap gap-2">
              <span>Delimiter: <strong className="font-mono text-soc-text">{analysis.delimiter ?? "none"}</strong></span>
              <span>·</span>
              <span>Fields: <strong className="font-mono text-soc-text">{analysis.field_count}</strong></span>
            </div>

            {analysis.notes && analysis.notes.length > 0 && (
              <div className="space-y-0.5 bg-soc-panelAlt/40 p-2 rounded-lg border border-soc-border">
                {analysis.notes.map((n, i) => (
                  <div key={i} className="text-[11px] text-soc-textDim leading-tight">· {n}</div>
                ))}
              </div>
            )}

            <div className="w-full overflow-x-auto no-scrollbar border border-soc-border rounded-xl">
              <table className="table min-w-full text-2xs">
                <thead>
                  <tr>
                    <th className="px-2.5 py-1.5 whitespace-nowrap">Field</th>
                    <th className="px-2.5 py-1.5 whitespace-nowrap">Value</th>
                    <th className="px-2.5 py-1.5 whitespace-nowrap">Suggested</th>
                    <th className="px-2.5 py-1.5 text-center whitespace-nowrap">Conf.</th>
                    <th className="px-2.5 py-1.5 text-center whitespace-nowrap">Approve</th>
                  </tr>
                </thead>
                <tbody>
                  {analysis.candidates.map((c, i) => (
                    <tr key={i} className="text-2xs hover:bg-soc-panelAlt/40">
                      <td className="font-mono font-bold text-soc-text px-2.5 py-1.5 max-w-[85px] truncate" title={c.name}>
                        {c.name}
                      </td>
                      <td className="font-mono text-soc-textMuted px-2.5 py-1.5 max-w-[110px] truncate" title={c.value}>
                        {c.value}
                      </td>
                      <td className="font-mono text-soc-accent font-semibold px-2.5 py-1.5 max-w-[100px] truncate" title={c.suggested_canonical || "—"}>
                        {c.suggested_canonical || "—"}
                      </td>
                      <td className="font-mono text-center px-2.5 py-1.5">
                        {c.confidence.toFixed(2)}
                      </td>
                      <td className="text-center px-2.5 py-1.5">
                        {c.suggested_canonical ? (
                          <input
                            type="checkbox"
                            className="rounded cursor-pointer"
                            checked={!!approved[c.name]}
                            onChange={(e) => setApproved({ ...approved, [c.name]: e.target.checked })}
                          />
                        ) : (
                          <span className="text-soc-textDim">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex flex-wrap gap-2 pt-1">
              <button
                className="btn btn-primary text-2xs !py-1.5 !px-3 rounded-lg font-bold flex items-center gap-1.5 shadow-sm"
                onClick={() => approveMutation.mutate()}
                disabled={approveMutation.isPending || !Object.values(approved).some(Boolean)}
              >
                <Check className="w-3 h-3" />
                <span>Approve Selected</span>
              </button>
              <button
                className="btn text-2xs !py-1.5 !px-3 rounded-lg font-semibold flex items-center gap-1.5"
                onClick={() => replayMutation.mutate()}
                disabled={replayMutation.isPending}
              >
                <RefreshCw className={`w-3 h-3 ${replayMutation.isPending ? "animate-spin text-soc-accent" : ""}`} />
                <span>Replay Event</span>
              </button>
            </div>

            {replayMutation.data && (
              <div className="text-2xs p-2 rounded-lg bg-soc-panelAlt border border-soc-border mt-2">
                Result: <span className={`font-bold ${replayMutation.data.result === "SUCCESS" ? "text-emerald-500" : "text-red-400"}`}>
                  {replayMutation.data.result}
                </span> → <span className="font-mono text-soc-text">{replayMutation.data.new_status}</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}