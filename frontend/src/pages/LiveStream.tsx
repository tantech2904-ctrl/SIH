import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Pause, Play, Trash2 } from "lucide-react";
import { LiveEventStream } from "@/services/ws";
import { SeverityBadge } from "@/components/SeverityBadge";
import { formatTime, truncate } from "@/utils/format";
import { riskColor, statusColor } from "@/utils/colors";
import type { EventListItem } from "@/types";

export default function LiveStream() {
  const [events, setEvents] = useState<EventListItem[]>([]);
  const [paused, setPaused] = useState(false);
  const streamRef = useRef<LiveEventStream | null>(null);
  // Owned by the component, not the poller, so it survives Pause → Resume.
  const lastSeenRef = useRef<string | null>(null);

  useEffect(() => {
    if (paused) return;

    const stream = new LiveEventStream(3000, { lastSeenRef });
    streamRef.current = stream;

    stream.start((fresh) => {
      setEvents((prev) => {
        // Defensive dedup by event_id in case the backend ever returns a
        // batch that overlaps with what's already on screen.
        const seen = new Set(prev.map((e) => e.event_id));
        const unique = fresh.filter((e) => !seen.has(e.event_id));
        if (unique.length === 0) return prev;
        return [...unique, ...prev].slice(0, 500);
      });
    });

    return () => {
      stream.stop();
      streamRef.current = null;
    };
  }, [paused]);

  return (
    <div className="p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-wide">Live Event Stream</h1>
          <div className="text-2xs text-soc-textDim">
            Polling the backend every 3s. Pause to freeze the view.
          </div>
        </div>
        <div className="flex gap-2">
          <button className="btn text-xs" onClick={() => setPaused((p) => !p)}>
            {paused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
            {paused ? "Resume" : "Pause"}
          </button>
          <button className="btn text-xs" onClick={() => setEvents([])}>
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