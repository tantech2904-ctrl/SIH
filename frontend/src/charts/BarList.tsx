export function BarList({
  title,
  data,
  color = "#38bdf8",
}: {
  title: string;
  data: { label: string; value: number }[];
  color?: string;
}) {
  const max = Math.max(1, ...data.map((d) => d.value));
  return (
    <div>
      <div className="text-2xs uppercase tracking-widest text-soc-textDim mb-2">{title}</div>
      {data.length === 0 ? (
        <div className="text-xs text-soc-textDim py-4">No data</div>
      ) : (
        <div className="space-y-1.5">
          {data.map((d) => (
            <div key={d.label} className="text-xs">
              <div className="flex justify-between">
                <span className="truncate text-soc-textMuted mr-2">{d.label || "—"}</span>
                <span className="font-mono text-soc-text tabular-nums">{d.value}</span>
              </div>
              <div className="h-1 bg-soc-bg rounded overflow-hidden mt-0.5">
                <div
                  className="h-full"
                  style={{ width: `${(d.value / max) * 100}%`, backgroundColor: color }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}