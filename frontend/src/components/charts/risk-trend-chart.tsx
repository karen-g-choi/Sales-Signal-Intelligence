import {
  Bar,
  ComposedChart,
  CartesianGrid,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { formatNumberCompact, monthLabel } from "@/lib/utils";

interface RiskTrendChartProps {
  data: Array<{
    monthStart: string;
    reportedSales: number;
    baselineSales: number;
    eventLinkedSales: number;
    gapToBaseline: number;
  }>;
}

export function RiskTrendChart({ data }: RiskTrendChartProps) {
  return (
    <div className="h-[360px] w-full">
      <ResponsiveContainer>
        <ComposedChart data={data}>
          <CartesianGrid stroke="#E5E7EB" strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="monthStart" tickFormatter={monthLabel} tick={{ fill: "#6B7280", fontSize: 12 }} />
          <YAxis tick={{ fill: "#6B7280", fontSize: 12 }} tickFormatter={(value: number) => formatNumberCompact(value)} />
          <Tooltip
            labelFormatter={(value) => monthLabel(String(value))}
            formatter={(value: number, name: string) => {
              const labels: Record<string, string> = {
                reportedSales: "Reported Sales",
                baselineSales: "Underlying Baseline",
                eventLinkedSales: "Event-Linked Sales",
                gapToBaseline: "Gap vs Baseline",
              };
              return [`SEK ${formatNumberCompact(value)}`, labels[name] ?? name];
            }}
          />
          <Legend />
          <Bar dataKey="eventLinkedSales" name="Event-Linked Sales" fill="#C97A52" barSize={20} radius={[8, 8, 0, 0]} />
          <Line type="monotone" dataKey="reportedSales" name="Reported Sales" stroke="#1F3A5F" strokeWidth={3} dot={{ r: 3 }} />
          <Line type="monotone" dataKey="baselineSales" name="Underlying Baseline" stroke="#94A3B8" strokeWidth={2.5} strokeDasharray="6 4" dot={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
