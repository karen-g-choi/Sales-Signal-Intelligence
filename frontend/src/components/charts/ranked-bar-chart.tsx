import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

interface RankedBarChartProps {
  data: Array<Record<string, string | number>>;
  categoryKey: string;
  valueKey: string;
  color: string;
}

export function RankedBarChart({ data, categoryKey, valueKey, color }: RankedBarChartProps) {
  return (
    <div className="h-[320px] w-full">
      <ResponsiveContainer>
        <BarChart data={[...data].slice(0, 8).reverse()} layout="vertical" margin={{ left: 20, right: 12 }}>
          <CartesianGrid stroke="#E5E7EB" strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" tick={{ fill: "#6B7280", fontSize: 12 }} />
          <YAxis dataKey={categoryKey} type="category" width={110} tick={{ fill: "#6B7280", fontSize: 12 }} />
          <Tooltip />
          <Bar dataKey={valueKey} fill={color} radius={[0, 10, 10, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
