import { useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, XCircle, ShieldCheck, RefreshCw, FileText, GitBranch, AlertTriangle } from "lucide-react";
import {
  useEvent, useEventRaw, useEventTimeline, useEventEnrichment, useEventReplay,
} from "@/hooks/useApi";
import { api } from "@/services/api";
import { Loading, ErrorBox, EmptyState } from "@/components/Loading";
import { SeverityBadge } from "@/components/SeverityBadge";
import { PipelineViz } from "@/components/PipelineViz";
import { formatTime, formatBytes } from "@/utils/format";
import { riskColor, providerStatusColor } from "@/utils/colors";

const TABS = [
  "Overview", "Raw", "Integrity", "Detection", "Parser", "CSE", "Mappings",
  "Enrichment", "ATT&CK", "Timeline", "Replay", "Report",
];

export default function EventDetail() {
  const { id } = useParams<{ id: string }>();
  const [tab, setTab] = useState("Overview");
  const { data: event, isLoading, error } = useEvent(id);

  if (isLoading) return <Loading />;
  if (error) return <div className="p-6"><ErrorBox error={error} /></div>;
  if (!event) return null;

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-2xs text-soc-textDim uppercase tracking-widest">Event</div>
          <h1 className="text-base font-mono font-semibold">{event.event_id}</h1>
          <div className="mt-1 flex items-center gap-2 text-xs text-soc-textMuted">
            <SeverityBadge severity={event.severity} />
            <span>{event.detected_format || "—"}</span>
            <span>·</span>
            <span>{event.parser_id || "—"} v{event.parser_version || "—"}</span>
            <span>·</span>
            <span>risk {event.risk_score ?? "—"}</span>
            <span>·</span>
            <span>{event.processing_status}</span>
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="flex border-b border-soc-border overflow-x-auto">
          {TABS.map((t) => (
            <button
              key={t}
              className={`px-3 py-2 text-xs border-b-2 whitespace-nowrap ${
                tab === t
                  ? "border-soc-accent text-soc-text"
                  : "border-transparent text-soc-textMuted hover:text-soc-text"
              }`}
              onClick={() => setTab(t)}
            >
              {t}
            </button>
          ))}
        </div>
        <div className="p-3">
          {tab === "Overview" && <OverviewTab event={event} />}
          {tab === "Raw" && id && <RawTab id={id} />}
          {tab === "Integrity" && id && <IntegrityTab id={id} />}
          {tab === "Detection" && id && <DetectionTab id={id} />}
          {tab === "Parser" && <ParserTab event={event} />}
          {tab === "CSE" && <CSETab event={event} />}
          {tab === "Mappings" && <MappingsTab event={event} />}
          {tab === "Enrichment" && id && <EnrichmentTab id={id} />}
          {tab === "ATT&CK" && id && <AttackTab id={id} />}
          {tab === "Timeline" && id && <TimelineTab id={id} />}
          {tab === "Replay" && id && <ReplayTab id={id} />}
          {tab === "Report" && id && <ReportTab id={id} />}
        </div>
      </div>
    </div>
  );
}

function OverviewTab({ event }: { event: any }) {
  return (
    <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-xs">
      <Row label="Event ID" value={event.event_id} mono />
      <Row label="Ingestion ID" value={event.ingestion_id} mono />
      <Row label="Correlation ID" value={event.correlation_id} mono />
      <Row label="Ingested At" value={formatTime(event.ingested_at)} />
      <Row label="Source" value={event.source} />
      <Row label="Source Type" value={event.source_type} />
      <Row label="Filename" value={event.filename} />
      <Row label="Content Type" value={event.content_type} />
      <Row label="Raw Size" value={formatBytes(event.raw_size)} />
      <Row label="SHA-256" value={event.sha256} mono />
      <Row label="Detected Format" value={event.detected_format || "—"} />
      <Row label="Detection Confidence" value={event.detection_confidence?.toFixed(3) ?? "—"} />
      <Row label="Parser" value={event.parser_id || "—"} />
      <Row label="Parser Version" value={event.parser_version || "—"} />
      <Row label="Processing Status" value={event.processing_status} />
      <Row label="Severity" value={event.severity || "—"} />
      <Row label="Risk Score" value={String(event.risk_score ?? "—")} />
      <Row
        label="Threat Context"
        value={
          event.canonical?.threat_context?.malicious
            ? "Malicious indicators detected"
            : event.canonical?.threat_context && Object.keys(event.canonical.threat_context).length
              ? "Context present"
              : "—"
        }
      />
      {event.error_message ? <Row label="Error" value={event.error_message} /> : null}
    </div>
  );
}

function Row({ label, value, mono }: { label: string; value: any; mono?: boolean }) {
  return (
    <>
      <div className="text-soc-textDim">{label}</div>
      <div className={`${mono ? "font-mono" : ""} break-all`}>{String(value ?? "—")}</div>
    </>
  );
}

function RawTab({ id }: { id: string }) {
  const { data, isLoading, error } = useEventRaw(id);
  if (isLoading) return <Loading />;
  if (error) return <ErrorBox error={error} />;
  if (!data) return null;
  return (
    <div>
      <div className="text-2xs text-soc-textDim mb-2">
        Content-Type: {data.content_type} · Size: {formatBytes(data.raw_size)} · SHA-256: <span className="font-mono">{data.sha256}</span>
      </div>
      <pre className="text-2xs font-mono bg-soc-bg p-2 rounded overflow-auto max-h-[420px] whitespace-pre-wrap">
        {data.content}
      </pre>
    </div>
  );
}

function IntegrityTab({ id }: { id: string }) {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["integrity", id],
    queryFn: () => api.getIntegrity(id),
  });
  if (isLoading) return <Loading />;
  if (error) return <ErrorBox error={error} />;
  if (!data) return null;
  const ok = data.integrity_status === "VERIFIED";
  return (
    <div className="space-y-2 text-xs">
      <div className={`flex items-center gap-2 ${ok ? "text-emerald-400" : "text-red-400"}`}>
        {ok ? <CheckCircle2 className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
        <span className="font-semibold">{data.integrity_status}</span>
        <button className="btn text-2xs !py-0.5 !px-2" onClick={() => refetch()}>
          <RefreshCw className="w-3 h-3" /> Re-verify
        </button>
      </div>
      <div className="grid grid-cols-[160px_1fr] gap-x-4 gap-y-1">
        <div className="text-soc-textDim">Original hash</div>
        <div className="font-mono break-all">{data.original_hash}</div>
        <div className="text-soc-textDim">Recalculated</div>
        <div className="font-mono break-all">{data.recalculated_hash || "—"}</div>
        <div className="text-soc-textDim">Verified at</div>
        <div>{formatTime(data.verification_timestamp)}</div>
      </div>
      <div className="text-2xs text-soc-textDim">
        SHA-256 is an integrity mechanism. It is not encryption.
      </div>
    </div>
  );
}

function DetectionTab({ id }: { id: string }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["alerts-for-event", id],
    queryFn: async () => {
      const res = await api.listAlerts({ size: 100, page: 1 });
      return res.items.filter((a) => a.event_id === id);
    },
  });
  if (isLoading) return <Loading />;
  if (error) return <ErrorBox error={error} />;
  if (!data || data.length === 0) {
    return <EmptyState message="No detection alerts fired for this event" />;
  }
  return (
    <div className="space-y-2">
      {data.map((a) => (
        <div key={a.alert_id} className="panel p-2 text-xs">
          <div className="flex items-center justify-between">
            <div className="font-semibold">{a.rule_name}</div>
            <SeverityBadge severity={a.severity} small />
          </div>
          <div className="text-soc-textMuted mt-1">{a.description}</div>
          <div className="text-2xs text-soc-textDim mt-1 font-mono">
            rule={a.rule_id} risk={a.risk_score} mitre={a.mitre.join(",") || "—"}
          </div>
        </div>
      ))}
    </div>
  );
}

function ParserTab({ event }: { event: any }) {
  return (
    <div className="text-xs space-y-2">
      <div className="grid grid-cols-[160px_1fr] gap-x-4 gap-y-1">
        <div className="text-soc-textDim">Parser ID</div>
        <div className="font-mono">{event.parser_id || "—"}</div>
        <div className="text-soc-textDim">Parser Version</div>
        <div>{event.parser_version || "—"}</div>
        <div className="text-soc-textDim">Detected Format</div>
        <div>{event.detected_format || "—"}</div>
        <div className="text-soc-textDim">Detection Confidence</div>
        <div>{event.detection_confidence?.toFixed(4) ?? "—"}</div>
      </div>
    </div>
  );
}

function CSETab({ event }: { event: any }) {
  if (!event.canonical) return <EmptyState message="No canonical event (quarantined or failed)" />;
  return (
    <pre className="text-2xs font-mono bg-soc-bg p-2 rounded overflow-auto max-h-[480px]">
      {JSON.stringify(event.canonical, null, 2)}
    </pre>
  );
}

function MappingsTab({ event }: { event: any }) {
  const provenance = event.canonical?.mapping_provenance || [];
  if (provenance.length === 0) return <EmptyState message="No mapping provenance recorded" />;
  return (
    <div className="overflow-x-auto">
      <table className="table">
        <thead>
          <tr>
            <th>Original Field</th>
            <th>Value</th>
            <th></th>
            <th>Canonical</th>
            <th>Transformation</th>
            <th>Confidence</th>
            <th>Source</th>
          </tr>
        </thead>
        <tbody>
          {provenance.map((p: any, i: number) => (
            <tr key={i} className="text-xs">
              <td className="font-mono">{p.original_field}</td>
              <td className="font-mono text-soc-textMuted max-w-[200px] truncate">{p.original_value}</td>
              <td className="text-soc-textDim"><GitBranch className="w-3 h-3" /></td>
              <td className="font-mono text-soc-accent">{p.canonical_field}</td>
              <td>{p.transformation}</td>
              <td className="font-mono">{p.confidence?.toFixed(2)}</td>
              <td>{p.source}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function EnrichmentTab({ id }: { id: string }) {
  const { data, isLoading, error } = useEventEnrichment(id);
  if (isLoading) return <Loading />;
  if (error) return <ErrorBox error={error} />;
  if (!data) return <EmptyState message="No enrichment data" />;
  const providers = data.providers || {};
  const indicators = data.indicators || [];
  return (
    <div className="space-y-3 text-xs">
      <div className="flex flex-wrap gap-2">
        {Object.entries(providers).map(([p, v]: any) => (
          <div key={p} className="panel px-2 py-1 text-2xs flex items-center gap-2">
            <span className="font-semibold">{p}</span>
            <span className={providerStatusColor(v.status)}>{v.status}</span>
            <span className="text-soc-textDim">({v.count})</span>
          </div>
        ))}
      </div>
      {indicators.length === 0 ? <EmptyState message="No indicators extracted" /> : null}
      {indicators.map((ind: any, i: number) => (
        <div key={i} className="panel p-2">
          <div className="font-mono text-xs">
            {ind.type}: <span className="text-soc-accent">{ind.indicator}</span>
          </div>
          <table className="table mt-2">
            <thead>
              <tr><th>Provider</th><th>Status</th><th>Result</th></tr>
            </thead>
            <tbody>
              {ind.results.map((r: any, j: number) => (
                <tr key={j} className="text-2xs">
                  <td>{r.provider}</td>
                  <td className={providerStatusColor(r.status)}>{r.status}{r.cached ? " (cached)" : ""}</td>
                  <td className="font-mono text-soc-textMuted max-w-[400px] truncate">
                    {JSON.stringify(r.result)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}

function AttackTab({ id }: { id: string }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["attck-event", id],
    queryFn: () => api.attckForEvent(id),
  });
  if (isLoading) return <Loading />;
  if (error) return <ErrorBox error={error} />;
  if (!data || data.items.length === 0) return <EmptyState message="No ATT&CK techniques mapped" />;
  return (
    <table className="table">
      <thead>
        <tr><th>Technique</th><th>Name</th><th>Tactic</th><th>Confidence</th><th>Reason</th></tr>
      </thead>
      <tbody>
        {data.items.map((t: any, i: number) => (
          <tr key={i} className="text-xs">
            <td className="font-mono text-soc-accent">{t.technique_id}</td>
            <td>{t.technique_name}</td>
            <td>{t.tactic}</td>
            <td className="font-mono">{t.confidence?.toFixed(2)}</td>
            <td className="text-soc-textMuted">{t.reason}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function TimelineTab({ id }: { id: string }) {
  const { data, isLoading, error } = useEventTimeline(id);
  if (isLoading) return <Loading />;
  if (error) return <ErrorBox error={error} />;
  if (!data) return null;
  return (
    <div className="space-y-3">
      <PipelineViz stages={data.stages} />
      <table className="table mt-3">
        <thead>
          <tr><th>Stage</th><th>Status</th><th>Started</th><th>Duration</th><th>Component</th><th>Error</th></tr>
        </thead>
        <tbody>
          {data.stages.map((s, i) => (
            <tr key={i} className="text-xs">
              <td className="font-mono">{s.stage}</td>
              <td className={s.status === "OK" ? "text-emerald-400" : "text-red-400"}>{s.status}</td>
              <td>{formatTime(s.started_at)}</td>
              <td className="font-mono">{s.duration_ms}ms</td>
              <td>{s.component}</td>
              <td className="text-red-400">{s.error || ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ReplayTab({ id }: { id: string }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["replay-history", id],
    queryFn: () => api.getReplayHistory(id),
  });
  const replay = useEventReplay(id);
  if (isLoading) return <Loading />;
  if (error) return <ErrorBox error={error} />;
  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <button
          className="btn btn-primary text-xs"
          onClick={() => replay.mutate(undefined)}
          disabled={replay.isPending}
        >
          <RefreshCw className={`w-3.5 h-3.5 ${replay.isPending ? "animate-spin" : ""}`} />
          Replay event
        </button>
        {replay.error ? <span className="text-xs text-red-400">{String(replay.error)}</span> : null}
      </div>
      {(!data || data.items.length === 0) ? (
        <EmptyState message="No replay history" />
      ) : (
        <table className="table">
          <thead>
            <tr><th>Replay ID</th><th>Previous</th><th>New</th><th>Operator</th><th>Result</th><th>At</th></tr>
          </thead>
          <tbody>
            {data.items.map((r: any) => (
              <tr key={r.replay_id} className="text-xs">
                <td className="font-mono">{r.replay_id.slice(0, 8)}</td>
                <td>{r.previous_status}</td>
                <td>{r.new_status}</td>
                <td>{r.operator}</td>
                <td>{r.result}</td>
                <td>{formatTime(r.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function ReportTab({ id }: { id: string }) {
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<any>(null);
  async function generate() {
    setLoading(true); setErr(null);
    try {
      const r = await api.eventReport(id);
      setReport(r);
    } catch (e) { setErr(e); }
    finally { setLoading(false); }
  }
  async function downloadJson() {
    if (!report) return;
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ulpf-report-${id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <button className="btn btn-primary text-xs" onClick={generate} disabled={loading}>
          <FileText className="w-3.5 h-3.5" /> Generate evidence report
        </button>
        {loading ? <Loader2Icon /> : null}
      </div>
      {err ? <ErrorBox error={err} /> : null}
      {report ? (
        <>
          <div className="panel p-2 text-xs">
            <div className="flex items-center justify-between gap-2">
              <div>
                <div className="text-soc-textDim">Report UUID</div>
                <div className="font-mono text-soc-accent">{report.event?.event_id || id}</div>
              </div>
              <button className="btn text-2xs" onClick={downloadJson}>Download JSON</button>
            </div>
            <div className="text-2xs text-soc-textDim mt-1">
              Generated {report.generated_at ? formatTime(report.generated_at) : "—"}
            </div>
          </div>
          <pre className="text-2xs font-mono bg-soc-bg p-2 rounded overflow-auto max-h-[480px]">
            {JSON.stringify(report, null, 2)}
          </pre>
        </>
      ) : null}
    </div>
  );
}

function Loader2Icon() {
  return <span className="text-2xs text-soc-textDim">generating…</span>;
}