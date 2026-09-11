import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Upload, FileText, Loader2 } from "lucide-react";
import { api } from "@/services/api";
import { ErrorBox } from "@/components/Loading";

export default function Ingest() {
  const qc = useQueryClient();
  const nav = useNavigate();
  const [raw, setRaw] = useState(
    "CEF:0|AcmeCorp|AuthApp|1.0|4625|Failed Logon|7|rt=2026-01-01T00:00:00Z src=203.0.113.5 suser=administrator dhost=dc01 outcome=failure",
  );
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<any>(null);

  const rawMutation = useMutation({
    mutationFn: () => api.ingestRaw(raw, { filename: "inline.cef" }),
    onSuccess: (d) => {
      setResult(d);
      qc.invalidateQueries({ queryKey: ["events"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });

  const fileMutation = useMutation({
    mutationFn: () => api.ingestFile(file!, "ui-upload"),
    onSuccess: (d) => {
      setResult(d);
      qc.invalidateQueries({ queryKey: ["events"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });

  const batchMutation = useMutation({
    mutationFn: () => api.ingestBatch(file!, "ui-batch"),
    onSuccess: (d) => {
      setResult(d);
      qc.invalidateQueries({ queryKey: ["events"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });

  const busy = rawMutation.isPending || fileMutation.isPending || batchMutation.isPending;
  const error = rawMutation.error || fileMutation.error || batchMutation.error;

  return (
    <div className="p-4 space-y-4">
      <div>
        <h1 className="text-lg font-semibold tracking-wide">Log Ingestion</h1>
        <div className="text-2xs text-soc-textDim">
          Raw evidence is preserved and SHA-256 hashed before any processing.
        </div>
      </div>

      {error ? <ErrorBox error={error} /> : null}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="panel p-3">
          <div className="panel-title mb-2">Paste Raw Log</div>
          <textarea
            className="input font-mono text-xs h-56"
            value={raw}
            onChange={(e) => setRaw(e.target.value)}
          />
          <div className="flex justify-end mt-2">
            <button
              className="btn btn-primary text-xs"
              onClick={() => rawMutation.mutate()}
              disabled={busy || !raw}
            >
              {rawMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
              Ingest
            </button>
          </div>
        </div>

        <div className="panel p-3">
          <div className="panel-title mb-2">Upload File</div>
          <div className="border border-dashed border-soc-border rounded p-4 text-center">
            <FileText className="w-6 h-6 mx-auto text-soc-textDim" />
            <input
              type="file"
              className="mt-2 text-xs"
              accept=".log,.txt,.json,.jsonl,.xml,.csv"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
            <div className="text-2xs text-soc-textDim mt-1">
              .log .txt .json .jsonl .xml .csv
            </div>
          </div>
          <div className="flex justify-end gap-2 mt-2">
            <button
              className="btn text-xs"
              onClick={() => fileMutation.mutate()}
              disabled={!file || busy}
            >
              {fileMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
              Single event
            </button>
            <button
              className="btn btn-primary text-xs"
              onClick={() => batchMutation.mutate()}
              disabled={!file || busy}
            >
              {batchMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
              Batch (line-split)
            </button>
          </div>
        </div>
      </div>

      {result ? (
        <div className="panel p-3">
          <div className="panel-title mb-2">Result</div>
          <pre className="text-2xs font-mono text-soc-textMuted bg-soc-bg p-2 rounded overflow-auto max-h-64">
            {JSON.stringify(result, null, 2)}
          </pre>
          {result.event_id ? (
            <button className="btn btn-primary text-xs mt-2"
              onClick={() => nav(`/events/${result.event_id}`)}>
              Open event
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}