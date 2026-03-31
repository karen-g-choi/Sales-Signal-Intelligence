import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import { formatCurrency, formatNumberCompact, formatPercent } from "@/lib/utils";

const colors = ["#1F3A5F", "#324B6B", "#48607D", "#64748B", "#7B8CA3", "#94A3B8", "#CBD5E1"];

type MixRow = {
  label: string;
  value: number;
  sharePct: number;
};

export function DetailCategoryMixChart({ data }: { data: MixRow[] }) {
  const total = data.reduce((sum, item) => sum + item.value, 0);
  const topCategory = data[0];
  const topThreeShare = data.slice(0, 3).reduce((sum, item) => sum + item.sharePct, 0);
  const categoryCount = data.length;

  return (
    <div className="grid gap-5 xl:grid-cols-[0.88fr_1.12fr] xl:items-center">
      <div className="space-y-4">
        <div className="mx-auto h-[320px] w-full max-w-[320px]">
          <ResponsiveContainer>
            <PieChart>
              <Pie data={data} dataKey="value" nameKey="label" innerRadius={72} outerRadius={112} paddingAngle={2} cornerRadius={6}>
                {data.map((entry, index) => (
                  <Cell key={entry.label} fill={colors[index % colors.length]} stroke="#FFFFFF" strokeWidth={5} />
                ))}
              </Pie>
              <text x="50%" y="43%" textAnchor="middle" dominantBaseline="central" fill="#6B7280" fontSize={11} fontWeight={700}>
                SELECTED SCOPE
              </text>
              <text x="50%" y="52%" textAnchor="middle" dominantBaseline="central" fill="#111827" fontSize={26} fontWeight={700}>
                {formatNumberCompact(total)}
              </text>
              <text x="50%" y="59%" textAnchor="middle" dominantBaseline="central" fill="#6B7280" fontSize={12}>
                SEK total sales
              </text>
              <Tooltip
                formatter={(value: number, _name, payload) => {
                  const item = payload?.payload as { sharePct: number } | undefined;
                  return [`SEK ${formatNumberCompact(value)} (${formatPercent(item?.sharePct ?? 0)})`, "Sales share"];
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
          <SummaryCard label="Top category" value={topCategory?.label ?? "N/A"} note={topCategory ? `${formatPercent(topCategory.sharePct)} of selected sales` : "No data"} />
          <SummaryCard label="Top 3 concentration" value={formatPercent(topThreeShare)} note="Share of sales concentrated in the three largest categories" />
          <SummaryCard label="Category count" value={String(categoryCount)} note="Distinct categories currently visible in the selected scope" />
        </div>
      </div>

      <div className="space-y-3">
        {data.map((row, index) => (
          <div key={row.label} className="rounded-2xl border border-slate-100 bg-slate-50 px-4 py-3">
            <div className="flex items-start gap-3">
              <span className="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: colors[index % colors.length] }} />
              <div className="min-w-0 flex-1">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 pr-2 text-[15px] font-medium leading-6 text-ink break-words">{row.label}</div>
                  <div className="shrink-0 text-sm font-semibold text-slateblue">{formatPercent(row.sharePct)}</div>
                </div>
                <div className="mt-1 text-[13px] leading-5 text-[#666] break-words">{formatCurrency(row.value)} in the selected scope</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function SummaryCard({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <div className="rounded-2xl border border-slate-100 bg-slate-50 px-4 py-3">
      <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">{label}</div>
      <div className="mt-2 text-lg font-semibold tracking-[-0.02em] text-ink">{value}</div>
      <div className="mt-1 text-[13px] leading-5 text-[#666]">{note}</div>
    </div>
  );
}
