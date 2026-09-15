import { useAuth } from "@/hooks/useAuth";
import { useProviders } from "@/hooks/useApi";

export default function Settings() {
  const { user } = useAuth();
  const { data: providers } = useProviders();

  return (
    <div className="p-4 space-y-3">
      <div>
        <h1 className="text-lg font-semibold tracking-wide">Settings</h1>
        <div className="text-2xs text-soc-textDim">
          Secrets and provider credentials are configured via environment variables only.
        </div>
      </div>

      <div className="panel p-3 text-xs">
        <div className="panel-title mb-2">Current Session</div>
        {user ? (
          <div className="grid grid-cols-[120px_1fr] gap-x-4 gap-y-1">
            <div className="text-soc-textDim">Email</div><div>{user.email}</div>
            <div className="text-soc-textDim">Roles</div><div>{user.roles.join(", ")}</div>
          </div>
        ) : null}
      </div>

      <div className="panel p-3 text-xs">
        <div className="panel-title mb-2">Provider Status</div>
        <table className="table">
          <thead><tr><th>Provider</th><th>Status</th></tr></thead>
          <tbody>
            {providers?.providers.map((p) => (
              <tr key={p.provider} className="text-xs">
                <td>{p.provider}</td>
                <td>{p.configured ? "CONFIGURED" : "NOT_CONFIGURED"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="panel p-3 text-xs">
        <div className="panel-title mb-2">Environment</div>
        <div className="text-soc-textMuted leading-relaxed">
          Configure the platform via <span className="kbd">.env</span>:
          <ul className="list-disc list-inside mt-2 space-y-0.5">
            <li><span className="font-mono">DATABASE_URL</span> — PostgreSQL connection string</li>
            <li><span className="font-mono">REDIS_URL</span> — Celery broker</li>
            <li><span className="font-mono">MINIO_ENDPOINT</span> — S3-compatible raw evidence store</li>
            <li><span className="font-mono">VIRUSTOTAL_API_KEY</span>, <span className="font-mono">ABUSEIPDB_API_KEY</span>, <span className="font-mono">OTX_API_KEY</span> — optional enrichment</li>
            <li><span className="font-mono">MAXMIND_DB_PATH</span> — optional GeoIP mmdb</li>
          </ul>
        </div>
      </div>
    </div>
  );
}