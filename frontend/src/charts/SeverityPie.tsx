import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { severityHex } from "@/utils/colors";
import { useTheme } from "@/context/ThemeContext";

export function SeverityPie({ data }: { data: Record<string, number> }) {
  const { effectiveTheme } = useTheme();
  const isDark = effectiveTheme === "dark";

  const entries = Object.entries(data || {}).map(([k, v]) => ({ name: k, value: v }));
  if (entries.length === 0) {
    return <div className="text-xs text-soc-textDim py-6 text-center">No events ingested</div>;
  }

  const strokeColor = isDark ? "#0d1522" : "#ffffff";
  const tooltipBg = isDark ? "#0f172a" : "#ffffff";
  const tooltipBorder = isDark ? "#334155" : "#cbd5e1";
  const tooltipText = isDark ? "#f8fafc" : "#0f172a";

  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie
          data={entries}
          dataKey="value"
          nameKey="name"
          innerRadius={45}
          outerRadius={80}
          stroke={strokeColor}
          strokeWidth={2}
          paddingAngle={3}
        >
          {entries.map((e) => (
            <Cell key={e.name} fill={severityHex(e.name)} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            background: tooltipBg,
            border: `1px solid ${tooltipBorder}`,
            borderRadius: "8px",
            fontSize: 12,
            boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
          }}
          itemStyle={{ color: tooltipText }}
        />
        <Legend wrapperStyle={{ fontSize: 11, paddingTop: 6 }} />
      </PieChart>
    </ResponsiveContainer>
  );
}