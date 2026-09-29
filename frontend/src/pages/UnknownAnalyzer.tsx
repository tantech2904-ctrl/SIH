import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  FileQuestion,
  Search,
  CheckCircle2,
  RefreshCw,
  X,
  Code2,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  Check,
} from "lucide-react";
import { useQuarantine } from "@/hooks/useApi";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/services/api";
import { Loading, ErrorBox, EmptyState } from "@/components/Loading";
import { formatTime } from "@/utils/format";

export default function UnknownAnalyzer() {
  const { data, isLoading, error } = useQuarantine({
    reason: "UNKNOWN_FORMAT",
    size: 100,
    page: 1,
  });

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const qc = useQueryClient();
  const nav = useNavigate();

  // Load structural analysis when an item is selected
  const { data: analysis, isLoading: analysisLoading } = useQuery({
    queryKey: ["quarantine-analysis", selectedId],
    queryFn: () => (selectedId ? api.getQuarantineAnalysis(selectedId) : null),
    enabled: !!selectedId,
  });

  const [approvedMappings, setApprovedMappings] = useState<Record<string, boolean>>({});
  const [replaySuccess, setReplaySuccess] = useState<string | null>(null);

  const approveMutation = useMutation({
    mutationFn: () => {
      const selectedFields = Object.entries(approvedMappings)
        .filter(([, v]) => v)
        .map(([k]) => ({
          original_field: k,
          canonical_field:
            analysis?.candidates?.find((c: any) => c.name === k)?.suggested_canonical || k,
        }));
      return api.approveQuarantineMapping(selectedId!, selectedFields);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["quarantine"] });
    },
  });

  const replayMutation = useMutation({
    mutationFn: () => api.replayQuarantine(selectedId!),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["quarantine"] });
      qc.invalidateQueries({ queryKey: ["events"] });
      setReplaySuccess(`Replay successful! Event promoted to status: ${res.new_status}`);
    },
  });

  const selectedEvent = data?.items.find((item) => item.id === selectedId);

  return (
    <div className="p-4 sm:p-5 space-y-4 max-w-full">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-2xl bg-amber-500/15 border border-amber-500/30 text-amber-500 flex items-center justify-center font-bold">
            <FileQuestion className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-soc-text">
              Unknown Format Analyzer
            </h1>
            <p className="text-xs text-soc-textDim">
              Heuristic token extraction and schema normalization for previously-unseen logs
            </p>
          </div>
        </div>

        <button
          onClick={() => nav("/platform?tab=testlab")}
          className="btn text-xs font-semibold rounded-xl self-start sm:self-auto"
        >
          <Sparkles className="w-3.5 h-3.5 text-soc-accent" />
          <span>Generate Unknown Log in Test Lab</span>
        </button>
      </div>

      {/* Main Table Panel */}
      <div className="panel rounded-2xl shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8"><Loading /></div>
        ) : error ? (
          <div className="p-4"><ErrorBox error={error} /></div>
        ) : !data || data.items.length === 0 ? (
          <div className="p-8 text-center">
            <EmptyState
              message="No Unknown Format Logs in Quarantine"
              hint="All incoming events matched existing parser signatures. Run the 'unknown_vendor' scenario in the Test Lab to simulate an arbitrary log format."
            />
          </div>
        ) : (
          <div className="w-full overflow-x-auto no-scrollbar">
            <table className="table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Event ID</th>
                  <th>Detection Confidence</th>
                  <th>Quarantine Reason</th>
                  <th>Message / Raw Preview</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((q) => (
                  <tr
                    key={q.id}
                    className={`text-xs hover:bg-soc-panelAlt/60 cursor-pointer transition-colors ${
                      selectedId === q.id ? "bg-soc-accent/10" : ""
                    }`}
                    onClick={() => {
                      setSelectedId(q.id);
                      setReplaySuccess(null);
                    }}
                  >
                    <td className="font-mono text-soc-textMuted whitespace-nowrap">
                      {formatTime(q.created_at)}
                    </td>
                    <td className="font-mono text-soc-accent font-bold">
                      {q.event_id.slice(0, 10)}…
                    </td>
                    <td className="font-mono">
                      <span className="px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-500 font-bold border border-amber-500/20 text-[10px]">
                        {q.detection_confidence?.toFixed(3) ?? "0.000"}
                      </span>
                    </td>
                    <td className="font-mono text-soc-text">{q.reason}</td>
                    <td className="max-w-[320px] truncate text-soc-textMuted font-mono text-[11px]">
                      {q.detail || "Unrecognized log structure"}
                    </td>
                    <td>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedId(q.id);
                          setReplaySuccess(null);
                        }}
                        className="btn btn-primary text-2xs !py-1 !px-3 rounded-lg font-bold shadow-sm"
                      >
                        Analyze
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Interactive Structural Analysis Modal / Drawer */}
      {selectedId && selectedEvent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="w-full max-w-2xl rounded-2xl border border-soc-border bg-soc-panel p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-soc-border">
              <div className="flex items-center gap-2.5">
                <div className="h-8 w-8 rounded-xl bg-soc-accent/15 text-soc-accent flex items-center justify-center">
                  <Code2 className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-soc-text">
                    Structural Log Analysis: {selectedEvent.event_id.slice(0, 12)}…
                  </h3>
                  <div className="text-[11px] text-soc-textDim">
                    Candidate tokens extracted from raw payload
                  </div>
                </div>
              </div>
              <button
                onClick={() => setSelectedId(null)}
                className="text-soc-textDim hover:text-soc-text text-sm font-bold p-1"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Event Summary Details */}
            <div className="grid grid-cols-2 gap-2 text-xs rounded-xl bg-soc-panelAlt p-3 border border-soc-border font-mono">
              <div>
                <span className="text-soc-textDim">Event ID: </span>
                <span className="text-soc-accent select-all">{selectedEvent.event_id}</span>
              </div>
              <div>
                <span className="text-soc-textDim">Stage: </span>
                <span>{selectedEvent.stage}</span>
              </div>
              <div className="col-span-2 truncate">
                <span className="text-soc-textDim">Detail: </span>
                <span className="text-soc-text">{selectedEvent.detail}</span>
              </div>
            </div>

            {/* Analysis Results */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-soc-text">
                  Extracted Candidates & Canonical Mapping
                </span>
                {analysis && (
                  <span className="text-[10px] font-mono text-soc-textDim">
                    Delimiter: <strong className="text-soc-accent">{analysis.delimiter || "whitespace"}</strong> · {analysis.field_count} fields
                  </span>
                )}
              </div>

              {analysisLoading ? (
                <div className="py-6 text-center"><Loading /></div>
              ) : !analysis || !analysis.candidates || analysis.candidates.length === 0 ? (
                <div className="rounded-xl border border-dashed border-soc-border p-4 text-center text-xs text-soc-textDim">
                  No structural delimiter could be inferred. Raw payload is preserved in WORM storage.
                </div>
              ) : (
                <div className="rounded-xl border border-soc-border overflow-hidden">
                  <table className="table text-2xs">
                    <thead>
                      <tr>
                        <th>Extracted Field</th>
                        <th>Sample Value</th>
                        <th>Suggested Canonical CSE Field</th>
                        <th>Conf.</th>
                        <th>Map</th>
                      </tr>
                    </thead>
                    <tbody>
                      {analysis.candidates.map((c: any, i: number) => (
                        <tr key={i} className="hover:bg-soc-panelAlt/50">
                          <td className="font-mono font-bold text-soc-text">{c.name}</td>
                          <td className="font-mono text-soc-textDim max-w-[140px] truncate">
                            {c.value}
                          </td>
                          <td className="font-mono text-soc-accent font-semibold">
                            {c.suggested_canonical || "unmapped"}
                          </td>
                          <td className="font-mono">{c.confidence.toFixed(2)}</td>
                          <td>
                            {c.suggested_canonical ? (
                              <input
                                type="checkbox"
                                className="rounded"
                                checked={!!approvedMappings[c.name]}
                                onChange={(e) =>
                                  setApprovedMappings({
                                    ...approvedMappings,
                                    [c.name]: e.target.checked,
                                  })
                                }
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
              )}

              {replaySuccess && (
                <div className="rounded-xl border border-emerald-500/40 bg-emerald-500/10 p-3 text-xs text-emerald-400 font-semibold flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 shrink-0" />
                  <span>{replaySuccess}</span>
                </div>
              )}
            </div>

            {/* Bottom Actions */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-3 border-t border-soc-border">
              <Link
                to={`/events/${selectedEvent.event_id}`}
                className="text-xs text-soc-accent hover:underline font-bold"
              >
                Inspect Raw Event Evidence →
              </Link>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => approveMutation.mutate()}
                  disabled={approveMutation.isPending || !Object.values(approvedMappings).some(Boolean)}
                  className="btn text-xs font-semibold rounded-xl"
                >
                  <Check className="h-3.5 w-3.5" />
                  <span>Approve Mappings</span>
                </button>

                <button
                  type="button"
                  onClick={() => replayMutation.mutate()}
                  disabled={replayMutation.isPending}
                  className="btn btn-primary text-xs font-bold rounded-xl shadow-md flex items-center gap-1.5"
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${replayMutation.isPending ? "animate-spin" : ""}`} />
                  <span>Replay Log</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}