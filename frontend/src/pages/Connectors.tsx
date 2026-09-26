import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { useConnectors, useSetConnectorConfig } from "@/hooks/useApi";
import { Loading, ErrorBox, EmptyState } from "@/components/Loading";
import { formatTime } from "@/utils/format";
import type { Connector } from "@/types";

function StatusBadge({ status }: { status: "online" | "stale" | "offline" }) {
  const map = {
    online:  "text-green-400 bg-green-500/10 border-green-500/40",
    stale:   "text-amber-400 bg-amber-500/10 border-amber-500/40",
    offline: "text-red-400 bg-red-500/10 border-red-500/40",
  };
  const label = { online: "● Online", stale: "● Stale", offline: "● Offline" };
  return <span className={`badge border ${map[status]}`}>{label[status]}</span>;
}

function Toggle({
  on,
  pending,
  onChange,
}: {
  on: boolean;
  pending: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <button
      type="button"
      disabled={pending}
      onClick={() => onChange(!on)}
      className={`relative inline-flex h-5 w-9 items-center rounded-full border transition-colors ${
        on
          ? "bg-soc-accent/40 border-soc-accent"
          : "bg-soc-panelAlt border-soc-border"
      } ${pending ? "opacity-50 cursor-wait" : "cursor-pointer"}`}
      aria-pressed={on}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-soc-text transition-transform ${
          on ? "translate-x-4" : "translate-x-0"
        }`}
      />
    </button>
  );
}

function AdapterRow({
  connector,
  adapter,
  desiredSet,
  runningSet,
  mutationPending,
  onToggle,
}: {
  connector: Connector;
  adapter: string;
  desiredSet: Set<string> | null;
  runningSet: Set<string>;
  mutationPending: boolean;
  onToggle: (adapter: string, next: boolean) => void;
}) {
  // desiredSet === null means "no opinion" — UI shows the running state as truth.
  const effectiveDesired = desiredSet ?? runningSet;
  const desiredOn = effectiveDesired.has(adapter);
  const runningOn = runningSet.has(adapter);
  const diverging = desiredSet !== null && desiredOn !== runningOn;

  return (
    <div className="flex items-center justify-between py-2 px-3 border-b border-soc-border last:border-b-0">
      <div className="flex items-center gap-3 min-w-0">
        <Toggle
          on={desiredOn}
          pending={mutationPending}
          onChange={(next) => onToggle(adapter, next)}
        />
        <span className="font-mono text-xs">{adapter}</span>
      </div>
      <div className="flex items-center gap-3 text-2xs">
        {diverging && (
          <span className="text-amber-400">
            Desired: {desiredOn ? "on" : "off"} · Running: {runningOn ? "on" : "off"} (converging…)
          </span>
        )}
        {!diverging && runningOn && (
          <span className="text-green-400">running</span>
        )}
        {!diverging && !runningOn && desiredSet === null && (
          <span className="text-soc-textDim">idle (local config governs)</span>
        )}
        {!diverging && !runningOn && desiredSet !== null && (
          <span className="text-soc-textDim">stopped</span>
        )}
      </div>
    </div>
  );
}

function ExpandedRow({ connector }: { connector: Connector }) {
  const setConfig = useSetConnectorConfig();

  // Which adapters should the UI show? Union of available + currently running
  // (running should always be a subset of available, but be defensive).
  const allAdapters = Array.from(
    new Set([...(connector.available_adapters || []), ...(connector.adapters || [])]),
  ).sort();

  if (!connector.available_adapters || connector.available_adapters.length === 0) {
    return (
      <div className="px-4 py-3 text-2xs text-amber-400">
        This connector hasn't reported its available adapters yet.
        Restart it with the latest connector version to enable adapter toggles.
      </div>
    );
  }

  const desiredSet = connector.desired_adapters === null
    ? null
    : new Set(connector.desired_adapters);

  const runningSet = new Set(connector.adapters || []);

  const onToggle = (adapter: string, next: boolean) => {
    // If desired is null, we "materialize" it from the running set first so
    // we don't accidentally clobber unrelated adapters when the user flips
    // a single toggle.
    const base = desiredSet === null ? new Set(runningSet) : new Set(desiredSet);
    if (next) base.add(adapter);
    else base.delete(adapter);
    setConfig.mutate({
      id: connector.connector_id,
      body: { desired_adapters: Array.from(base).sort() },
    });
  };

  if (allAdapters.length === 0) {
    return (
      <div className="px-4 py-3 text-2xs text-soc-textDim">
        This connector reported no adapters.
      </div>
    );
  }

  return (
    <div className="bg-soc-panelAlt/40 border-t border-soc-border">
      <div className="px-3 py-2 text-2xs text-soc-textDim border-b border-soc-border">
        Toggle adapters. The connector converges within {connector.config_poll_interval_s}s.
        {desiredSet === null && (
          <> Currently following local config — your first toggle will pin the desired set.</>
        )}
      </div>
      {allAdapters.map((name) => (
        <AdapterRow
          key={name}
          connector={connector}
          adapter={name}
          desiredSet={desiredSet}
          runningSet={runningSet}
          mutationPending={setConfig.isPending}
          onToggle={onToggle}
        />
      ))}
    </div>
  );
}

export default function Connectors() {
  const { data, isLoading, error } = useConnectors();
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const toggleExpanded = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <div className="p-4 space-y-3">
      <div>
        <h1 className="text-lg font-semibold tracking-wide">Connectors</h1>
        <div className="text-2xs text-soc-textDim">
          Host-side connectors streaming native log sources. Heartbeat every 60s.
          Click a host to manage its adapters.
        </div>
      </div>

      <div className="panel overflow-hidden">
        {isLoading ? (
          <Loading />
        ) : error ? (
          <div className="p-3"><ErrorBox error={error} /></div>
        ) : !data || data.items.length === 0 ? (
          <EmptyState
            message="No connectors have reported in yet"
            hint="Start the ULPF connector on a Windows, Linux, or macOS host."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th className="w-6"></th>
                  <th>Status</th>
                  <th>Hostname</th>
                  <th>OS</th>
                  <th>Adapters</th>
                  <th>Version</th>
                  <th>Last Heartbeat</th>
                  <th>Last Event</th>
                  <th className="text-right">Events</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((c) => {
                  const isOpen = expanded.has(c.connector_id);
                  return (
                    <>
                      <tr
                        key={c.connector_id}
                        className="text-xs cursor-pointer hover:bg-soc-panelAlt/40"
                        onClick={() => toggleExpanded(c.connector_id)}
                      >
                        <td className="text-soc-textDim">
                          {isOpen ? (
                            <ChevronDown className="w-3.5 h-3.5" />
                          ) : (
                            <ChevronRight className="w-3.5 h-3.5" />
                          )}
                        </td>
                        <td><StatusBadge status={c.status} /></td>
                        <td className="font-semibold">{c.hostname}</td>
                        <td>{c.os}</td>
                        <td className="font-mono text-2xs">
                          {c.adapters.join(", ") || "—"}
                        </td>
                        <td className="text-soc-textDim">{c.version}</td>
                        <td className="text-soc-textMuted whitespace-nowrap">
                          {formatTime(c.last_heartbeat)}
                        </td>
                        <td className="text-soc-textMuted whitespace-nowrap">
                          {c.last_event_at ? formatTime(c.last_event_at) : "—"}
                        </td>
                        <td className="text-right font-mono">
                          {c.events_total.toLocaleString()}
                        </td>
                      </tr>
                      {isOpen && (
                        <tr key={`${c.connector_id}-expanded`}>
                          <td colSpan={9} className="p-0">
                            <ExpandedRow connector={c} />
                          </td>
                        </tr>
                      )}
                    </>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {data && data.items.length > 0 && (
        <div className="text-2xs text-soc-textDim">
          Total: {data.total} connector{data.total === 1 ? "" : "s"}
        </div>
      )}
    </div>
  );
}