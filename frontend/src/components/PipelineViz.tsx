import { CheckCircle2, XCircle, Circle, Clock } from "lucide-react";
import type { TimelineStage } from "@/types";

const ORDER = [
  "INGESTED", "PRESERVED", "HASHED", "DETECTED", "PARSED",
  "NORMALIZED", "ANALYZED", "VALIDATED", "ROUTED",
];

const LABELS: Record<string, string> = {
  INGESTED: "Ingest",
  PRESERVED: "Preserve",
  HASHED: "SHA-256",
  DETECTED: "Detect",
  PARSED: "Parse",
  NORMALIZED: "Normalize",
  ANALYZED: "Analyze",
  VALIDATED: "Validate",
  ROUTED: "Route",
};

export function PipelineViz({ stages }: { stages: TimelineStage[] }) {
  const byStage = new Map<string, TimelineStage>();
  stages.forEach((s) => byStage.set(s.stage, s));

  return (
    <div className="flex flex-wrap gap-1.5 items-center">
      {ORDER.map((name, idx) => {
        const s = byStage.get(name);
        const Icon = !s ? Circle : s.status === "OK" ? CheckCircle2 : s.status === "WARNING" ? Clock : XCircle;
        const color = !s
          ? "text-soc-textDim"
          : s.status === "OK"
          ? "text-emerald-400"
          : s.status === "WARNING"
          ? "text-amber-400"
          : "text-red-400";
        return (
          <div key={name} className="flex items-center gap-1">
            <div className="flex items-center gap-1.5 px-2 py-1 rounded border border-soc-border bg-soc-panelAlt text-2xs">
              <Icon className={`w-3 h-3 ${color}`} />
              <span className="text-soc-text">{LABELS[name] || name}</span>
              {s?.duration_ms ? (
                <span className="text-soc-textDim font-mono">{s.duration_ms}ms</span>
              ) : null}
            </div>
            {idx < ORDER.length - 1 ? (
              <span className="text-soc-textDim text-2xs">→</span>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}