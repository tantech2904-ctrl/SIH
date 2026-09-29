import { useEffect, useState } from "react";
import { MapPin } from "lucide-react";
import { api } from "@/services/api";
import { ErrorBox, Loading } from "@/components/Loading";
import { providerStatusColor } from "@/utils/colors";

export default function GeoIP() {
  const [ip, setIp] = useState("");
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<any>(null);
  const [providers, setProviders] = useState<any[]>([]);

  useEffect(() => {
    api.providersStatus().then((p) => setProviders(p.providers)).catch(() => {});
  }, []);

  async function lookup() {
    setLoading(true); setErr(null); setData(null);
    try {
      const r = await api.tiLookup(ip, "ip");
      setData(r);
    } catch (e) { setErr(e); }
    finally { setLoading(false); }
  }

  const geo = data?.results?.find((r: any) => r.provider === "GeoIP");
  const geoProvider = providers.find((p) => p.provider === "GeoIP");

  return (
    <div className="p-4 space-y-3">
      <div>
        <h1 className="text-lg font-semibold tracking-wide">GeoIP Intelligence</h1>
        <div className="text-2xs text-soc-textDim">
          Private, loopback, and link-local addresses are explicitly not geolocated.
        </div>
      </div>

      {geoProvider && !geoProvider.configured ? (
        <div className="panel p-3 text-xs text-amber-400">
          GeoIP provider is NOT_CONFIGURED. Set GEOIP_ENABLED=true and MAXMIND_DB_PATH to enable.
        </div>
      ) : null}

      <div className="panel p-3 flex gap-2">
        <input className="input flex-1 font-mono" placeholder="Public IP address"
          value={ip} onChange={(e) => setIp(e.target.value)} />
        <button className="btn btn-primary text-xs" disabled={!ip || loading} onClick={lookup}>
          <MapPin className="w-3.5 h-3.5" /> Lookup
        </button>
      </div>

      {loading ? <Loading /> : null}
      {err ? <ErrorBox error={err} /> : null}

      {geo ? (
        <div className="panel p-3 text-xs">
          <div className="flex items-center justify-between mb-2">
            <div className="panel-title">GeoIP Result</div>
            <span className={providerStatusColor(geo.status)}>{geo.status}</span>
          </div>
          <pre className="font-mono text-soc-textMuted bg-soc-bg p-2 rounded overflow-auto">
            {JSON.stringify(geo.result, null, 2)}
          </pre>
        </div>
      ) : null}
    </div>
  );
}