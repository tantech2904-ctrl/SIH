import { useState } from "react";
import { FileText } from "lucide-react";
import { api } from "@/services/api";
import { ErrorBox } from "@/components/Loading";

export default function Reports() {
  const [eventId, setEventId] = useState("");
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<any>(null);

  async function gen() {
    setLoading(true); setErr(null); setData(null);
    try { setData(await api.eventReport(eventId)); }
    catch (e) { setErr(e); }
    finally { setLoading(false); }
  }

  function download() {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ulpf-report-${eventId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="p-4 space-y-3">
      <div>
        <h1 className="text-lg font-semibold tracking-wide">Reports</h1>
        <div className="text-2xs text-soc-textDim">
          Evidence report generation is audited. Exports are logged.
        </div>
      </div>
      <div className="panel p-3 flex gap-2">
        <input className="input flex-1 font-mono" placeholder="Event UUID"
          value={eventId} onChange={(e) => setEventId(e.target.value)} />
        <button className="btn btn-primary text-xs" disabled={!eventId || loading} onClick={gen}>
          <FileText className="w-3.5 h-3.5" /> Generate
        </button>
        {data ? (
          <button className="btn text-xs" onClick={download}>Download JSON</button>
        ) : null}
      </div>
      {err ? <ErrorBox error={err} /> : null}
      {data ? (
        <pre className="panel p-3 text-2xs font-mono overflow-auto max-h-[560px]">
          {JSON.stringify(data, null, 2)}
        </pre>
      ) : null}
    </div>
  );
}