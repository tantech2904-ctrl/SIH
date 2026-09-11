import { Link } from "react-router-dom";
import {
  Activity, AlertTriangle, Database, FileWarning, ShieldAlert, Zap,
} from "lucide-react";
import { useDashboard } from "@/hooks/useApi";
import { StatCard } from "@/components/StatCard";
import { Loading, ErrorBox, EmptyState } from "@/components/Loading";
import { SeverityPie } from "@/charts/SeverityPie";
import { ThroughputLine } from "@/charts/ThroughputLine";
import { BarList } from "@/charts/BarList";

export default function Dashboard() {
  const { data, isLoading, error } = useDashboard();

  if (isLoading) return <Loading />;
  if (error) return <div className="page-shell"><ErrorBox error={error} /></div>;
  if (!data) return null;

  const hasEvents = data.totals.events > 0;

  return (
    <div className="page-shell space-y-4">
      <div className="page-header">
        <div>
          <div className="text-[10px] font-medium uppercase tracking-[0.24em] text-soc-accent">
            Operations overview
          </div>
          <h1 className="text-xl font-semibold tracking-tight text-soc-text sm:text-2xl">
            SOC Dashboard
          </h1>
        </div>
        <div className="text-xs text-soc-textDim">
          Real backend-derived metrics • Updated continuously
        </div>
      </div>

      {!hasEvents ? (
        <div className="panel p-6">
          <EmptyState
            message="No events ingested"
            hint="Head to Log Ingestion to upload a log, or open the Test Lab to generate synthetic telemetry."
          />
          <div className="mt-4 flex flex-wrap justify-center gap-2">
            <Link to="/ingest" className="btn btn-primary text-xs">Upload Logs</Link>
            <Link to="/testlab" className="btn text-xs">Open Test Lab</Link>
          </div>
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-6">
        <StatCard
          label="Total Events"
          value={data.totals.events.toLocaleString()}
          icon={<Database className="w-3.5 h-3.5" />}
        />
        <StatCard
          label="Canonical Events"
          value={data.totals.canonical_events.toLocaleString()}
          icon={<Activity className="w-3.5 h-3.5" />}
        />
        <StatCard
          label="Events / sec"
          value={data.throughput.events_per_second.toFixed(3)}
          sub={`${data.throughput.events_last_minute} in last minute`}
          icon={<Zap className="w-3.5 h-3.5" />}
          accent="text-soc-accent"
        />
        <StatCard
          label="High Risk"
          value={data.totals.high_risk_events.toLocaleString()}
          sub="risk ≥ 70"
          icon={<ShieldAlert className="w-3.5 h-3.5" />}
          accent="text-sev-high"
        />
        <StatCard
          label="Critical Alerts"
          value={data.totals.critical_alerts.toLocaleString()}
          icon={<AlertTriangle className="w-3.5 h-3.5" />}
          accent="text-sev-critical"
        />
        <StatCard
          label="Quarantined"
          value={data.totals.quarantined.toLocaleString()}
          icon={<FileWarning className="w-3.5 h-3.5" />}
          accent="text-amber-400"
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="panel p-3">
          <div className="panel-title mb-2">Severity Distribution</div>
          <SeverityPie data={data.severity_counts} />
        </div>
        <div className="panel p-3 lg:col-span-2">
          <div className="panel-title mb-2">Hourly Throughput (24h)</div>
          <ThroughputLine data={data.hourly_throughput} />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div className="panel p-3">
          <BarList
            title="Top Source IPs"
            data={data.top_source_ips.map((x) => ({ label: x.ip, value: x.count }))}
            color="#34d399"
          />
        </div>
        <div className="panel p-3">
          <BarList
            title="Top Destination IPs"
            data={data.top_destination_ips.map((x) => ({ label: x.ip, value: x.count }))}
            color="#86efac"
          />
        </div>
        <div className="panel p-3">
          <BarList
            title="Top Vendors"
            data={Object.entries(data.top_vendors).map(([k, v]) => ({ label: k, value: v }))}
            color="#22c55e"
          />
        </div>
        <div className="panel p-3">
          <BarList
            title="Formats"
            data={Object.entries(data.format_counts).map(([k, v]) => ({ label: k, value: v }))}
            color="#facc15"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="panel p-3">
          <BarList
            title="Categories"
            data={Object.entries(data.category_counts).map(([k, v]) => ({ label: k, value: v }))}
          />
        </div>
        <div className="panel p-3">
          <BarList
            title="Processing Status"
            data={Object.entries(data.status_counts).map(([k, v]) => ({ label: k, value: v }))}
            color="#f97316"
          />
        </div>
        <div className="panel p-3">
          <BarList
            title="Alerts Open"
            data={[{ label: "Open alerts", value: data.totals.open_alerts }]}
            color="#f87171"
          />
        </div>
      </div>
    </div>
  );
}