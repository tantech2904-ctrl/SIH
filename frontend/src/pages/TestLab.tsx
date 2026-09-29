import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FlaskConical, Zap } from "lucide-react";
import { api } from "@/services/api";
import { useTestLabScenarios } from "@/hooks/useApi";
import { ErrorBox } from "@/components/Loading";

export default function TestLab() {
  const { data: scenarios } = useTestLabScenarios();
  const [scenario, setScenario] = useState("bruteforce");
  const [count, setCount] = useState(1);
  const [result, setResult] = useState<any>(null);
  const qc = useQueryClient();
  const gen = useMutation({
    mutationFn: () => api.testlabGenerate(scenario, count),
    onSuccess: (d) => {
      setResult(d);
      qc.invalidateQueries({ queryKey: ["events"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["quarantine"] });
    },
  });

  return (
    <div className="p-4 space-y-3">
      <div>
        <h1 className="text-lg font-semibold tracking-wide">Security Test Lab</h1>
        <div className="text-2xs text-soc-textDim">
          Generates synthetic log events only. ULPF never launches attacks, scans, or exploits.
        </div>
      </div>

      <div className="panel p-3 grid grid-cols-1 md:grid-cols-4 gap-2">
        <div className="md:col-span-2">
          <label className="label">Scenario</label>
          <select className="input" value={scenario} onChange={(e) => setScenario(e.target.value)}>
            {(scenarios?.scenarios || ["bruteforce", "portscan", "malware_hash", "malformed", "unknown_vendor", "schema_drift"]).map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
            <option value="all">all</option>
          </select>
        </div>
        <div>
          <label className="label">Count</label>
          <input className="input" type="number" min={1} max={500}
            value={count} onChange={(e) => setCount(Number(e.target.value))} />
        </div>
        <div className="flex items-end">
          <button className="btn btn-primary text-xs" disabled={gen.isPending}
            onClick={() => gen.mutate()}>
            <Zap className="w-3.5 h-3.5" /> Generate telemetry
          </button>
        </div>
      </div>

      {gen.error ? <ErrorBox error={gen.error} /> : null}

      {result ? (
        <div className="panel p-3">
          <div className="panel-title mb-2">Generated {result.generated} events</div>
          <pre className="text-2xs font-mono bg-soc-bg p-2 rounded overflow-auto max-h-64">
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      ) : null}
    </div>
  );
}