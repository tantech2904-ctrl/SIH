import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/api";
import { Loading, ErrorBox } from "@/components/Loading";

export default function ATTACK() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["attck"],
    queryFn: () => api.attckList(),
  });
  return (
    <div className="p-4 space-y-3">
      <div>
        <h1 className="text-lg font-semibold tracking-wide">MITRE ATT&CK Reference</h1>
        <div className="text-2xs text-soc-textDim">
          Local defensive mapping subset — not complete ATT&CK coverage.
        </div>
      </div>
      <div className="panel overflow-hidden">
        {isLoading ? <Loading /> : error ? <ErrorBox error={error} /> : (
          <table className="table">
            <thead>
              <tr><th>Technique ID</th><th>Name</th><th>Tactic</th></tr>
            </thead>
            <tbody>
              {data?.techniques.map((t: any) => (
                <tr key={t.technique_id} className="text-xs">
                  <td className="font-mono text-soc-accent">{t.technique_id}</td>
                  <td>{t.technique_name}</td>
                  <td>{t.tactic}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}