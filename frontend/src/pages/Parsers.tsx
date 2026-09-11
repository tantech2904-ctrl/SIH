import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Power, PowerOff } from "lucide-react";
import { useState } from "react";
import { useParsers } from "@/hooks/useApi";
import { api } from "@/services/api";
import { Loading, ErrorBox, EmptyState } from "@/components/Loading";

const emptyForm = {
  parser_id: "",
  name: "",
  vendor: "generic",
  format: "custom",
  version: "1.0.0",
  enabled: true,
};

export default function Parsers() {
  const { data, isLoading, error } = useParsers();
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyForm);

  const enable = useMutation({
    mutationFn: (id: string) => api.enableParser(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["parsers"] }),
  });
  const disable = useMutation({
    mutationFn: (id: string) => api.disableParser(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["parsers"] }),
  });
  const create = useMutation({
    mutationFn: (payload: typeof emptyForm) => api.createParser(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["parsers"] });
      setShowForm(false);
      setForm(emptyForm);
    },
  });

  const onFieldChange = (key: keyof typeof emptyForm, value: string | boolean) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <div className="p-4 space-y-3">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold tracking-wide">Parser Management</h1>
          <div className="text-2xs text-soc-textDim">
            Add, enable, or disable parser definitions used by the detection pipeline.
          </div>
        </div>
        <button className="btn btn-primary text-2xs !py-2 !px-3" onClick={() => setShowForm((v) => !v)}>
          <Plus className="w-3 h-3" /> Add Parser
        </button>
      </div>

      {showForm && (
        <div className="panel p-3">
          <div className="text-xs font-medium text-soc-text mb-3">Create parser definition</div>
          <form
            className="grid gap-3 md:grid-cols-2"
            onSubmit={(e) => {
              e.preventDefault();
              create.mutate(form);
            }}
          >
            <label className="space-y-1 text-2xs text-soc-textDim">
              Parser ID
              <input
                className="input"
                value={form.parser_id}
                onChange={(e) => onFieldChange("parser_id", e.target.value)}
                placeholder="custom_json"
                required
              />
            </label>
            <label className="space-y-1 text-2xs text-soc-textDim">
              Name
              <input
                className="input"
                value={form.name}
                onChange={(e) => onFieldChange("name", e.target.value)}
                placeholder="Custom JSON Parser"
              />
            </label>
            <label className="space-y-1 text-2xs text-soc-textDim">
              Vendor
              <input
                className="input"
                value={form.vendor}
                onChange={(e) => onFieldChange("vendor", e.target.value)}
              />
            </label>
            <label className="space-y-1 text-2xs text-soc-textDim">
              Format
              <input
                className="input"
                value={form.format}
                onChange={(e) => onFieldChange("format", e.target.value)}
              />
            </label>
            <label className="space-y-1 text-2xs text-soc-textDim">
              Version
              <input
                className="input"
                value={form.version}
                onChange={(e) => onFieldChange("version", e.target.value)}
              />
            </label>
            <label className="space-y-1 text-2xs text-soc-textDim flex items-center gap-2 pt-5">
              <input
                type="checkbox"
                checked={form.enabled}
                onChange={(e) => onFieldChange("enabled", e.target.checked)}
              />
              Enabled
            </label>
            <div className="md:col-span-2 flex justify-end gap-2">
              <button type="button" className="btn text-2xs" onClick={() => setShowForm(false)}>
                Cancel
              </button>
              <button type="submit" className="btn btn-primary text-2xs" disabled={create.isPending}>
                {create.isPending ? "Saving..." : "Save Parser"}
              </button>
            </div>
          </form>
        </div>
      )}

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