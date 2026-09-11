import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { severityHex } from "@/utils/colors";

export function SeverityPie({ data }: { data: Record<string, number> }) {
  const entries = Object.entries(data || {}).map(([k, v]) => ({ name: k, value: v }));
  if (entries.length === 0) {
    return <div className="text-xs text-soc-textDim py-6 text-center">No events ingested</div>;
  }
  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie data={entries} dataKey="value" nameKey="name" innerRadius={40} outerRadius={80} stroke="#0a0e1a">
          {entries.map((e) => (
            <Cell key={e.name} fill={severityHex(e.name)} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{ background: "#0f1626", border: "1px solid #1f2a44", fontSize: 12 }}
          itemStyle={{ color: "#e2e8f0" }}
        />
        <Legend wrapperStyle={{ fontSize: 11 }} />
      </PieChart>
    </ResponsiveContainer>
  );
}