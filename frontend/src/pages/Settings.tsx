import { useEffect, useMemo, useState } from "react";
import { Eye, EyeOff, Save, Loader2, Info } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useSettings, useUpdateSettings, useRequestRestart } from "@/hooks/useApi";
import { Loading, ErrorBox } from "@/components/Loading";
import { RestartModal } from "@/components/RestartModal";
import type { SettingsItem } from "@/types";

const MASKED = "••••••••";

export default function Settings() {
  const { user } = useAuth();
  const { data, isLoading, error } = useSettings();
  const update = useUpdateSettings();
  const restart = useRequestRestart();

  // Local edit state: keyed by setting key
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [revealed, setRevealed] = useState<Record<string, boolean>>({});
  const [banner, setBanner] = useState<{ kind: "ok" | "err"; text: string } | null>(null);
  const [restartModal, setRestartModal] = useState<{
    open: boolean;
    keys: string[];
    error: string | null;
  }>({ open: false, keys: [], error: null });

  // Reset draft when data changes
  useEffect(() => {
    if (!data) return;
    const next: Record<string, string> = {};
    for (const g of data.groups) {
      for (const item of g.items) next[item.key] = item.sensitive ? "" : item.value;
    }
    setDraft(next);
  }, [data]);

  const groups = data?.groups ?? [];

  function setValue(key: string, v: string) {
    setDraft((d) => ({ ...d, [key]: v }));
  }

  function toggleReveal(key: string) {
    setRevealed((r) => ({ ...r, [key]: !r[key] }));
  }

  // Determine which keys changed relative to server state
  const changedKeys = useMemo(() => {
    if (!data) return [];
    const out: string[] = [];
    for (const g of data.groups) {
      for (const item of g.items) {
        const local = draft[item.key];
        if (item.sensitive) {
          // Only counts as changed if the user typed something
          if (local && local !== "") out.push(item.key);
        } else {
          if (local !== item.value) out.push(item.key);
        }
      }
    }
    return out;
  }, [data, draft]);

  const restartKeysChanged = useMemo(() => {
    if (!data) return [];
    const out: string[] = [];
    for (const g of data.groups) {
      for (const item of g.items) {
        if (item.requires_restart && changedKeys.includes(item.key)) out.push(item.key);
      }
    }
    return out;
  }, [data, changedKeys]);

  function buildUpdates() {
    const out: Record<string, string> = {};
    for (const k of changedKeys) out[k] = draft[k];
    return out;
  }

  async function save(forceRestart = false) {
    setBanner(null);
    const updates = buildUpdates();
    if (Object.keys(updates).length === 0) {
      setBanner({ kind: "ok", text: "No changes to save." });
      return;
    }

    if (restartKeysChanged.length > 0 && !forceRestart) {
      setRestartModal({ open: true, keys: restartKeysChanged, error: null });
      return;
    }

    try {
      const r = await update.mutateAsync(updates);
      if (r.rejected && r.rejected.length > 0) {
        setBanner({
          kind: "err",
          text: "Some keys were rejected: " + r.rejected.map((x) => `${x.key} (${x.reason})`).join(", "),
        });
        return;
      }
      if (r.restart_required) {
        try {
          const rr = await restart.mutateAsync();
          if (rr.restarted) {
            // Clear the current session so the login page renders the
            // form instead of auto-redirecting back to the dashboard.
            localStorage.removeItem("ulpf.access_token");
            localStorage.removeItem("ulpf.refresh_token");
            sessionStorage.setItem("ulpf.restarting", "true");
            window.setTimeout(() => {
              window.location.href = "/login";
            }, 300);
          } else {
            setBanner({ kind: "err", text: rr.message });
          }
        } catch (e: any) {
          setBanner({ kind: "err", text: e?.message || "Restart request failed." });
        }
        return;
      }
      setBanner({ kind: "ok", text: `Saved ${r.updated.length} setting(s).` });
    } catch (e: any) {
      setBanner({ kind: "err", text: e?.message || "Save failed." });
    }
  }

  async function confirmRestart() {
    setRestartModal((m) => ({ ...m, error: null }));
    await save(true);
  }

  if (isLoading) return <Loading />;
  if (error) return <div className="p-4"><ErrorBox error={error} /></div>;

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold tracking-wide">Settings</h1>
          <div className="text-2xs text-soc-textDim">
            Editable ULPF configuration. Some changes require a backend restart.
          </div>
        </div>
        <button
          className="btn btn-primary text-xs"
          onClick={() => save(false)}
          disabled={update.isPending || changedKeys.length === 0}
        >
          {update.isPending ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Save className="w-3.5 h-3.5" />
          )}
          Save changes
        </button>
      </div>

      {/* Current Session */}
      <div className="panel p-3 text-xs">
        <div className="panel-title mb-2">Current Session</div>
        {user ? (
          <div className="grid grid-cols-[120px_1fr] gap-x-4 gap-y-1">
            <div className="text-soc-textDim">Email</div>
            <div>{user.email}</div>
            <div className="text-soc-textDim">Roles</div>
            <div>{user.roles.join(", ")}</div>
          </div>
        ) : null}
      </div>

      {banner && (
        <div
          className={
            banner.kind === "ok"
              ? "panel p-3 border-l-4 border-emerald-500 bg-emerald-500/5 text-sm"
              : "panel p-3 border-l-4 border-red-500 bg-red-500/5 text-sm"
          }
        >
          {banner.text}
        </div>
      )}

      {changedKeys.length > 0 && (
        <div className="panel p-3 text-xs flex items-center gap-2 text-amber-400">
          <Info className="w-3.5 h-3.5" />
          {changedKeys.length} unsaved change{changedKeys.length !== 1 ? "s" : ""}.
          {restartKeysChanged.length > 0 && (
            <span className="ml-1">
              {restartKeysChanged.length} require a backend restart.
            </span>
          )}
        </div>
      )}

      {groups.map((g) => (
        <div key={g.name} className="panel">
          <div className="panel-header">
            <div className="panel-title">{g.name}</div>
          </div>
          <div className="p-3 grid grid-cols-1 md:grid-cols-2 gap-4">
            {g.items.map((item) => (
              <FieldRow
                key={item.key}
                item={item}
                value={draft[item.key] ?? ""}
                revealed={!!revealed[item.key]}
                onChange={(v) => setValue(item.key, v)}
                onToggleReveal={() => toggleReveal(item.key)}
              />
            ))}
          </div>
        </div>
      ))}

      <RestartModal
        open={restartModal.open}
        restartKeys={restartModal.keys}
        saving={update.isPending || restart.isPending}
        error={restartModal.error}
        onCancel={() => setRestartModal({ open: false, keys: [], error: null })}
        onConfirm={confirmRestart}
      />
    </div>
  );
}

function FieldRow({
  item, value, revealed, onChange, onToggleReveal,
}: {
  item: SettingsItem;
  value: string;
  revealed: boolean;
  onChange: (v: string) => void;
  onToggleReveal: () => void;
}) {
  const inputType =
    item.type === "int" || item.type === "float"
      ? "number"
      : item.sensitive
      ? (revealed ? "text" : "password")
      : "text";

  return (
    <div>
      <label className="label flex items-center gap-2">
        <span>{item.label}</span>
        {item.sensitive && item.is_set && (
          <span className="rounded-full bg-soc-accent/15 px-1.5 py-0.5 text-[10px] text-soc-accent">
            SET
          </span>
        )}
        {item.requires_restart && (
          <span className="rounded-full bg-amber-500/15 px-1.5 py-0.5 text-[10px] text-amber-400">
            RESTART
          </span>
        )}
      </label>

      {item.type === "bool" ? (
        <div className="flex items-center gap-2">
          <button
            type="button"
            role="switch"
            aria-checked={value === "true"}
            onClick={() => onChange(value === "true" ? "false" : "true")}
            className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
              value === "true" ? "bg-soc-accent" : "bg-soc-panelAlt border border-soc-border"
            }`}
          >
            <span
              className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
                value === "true" ? "translate-x-5" : "translate-x-1"
              }`}
            />
          </button>
          <span className="text-xs text-soc-textMuted">
            {value === "true" ? "Enabled" : "Disabled"}
          </span>
        </div>
      ) : (
        <div className="relative">
          <input
            className="input pr-8"
            type={inputType}
            value={value}
            step={item.type === "float" ? "0.1" : undefined}
            placeholder={
              item.sensitive && item.is_set
                ? "Leave blank to keep current"
                : ""
            }
            onChange={(e) => onChange(e.target.value)}
          />
          {item.sensitive && (
            <button
              type="button"
              className="absolute right-2 top-1/2 -translate-y-1/2 text-soc-textDim hover:text-soc-text"
              onClick={onToggleReveal}
              aria-label={revealed ? "Hide value" : "Show value"}
            >
              {revealed ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
            </button>
          )}
        </div>
      )}

      <div className="mt-1 text-2xs text-soc-textDim">{item.description}</div>
      <div className="mt-0.5 text-[10px] font-mono text-soc-textDim opacity-60">{item.key}</div>
    </div>
  );
}