import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { ScanSearch } from "lucide-react";
import { api } from "@/services/api";
import { ErrorBox } from "@/components/Loading";

export default function FormatDetection() {
  const [raw, setRaw] = useState("");
  const [result, setResult] = useState<any>(null);
  const mut = useMutation({
    mutationFn: () => api.ingestRaw(raw, { filename: "detect.log" }),
    onSuccess: (d) => setResult(d),
  });

  return (
    <div className="p-4 space-y-3">
      <div>
        <h1 className="text-lg font-semibold tracking-wide">Format Detection</h1>
        <div className="text-2xs text-soc-textDim">
          Multi-signal detection with transparent confidence scoring. Not extension-based.
        </div>
      </div>
      <div className="panel p-3">
        <label className="label">Raw input</label>
        <textarea
          className="input font-mono text-xs h-40"
          value={raw}
          onChange={(e) => setRaw(e.target.value)}
          placeholder="Paste a log line to detect its format…"
        />
        <div className="flex justify-end mt-2">
          <button className="btn btn-primary text-xs" disabled={!raw || mut.isPending}
            onClick={() => mut.mutate()}>
            <ScanSearch className="w-3.5 h-3.5" /> Detect & ingest
          </button>
        </div>
      </div>
      {mut.error ? <ErrorBox error={mut.error} /> : null}
      {result ? (
        <div className="panel p-3 text-xs">
          <div className="grid grid-cols-[160px_1fr] gap-x-4 gap-y-1">
            <div className="text-soc-textDim">Detected format</div>
            <div className="font-semibold text-soc-accent">{result.detected_format || "—"}</div>
            <div className="text-soc-textDim">Confidence</div>
            <div className="font-mono">{result.detection_confidence?.toFixed(4)}</div>
            <div className="text-soc-textDim">Parser</div>
            <div className="font-mono">{result.parser_id || "—"}</div>
            <div className="text-soc-textDim">Event ID</div>
            <div className="font-mono">{result.event_id}</div>
          </div>
        </div>
      ) : null}
    </div>
  );
}