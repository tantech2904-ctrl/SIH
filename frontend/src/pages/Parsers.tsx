import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Power, PowerOff } from "lucide-react";
import { useParsers } from "@/hooks/useApi";
import { api } from "@/services/api";
import { Loading, ErrorBox, EmptyState } from "@/components/Loading";

export default function Parsers() {
  const { data, isLoading, error } = useParsers();
  const qc = useQueryClient();
  const enable = useMutation({
    mutationFn: (id: string) => api.enableParser(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["parsers"] }),
  });
  const disable = useMutation({
    mutationFn: (id: string) => api.disableParser(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["parsers"] }),
  });

  return (
    <div className="p-4 space-y-3">
      <div>
        <h1 className="text-lg font-semibold tracking-wide">Parser Management</h1>
        <div className="text-2xs text-soc-textDim">
          Adding a new parser does not require changes to the core pipeline.
        </div>
      </div>
      <div className="panel overflow-hidden">
        {isLoading ? <Loading /> : error ? <ErrorBox error={error} /> :
          !data || data.items.length === 0 ? <EmptyState message="No parsers registered" /> : (
            <table className="table">
              <thead>
                <tr><th>Parser</th><th>Vendor</th><th>Format</th><th>Version</th><th>Success</th><th>Failure</th><th>Enabled</th><th></th></tr>
              </thead>
              <tbody>
                {data.items.map((p) => (
                  <tr key={p.parser_id} className="text-xs">
                    <td className="font-mono">{p.parser_id}</td>
                    <td>{p.vendor}</td>
                    <td>{p.format}</td>
                    <td className="font-mono">{p.version}</td>
                    <td className="text-emerald-400 font-mono">{p.success_count}</td>
                    <td className="text-red-400 font-mono">{p.failure_count}</td>
                    <td>{p.enabled ? "yes" : "no"}</td>
                    <td>
                      {p.enabled ? (
                        <button className="btn text-2xs !py-0.5 !px-2"
                          onClick={() => disable.mutate(p.parser_id)}>
                          <PowerOff className="w-3 h-3" /> Disable
                        </button>
                      ) : (
                        <button className="btn text-2xs !py-0.5 !px-2"
                          onClick={() => enable.mutate(p.parser_id)}>
                          <Power className="w-3 h-3" /> Enable
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