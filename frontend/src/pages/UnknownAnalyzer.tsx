import { Link } from "react-router-dom";
import { useQuarantine } from "@/hooks/useApi";
import { Loading, ErrorBox, EmptyState } from "@/components/Loading";
import { formatTime } from "@/utils/format";

export default function UnknownAnalyzer() {
  const { data, isLoading, error } = useQuarantine({
    reason: "UNKNOWN_FORMAT", size: 100, page: 1,
  });
  return (
    <div className="p-4 space-y-3">
      <div>
        <h1 className="text-lg font-semibold tracking-wide">Unknown Format Analyzer</h1>
        <div className="text-2xs text-soc-textDim">
          Structural analysis of previously-unseen logs. Analysts approve mappings before replay.
        </div>
      </div>
      <div className="panel overflow-hidden">
        {isLoading ? <Loading /> : error ? <ErrorBox error={error} /> :
          !data || data.items.length === 0 ? (
            <EmptyState message="No unknown-format logs"
              hint="Use the Test Lab 'unknown_vendor' scenario to generate a sample." />
          ) : (
            <table className="table">
              <thead>
                <tr><th>Time</th><th>Event</th><th>Confidence</th><th>Detail</th><th></th></tr>
              </thead>
              <tbody>
                {data.items.map((q) => (
                  <tr key={q.id} className="text-xs">
                    <td>{formatTime(q.created_at)}</td>
                    <td className="font-mono">{q.event_id.slice(0, 8)}</td>
                    <td className="font-mono">{q.detection_confidence?.toFixed(3) ?? "—"}</td>
                    <td className="text-soc-textMuted">{q.detail}</td>
                    <td>
                      <Link className="btn text-2xs !py-0.5 !px-2"
                        to={`/quarantine?sel=${q.id}`}>
                        Analyze
                      </Link>
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