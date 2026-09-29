import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { useTheme } from "@/context/ThemeContext";

export function ThroughputLine({ data }: { data: { hour: string; count: number }[] }) {
  const { effectiveTheme } = useTheme();
  const isDark = effectiveTheme === "dark";

  if (!data || data.length === 0) {
    return <div className="text-xs text-soc-textDim py-6 text-center">No throughput data</div>;
  }

  const gridColor = isDark ? "#1e293b" : "#e2e8f0";
  const tickColor = isDark ? "#64748b" : "#94a3b8";
  const tooltipBg = isDark ? "#0f172a" : "#ffffff";
  const tooltipBorder = isDark ? "#334155" : "#cbd5e1";
  const tooltipText = isDark ? "#f8fafc" : "#0f172a";

  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid stroke={gridColor} strokeDasharray="3 3" />
        <XAxis
          dataKey="hour"
          tick={{ fill: tickColor, fontSize: 10 }}
          tickFormatter={(v) => String(v).slice(11, 16)}
        />
        <YAxis tick={{ fill: tickColor, fontSize: 10 }} />
        <Tooltip
          contentStyle={{
            background: tooltipBg,
            border: `1px solid ${tooltipBorder}`,
            borderRadius: "8px",
            fontSize: 12,
            boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
          }}
          labelStyle={{ color: tickColor, fontWeight: 600 }}
          itemStyle={{ color: tooltipText }}
        />
        <Line
          type="monotone"
          dataKey="count"
          stroke={isDark ? "#06b6d4" : "#0284c7"}
          strokeWidth={2.5}
          dot={false}
          activeDot={{ r: 4, fill: isDark ? "#67e8f9" : "#0284c7" }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}