import type { ReactNode } from "react";

export function StatCard({
  label,
  value,
  sub,
  accent,
  icon,
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  accent?: string;
  icon?: ReactNode;
}) {
  return (
    <div className="panel p-3 flex flex-col gap-1 min-w-0">
      <div className="flex items-center justify-between">
        <span className="stat-label">{label}</span>
        {icon ? <span className="text-soc-textDim">{icon}</span> : null}
      </div>
      <div className={`stat-value ${accent || "text-soc-text"}`}>{value}</div>
      {sub ? <div className="text-2xs text-soc-textDim">{sub}</div> : null}
    </div>
  );
}