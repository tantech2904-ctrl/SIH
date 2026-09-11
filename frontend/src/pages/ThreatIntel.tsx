import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Search, ShieldAlert } from "lucide-react";
import { api } from "@/services/api";
import { ErrorBox, Loading } from "@/components/Loading";
import { providerStatusColor } from "@/utils/colors";

export default function ThreatIntel() {
  const [indicator, setIndicator] = useState("");
  const lookup = useMutation({
    mutationFn: () => api.tiLookup(indicator),
  });

  return (
    <div className="p-4 space-y-3">
      <div>
        <h1 className="text-lg font-semibold tracking-wide">Threat Intelligence Lookup</h1>
        <div className="text-2xs text-soc-textDim">
          Only the minimum indicator is sent externally. Providers with no credentials return NOT_CONFIGURED.
        </div>
      </div>

      <div className="panel p-3 flex gap-2">
        <input
          className="input flex-1 font-mono"
          placeholder="IP, domain, URL, or hash…"
          value={indicator}
          onChange={(e) => setIndicator(e.target.value)}
        />
        <button
          className="btn btn-primary text-xs"
          disabled={!indicator || lookup.isPending}
          onClick={() => lookup.mutate()}
        >
          <Search className="w-3.5 h-3.5" /> Lookup
        </button>
      </div>

      {lookup.isPending ? <Loading label="Querying providers…" /> : null}
      {lookup.error ? <ErrorBox error={lookup.error} /> : null}

      {lookup.data ? (
        <div className="panel p-3 space-y-2">
          <div className="text-xs">
            Indicator: <span className="font-mono text-soc-accent">{lookup.data.indicator}</span>
            {" · "}
            Type: <span className="font-mono">{lookup.data.type}</span>
          </div>
          <table className="table">
            <thead>
              <tr><th>Provider</th><th>Status</th><th>Latency</th><th>Result</th></tr>
            </thead>
            <tbody>
              {lookup.data.results.map((r: any, i: number) => (
                <tr key={i} className="text-xs">
                  <td>{r.provider}</td>
                  <td className={providerStatusColor(r.status)}>{r.status}</td>
                  <td className="font-mono">{r.latency_ms}ms</td>
                  <td className="font-mono text-soc-textMuted max-w-[500px] truncate">
                    {JSON.stringify(r.result)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="panel p-6 flex flex-col items-center justify-center text-soc-textDim">
          <ShieldAlert className="w-6 h-6 mb-2" />
          <div className="text-xs">Enter an indicator to query configured providers.</div>
        </div>
      )}
    </div>
  );
}