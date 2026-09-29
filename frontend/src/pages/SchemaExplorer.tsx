import { useCSESchema } from "@/hooks/useApi";
import { Loading, ErrorBox, EmptyState } from "@/components/Loading";

export default function SchemaExplorer() {
  const { data, isLoading, error } = useCSESchema();
  return (
    <div className="p-4 space-y-3">
      <div>
        <h1 className="text-lg font-semibold tracking-wide">CSE Schema Explorer</h1>
        <div className="text-2xs text-soc-textDim">
          Practical, OCSF-aligned Canonical Security Event schema.
        </div>
      </div>
      {isLoading ? <Loading /> : error ? <ErrorBox error={error} /> :
        !data ? <EmptyState message="Schema unavailable" /> : (
          <div className="panel overflow-hidden">
            <table className="table">
              <thead>
                <tr><th>Canonical Path</th><th>Column</th><th>Type</th><th>Required</th><th>Description</th></tr>
              </thead>
              <tbody>
                {data.fields.map((f) => (
                  <tr key={f.path} className="text-xs">
                    <td className="font-mono text-soc-accent">{f.path}</td>
                    <td className="font-mono text-soc-textMuted">{f.column}</td>
                    <td>{f.type}</td>
                    <td>{f.required ? "yes" : "no"}</td>
                    <td className="text-soc-textMuted">{f.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
    </div>
  );
}