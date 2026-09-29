import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Check } from "lucide-react";
import { useDrift } from "@/hooks/useApi";
import { api } from "@/services/api";
import { Loading, ErrorBox, EmptyState } from "@/components/Loading";

export default function SchemaDrift() {
  const { data, isLoading, error } = useDrift();
  const qc = useQueryClient();
  const approve = useMutation({
    mutationFn: (id: string) => api.approveDrift(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["drift"] });
      qc.invalidateQueries({ queryKey: ["mappings"] });
    },
  });

  return (
    <div className="p-4 space-y-3">
      <div>
        <h1 className="text-lg font-semibold tracking-wide">Schema Drift</h1>
        <div className="text-2xs text-soc-textDim">
          When a known vendor introduces a new field, ULPF proposes a mapping.
        </div>
      </div>
      <div className="panel overflow-hidden">
        {isLoading ? <Loading /> : error ? <ErrorBox error={error} /> :
          !data || data.items.length === 0 ? (
            <EmptyState message="No drift detected" />
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Vendor</th><th>Parser</th><th>Expected</th><th>Observed</th>
                  <th>Suggested Canonical</th><th>Confidence</th><th>Events</th><th>Reason</th><th></th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((d) => (
                  <tr key={d.id} className="text-xs">
                    <td>{d.vendor}</td>
                    <td className="font-mono">{d.parser_id}</td>
                    <td className="font-mono">{d.expected_field}</td>
                    <td className="font-mono text-amber-400">{d.observed_field}</td>
                    <td className="font-mono text-soc-accent">{d.suggested_canonical || "—"}</td>
                    <td className="font-mono">{d.confidence.toFixed(2)}</td>
                    <td className="font-mono">{d.affected_events}</td>
                    <td className="text-soc-textMuted max-w-[280px]">{d.reason}</td>
                    <td>
                      {d.approved ? (
                        <span className="text-emerald-400 text-2xs">approved</span>
                      ) : (
                        <button
                          className="btn text-2xs !py-0.5 !px-2"
                          disabled={!d.suggested_canonical || approve.isPending}
                          onClick={() => approve.mutate(d.id)}
                        >
                          <Check className="w-3 h-3" /> Approve
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
      </div>
    </div>
  );
}