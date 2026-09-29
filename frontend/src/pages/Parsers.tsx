import React, { useState } from "react";
import { useMutation, useQueryClient, useQuery } from "@tanstack/react-query";
import {
  Plus,
  Power,
  PowerOff,
  GitBranch,
  Trash2,
  Check,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Puzzle,
} from "lucide-react";
import { useParsers } from "@/hooks/useApi";
import { api } from "@/services/api";
import { Loading, ErrorBox, EmptyState } from "@/components/Loading";

interface MappingRow {
  original_field: string;
  canonical_field: string;
  transformation: string;
}

const emptyForm = {
  parser_id: "",
  name: "",
  vendor: "generic",
  format: "json",
  version: "1.0.0",
  enabled: true,
};

const COMMON_CANONICAL_FIELDS = [
  "network.source.ip",
  "network.destination.ip",
  "network.source.port",
  "network.destination.port",
  "network.protocol",
  "actor.user.name",
  "actor.user.id",
  "event.category",
  "event.action",
  "event.severity",
  "threat.signature",
  "host.hostname",
  "host.ip",
];

export default function Parsers() {
  const { data, isLoading, error } = useParsers();
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [expandedParser, setExpandedParser] = useState<string | null>(null);

  // Plug and play mappings in parser creation
  const [mappings, setMappings] = useState<MappingRow[]>([
    { original_field: "src_ip", canonical_field: "network.source.ip", transformation: "none" },
    { original_field: "dest_ip", canonical_field: "network.destination.ip", transformation: "none" },
    { original_field: "user", canonical_field: "actor.user.name", transformation: "lowercase" },
  ]);

  const addMappingRow = () => {
    setMappings((prev) => [
      ...prev,
      { original_field: "", canonical_field: "network.source.ip", transformation: "none" },
    ]);
  };

  const removeMappingRow = (index: number) => {
    setMappings((prev) => prev.filter((_, i) => i !== index));
  };

  const updateMappingRow = (index: number, field: keyof MappingRow, val: string) => {
    setMappings((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], [field]: val };
      return next;
    });
  };

  const enable = useMutation({
    mutationFn: (id: string) => api.enableParser(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["parsers"] }),
  });

  const disable = useMutation({
    mutationFn: (id: string) => api.disableParser(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["parsers"] }),
  });

  const del = useMutation({
    mutationFn: (id: string) => api.deleteParser(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["parsers"] });
      qc.invalidateQueries({ queryKey: ["mappings"] });
    },
  });

  const create = useMutation({
    mutationFn: async () => {
      // 1. Create parser
      const created = await api.createParser(form);
      // 2. Automatically create all associated field mappings (Plug & Play!)
      for (const m of mappings) {
        if (m.original_field && m.canonical_field) {
          try {
            await api.createMapping({
              parser_id: form.parser_id,
              original_field: m.original_field,
              canonical_field: m.canonical_field,
              transformation: m.transformation,
              confidence: 1.0,
            });
          } catch (e) {
            console.error("Failed to register mapping:", e);
          }
        }
      }
      return created;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["parsers"] });
      qc.invalidateQueries({ queryKey: ["mappings"] });
      setShowForm(false);
      setForm(emptyForm);
    },
  });

  const onFieldChange = (key: keyof typeof emptyForm, value: string | boolean) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <div className="p-4 sm:p-5 space-y-4 max-w-full">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-2xl bg-soc-accent/15 border border-soc-accent/30 text-soc-accent flex items-center justify-center font-bold">
            <Puzzle className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-soc-text">
              Parsers Engine & Plug-and-Play Mappings
            </h1>
            <p className="text-xs text-soc-textDim">
              Extensible log normalizers with direct CSE field mapping integration and real-time telemetry stats
            </p>
          </div>
        </div>

        <button
          className="btn btn-primary text-xs !py-2 !px-4 rounded-xl font-bold shadow-md flex items-center gap-2 self-start sm:self-auto"
          onClick={() => setShowForm((v) => !v)}
        >
          <Plus className="w-4 h-4" />
          <span>{showForm ? "Close Form" : "Add Plug & Play Parser"}</span>
        </button>
      </div>

      {/* Plug & Play Add Parser Form */}
      {showForm && (
        <div className="panel p-5 rounded-2xl shadow-md space-y-4 border border-soc-accent/30 bg-soc-panelAlt/30 animate-in fade-in duration-200">
          <div className="flex items-center gap-2 text-sm font-bold text-soc-text">
            <Sparkles className="w-4 h-4 text-soc-accent" />
            <span>Register New Parser with Integrated Field Mappings</span>
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              create.mutate();
            }}
            className="space-y-4"
          >
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              <label className="space-y-1 text-2xs text-soc-textDim">
                <span>Parser Unique Identifier *</span>
                <input
                  className="input rounded-xl text-xs font-mono"
                  value={form.parser_id}
                  onChange={(e) => onFieldChange("parser_id", e.target.value)}
                  placeholder="e.g. cisco_firewall"
                  required
                />
              </label>

              <label className="space-y-1 text-2xs text-soc-textDim">
                <span>Display Name</span>
                <input
                  className="input rounded-xl text-xs"
                  value={form.name}
                  onChange={(e) => onFieldChange("name", e.target.value)}
                  placeholder="Cisco ASA Firewall Parser"
                />
              </label>

              <label className="space-y-1 text-2xs text-soc-textDim">
                <span>Vendor / Manufacturer</span>
                <input
                  className="input rounded-xl text-xs"
                  value={form.vendor}
                  onChange={(e) => onFieldChange("vendor", e.target.value)}
                  placeholder="cisco"
                />
              </label>

              <label className="space-y-1 text-2xs text-soc-textDim">
                <span>Log Payload Format</span>
                <select
                  className="input rounded-xl text-xs"
                  value={form.format}
                  onChange={(e) => onFieldChange("format", e.target.value)}
                >
                  <option value="json">JSON / Structured</option>
                  <option value="xml">XML / EventLog</option>
                  <option value="syslog">Syslog RFC 5424/3164</option>
                  <option value="cef">CEF (ArcSight)</option>
                  <option value="csv">CSV / Delimited</option>
                  <option value="custom">Custom Regex Pattern</option>
                </select>
              </label>

              <label className="space-y-1 text-2xs text-soc-textDim">
                <span>Version</span>
                <input
                  className="input rounded-xl text-xs font-mono"
                  value={form.version}
                  onChange={(e) => onFieldChange("version", e.target.value)}
                  placeholder="1.0.0"
                />
              </label>

              <label className="flex items-center gap-2 pt-6 text-xs text-soc-text font-semibold">
                <input
                  type="checkbox"
                  className="rounded text-soc-accent"
                  checked={form.enabled}
                  onChange={(e) => onFieldChange("enabled", e.target.checked)}
                />
                <span>Enable immediately</span>
              </label>
            </div>

            {/* Integrated Field Mappings Sub-section (Plug & Play) */}
            <div className="pt-2 border-t border-soc-border space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-soc-text flex items-center gap-2">
                    <GitBranch className="w-3.5 h-3.5 text-soc-accent" />
                    <span>Plug & Play Field Normalization Mappings</span>
                  </h4>
                  <p className="text-[11px] text-soc-textDim">
                    Map incoming log fields directly into the Canonical Security Event (CSE) schema
                  </p>
                </div>
                <button
                  type="button"
                  onClick={addMappingRow}
                  className="btn text-2xs !py-1 !px-2.5 rounded-lg font-bold"
                >
                  <Plus className="w-3 h-3" />
                  <span>Add Mapping</span>
                </button>
              </div>

              <div className="rounded-xl border border-soc-border overflow-hidden">
                <table className="table text-xs">
                  <thead>
                    <tr>
                      <th>Original Log Field</th>
                      <th>Transformation</th>
                      <th>Target Canonical CSE Field</th>
                      <th className="w-12"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {mappings.map((m, idx) => (
                      <tr key={idx}>
                        <td>
                          <input
                            className="input rounded-lg font-mono text-xs !py-1"
                            placeholder="e.g. client_ip"
                            value={m.original_field}
                            onChange={(e) =>
                              updateMappingRow(idx, "original_field", e.target.value)
                            }
                            required
                          />
                        </td>
                        <td>
                          <select
                            className="input rounded-lg text-xs !py-1"
                            value={m.transformation}
                            onChange={(e) =>
                              updateMappingRow(idx, "transformation", e.target.value)
                            }
                          >
                            <option value="none">none (pass-through)</option>
                            <option value="lowercase">lowercase</option>
                            <option value="uppercase">uppercase</option>
                            <option value="to_int">to_integer</option>
                            <option value="to_float">to_float</option>
                            <option value="ip_normalize">normalize_ip</option>
                          </select>
                        </td>
                        <td>
                          <input
                            list="canonical-fields"
                            className="input rounded-lg font-mono text-xs text-soc-accent font-semibold !py-1"
                            value={m.canonical_field}
                            onChange={(e) =>
                              updateMappingRow(idx, "canonical_field", e.target.value)
                            }
                            required
                          />
                        </td>
                        <td className="text-center">
                          <button
                            type="button"
                            onClick={() => removeMappingRow(idx)}
                            className="text-soc-textDim hover:text-red-400 p-1"
                            title="Remove Mapping"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <datalist id="canonical-fields">
                {COMMON_CANONICAL_FIELDS.map((f) => (
                  <option key={f} value={f} />
                ))}
              </datalist>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                className="btn text-xs font-semibold rounded-xl px-4"
                onClick={() => setShowForm(false)}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn btn-primary text-xs font-bold rounded-xl px-5 shadow-md"
                disabled={create.isPending}
              >
                {create.isPending ? "Registering Parser & Mappings..." : "Save & Activate"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Main Parsers Registry Table with Live Dynamic Counters */}
      <div className="panel rounded-2xl shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8"><Loading /></div>
        ) : error ? (
          <div className="p-4"><ErrorBox error={error} /></div>
        ) : !data || data.items.length === 0 ? (
          <div className="p-8 text-center">
            <EmptyState message="No parsers registered in the pipeline" />
          </div>
        ) : (
          <div className="w-full overflow-x-auto no-scrollbar">
            <table className="table text-xs">
              <thead>
                <tr>
                  <th>Parser ID</th>
                  <th>Display Name</th>
                  <th>Vendor</th>
                  <th>Format</th>
                  <th>Version</th>
                  <th className="text-center">Success (Live)</th>
                  <th className="text-center">Failure (Live)</th>
                  <th>Status</th>
                  <th>Mappings</th>
                  <th className="text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((p) => {
                  const isExpanded = expandedParser === p.parser_id;
                  return (
                    <React.Fragment key={p.parser_id}>
                      <tr className="hover:bg-soc-panelAlt/50 transition-colors">
                        <td className="font-mono font-bold text-soc-accent">{p.parser_id}</td>
                        <td className="font-semibold text-soc-text">{p.name || p.parser_id}</td>
                        <td className="text-soc-textMuted">{p.vendor}</td>
                        <td>
                          <span className="px-2 py-0.5 rounded-full font-mono text-[10px] bg-soc-panelAlt border border-soc-border text-soc-text">
                            {p.format}
                          </span>
                        </td>
                        <td className="font-mono text-soc-textDim">{p.version}</td>
                        <td className="text-center font-mono font-bold text-emerald-500">
                          {p.success_count}
                        </td>
                        <td className="text-center font-mono font-bold text-red-400">
                          {p.failure_count}
                        </td>
                        <td>
                          <span
                            className={`badge border text-[10px] font-bold ${
                              p.enabled
                                ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/30"
                                : "bg-red-500/10 text-red-400 border-red-500/30"
                            }`}
                          >
                            {p.enabled ? "Active" : "Disabled"}
                          </span>
                        </td>
                        <td>
                          <button
                            onClick={() =>
                              setExpandedParser(isExpanded ? null : p.parser_id)
                            }
                            className="inline-flex items-center gap-1 text-[11px] font-semibold text-soc-accent hover:underline"
                          >
                            <GitBranch className="w-3 h-3" />
                            <span>{isExpanded ? "Hide Mappings" : "View Mappings"}</span>
                            {isExpanded ? (
                              <ChevronUp className="w-3 h-3" />
                            ) : (
                              <ChevronDown className="w-3 h-3" />
                            )}
                          </button>
                        </td>
                        <td className="text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            {p.enabled ? (
                              <button
                                className="btn text-2xs !py-1 !px-2 rounded-lg text-soc-textDim hover:text-amber-500 hover:border-amber-500/40"
                                onClick={() => disable.mutate(p.parser_id)}
                                title="Disable Parser"
                                disabled={disable.isPending}
                              >
                                <PowerOff className="w-3 h-3" />
                                <span>Disable</span>
                              </button>
                            ) : (
                              <button
                                className="btn btn-primary text-2xs !py-1 !px-2 rounded-lg font-bold"
                                onClick={() => enable.mutate(p.parser_id)}
                                title="Enable Parser"
                                disabled={enable.isPending}
                              >
                                <Power className="w-3 h-3" />
                                <span>Enable</span>
                              </button>
                            )}
                            <button
                              className="btn text-2xs !py-1 !px-2 rounded-lg text-soc-textDim hover:text-red-500 hover:border-red-500/40 hover:bg-red-500/10 transition"
                              onClick={() => {
                                if (window.confirm(`Delete parser "${p.name || p.parser_id}"? This will permanently remove it and its custom field mappings.`)) {
                                  del.mutate(p.parser_id);
                                }
                              }}
                              title="Delete Parser"
                              disabled={del.isPending}
                            >
                              <Trash2 className="w-3 h-3 text-red-500" />
                              <span className="text-red-500 font-semibold">Delete</span>
                            </button>
                          </div>
                        </td>
                      </tr>

                      {/* Inline Expanded Mappings Row */}
                      {isExpanded && (
                        <tr className="bg-soc-panelAlt/30 border-b border-soc-border">
                          <td colSpan={10} className="p-4">
                            <ParserMappingsInline parserId={p.parser_id} />
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

// Inline Sub-component to display and quickly add mappings to an existing parser
function ParserMappingsInline({ parserId }: { parserId: string }) {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["mappings", parserId],
    queryFn: () => api.listMappings(parserId),
  });

  const [newOrig, setNewOrig] = useState("");
  const [newCanon, setNewCanon] = useState("network.source.ip");
  const [adding, setAdding] = useState(false);

  const addMapping = async () => {
    if (!newOrig || !newCanon) return;
    setAdding(true);
    try {
      await api.createMapping({
        parser_id: parserId,
        original_field: newOrig.trim(),
        canonical_field: newCanon.trim(),
        transformation: "none",
        confidence: 1.0,
      });
      qc.invalidateQueries({ queryKey: ["mappings", parserId] });
      setNewOrig("");
    } catch (err) {
      console.error(err);
    } finally {
      setAdding(false);
    }
  };

  const removeMapping = async (id: string, name: string) => {
    if (!window.confirm(`Remove custom mapping for "${name}"?`)) return;
    try {
      await api.deleteMapping(id);
      qc.invalidateQueries({ queryKey: ["mappings", parserId] });
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="space-y-3 rounded-2xl border border-soc-border bg-soc-panel p-4 shadow-sm text-xs">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pb-2 border-b border-soc-border">
        <div className="flex items-center gap-2">
          <GitBranch className="w-4 h-4 text-soc-accent" />
          <span className="font-bold text-soc-text text-sm">
            Active CSE Field Mappings: <span className="font-mono text-soc-accent">{parserId}</span>
          </span>
          {data && (
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-soc-panelAlt border border-soc-border text-soc-textMuted font-bold">
              {data.items.length} mapped
            </span>
          )}
        </div>
        <span className="text-[11px] text-soc-textDim">
          Maps vendor raw log tokens into standardized CSE canonical paths
        </span>
      </div>

      {isLoading ? (
        <div className="py-4"><Loading /></div>
      ) : !data || data.items.length === 0 ? (
        <div className="text-soc-textDim py-3 text-center bg-soc-panelAlt/30 rounded-xl border border-dashed border-soc-border">
          No field mappings defined yet for this parser. Use the form below to map fields.
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5 max-h-64 overflow-y-auto pr-1">
          {data.items.map((m) => {
            const isBuiltin = m.source === "builtin" || m.id.startsWith("builtin:");
            return (
              <div
                key={m.id}
                className="p-2.5 rounded-xl border border-soc-border bg-soc-panelAlt/50 hover:bg-soc-panelAlt/80 transition flex items-center justify-between font-mono text-[11px] group"
              >
                <div className="min-w-0 flex-1 pr-2">
                  <div className="flex items-center gap-1.5 truncate">
                    <span className="text-soc-text font-bold" title={m.original_field}>
                      {m.original_field}
                    </span>
                    <span className="text-soc-textDim">→</span>
                    <span className="text-soc-accent font-semibold truncate" title={m.canonical_field}>
                      {m.canonical_field}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    <span
                      className={`text-[9px] px-1.5 py-0.2 rounded font-sans font-bold border ${
                        isBuiltin
                          ? "bg-sky-500/10 text-sky-500 border-sky-500/30"
                          : "bg-amber-500/10 text-amber-500 border-amber-500/30"
                      }`}
                    >
                      {isBuiltin ? "Shipped" : "Custom"}
                    </span>
                    <span className="text-[9px] text-soc-textDim">
                      {m.transformation}
                    </span>
                  </div>
                </div>

                {!isBuiltin && (
                  <button
                    onClick={() => removeMapping(m.id, m.original_field)}
                    className="p-1 rounded hover:bg-red-500/10 text-soc-textDim hover:text-red-500 transition shrink-0"
                    title="Delete custom mapping"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Quick Mapping Adder Form */}
      <div className="pt-3 border-t border-soc-border">
        <div className="text-[11px] font-bold text-soc-text mb-2">
          + Add or Override Field Mapping for this Parser:
        </div>
        <div className="flex flex-col sm:flex-row items-center gap-2">
          <input
            className="input rounded-xl font-mono text-xs !py-1.5 sm:w-1/3"
            placeholder="Original log field (e.g. src_ip)"
            value={newOrig}
            onChange={(e) => setNewOrig(e.target.value)}
          />
          <input
            className="input rounded-xl font-mono text-xs text-soc-accent font-semibold !py-1.5 sm:w-1/3"
            placeholder="Target CSE field (e.g. source.ip)"
            value={newCanon}
            onChange={(e) => setNewCanon(e.target.value)}
            list="canonical-fields"
          />
          <button
            onClick={addMapping}
            disabled={adding || !newOrig.trim()}
            className="btn btn-primary text-xs !py-1.5 !px-4 rounded-xl font-bold shadow-md whitespace-nowrap self-stretch sm:self-auto"
          >
            {adding ? "Saving..." : "Add Field Mapping"}
          </button>
        </div>
      </div>
    </div>
  );
}