import { useHealth } from "@/hooks/useApi";
import { useProviders } from "@/hooks/useApi";
import { Loading, ErrorBox } from "@/components/Loading";
import { CheckCircle2, XCircle } from "lucide-react";
import { providerStatusColor } from "@/utils/colors";

export default function Health() {
  const { data: health, isLoading, error } = useHealth();
  const { data: providers } = useProviders();

  if (isLoading) return <Loading />;
  if (error) return <div className="p-6"><ErrorBox error={error} /></div>;

  return (
    <div className="p-4 space-y-3">
      <div>
        <h1 className="text-lg font-semibold tracking-wide">System Health</h1>
        <div className="text-2xs text-soc-textDim">
          Readiness probe aggregates: database, redis, object store, parsers.
        </div>
      </div>

      <div className="panel p-3">
        <div className="flex items-center gap-2 mb-2">
          {health?.ready ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          ) : (
            <XCircle className="w-4 h-4 text-red-400" />
          )}
          <span className="font-semibold text-sm">
            {health?.ready ? "READY" : "NOT READY"}
          </span>
          <span className="text-2xs text-soc-textDim">{health?.time}</span>
        </div>
        <table className="table">
          <thead><tr><th>Component</th><th>OK</th><th>Details</th></tr></thead>
          <tbody>
            {health ? Object.entries(health.checks || {}).map(([k, v]: any) => (
              <tr key={k} className="text-xs">
                <td className="font-mono">{k}</td>
                <td className={v.ok ? "text-emerald-400" : "text-red-400"}>{String(v.ok)}</td>
                <td className="font-mono text-soc-textMuted">{JSON.stringify(v)}</td>
              </tr>
            )) : null}
          </tbody>
        </table>
      </div>

      <div className="panel p-3">
        <div className="panel-title mb-2">Enrichment Provider Status</div>
        <table className="table">
          <thead><tr><th>Provider</th><th>Configured</th><th>Indicator Types</th></tr></thead>
          <tbody>
            {providers?.providers.map((p) => (
              <tr key={p.provider} className="text-xs">
                <td>{p.provider}</td>
                <td className={p.configured ? "text-emerald-400" : "text-soc-textDim"}>
                  {p.configured ? "yes" : "no (NOT_CONFIGURED)"}
                </td>
                <td className="font-mono text-soc-textMuted">{p.indicator_types.join(", ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}