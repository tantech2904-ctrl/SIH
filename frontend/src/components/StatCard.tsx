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
    <div className="panel p-4 flex flex-col justify-between gap-2 min-w-0 transition-all duration-200 hover:border-soc-accent/40 group hover:shadow-md">
      <div className="flex items-center justify-between gap-2">
        <span className="stat-label text-soc-textDim group-hover:text-soc-text transition-colors">
          {label}
        </span>
        {icon ? (
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-soc-panelAlt border border-soc-border text-soc-textDim group-hover:text-soc-accent group-hover:border-soc-accent/30 transition-all">
            {icon}
          </div>
        ) : null}
      </div>
      <div>
        <div className={`stat-value ${accent || "text-soc-text"}`}>{value}</div>
        {sub ? (
          <div className="text-[11px] text-soc-textDim mt-0.5 truncate font-medium">
            {sub}
          </div>
        ) : null}
      </div>
    </div>
  );
}