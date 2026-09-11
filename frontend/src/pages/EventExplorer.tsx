import { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { Search, ChevronLeft, ChevronRight } from "lucide-react";
import { useEvents } from "@/hooks/useApi";
import { SeverityBadge } from "@/components/SeverityBadge";
import { Loading, ErrorBox, EmptyState } from "@/components/Loading";
import { formatTime, truncate } from "@/utils/format";
import { riskColor, statusColor } from "@/utils/colors";

export default function EventExplorer() {
  const [q, setQ] = useState("");
  const [severity, setSeverity] = useState("");
  const [format, setFormat] = useState("");
  const [eventType, setEventType] = useState("");
  const [sourceIp, setSourceIp] = useState("");
  const [destIp, setDestIp] = useState("");
  const [minRisk, setMinRisk] = useState("");
  const [page, setPage] = useState(1);
  const size = 50;

  const params = useMemo(
    () => ({
      q: q || undefined,
      severity: severity || undefined,
      format: format || undefined,
      event_type: eventType || undefined,
      source_ip: sourceIp || undefined,
      destination_ip: destIp || undefined,
      min_risk: minRisk ? Number(minRisk) : undefined,
      page,
      size,
    }),
    [q, severity, format, eventType, sourceIp, destIp, minRisk, page],
  );

  const { data, isLoading, error } = useEvents(params);

  return (
    <div className="p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-wide">Event Explorer</h1>
          <div className="text-2xs text-soc-textDim">
            Server-side filtering. Backend pagination.
          </div>
        </div>
      </div>

      <div className="panel p-3 grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-2">
        <div className="lg:col-span-2">
          <label className="label">Search</label>
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2 top-2.5 text-soc-textDim" />
            <input
              className="input pl-7"
              placeholder="message / ip / user…"
              value={q}
              onChange={(e) => { setQ(e.target.value); setPage(1); }}
            />
          </div>
        </div>
        <div>
          <label className="label">Severity</label>
          <select className="input" value={severity}
            onChange={(e) => { setSeverity(e.target.value); setPage(1); }}>
            <option value="">All</option>
            {["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"].map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="label">Format</label>
          <select className="input" value={format}
            onChange={(e) => { setFormat(e.target.value); setPage(1); }}>
            <option value="">All</option>
            {["JSON", "JSONL", "XML", "CSV", "RFC5424", "CEF", "LEEF"].map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="label">Event Type</label>
          <input className="input" value={eventType}
            onChange={(e) => { setEventType(e.target.value); setPage(1); }}
            placeholder="authentication…" />
        </div>
        <div>
          <label className="label">Source IP</label>
          <input className="input font-mono" value={sourceIp}
            onChange={(e) => { setSourceIp(e.target.value); setPage(1); }} />
        </div>
        <div>
          <label className="label">Dest IP</label>
          <input className="input font-mono" value={destIp}
            onChange={(e) => { setDestIp(e.target.value); setPage(1); }} />
        </div>
      </div>

      <div className="flex items-center gap-2">
        <label className="text-2xs text-soc-textDim">Min risk</label>
        <input className="input !w-20" type="number" min={0} max={100}
          value={minRisk}
          onChange={(e) => { setMinRisk(e.target.value); setPage(1); }} />
        {error ? <span className="text-xs text-red-400">{String(error)}</span> : null}
      </div>

      <div className="panel overflow-hidden">
        {isLoading ? (
          <Loading />
        ) : error ? (
          <div className="p-3"><ErrorBox error={error} /></div>
        ) : !data || data.items.length === 0 ? (
          <EmptyState message="No matching events" hint="Adjust filters or ingest new logs." />
        ) : (
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Severity</th>
                  <th>Type</th>
                  <th>Src</th>
                  <th>Dst</th>
                  <th>User</th>
                  <th>Vendor</th>
                  <th>Format</th>
                  <th>Message</th>
                  <th>Risk</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((e) => (
                  <tr key={e.event_id} className="text-xs">
                    <td className="font-mono text-soc-textMuted whitespace-nowrap">
                      <Link className="hover:underline" to={`/events/${e.event_id}`}>
                        {formatTime(e.timestamp)}
                      </Link>
                    </td>
                    <td><SeverityBadge severity={e.severity} small /></td>
                    <td>{e.event_type}</td>
                    <td className="font-mono">{e.source_ip || "—"}</td>
                    <td className="font-mono">{e.destination_ip || "—"}</td>
                    <td>{e.user_name || "—"}</td>
                    <td>{e.vendor || "—"}</td>
                    <td className="text-soc-textMuted">{e.detected_format || "—"}</td>
                    <td className="text-soc-textMuted max-w-[320px]">
                      {truncate(e.message, 100)}
                    </td>
                    <td className={`font-mono ${riskColor(e.risk_score)}`}>
                      {e.risk_score ?? "—"}
                    </td>
                    <td>
                      <span className={`badge border ${statusColor(e.processing_status)}`}>
                        {e.processing_status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="flex items-center justify-between px-3 py-2 border-t border-soc-border text-xs">
          <div className="text-soc-textDim">
            Total: {data?.total ?? 0} · Page {page} of {data?.pages || 1}
          </div>
          <div className="flex gap-1">
            <button className="btn text-xs" disabled={page <= 1} onClick={() => setPage(page - 1)}>
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <button className="btn text-xs"
              disabled={!data || page >= (data.pages || 1)}
              onClick={() => setPage(page + 1)}>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}