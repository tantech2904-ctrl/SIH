import { useState } from "react";
import { ShieldCheck, Search } from "lucide-react";
import { api } from "@/services/api";
import { ErrorBox, Loading, EmptyState } from "@/components/Loading";

export default function Evidence() {
  const [eventId, setEventId] = useState("");
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<any>(null);

  async function verify() {
    setLoading(true); setErr(null); setData(null);
    try {
      const r = await api.getIntegrity(eventId);
      setData(r);
    } catch (e) { setErr(e); }
    finally { setLoading(false); }
  }

  return (
    <div className="p-4 space-y-3">
      <div>
        <h1 className="text-lg font-semibold tracking-wide">Chain of Custody / Evidence</h1>
        <div className="text-2xs text-soc-textDim">
          Evidence access is audited. SHA-256 is verified against preserved raw bytes.
          ULPF does not claim legal admissibility — it provides technical integrity.
        </div>
      </div>
      <div className="panel p-3 flex gap-2">
        <input className="input flex-1 font-mono" placeholder="Event UUID"
          value={eventId} onChange={(e) => setEventId(e.target.value)} />
        <button className="btn btn-primary text-xs" disabled={!eventId} onClick={verify}>
          <Search className="w-3.5 h-3.5" /> Verify integrity
        </button>
      </div>
      {loading ? <Loading label="Re-hashing evidence…" /> : null}
      {err ? <ErrorBox error={err} /> : null}
      {data ? (
        <div className="panel p-3 text-xs space-y-2">
          <div className="flex items-center gap-2">
            <ShieldCheck className={`w-4 h-4 ${data.integrity_status === "VERIFIED" ? "text-emerald-400" : "text-red-400"}`} />
            <span className="font-semibold">{data.integrity_status}</span>
          </div>
          <div className="grid grid-cols-[160px_1fr] gap-x-4 gap-y-1">
            <div className="text-soc-textDim">Evidence ID</div>
            <div className="font-mono">{data.evidence_id}</div>
            <div className="text-soc-textDim">Original</div>
            <div className="font-mono break-all">{data.original_hash}</div>
            <div className="text-soc-textDim">Recalculated</div>
            <div className="font-mono break-all">{data.recalculated_hash || "—"}</div>
            <div className="text-soc-textDim">Verified at</div>
            <div>{data.verification_timestamp}</div>
          </div>
        </div>
      ) : null}
    </div>
  );
}