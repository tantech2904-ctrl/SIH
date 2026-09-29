import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Pause, Play, Trash2, Radio, Server, Copy, Info } from "lucide-react";
import { EventStreamClient } from "@/services/sse";
import { api } from "@/services/api";
import { SeverityBadge } from "@/components/SeverityBadge";
import { formatTime, truncate } from "@/utils/format";
import { riskColor, statusColor } from "@/utils/colors";
import type { EventListItem } from "@/types";

type ConnectionState = "connecting" | "connected" | "reconnecting";

export default function LiveStream() {
  const [events, setEvents] = useState<EventListItem[]>([]);
  const [paused, setPaused] = useState(false);
  const [connState, setConnState] = useState<ConnectionState>("connecting");
  const streamRef = useRef<EventStreamClient | null>(null);
  // Mirrors `paused` for the SSE callback so the callback doesn't need to be
  // recreated when pause toggles. The stream stays alive either way; the
  // callback just decides whether to append.
  const pausedRef = useRef(false);
  const lastSeenRef = useRef<string | null>(null);

  useEffect(() => {
    pausedRef.current = paused;
  }, [paused]);

  useEffect(() => {
    let cancelled = false;
    setConnState("connecting");

    (async () => {
      try {
        const initial = await api.listEvents({ size: 30, page: 1 });
        if (cancelled) return;
        setEvents(() => {
          const unique = initial.items.slice(0, 500);
          if (unique.length > 0) {
            lastSeenRef.current = unique[0].event_id;
          }
          return unique;
        });
      } catch {
        // Bootstrap failure is non-fatal — the stream may still work.
      }

      if (cancelled) return;

      const client = new EventStreamClient(
        "/api/v1/events/stream",
        (payload: EventListItem) => {
          setConnState("connected");
          if (pausedRef.current) return; // paused: drop on the floor
          setEvents((prev) => {
            const seen = new Set(prev.map((e) => e.event_id));
            if (seen.has(payload.event_id)) return prev;
            lastSeenRef.current = payload.event_id;
            return [payload, ...prev].slice(0, 500);
          });
        },
        (status) => setConnState(status),
      );
      streamRef.current = client;
      client.start();
    })();

    return () => {
      cancelled = true;
      streamRef.current?.stop();
      streamRef.current = null;
    };
    // No dependencies — this effect runs exactly once per mount.
  }, []);

  const handleClear = () => {
    setEvents([]);
    lastSeenRef.current = null;
    // Do not tell the stream to replay anything on the next reconnect.
    streamRef.current?.reset();
  };

  const [copied, setCopied] = useState(false);
  const copyCommand = () => {
    navigator.clipboard
      .writeText("cd /d \"%~dp0..\" && scripts\\ulpf-connector\\run_connector.bat")
      .then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2500);
      })
      .catch(() => {/* clipboard not available */});
  };

  return (
    <div className="p-4 space-y-3">
      {/* Connector Instructions Banner */}
      <div className="rounded-2xl border border-amber-500/30 bg-amber-500/8 p-4">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-amber-500/15 text-amber-500">
            <Server className="h-4 w-4" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-bold text-soc-text">
                Host Log Connector Windows Only For Demo
              </span>
              <span className="rounded-full border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-amber-500">
                Not in Docker
              </span>
            </div>
            <p className="mt-1.5 text-xs leading-relaxed text-soc-textMuted">
              The Windows Event Log Connector runs{" "}
              <strong className="text-soc-text">directly on the host machine</strong>, outside
              container, because it requires access to Windows system APIs (
              <code className="rounded bg-soc-panelAlt px-1 py-0.5 font-mono text-[11px]">
                wevtutil
              </code>{" "}
              /{" "}
              <code className="rounded bg-soc-panelAlt px-1 py-0.5 font-mono text-[11px]">
                win32evtlog
              </code>
              ) that cannot run inside a container. This is intentional by design, the connector
              is a lightweight host agent that forwards events securely via UDP port 5140(The container comes shipped with other OS connectors too).
            </p>
            <div className="mt-2.5 space-y-1 text-xs text-soc-textMuted">
              <div className="font-semibold text-soc-text">To stream real host logs:</div>
              <div className="flex items-start gap-2">
                <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-soc-accent/20 text-[10px] font-bold text-soc-accent leading-none">
                  1
                </span>
                <span>
                  Navigate to{" "}
                  <code className="rounded bg-soc-panelAlt px-1 font-mono text-[11px]">
                    scripts\ulpf-connector\
                  </code>{" "}
                  in your project folder
                </span>
              </div>
              <div className="flex items-start gap-2">
                <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-soc-accent/20 text-[10px] font-bold text-soc-accent leading-none">
                  2
                </span>
                <span>
                  Right-click{" "}
                  <code className="rounded bg-soc-panelAlt px-1 font-mono text-[11px]">
                    run_connector.bat
                  </code>{" "}
                  → <strong className="text-soc-text">Run as Administrator</strong>
                </span>
              </div>
              <div className="flex items-start gap-2">
                <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-soc-accent/20 text-[10px] font-bold text-soc-accent leading-none">
                  3
                </span>
                <span>Events appear in this table within seconds via UDP port 5140</span>
              </div>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                onClick={copyCommand}
                className="btn text-xs rounded-xl flex items-center gap-1.5"
              >
                {copied ? (
                  <>
                    <span className="text-emerald-500">✓</span> Copied!
                  </>
                ) : (
                  <>
                    <Copy className="h-3 w-3" /> Copy Run Command
                  </>
                )}
              </button>
              <div className="flex items-center gap-1.5 rounded-xl border border-soc-border bg-soc-panelAlt/60 px-3 py-1.5 text-xs text-soc-textDim">
                <Info className="h-3 w-3 shrink-0" />
                <span>
                  Or use <strong className="text-soc-text">▶ Run Demo</strong> on the Dashboard
                  for instant synthetic logs without the connector
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-wide flex items-center gap-2">
            Live Event Stream
            <ConnectionBadge state={connState} />
          </h1>
          <div className="text-2xs text-soc-textDim">
            Streaming via Server-Sent Events. New events arrive in real time.
          </div>
        </div>
        <div className="flex gap-2">
          <button className="btn text-xs" onClick={() => setPaused((p) => !p)}>
            {paused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
            {paused ? "Resume" : "Pause"}
          </button>
          <button className="btn text-xs" onClick={handleClear}>
            <Trash2 className="w-3.5 h-3.5" /> Clear
          </button>
        </div>
      </div>

      <div className="panel overflow-hidden">
        {events.length === 0 ? (
          <div className="p-6 text-xs text-soc-textDim text-center">
            Waiting for events…
          </div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Format</th>
                <th>Type</th>
                <th>Severity</th>
                <th>Src</th>
                <th>Dst</th>
                <th>User</th>
                <th>Message</th>
                <th>Risk</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {events.map((e) => (
                <tr key={e.event_id} className="text-xs">
                  <td className="font-mono text-soc-textMuted whitespace-nowrap">
                    <Link className="hover:underline" to={`/events/${e.event_id}`}>
                      {formatTime(e.timestamp)}
                    </Link>
                  </td>
                  <td className="text-soc-textMuted">{e.detected_format || "—"}</td>
                  <td>{e.event_type}</td>
                  <td><SeverityBadge severity={e.severity} small /></td>
                  <td className="font-mono">{e.source_ip || "—"}</td>
                  <td className="font-mono">{e.destination_ip || "—"}</td>
                  <td>{e.user_name || "—"}</td>
                  <td className="text-soc-textMuted max-w-[360px]">
                    {truncate(e.message, 120)}
                  </td>
                  <td className={`font-mono ${riskColor(e.risk_score)}`}>
                    {e.risk_score ?? "—"}
                  </td>
                  <td>
                    <span className={`badge border ${statusColor(e.processing_status)}`}>
                      {e.processing_status}
                    </span>
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

function ConnectionBadge({ state }: { state: ConnectionState }) {
  const map: Record<ConnectionState, { cls: string; label: string }> = {
    connecting:   { cls: "text-amber-400 bg-amber-500/10 border-amber-500/40",  label: "● Connecting" },
    connected:    { cls: "text-green-400 bg-green-500/10 border-green-500/40",  label: "● Live" },
    reconnecting: { cls: "text-amber-400 bg-amber-500/10 border-amber-500/40",  label: "● Reconnecting" },
  };
  const { cls, label } = map[state];
  return (
    <span className={`badge border text-2xs ${cls}`}>
      <Radio className="inline w-3 h-3 mr-1" />
      {label.replace("● ", "")}
    </span>
  );
}