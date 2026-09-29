import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
import { api } from "@/services/api";
import { Loading, ErrorBox, EmptyState } from "@/components/Loading";
import { useParsers } from "@/hooks/useApi";

export default function Mappings() {
  const { data: parsers } = useParsers();
  const [parserId, setParserId] = useState<string>("");
  const qc = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ["mappings", parserId],
    queryFn: () => api.listMappings(parserId || undefined),
  });
  const [showNew, setShowNew] = useState(false);
  const [nOf, setNOf] = useState("");
  const [nCf, setNCf] = useState("");
  const [nPid, setNPid] = useState("");

  const upsert = useMutation({
    mutationFn: () =>
      api.upsertMapping({
        parser_id: nPid,
        original_field: nOf,
        canonical_field: nCf,
        confidence: 1.0,
      } as any),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mappings"] });
      setShowNew(false); setNOf(""); setNCf(""); setNPid("");
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) => api.deleteMapping(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mappings"] }),
  });

  return (
    <div className="p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-wide">Field Mappings</h1>
          <div className="text-2xs text-soc-textDim">
            Analyst-approved mappings override built-in aliases.
          </div>
        </div>
        <button className="btn text-xs" onClick={() => setShowNew((s) => !s)}>
          <Plus className="w-3.5 h-3.5" /> New mapping
        </button>
      </div>

      {showNew ? (
        <div className="panel p-3 grid grid-cols-1 md:grid-cols-4 gap-2">
          <div>
            <label className="label">Parser</label>
            <select className="input" value={nPid} onChange={(e) => setNPid(e.target.value)}>
              <option value="">Select parser…</option>
              {parsers?.items.map((p) => (
                <option key={p.parser_id} value={p.parser_id}>{p.parser_id}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Original Field</label>
            <input className="input font-mono" value={nOf} onChange={(e) => setNOf(e.target.value)} />
          </div>
          <div>
            <label className="label">Canonical Field</label>
            <input className="input font-mono" value={nCf} onChange={(e) => setNCf(e.target.value)} />
          </div>
          <div className="flex items-end">
            <button
              className="btn btn-primary text-xs"
              disabled={!nPid || !nOf || !nCf || upsert.isPending}
              onClick={() => upsert.mutate()}
            >
              Save
            </button>
          </div>
        </div>
      ) : null}

      <div className="panel p-3">
        <label className="label">Filter by parser</label>
        <select className="input !w-64" value={parserId} onChange={(e) => setParserId(e.target.value)}>
          <option value="">All parsers</option>
          {parsers?.items.map((p) => (
            <option key={p.parser_id} value={p.parser_id}>{p.parser_id}</option>
          ))}
        </select>
      </div>

      <div className="panel overflow-hidden">
        {isLoading ? <Loading /> : error ? <ErrorBox error={error} /> :
          !data || data.items.length === 0 ? (
            <EmptyState message="No custom mappings" hint="Built-in alias table is used by default." />
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Parser</th><th>Original</th><th>Canonical</th><th>Transform</th>
                  <th>Confidence</th><th>Source</th><th></th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((m) => (
                  <tr key={m.id} className="text-xs">
                    <td className="font-mono">{m.parser_id}</td>
                    <td className="font-mono">{m.original_field}</td>
                    <td className="font-mono text-soc-accent">{m.canonical_field}</td>
                    <td>{m.transformation}</td>
                    <td className="font-mono">{m.confidence.toFixed(2)}</td>
                    <td>{m.source}</td>
                    <td>
                      <button className="btn text-2xs !py-0.5 !px-2" onClick={() => remove.mutate(m.id)}>
                        <Trash2 className="w-3 h-3" />
                      </button>
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