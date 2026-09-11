import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

export function ThroughputLine({ data }: { data: { hour: string; count: number }[] }) {
  if (!data || data.length === 0) {
    return <div className="text-xs text-soc-textDim py-6 text-center">No throughput data</div>;
  }
  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="#1f2a44" strokeDasharray="3 3" />
        <XAxis
          dataKey="hour"
          tick={{ fill: "#64748b", fontSize: 10 }}
          tickFormatter={(v) => String(v).slice(11, 16)}
        />
        <YAxis tick={{ fill: "#64748b", fontSize: 10 }} />
        <Tooltip
          contentStyle={{ background: "#0f1626", border: "1px solid #1f2a44", fontSize: 12 }}
          labelStyle={{ color: "#94a3b8" }}
        />
        <Line type="monotone" dataKey="count" stroke="#38bdf8" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}