import {
  CartesianGrid,
  Legend,
  LabelList,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { formatNumberCompact, monthLabel } from "@/lib/utils";

interface MonthlyTrendChartProps {
  data: Array<{
    monthStart: string;
    currentYearSales: number;
    currentYearTarget: number;
    previousYearSales: number;
    achievementRate?: number;
  }>;
}

export function MonthlyTrendChart({ data }: MonthlyTrendChartProps) {
  return (
    <div className="h-[340px] w-full">
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 16, right: 8, left: 4, bottom: 0 }}>
          <CartesianGrid stroke="#E5E7EB" strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="monthStart" tickFormatter={monthLabel} tick={{ fill: "#6B7280", fontSize: 12 }} />
          <YAxis tick={{ fill: "#6B7280", fontSize: 12 }} tickFormatter={(value: number) => formatNumberCompact(value)} />
          <Tooltip
            formatter={(value: number, name: string) => {
              if (name === "Achievement Rate") {
                return `${(value * 100).toFixed(0)}%`;
              }
              return `SEK ${formatNumberCompact(value)}`;
            }}
            labelFormatter={(value) => monthLabel(String(value))}
          />
          <Legend verticalAlign="bottom" height={28} wrapperStyle={{ paddingTop: "8px" }} />
          <Line type="monotone" dataKey="currentYearSales" stroke="#1F3A5F" strokeWidth={3} dot={{ r: 3 }} name="Current Year Sales">
            <LabelList
              dataKey="achievementRate"
              position="top"
              formatter={(value: number) => `${Math.round((value ?? 0) * 100)}%`}
              style={{ fill: "#6B7280", fontSize: 11, fontWeight: 500 }}
              offset={10}
            />
          </Line>
          <Line type="monotone" dataKey="currentYearTarget" stroke="#64748B" strokeWidth={2} strokeDasharray="5 5" dot={false} name="Target" />
          <Line type="monotone" dataKey="previousYearSales" stroke="#CBD5E1" strokeWidth={2} dot={false} name="Previous Year" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
