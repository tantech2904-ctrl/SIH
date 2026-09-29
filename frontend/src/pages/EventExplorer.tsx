import { useState, useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { Search, ChevronLeft, ChevronRight, Filter, RotateCcw, Download, Brain, X, Check } from "lucide-react";
import { useEvents } from "@/hooks/useApi";
import { api } from "@/services/api";
import { SeverityBadge } from "@/components/SeverityBadge";
import { Loading, ErrorBox, EmptyState } from "@/components/Loading";
import { formatTime, truncate } from "@/utils/format";
import { riskColor, statusColor } from "@/utils/colors";

export default function EventExplorer() {
  const qc = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();

  const [q, setQ] = useState(searchParams.get("q") || "");
  const [severity, setSeverity] = useState(searchParams.get("severity") || "");
  const [format, setFormat] = useState(searchParams.get("format") || "");
  const [eventType, setEventType] = useState(searchParams.get("event_type") || "");
  const [sourceIp, setSourceIp] = useState(searchParams.get("source_ip") || "");
  const [destIp, setDestIp] = useState(searchParams.get("destination_ip") || "");
  const [sourceType, setSourceType] = useState(searchParams.get("source_type") || "");
  const [minRisk, setMinRisk] = useState(searchParams.get("min_risk") || "");
  const [page, setPage] = useState(Number(searchParams.get("page")) || 1);
  const size = 50;

  // ML Export Modal State
  const [showExportModal, setShowExportModal] = useState(false);
  const [exportFormat, setExportFormat] = useState<"jsonl" | "csv" | "json">("jsonl");
  const [exportLimit, setExportLimit] = useState(1000);
  const [exportOnlyThreats, setExportOnlyThreats] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportSuccess, setExportSuccess] = useState(false);

  const params = useMemo(
    () => ({
      q: q || undefined,
      severity: severity || undefined,
      format: format || undefined,
      event_type: eventType || undefined,
      source_ip: sourceIp || undefined,
      destination_ip: destIp || undefined,
      source_type: sourceType || undefined,
      min_risk: minRisk ? Number(minRisk) : undefined,
      page,
      size,
    }),
    [q, severity, format, eventType, sourceIp, destIp, sourceType, minRisk, page],
  );

  const { data, isLoading, error, refetch } = useEvents(params);

  const resetFilters = () => {
    setQ("");
    setSeverity("");
    setFormat("");
    setEventType("");
    setSourceIp("");
    setDestIp("");
    setSourceType("");
    setMinRisk("");
    setPage(1);

    // Clear search parameters from URL while preserving workspace tab if present
    const tab = searchParams.get("tab");
    setSearchParams(tab ? { tab } : {}, { replace: true });

    // Invalidate react-query cache and refetch fresh unfiltered events
    qc.invalidateQueries({ queryKey: ["events"] });
    setTimeout(() => {
      refetch();
    }, 0);
  };

  return (
    <div className="p-4 sm:p-5 space-y-4 max-w-full overflow-hidden">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-soc-text">
            Event Explorer
          </h1>
          <p className="text-xs text-soc-textDim">
            Filter normalized events across IP, severity, and risk, or export labeled ML training datasets
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowExportModal(true)}
            className="btn btn-primary text-xs !py-1.5 !px-3 rounded-xl font-bold flex items-center gap-1.5 shadow-sm"
            title="Export labeled event datasets for machine learning models"
          >
            <Brain className="w-3.5 h-3.5 text-sky-200" />
            <span>Export ML Dataset</span>
          </button>
          <button
            type="button"
            onClick={resetFilters}
            className="btn text-xs !py-1.5 !px-3 rounded-xl font-medium text-soc-textMuted hover:text-soc-text"
            title="Reset Filters"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset</span>
          </button>
        </div>
      </div>

      {/* Responsive Filter Grid */}
      <div className="panel p-3.5 rounded-2xl shadow-sm space-y-2.5">
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 xl:grid-cols-8 gap-2.5">
          <div className="sm:col-span-2">
            <label className="label">Search Query</label>
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-soc-textDim" />
              <input
                className="input pl-8 rounded-xl text-xs"
                placeholder="message / ip / user…"
                value={q}
                onChange={(e) => {
                  setQ(e.target.value);
                  setPage(1);
                }}
              />
            </div>
          </div>

          <div>
            <label className="label">Severity</label>
            <select
              className="input rounded-xl text-xs"
              value={severity}
              onChange={(e) => {
                setSeverity(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All</option>
              {["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"].map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="label">Format</label>
            <select
              className="input rounded-xl text-xs"
              value={format}
              onChange={(e) => {
                setFormat(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All</option>
              {["JSON", "JSONL", "XML", "CSV", "RFC5424", "CEF", "LEEF"].map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="label">Event Type</label>
            <input
              className="input rounded-xl text-xs"
              value={eventType}
              onChange={(e) => {
                setEventType(e.target.value);
                setPage(1);
              }}
              placeholder="auth / network…"
            />
          </div>

          <div>
            <label className="label">Source IP</label>
            <input
              className="input font-mono rounded-xl text-xs"
              value={sourceIp}
              onChange={(e) => {
                setSourceIp(e.target.value);
                setPage(1);
              }}
              placeholder="192.168.1.1"
            />
          </div>

          <div>
            <label className="label">Dest IP</label>
            <input
              className="input font-mono rounded-xl text-xs"
              value={destIp}
              onChange={(e) => {
                setDestIp(e.target.value);
                setPage(1);
              }}
              placeholder="10.0.0.1"
            />
          </div>

          <div>
            <label className="label">Min Risk (0-100)</label>
            <input
              className="input rounded-xl text-xs font-mono"
              type="number"
              min={0}
              max={100}
              value={minRisk}
              onChange={(e) => {
                setMinRisk(e.target.value);
                setPage(1);
              }}
              placeholder="70"
            />
          </div>
        </div>
      </div>

      {/* Main Events Table Panel */}
      <div className="panel rounded-2xl shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8"><Loading /></div>
        ) : error ? (
          <div className="p-4"><ErrorBox error={error} /></div>
        ) : !data || data.items.length === 0 ? (
          <div className="p-8">
            <EmptyState
              message="No matching events found"
              hint="Adjust search query or filters, or stream telemetry from connectors or UDP port 5140."
            />
          </div>
        ) : (
          <div className="w-full overflow-x-auto no-scrollbar">
            <table className="table min-w-[1000px]">
              <thead>
                <tr>
                  <th className="w-28">Timestamp</th>
                  <th className="w-20">Severity</th>
                  <th className="w-24">Type</th>
                  <th className="w-28">Source IP</th>
                  <th className="w-28">Dest IP</th>
                  <th className="w-24">User</th>
                  <th className="w-20">Format</th>
                  <th className="w-16">Threat</th>
                  <th>Message / Raw Payload</th>
                  <th className="w-16 text-center">Risk</th>
                  <th className="w-24">Status</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((e) => (
                  <tr
                    key={e.event_id}
                    className="hover:bg-soc-panelAlt/60 transition-colors text-xs cursor-pointer"
                  >
                    <td className="font-mono text-soc-textMuted whitespace-nowrap">
                      <Link
                        className="hover:text-soc-accent font-semibold"
                        to={`/events/${e.event_id}`}
                      >
                        {formatTime(e.timestamp)}
                      </Link>
                    </td>
                    <td>
                      <SeverityBadge severity={e.severity} small />
                    </td>
                    <td className="font-mono text-[11px] text-soc-text truncate max-w-[100px]">
                      {e.event_type || "—"}
                    </td>
                    <td className="font-mono text-[11px] text-soc-accent truncate max-w-[110px]">
                      {e.source_ip || "—"}
                    </td>
                    <td className="font-mono text-[11px] text-soc-textDim truncate max-w-[110px]">
                      {e.destination_ip || "—"}
                    </td>
                    <td className="text-soc-text truncate max-w-[90px]">
                      {e.user_name || "—"}
                    </td>
                    <td className="text-soc-textMuted font-mono text-[11px]">
                      {e.detected_format || "—"}
                    </td>
                    <td>
                      {e.threat_malicious ? (
                        <span className="badge border text-red-500 bg-red-500/10 border-red-500/40 text-[9px] font-bold">
                          Threat
                        </span>
                      ) : (
                        <span className="text-soc-textDim">—</span>
                      )}
                    </td>
                    <td className="text-soc-textMuted max-w-[340px] truncate font-mono text-[11px]">
                      {truncate(e.message || "—", 90)}
                    </td>
                    <td className={`font-mono font-bold text-center ${riskColor(e.risk_score)}`}>
                      {e.risk_score ?? "—"}
                    </td>
                    <td>
                      <span className={`badge border ${statusColor(e.processing_status)} text-[9px]`}>
                        {e.processing_status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Bar */}
        <div className="flex items-center justify-between px-4 py-3 border-t border-soc-border bg-soc-panelAlt/30 text-xs">
          <div className="text-soc-textDim font-medium">
            Total Events: <span className="font-bold text-soc-text">{data?.total ?? 0}</span> · Page {page} of {data?.pages || 1}
          </div>
          <div className="flex items-center gap-1.5">
            <button
              className="btn text-xs !py-1 !px-2.5 rounded-lg"
              disabled={page <= 1}
              onClick={() => setPage(page - 1)}
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <span className="px-2 font-mono text-xs font-semibold">{page}</span>
            <button
              className="btn text-xs !py-1 !px-2.5 rounded-lg"
              disabled={!data || page >= (data.pages || 1)}
              onClick={() => setPage(page + 1)}
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* ML Training Dataset Export Modal */}
      {showExportModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="w-full max-w-md rounded-2xl border border-soc-border bg-soc-panel p-5 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-soc-border">
              <div className="flex items-center gap-2.5">
                <div className="h-9 w-9 rounded-xl bg-soc-accent/15 text-soc-accent flex items-center justify-center font-bold">
                  <Brain className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-soc-text">
                    Export Dataset for ML Training
                  </h3>
                  <div className="text-[11px] text-soc-textDim">
                    Features: CSE tokens, risk score, severity, and binary threat labels
                  </div>
                </div>
              </div>
              <button
                onClick={() => setShowExportModal(false)}
                className="text-soc-textDim hover:text-soc-text p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3.5 text-xs">
              {/* Format Selection */}
              <div className="space-y-1.5">
                <label className="text-[11px] font-bold uppercase tracking-wider text-soc-textDim">
                  Dataset Format
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { id: "jsonl", label: "JSONL", sub: "PyTorch / Pandas" },
                    { id: "csv", label: "CSV", sub: "Scikit-Learn" },
                    { id: "json", label: "JSON", sub: "Standard Array" },
                  ].map((fmt) => (
                    <button
                      key={fmt.id}
                      type="button"
                      onClick={() => setExportFormat(fmt.id as any)}
                      className={`p-2.5 rounded-xl border text-center transition ${
                        exportFormat === fmt.id
                          ? "border-soc-accent bg-soc-accent/10 text-soc-accent font-bold"
                          : "border-soc-border bg-soc-panelAlt/50 text-soc-textMuted hover:text-soc-text"
                      }`}
                    >
                      <div className="text-xs font-mono">{fmt.label}</div>
                      <div className="text-[10px] text-soc-textDim mt-0.5">{fmt.sub}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Sample Volume */}
              <div className="space-y-1.5">
                <label className="text-[11px] font-bold uppercase tracking-wider text-soc-textDim">
                  Record Volume
                </label>
                <div className="grid grid-cols-4 gap-1.5 font-mono text-xs">
                  {[500, 1000, 5000, 10000].map((num) => (
                    <button
                      key={num}
                      type="button"
                      onClick={() => setExportLimit(num)}
                      className={`py-1.5 px-2 rounded-lg border text-center transition ${
                        exportLimit === num
                          ? "border-soc-accent bg-soc-accent/15 text-soc-accent font-bold"
                          : "border-soc-border bg-soc-panelAlt/40 text-soc-textDim hover:text-soc-text"
                      }`}
                    >
                      {num.toLocaleString()}
                    </button>
                  ))}
                </div>
              </div>

              {/* Threat Filter */}
              <div className="p-3 rounded-xl border border-soc-border bg-soc-panelAlt/40 flex items-center justify-between">
                <div>
                  <div className="font-semibold text-soc-text">Filter Threats Only</div>
                  <div className="text-[10px] text-soc-textDim">
                    Only export anomalies with risk score ≥ 50 or High/Critical severity
                  </div>
                </div>
                <input
                  type="checkbox"
                  className="rounded cursor-pointer h-4 w-4"
                  checked={exportOnlyThreats}
                  onChange={(e) => setExportOnlyThreats(e.target.checked)}
                />
              </div>

              {/* Dataset schema info */}
              <div className="p-3 rounded-xl border border-soc-accent/20 bg-soc-accent/5 text-[11px] text-soc-textMuted leading-relaxed">
                <strong>ML Features Included:</strong> <code className="font-mono text-soc-accent">is_threat</code> (target 0/1), <code className="font-mono text-soc-accent">risk_score</code> (0-100), <code className="font-mono text-soc-accent">severity_num</code> (0-4), IP addresses, ports, protocol, action, user, and normalized message.
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-soc-border">
              <button
                type="button"
                onClick={() => setShowExportModal(false)}
                className="btn text-xs font-semibold px-4"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={exporting}
                onClick={async () => {
                  setExporting(true);
                  try {
                    await api.downloadMlDataset({
                      format: exportFormat,
                      limit: exportLimit,
                      min_risk: exportOnlyThreats ? 50 : undefined,
                    });
                    setExportSuccess(true);
                    setTimeout(() => {
                      setExportSuccess(false);
                      setShowExportModal(false);
                    }, 1200);
                  } catch (e) {
                    console.error("ML export failed", e);
                  } finally {
                    setExporting(false);
                  }
                }}
                className="btn btn-primary text-xs font-bold px-4 flex items-center gap-1.5 shadow-md"
              >
                {exporting ? (
                  <span>Exporting {exportLimit.toLocaleString()} events…</span>
                ) : exportSuccess ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Downloaded!</span>
                  </>
                ) : (
                  <>
                    <Download className="w-3.5 h-3.5" />
                    <span>Download {exportLimit.toLocaleString()} Records</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}