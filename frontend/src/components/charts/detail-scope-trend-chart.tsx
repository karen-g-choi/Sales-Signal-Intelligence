import {
  CartesianGrid,
  LabelList,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { formatNumberCompact, monthLabel } from "@/lib/utils";

function AttainmentLabel(props: { x?: number; y?: number; value?: number | string }) {
  const { x = 0, y = 0, value } = props;
  const numericValue = typeof value === "number" ? value : Number(value ?? 0);
  const labelY = Math.max(y - 14, 18);

  return (
    <text x={x} y={labelY} textAnchor="middle" fill="#64748B" fontSize={11} fontWeight={500}>
      {`${Math.round(numericValue * 100)}%`}
    </text>
  );
}

export function DetailScopeTrendChart({
  data,
}: {
  data: Array<{
    monthStart: string;
    sales: number;
    target: number;
    attainmentPct: number;
  }>;
}) {
  return (
    <div className="h-[340px] w-full">
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 26, right: 8, left: 4, bottom: 0 }}>
          <CartesianGrid stroke="#E5E7EB" strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="monthStart" tickFormatter={monthLabel} tick={{ fill: "#6B7280", fontSize: 12 }} />
          <YAxis tick={{ fill: "#6B7280", fontSize: 12 }} tickFormatter={(value: number) => formatNumberCompact(value)} />
          <Tooltip
            labelFormatter={(value) => monthLabel(String(value))}
            formatter={(value: number, name: string) => {
              if (name === "Attainment") return [`${Math.round(value * 100)}%`, "Attainment"];
              return [`SEK ${formatNumberCompact(value)}`, name];
            }}
          />
          <Legend verticalAlign="bottom" height={28} wrapperStyle={{ paddingTop: "8px" }} />
          <Line type="monotone" dataKey="sales" name="Sales" stroke="#1F3A5F" strokeWidth={3} dot={{ r: 3 }}>
            <LabelList
              dataKey="attainmentPct"
              content={<AttainmentLabel />}
            />
          </Line>
          <Line type="monotone" dataKey="target" name="Target" stroke="#94A3B8" strokeWidth={2.5} strokeDasharray="5 5" dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
