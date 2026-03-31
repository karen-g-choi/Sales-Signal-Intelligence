import { MonthlyTrendChart } from "@/components/charts/monthly-trend-chart";
import { CompositionChart } from "@/components/charts/composition-chart";
import { DetailCategoryMixChart } from "@/components/charts/detail-category-mix-chart";
import { DetailScopeTrendChart } from "@/components/charts/detail-scope-trend-chart";
import { KpiCard } from "@/components/kpi-card";
import { PageHeader } from "@/components/page-header";
import { TableCard } from "@/components/table-card";
import { Button } from "@/components/ui/button";
import type { DashboardData, DashboardFilters } from "@/lib/types";
import { formatCurrency, formatNumberCompact, formatPercent, formatQuantity } from "@/lib/utils";

export function SalesOverviewPage({
  data,
  filters,
  onFiltersChange,
  onResetFilters,
}: {
  data: DashboardData;
  filters: DashboardFilters;
  onFiltersChange: (filters: DashboardFilters) => void;
  onResetFilters: () => void;
}) {
  const monthlyTrendData = data.monthlyTrend.map((row) => ({
    ...row,
    achievementRate: row.currentYearTarget > 0 ? row.currentYearSales / row.currentYearTarget : 0,
  }));
  const latestMonth = monthlyTrendData[monthlyTrendData.length - 1];
  const ytdTargetValue = monthlyTrendData.reduce((sum, row) => sum + row.currentYearTarget, 0);
  const currentMonthYoY =
    latestMonth && latestMonth.previousYearSales > 0
      ? latestMonth.currentYearSales / latestMonth.previousYearSales - 1
      : 0;
  const ytdAchievement = ytdTargetValue > 0 ? data.kpis.ytdSales / ytdTargetValue : 0;
  const targetInsights = buildTargetInsights(data.detailViews.targetInsight);
  const targetTableRows = buildBalancedTargetRows(data.detailViews.targetInsight);
  const executiveHeadline = buildExecutiveHeadline(data);
  const underTargetMonths = monthlyTrendData.filter((row) => row.currentYearSales < row.currentYearTarget).length;
  const currentMonthAchievement =
    latestMonth && latestMonth.currentYearTarget > 0 ? latestMonth.currentYearSales / latestMonth.currentYearTarget : 0;
  const summaryContext = buildExecutiveSummaryContext(data, {
    currentMonthAchievement,
    underTargetMonths,
    ytdAchievement,
  });

  return (
    <>
      <PageHeader
        title="Sales Overview"
        subtitle="A structured commercial reporting view of sales performance, mix, growth, and target delivery."
      />

      <section className="space-y-5">
        <div className="rounded-2xl border border-slate-200 bg-white px-7 py-7 shadow-[0_4px_12px_rgba(0,0,0,0.05)]">
        <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slateblue">Actionable Summary</div>
          <h2 className="mt-3 max-w-6xl text-[clamp(1.55rem,2vw,2rem)] font-semibold leading-[1.12] tracking-[-0.04em] text-ink">
            {executiveHeadline}
          </h2>
        </div>

        <div className="grid gap-5 xl:grid-cols-[1.35fr_0.9fr_0.9fr]">
          <div className="rounded-2xl border border-slate-200 bg-white px-7 py-7 shadow-[0_4px_12px_rgba(0,0,0,0.05)]">
            <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">Key Drivers</div>
            <ul className="mt-4 space-y-3 text-sm leading-[1.6] text-[#666]">
              {summaryContext.driverBullets.map((item) => (
                <li key={item} className="flex gap-3">
                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-slateblue" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
            <div className="mt-5 rounded-2xl border border-slate-100 bg-slate-50 px-4 py-4">
              <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">Management read-through</div>
              <div className="mt-2 text-[13px] leading-6 text-[#666]">{summaryContext.managementReadThrough}</div>
            </div>
          </div>

          <VisualProgressCard
            title="Target Context"
            value={data.kpis.targetAchievementPct}
            statusLabel={summaryContext.targetStatusLabel}
            statusTone={summaryContext.targetStatusTone}
            note={summaryContext.targetStatusNote}
            submetrics={summaryContext.targetSubmetrics}
          />

          <div className="grid gap-5">
            <ConcentrationCard
              title="Revenue Concentration"
              value={summaryContext.topCategoryName}
              deltaLabel={summaryContext.topCategoryDeltaLabel}
              note={summaryContext.topCategoryNote}
              statusLabel="Attention Needed"
            />
            <ConcentrationCard
              title="Customer Concentration"
              value={summaryContext.topCustomerName}
              deltaLabel={summaryContext.topCustomerDeltaLabel}
              note={summaryContext.topCustomerNote}
              statusLabel="Attention Needed"
            />
          </div>
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-5">
        <KpiCard
          label="YTD Sales"
          value={formatNumberCompact(data.kpis.ytdSales)}
          unitLabel="SEK"
          note={data.kpis.ytdGrowthPct >= 0 ? "Up versus the same period last year" : "Down versus the same period last year"}
        />
        <KpiCard
          label="Current Month Sales"
          value={formatNumberCompact(data.kpis.currentMonthSales)}
          unitLabel="SEK"
          note={currentMonthYoY >= 0 ? "Latest month is above prior year" : "Latest month is below prior year"}
        />
        <KpiCard
          label="Current Month Quantity"
          value={formatQuantity(data.kpis.currentMonthQuantity)}
          note="Order volume in the most recent month"
        />
        <KpiCard
          label="YTD Growth %"
          value={formatPercent(data.kpis.ytdGrowthPct)}
          note={data.kpis.ytdGrowthPct >= 0 ? "Growth is positive year to date" : "Growth is trailing prior year"}
        />
        <KpiCard
          label="Target Achievement %"
          value={formatPercent(data.kpis.targetAchievementPct)}
          note={data.kpis.targetAchievementPct >= 1 ? "Currently above annual plan" : "Currently below annual plan"}
        />
      </section>

      <section className="space-y-4">
        <div>
          <h2 className="text-xl font-semibold tracking-[-0.02em] text-ink">Core Evidence</h2>
          <p className="mt-1 text-sm leading-6 text-muted">
            These visuals answer the core management questions: are we above or below target, and where is revenue concentrated?
          </p>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.45fr_0.95fr]">
        <TableCard title="Are we above or below target?" subtitle="Monthly sales performance versus target, with prior year as context.">
          <div className="mb-5 grid gap-3 md:grid-cols-3">
            <div className="rounded-2xl bg-slate-50 px-4 py-3">
              <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">Current Month YoY</div>
              <div className="mt-1 text-xl font-semibold tracking-[-0.03em] text-ink">{formatPercent(currentMonthYoY)}</div>
              <div className="mt-1 text-xs leading-5 text-muted">
                {currentMonthYoY >= 0 ? "Growth is holding in the latest month" : "Latest month is softer than last year"}
              </div>
            </div>
            <div className="rounded-2xl bg-slate-50 px-4 py-3">
              <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">YTD Growth</div>
              <div className="mt-1 text-xl font-semibold tracking-[-0.03em] text-ink">{formatPercent(data.kpis.ytdGrowthPct)}</div>
              <div className="mt-1 text-xs leading-5 text-muted">
                {data.kpis.ytdGrowthPct >= 0 ? "Sales are expanding versus prior year" : "Sales are trailing the prior year base"}
              </div>
            </div>
            <div className="rounded-2xl bg-slate-50 px-4 py-3">
              <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">YTD Target Delivery</div>
              <div className="mt-1 text-xl font-semibold tracking-[-0.03em] text-ink">{formatPercent(ytdAchievement)}</div>
              <div className="mt-1 text-xs leading-5 text-muted">
                {underTargetMonths > 0 ? `${underTargetMonths} months are below plan in the current year` : "All visible months are at or above plan"}
              </div>
            </div>
          </div>
          <MonthlyTrendChart data={monthlyTrendData} />
        </TableCard>
        <TableCard title="Where is revenue concentrated?" subtitle="Category mix shows which parts of the business carry the largest share of sales.">
          <CompositionChart data={data.salesMix} />
        </TableCard>
      </section>

      <section className="space-y-4">
        <div>
          <h2 className="text-xl font-semibold tracking-[-0.02em] text-ink">Supporting Detail</h2>
          <p className="mt-1 text-sm leading-6 text-muted">
            These views show who drives the business and where commercial concentration is highest.
          </p>
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white px-6 py-5 shadow-soft">
        <div className="flex flex-wrap items-end gap-4">
          <InlineMultiSelect
            label="Customer"
            values={filters.customers}
            options={data.options.customers}
            onChange={(values) => onFiltersChange({ ...filters, customers: values })}
          />
          <InlineMultiSelect
            label="Category"
            values={filters.categories}
            options={data.options.categories}
            onChange={(values) => onFiltersChange({ ...filters, categories: values })}
          />
          <InlineFilterSelect
            label="Detail Window"
            value={String(filters.months)}
            options={[
              { label: "Last 6 months", value: "6" },
              { label: "Last 12 months", value: "12" },
              { label: "Last 24 months", value: "24" },
            ]}
            onChange={(value) => onFiltersChange({ ...filters, months: Number(value) })}
          />
          <Button variant="secondary" onClick={onResetFilters}>
            Reset slicers
          </Button>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <TableCard
          title="How is the selected scope performing over time?"
          subtitle="Monthly sales and attainment trend for the selected customers and categories."
        >
          <DetailScopeTrendChart data={data.detailViews.scopedTrend} />
        </TableCard>
        <TableCard
          title="What is the sales composition in the selected scope?"
          subtitle="Category composition for the selected customers and reporting window, including share of sales."
        >
          <DetailCategoryMixChart data={data.detailViews.categoryMix} />
        </TableCard>
      </section>

      <section className="space-y-4">
        <div>
          <h2 className="text-xl font-semibold tracking-[-0.02em] text-ink">Target Insight</h2>
          <p className="mt-1 text-sm leading-6 text-muted">
            A focused view of the current target shortfall and where leadership should look next.
          </p>
        </div>
      </section>

      <TableCard title="Target Delivery Summary" subtitle="Short observations designed to support the detailed table below.">
        <div className="grid gap-4 lg:grid-cols-2">
          {targetInsights.map((insight) => (
            <div
              key={insight}
              className="rounded-2xl border border-slate-100 bg-slate-50 px-5 py-4 text-sm leading-6 text-ink transition-all duration-200 hover:-translate-y-0.5 hover:border-slate-200 hover:bg-white hover:shadow-[0_6px_18px_rgba(15,23,42,0.08)]"
            >
              {insight}
            </div>
          ))}
        </div>
      </TableCard>

      <TableCard title="Target vs Actual Detail" subtitle="Current-month view of the largest target gaps and the strongest offsetting positions.">
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-slate-100 text-muted">
              <tr>
                <th className="pb-4 pr-6 font-medium">Customer</th>
                <th className="pb-4 pr-6 font-medium">Category</th>
                <th className="pb-4 pr-6 font-medium">Actual Sales</th>
                <th className="pb-4 pr-6 font-medium">Target Sales</th>
                <th className="pb-4 pr-6 font-medium">Target Attainment</th>
                <th className="pb-4 font-medium">Target Gap</th>
              </tr>
            </thead>
            <tbody>
              {targetTableRows.map((row) => (
                <tr key={`${row.customer}-${row.category}`} className="border-b border-slate-50">
                  <td className="py-4 pr-6 font-medium leading-6 text-ink">{row.customer}</td>
                  <td className="py-4 pr-6 leading-6 text-muted">{row.category}</td>
                  <td className="py-4 pr-6 whitespace-nowrap">{formatCurrency(row.actualSales)}</td>
                  <td className="py-4 pr-6 whitespace-nowrap">{formatCurrency(row.targetSales)}</td>
                  <td className={`py-4 pr-6 whitespace-nowrap font-medium ${row.targetAttainmentPct >= 1 ? "text-stable" : "text-ink"}`}>
                    {formatPercent(row.targetAttainmentPct)}
                  </td>
                  <td className={`py-4 whitespace-nowrap font-medium ${row.targetGap < 0 ? "text-critical" : "text-stable"}`}>
                    {row.targetGap > 0 ? "+" : ""}
                    {formatCurrency(row.targetGap)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </TableCard>
    </>
  );
}

function buildExecutiveHeadline(data: DashboardData) {
  const latestMonth = data.monthlyTrend[data.monthlyTrend.length - 1];
  const ytdTargetValue = data.monthlyTrend.reduce((sum, row) => sum + row.currentYearTarget, 0);
  const underTargetMonths = data.monthlyTrend.filter((row) => row.currentYearSales < row.currentYearTarget).length;
  const currentMonthAchievement =
    latestMonth && latestMonth.currentYearTarget > 0 ? latestMonth.currentYearSales / latestMonth.currentYearTarget : 0;
  const ytdAchievement = ytdTargetValue > 0 ? data.kpis.ytdSales / ytdTargetValue : 0;
  const summary = buildExecutiveSummaryContext(data, {
    currentMonthAchievement,
    underTargetMonths,
    ytdAchievement,
  });
  const targetStatus = data.kpis.targetAchievementPct >= 1 ? "Target Beat" : "Target Miss";

  if (summary.topCategoryName && summary.topCustomerName) {
    return `${targetStatus}: ${formatPercent(data.kpis.targetAchievementPct - 1)} vs plan, driven by ${summary.topCategoryName} and ${summary.topCustomerName}.`;
  }

  return `${targetStatus}: ${formatPercent(data.kpis.targetAchievementPct - 1)} versus plan, with performance concentrated in a limited number of customer and category positions.`;
}

function buildTargetInsights(targetRows: DashboardData["detailViews"]["targetInsight"]) {
  const negativeRows = targetRows.filter((row) => row.targetGap < 0);
  const biggestShortfall = [...negativeRows].sort((a, b) => a.targetGap - b.targetGap)[0];
  const categoryGap = negativeRows.reduce<Record<string, number>>((acc, row) => {
    acc[row.category] = (acc[row.category] ?? 0) + Math.abs(row.targetGap);
    return acc;
  }, {});
  const customerGap = negativeRows.reduce<Record<string, number>>((acc, row) => {
    acc[row.customer] = (acc[row.customer] ?? 0) + Math.abs(row.targetGap);
    return acc;
  }, {});

  const topCategories = Object.entries(categoryGap)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 2)
    .map(([category]) => category);
  const topCustomer = Object.entries(customerGap).sort((a, b) => b[1] - a[1])[0]?.[0];
  const topCustomerCount = negativeRows.filter((row) => row.customer === topCustomer).length;
  const positiveRows = targetRows.filter((row) => row.targetGap > 0);

  const insights = [];
  if (biggestShortfall) {
    insights.push(`Largest target shortfall is in ${biggestShortfall.category} for ${biggestShortfall.customer}.`);
  }
  if (topCategories.length > 0) {
    insights.push(`${topCategories.join(" and ")} drive most of the current under-target result.`);
  }
  if (topCustomer) {
    insights.push(`${topCustomer} accounts for ${topCustomerCount} of the largest current target gaps.`);
  }
  if (positiveRows.length === 0) {
    insights.push("No major over-target category is currently offsetting the shortfall.");
  } else {
    const strongestPositive = [...positiveRows].sort((a, b) => b.targetGap - a.targetGap)[0];
    if (strongestPositive) {
      insights.push(`${strongestPositive.category} for ${strongestPositive.customer} is the strongest over-target position in the current month.`);
    }
  }

  if (insights.length === 0) {
    insights.push("The selected scope is broadly on plan, with no material target gap currently visible.");
  }

  return insights.slice(0, 4);
}

function buildBalancedTargetRows(targetRows: DashboardData["detailViews"]["targetInsight"]) {
  const negatives = [...targetRows]
    .filter((row) => row.targetGap < 0)
    .sort((a, b) => a.targetGap - b.targetGap);
  const positives = [...targetRows]
    .filter((row) => row.targetGap > 0)
    .sort((a, b) => b.targetGap - a.targetGap);

  if (positives.length === 0) {
    return negatives.slice(0, 10);
  }

  if (negatives.length === 0) {
    return positives.slice(0, 10);
  }

  const negativeCount = Math.min(Math.max(4, Math.ceil(targetRows.length * 0.6)), 6, negatives.length);
  const positiveCount = Math.min(10 - negativeCount, positives.length);
  const balancedRows = [...negatives.slice(0, negativeCount), ...positives.slice(0, positiveCount)];

  return balancedRows.sort((a, b) => Math.abs(b.targetGap) - Math.abs(a.targetGap));
}

function InlineFilterSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: string[] | Array<{ label: string; value: string }>;
  onChange: (value: string) => void;
}) {
  return (
    <label className="min-w-[180px] space-y-2">
      <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">{label}</div>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-11 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm text-ink outline-none"
      >
        {options.map((option) => {
          if (typeof option === "string") {
            return (
              <option key={option} value={option}>
                {option}
              </option>
            );
          }
          return (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          );
        })}
      </select>
    </label>
  );
}

function InlineMultiSelect({
  label,
  values,
  options,
  onChange,
}: {
  label: string;
  values: string[];
  options: string[];
  onChange: (values: string[]) => void;
}) {
  const summary = values.length === 0 ? `All ${label.toLowerCase()}s` : values.length === 1 ? values[0] : `${values.length} selected`;

  return (
    <div className="min-w-[220px] space-y-2">
      <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">{label}</div>
      <details className="group relative">
        <summary className="flex h-11 cursor-pointer list-none items-center justify-between rounded-xl border border-slate-200 bg-white px-4 text-sm text-ink">
          <span className="truncate">{summary}</span>
          <span className="ml-3 text-muted">▾</span>
        </summary>
        <div className="absolute z-20 mt-2 max-h-72 w-full overflow-auto rounded-2xl border border-slate-200 bg-white p-3 shadow-soft">
          <button
            type="button"
            className="mb-2 text-xs font-medium text-slateblue"
            onClick={() => onChange([])}
          >
            Select all
          </button>
          <div className="space-y-2">
            {options.map((option) => {
              const checked = values.includes(option);
              return (
                <label key={option} className="flex items-center gap-3 rounded-xl px-2 py-2 text-sm hover:bg-slate-50">
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={(event) => {
                      if (event.target.checked) {
                        onChange([...values, option]);
                      } else {
                        onChange(values.filter((value) => value !== option));
                      }
                    }}
                    className="h-4 w-4 rounded border-slate-300"
                  />
                  <span className="truncate">{option}</span>
                </label>
              );
            })}
          </div>
        </div>
      </details>
    </div>
  );
}

function buildExecutiveSummaryContext(
  data: DashboardData,
  metrics: { currentMonthAchievement: number; underTargetMonths: number; ytdAchievement: number },
) {
  const negativeRows = data.targetInsight.filter((row) => row.targetGap < 0);
  const categoryGap = negativeRows.reduce<Record<string, { gap: number; actual: number; target: number }>>((acc, row) => {
    acc[row.category] = acc[row.category] ?? { gap: 0, actual: 0, target: 0 };
    acc[row.category].gap += row.targetGap;
    acc[row.category].actual += row.actualSales;
    acc[row.category].target += row.targetSales;
    return acc;
  }, {});
  const customerGap = negativeRows.reduce<Record<string, { gap: number; actual: number; target: number }>>((acc, row) => {
    acc[row.customer] = acc[row.customer] ?? { gap: 0, actual: 0, target: 0 };
    acc[row.customer].gap += row.targetGap;
    acc[row.customer].actual += row.actualSales;
    acc[row.customer].target += row.targetSales;
    return acc;
  }, {});

  const topCategory = Object.entries(categoryGap).sort((a, b) => a[1].gap - b[1].gap)[0];
  const topCustomer = Object.entries(customerGap).sort((a, b) => a[1].gap - b[1].gap)[0];
  const targetStatusTone: "green" | "amber" | "red" =
    data.kpis.targetAchievementPct > 1
      ? "green"
      : data.kpis.targetAchievementPct >= 0.95
        ? "amber"
        : "red";
  const targetStatusLabel =
    data.kpis.targetAchievementPct > 1
      ? "Ahead of plan"
      : data.kpis.targetAchievementPct >= 0.95
        ? "Slightly below plan"
        : "Below plan";

  const topCategoryGap = topCategory?.[1];
  const topCustomerGap = topCustomer?.[1];
  const topCategoryPct = topCategoryGap && topCategoryGap.target > 0 ? topCategoryGap.actual / topCategoryGap.target - 1 : 0;
  const topCustomerPct = topCustomerGap && topCustomerGap.target > 0 ? topCustomerGap.actual / topCustomerGap.target - 1 : 0;

  return {
    targetStatusTone,
    targetStatusLabel,
    targetStatusNote:
      data.kpis.targetAchievementPct > 1
        ? "Performance is modestly ahead of the current plan."
        : data.kpis.targetAchievementPct >= 0.95
          ? "Performance is close to plan, but still slightly under."
          : "Performance is materially under the current plan.",
    topCategoryName: topCategory?.[0] ?? "N/A",
    topCustomerName: topCustomer?.[0] ?? "N/A",
    topCategoryDeltaLabel: topCategoryGap
      ? `${formatCurrency(topCategoryGap.actual)} YTD (${formatPercent(topCategoryPct)} vs Target)`
      : "No material shortfall identified",
    topCustomerDeltaLabel: topCustomerGap
      ? `${formatCurrency(topCustomerGap.actual)} YTD (${formatPercent(topCustomerPct)} vs Target)`
      : "No material shortfall identified",
    topCategoryNote: topCategoryGap ? `${formatCurrency(Math.abs(topCategoryGap.gap))} shortfall versus plan.` : "No category gap currently visible.",
    topCustomerNote: topCustomerGap ? `${formatCurrency(Math.abs(topCustomerGap.gap))} shortfall versus plan.` : "No customer gap currently visible.",
    driverBullets: [
      topCategoryGap && topCategory
        ? `Main Driver: ${topCategory[0]} category shortfall (${formatCurrency(Math.abs(topCategoryGap.gap))}).`
        : "Main Driver: No material category shortfall currently visible.",
      topCustomerGap && topCustomer
        ? `Focus Area: ${topCustomer[0]} is the largest customer underperformance (${formatCurrency(Math.abs(topCustomerGap.gap))} below plan).`
        : "Focus Area: No single customer dominates the shortfall.",
      buildOffsetInsight(data),
    ],
    managementReadThrough:
      topCategoryGap && topCustomerGap
        ? `${topCategory?.[0] ?? "The main category"} and ${topCustomer?.[0] ?? "the largest customer"} explain most of the visible target pressure, while over-performance in selective categories only partially offsets the current miss.`
        : "The current plan pressure is relatively dispersed, with no single customer-category combination fully explaining the result.",
    targetSubmetrics: [
      {
        label: "Current month",
        value: formatPercent(metrics.currentMonthAchievement),
      },
      {
        label: "Months below plan",
        value: `${metrics.underTargetMonths}`,
      },
      {
        label: "YTD delivery",
        value: formatPercent(metrics.ytdAchievement),
      },
    ],
  };
}

function buildOffsetInsight(data: DashboardData) {
  const positiveRows = data.targetInsight.filter((row) => row.targetGap > 0).sort((a, b) => b.targetGap - a.targetGap);
  const bestOffset = positiveRows[0];
  if (!bestOffset) {
    return "Offset: No major over-target category is currently offsetting the shortfall.";
  }
  return `Offset: ${bestOffset.category} category is performing ${formatPercent(bestOffset.targetAttainmentPct - 1)} above plan.`;
}

function VisualProgressCard({
  title,
  value,
  statusLabel,
  statusTone,
  note,
  submetrics,
}: {
  title: string;
  value: number;
  statusLabel: string;
  statusTone: "green" | "amber" | "red";
  note: string;
  submetrics: Array<{ label: string; value: string }>;
}) {
  const clamped = Math.max(0, Math.min(value, 1.1));
  const degrees = clamped * 360;
  const toneClass =
    statusTone === "green" ? "text-stable" : statusTone === "amber" ? "text-watch" : "text-critical";
  const trackClass =
    statusTone === "green" ? "#16A34A" : statusTone === "amber" ? "#F59E0B" : "#DC2626";

  return (
    <div className="rounded-2xl border border-slate-100 bg-slate-50 px-7 py-7 shadow-[0_4px_12px_rgba(0,0,0,0.05)]">
      <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">{title}</div>
      <div className="mt-5 flex items-start gap-5">
        <div
          className="relative grid h-24 w-24 place-items-center rounded-full"
          style={{
            background: `conic-gradient(${trackClass} 0deg ${degrees}deg, #E5E7EB ${degrees}deg 360deg)`,
          }}
        >
          <div className="grid h-16 w-16 place-items-center rounded-full bg-white text-center">
            <div className="text-lg font-semibold tracking-[-0.03em] text-ink">{Math.round(value * 100)}%</div>
          </div>
        </div>
        <div className="min-w-0 flex-1">
          <div className={`text-sm font-semibold ${toneClass}`}>{statusLabel}</div>
          <div className="mt-2 text-[12px] leading-5 text-[#666]">{note}</div>
        </div>
      </div>
      <div className="mt-5 space-y-2">
        {submetrics.map((metric) => (
          <div
            key={metric.label}
            className="rounded-xl border border-slate-100 bg-white px-4 py-3 shadow-[0_2px_8px_rgba(15,23,42,0.03)]"
          >
            <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-muted">{metric.label}</div>
            <div className="mt-1.5 text-[15px] font-semibold text-ink">{metric.value}</div>
            <div className="mt-1 text-[11px] text-[#7A8496]">
              {metric.label === "Current Month"
                ? "Latest month delivery"
                : metric.label === "Months Below Plan"
                  ? "Count of under-plan months"
                  : "Current year attainment"}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ConcentrationCard({
  title,
  value,
  deltaLabel,
  note,
  statusLabel,
}: {
  title: string;
  value: string;
  deltaLabel: string;
  note: string;
  statusLabel: string;
}) {
  return (
    <div className="rounded-2xl border border-slate-100 bg-slate-50 px-7 py-7 shadow-[0_4px_12px_rgba(0,0,0,0.05)]">
      <div className="flex items-center justify-between gap-3">
        <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">{title}</div>
        <div className="inline-flex items-center gap-2 rounded-full bg-watch/10 px-3 py-1 text-[11px] font-semibold text-watch">
          <span className="h-2 w-2 rounded-full bg-watch" />
          {statusLabel}
        </div>
      </div>
      <div className="mt-4 text-xl font-semibold tracking-[-0.03em] text-ink">{value}</div>
      <div className="mt-2 text-[13px] leading-5 text-[#666]">{deltaLabel}</div>
      <div className="mt-3 text-[12px] leading-5 text-[#8A8A8A]">{note}</div>
    </div>
  );
}
