import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import { formatNumberCompact } from "@/lib/utils";

interface CompositionChartProps {
  data: Array<{
    label: string;
    value: number;
  }>;
}

const colors: Record<string, string> = {
  Maintenance: "#1F3A5F",
  Service: "#324B6B",
  Repair: "#48607D",
  Diagnostics: "#64748B",
  Powertrain: "#7B8CA3",
  "EV Service": "#94A3B8",
  Accessories: "#A9B7C9",
  Other: "#CBD5E1",
};

export function CompositionChart({ data }: CompositionChartProps) {
  return (
    <div className="h-[320px] w-full">
      <ResponsiveContainer>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="label"
            innerRadius={72}
            outerRadius={104}
            paddingAngle={2}
            stroke="#FFFFFF"
            strokeWidth={4}
          >
            {data.map((entry) => (
              <Cell key={entry.label} fill={colors[entry.label] ?? "#64748B"} />
            ))}
          </Pie>
          <Tooltip formatter={(value: number) => `SEK ${formatNumberCompact(value)}`} />
          <Legend
            verticalAlign="bottom"
            align="center"
            iconType="circle"
            wrapperStyle={{ fontSize: "12px", color: "#6B7280", paddingTop: "10px" }}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
