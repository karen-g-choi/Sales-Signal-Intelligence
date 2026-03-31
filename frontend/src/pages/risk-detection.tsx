import type { ReactNode } from "react";
import { CalendarRange, Info, TrendingUp, Zap } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/page-header";
import { RiskCard } from "@/components/risk-card";
import { TableCard } from "@/components/table-card";
import { RiskTrendChart } from "@/components/charts/risk-trend-chart";
import type { DashboardData } from "@/lib/types";
import { formatCurrency, formatPercent, monthLabel } from "@/lib/utils";

const badgeVariant = {
  Normal: "stable",
  Watch: "watch",
  Warning: "warning",
  Critical: "critical",
} as const;

export function RiskDetectionPage({ data }: { data: DashboardData }) {
  const filteredRiskRows = data.riskRows.filter((row) => row.severity !== "Normal");
  const topRiskRows = buildDiverseTopRiskRows(filteredRiskRows, 3);
  const eventInsight = buildEventInsight(data);
  const riskInsight = buildRiskInsight(data);

  return (
    <>
      <PageHeader
        title="Risk & Detection"
        subtitle="A business interpretation view that separates underlying demand from temporary distortion and shows where true performance is deteriorating."
      />

      <section className="grid gap-6 xl:grid-cols-[1.02fr_1.38fr]">
        <div className="space-y-6">
          <TableCard
            title="How to read this page"
            subtitle="A compact view of the logic behind the underlying sales assessment."
          >
            <div className="grid gap-4 md:grid-cols-[1fr_auto_1fr_auto_1fr]">
              <VisualLogicCard
                title="Normal sales"
                subtitle="Underlying baseline"
                visual={<SmoothTrendVisual />}
              />
              <EquationSymbol value="+" />
              <VisualLogicCard
                title="Event-linked sales"
                subtitle="Promotions and spikes"
                visual={<SpikeVisual />}
              />
              <EquationSymbol value="=" />
              <VisualLogicCard
                title="Reported sales"
                subtitle="Topline result"
                visual={<ReportedVisual />}
              />
            </div>
          </TableCard>

          <TableCard
            title="Business logic in plain English"
            subtitle="Defined in business terms before looking at the risk ranking."
          >
            <div className="space-y-5">
              <div className="flex flex-wrap gap-2">
                {["Promotions", "Bulk orders", "Warranty spikes", "Launch bursts", "Structural shifts"].map((item) => (
                  <span
                    key={item}
                    className="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-medium text-slateblue"
                  >
                    {item}
                  </span>
                ))}
              </div>

              <div className="space-y-4 text-sm leading-[1.6] text-[#666]">
                <DefinitionRow
                  term="Normal sales"
                  explanation="Reconstructed baseline demand after smoothing temporary spikes and one-off commercial distortion."
                />
                <DefinitionRow
                  term="Event-linked sales"
                  explanation="Temporary uplift from promotions, bulk orders, warranty actions, and other short-lived commercial events."
                />
                <DefinitionRow
                  term="Gap vs baseline"
                  explanation="The divergence between reported sales and underlying baseline, used to identify sustained weakness."
                />
              </div>
            </div>
          </TableCard>
        </div>

        <TableCard
          title="Normal vs Reported Sales"
          subtitle="This is the key chart: it shows when topline sales are being supported by temporary events rather than underlying demand."
        >
          <div className="mb-5 grid gap-4 md:grid-cols-3">
            <TrendMetric
              label="Underlying baseline"
              value={buildBaselineDirection(data)}
              note="Direction of smoothed underlying demand across the recent monthly view."
            />
            <TrendMetric
              label="Event-linked support"
              value={formatCurrency(data.underlyingTrend.reduce((sum, row) => sum + row.eventLinkedSales, 0))}
              note="Temporary sales uplift currently supporting the topline."
            />
            <TrendMetric
              label="Latest gap"
              value={formatCurrency(Math.abs(data.underlyingTrend.at(-1)?.gapToBaseline ?? 0))}
              note={
                (data.underlyingTrend.at(-1)?.gapToBaseline ?? 0) >= 0
                  ? "Reported sales still sit above the baseline."
                  : "Reported sales have fallen below the baseline."
              }
            />
          </div>
          <RiskTrendChart data={data.underlyingTrend} />
        </TableCard>
      </section>

      <section className="space-y-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-[1.8rem] font-semibold tracking-[-0.03em] text-ink">Context Layer</h2>
            <InfoHint text="This layer explains temporary distortion such as promotions, bulk orders, and structural shifts." />
          </div>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
            Event context helps explain why reported sales moved. This makes the baseline view more credible and prevents
            temporary spikes from being mistaken for lasting commercial strength.
          </p>
        </div>
      </section>

      <section>
        <TableCard
          title="Recent Event & Distortion Timeline"
          subtitle="Promotions, bulk orders, launch periods, and structural shifts shown in sequence so reported spikes can be linked back to business context."
        >
          <div className="mb-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {eventInsight.map((item) => (
              <div key={item.title} className="rounded-2xl border border-slate-100 bg-slate-50 px-5 py-4">
                <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">{item.title}</div>
                <div className="mt-2 text-lg font-semibold tracking-[-0.03em] text-ink">{item.value}</div>
                <div className="mt-2 text-sm leading-6 text-muted">{item.note}</div>
              </div>
            ))}
          </div>

          {data.eventTimeline.length === 0 ? (
            <div className="rounded-2xl border border-slate-100 bg-slate-50 px-5 py-4 text-sm text-muted">
              No event records are available in the recent monthly view.
            </div>
          ) : (
            <div className="max-h-[560px] overflow-y-auto pr-2">
              <div className="relative pl-5">
                <div className="absolute bottom-0 left-[11px] top-2 w-px bg-slate-200" />
                <div className="space-y-3">
                {data.eventTimeline.map((event) => (
                  <div key={`${event.monthStart}-${event.eventType}`} className="relative pl-8">
                    <div className="absolute left-0 top-4 h-5 w-5 rounded-full border-4 border-white bg-slateblue shadow-[0_2px_8px_rgba(31,58,95,0.16)]" />
                    <div className="rounded-2xl border border-slate-100 bg-slate-50 px-5 py-4">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="min-w-0 space-y-0.5">
                          <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">
                            {monthLabel(event.monthStart)}
                          </div>
                          <div className="text-sm font-semibold leading-6 tracking-[-0.01em] text-ink">{event.eventLabel}</div>
                          <div className="text-[13px] leading-5 text-muted">{event.customerScope}</div>
                        </div>
                        <div className="rounded-full bg-white px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.08em] text-slateblue">
                          {event.eventType.replaceAll("_", " ")}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
                </div>
              </div>
            </div>
          )}
        </TableCard>
      </section>

      <section className="space-y-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-[1.8rem] font-semibold tracking-[-0.03em] text-ink">Prioritized Risk</h2>
            <InfoHint text="Risk ranking is based on sustained monthly deviation versus baseline, supported by target and event context." />
          </div>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
            Only after separating baseline demand from temporary distortion do we identify the customer-category combinations
            showing the most meaningful deterioration.
          </p>
        </div>
      </section>

      <TableCard
          title="Risk Summary"
          subtitle="An insight-led summary of where the current deterioration is concentrated."
        >
        <div className="grid gap-4 lg:grid-cols-3">
          {riskInsight.map((item) => (
            <div key={item.title} className="rounded-2xl border border-slate-100 bg-slate-50 px-5 py-4">
              <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">{item.title}</div>
              <div className="mt-2 text-lg font-semibold tracking-[-0.02em] text-ink">{item.value}</div>
              <div className="mt-2 text-sm leading-6 text-muted">{item.note}</div>
            </div>
          ))}
        </div>
      </TableCard>

      <section className="space-y-6">
        <TableCard
          title="Top Priority Cases"
          subtitle="The most material deteriorations after baseline reconstruction and context review."
        >
          <div className="grid gap-4 xl:grid-cols-3">
            {topRiskRows.map((row) => (
              <RiskCard key={`${row.customer}-${row.category}`} row={row} />
            ))}
          </div>
        </TableCard>

        <TableCard
          title="Prioritized Risk Table"
          subtitle="Ranked by sustained deviation, target gap, and business-weighted impact."
        >
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-slate-100 text-muted">
                <tr>
                  <th className="pb-4 pr-6 font-medium">Customer</th>
                  <th className="pb-4 pr-6 font-medium">Category</th>
                  <th className="pb-4 pr-6 font-medium">Trend vs Baseline</th>
                  <th className="pb-4 pr-6 font-medium">Target Gap</th>
                  <th className="pb-4 pr-6 font-medium">Severity</th>
                  <th className="pb-4 font-medium">Possible Cause</th>
                </tr>
              </thead>
              <tbody>
                {filteredRiskRows.slice(0, 12).map((row) => (
                  <tr key={`${row.customer}-${row.category}`} className="border-b border-slate-50">
                    <td className="py-4 pr-6 font-medium leading-6 text-ink">{row.customer}</td>
                    <td className="py-4 pr-6 leading-6 text-muted">{row.category}</td>
                    <td className="py-4 pr-6">
                      <div className="font-medium text-ink">{formatPercent(row.deltaPct)}</div>
                      <div className="mt-1 text-xs leading-5 text-muted">
                        {row.deltaPct <= -0.12 ? "Clear multi-period decline versus baseline" : "Persistent softness across recent periods"}
                      </div>
                    </td>
                    <td className="py-4 pr-6">
                      <div className={`font-medium ${row.targetGap < 0 ? "text-critical" : "text-ink"}`}>
                        {formatCurrency(row.targetGap)}
                      </div>
                      <div className="mt-1 text-xs leading-5 text-muted">{formatPercent(row.targetAttainmentPct)} attainment</div>
                    </td>
                    <td className="py-4 pr-6">
                      <Badge variant={badgeVariant[row.severity]}>{row.severity}</Badge>
                    </td>
                    <td className="py-4 leading-6 text-muted">{row.possibleRiskFactor}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </TableCard>
      </section>
    </>
  );
}

function buildDiverseTopRiskRows(rows: DashboardData["riskRows"], limit: number) {
  const selected: DashboardData["riskRows"] = [];
  const seenCauses = new Set<string>();
  const diversifiedPool = [...rows].sort((a, b) => {
    if (b.severityRank !== a.severityRank) return b.severityRank - a.severityRank;
    if (a.possibleRiskFactor !== b.possibleRiskFactor) return a.possibleRiskFactor.localeCompare(b.possibleRiskFactor);
    return b.weightedImpact - a.weightedImpact;
  });

  for (const row of diversifiedPool) {
    if (selected.length >= limit) break;
    if (!seenCauses.has(row.possibleRiskFactor)) {
      selected.push(row);
      seenCauses.add(row.possibleRiskFactor);
    }
  }

  if (selected.length < limit) {
    for (const row of diversifiedPool) {
      if (selected.length >= limit) break;
      if (!selected.some((item) => item.customer === row.customer && item.category === row.category)) {
        selected.push(row);
      }
    }
  }

  return selected;
}

function VisualLogicCard({ title, subtitle, visual }: { title: string; subtitle: string; visual: ReactNode }) {
  return (
    <div className="rounded-2xl border border-slate-100 bg-slate-50 px-6 py-6">
      <div className="flex h-16 items-center justify-center rounded-2xl bg-white">{visual}</div>
      <div className="mt-4 text-base font-semibold tracking-[-0.02em] text-ink">{title}</div>
      <div className="mt-1 text-sm leading-6 text-[#666]">{subtitle}</div>
    </div>
  );
}

function TrendMetric({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <div className="rounded-2xl border border-slate-100 bg-slate-50 px-6 py-6">
      <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">{label}</div>
      <div className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-ink">{value}</div>
      <div className="mt-2 text-sm leading-[1.6] text-[#666]">{note}</div>
    </div>
  );
}

function EquationSymbol({ value }: { value: string }) {
  return (
    <div className="flex items-center justify-center text-3xl font-semibold tracking-[-0.03em] text-slateblue">
      {value}
    </div>
  );
}

function DefinitionRow({ term, explanation }: { term: string; explanation: string }) {
  return (
    <div className="grid gap-2 md:grid-cols-[160px_1fr]">
      <div className="text-sm font-semibold text-ink">{term}</div>
      <div className="text-sm leading-[1.6] text-[#666]">{explanation}</div>
    </div>
  );
}

function SmoothTrendVisual() {
  return (
    <svg viewBox="0 0 120 44" className="h-10 w-24 text-navy" aria-hidden="true">
      <path d="M4 30 C 24 26, 36 18, 54 20 S 86 24, 116 12" fill="none" stroke="currentColor" strokeWidth="3.5" strokeLinecap="round" />
    </svg>
  );
}

function SpikeVisual() {
  return (
    <svg viewBox="0 0 120 44" className="h-10 w-24 text-[#C97A52]" aria-hidden="true">
      <path d="M4 30 H40 L55 10 L70 32 H116" fill="none" stroke="currentColor" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ReportedVisual() {
  return (
    <div className="flex items-center justify-center gap-2 text-navy">
      <TrendingUp className="h-7 w-7" />
      <div className="text-2xl font-semibold">Σ</div>
    </div>
  );
}

function InfoHint({ text }: { text: string }) {
  return (
    <span title={text} className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-slate-100 text-slateblue">
      <Info className="h-3.5 w-3.5" />
    </span>
  );
}

function buildBaselineDirection(data: DashboardData) {
  if (data.underlyingTrend.length < 6) return "Stable";
  const firstHalf = data.underlyingTrend.slice(0, Math.floor(data.underlyingTrend.length / 2));
  const secondHalf = data.underlyingTrend.slice(Math.floor(data.underlyingTrend.length / 2));
  const firstAverage = firstHalf.reduce((sum, row) => sum + row.baselineSales, 0) / firstHalf.length;
  const secondAverage = secondHalf.reduce((sum, row) => sum + row.baselineSales, 0) / secondHalf.length;
  if (secondAverage < firstAverage * 0.97) return "Softening";
  if (secondAverage > firstAverage * 1.03) return "Improving";
  return "Stable";
}

function buildEventInsight(data: DashboardData) {
  const totalEventSupport = data.underlyingTrend.reduce((sum, row) => sum + row.eventLinkedSales, 0);
  const strongestEventMonth = [...data.underlyingTrend].sort((a, b) => b.eventLinkedSales - a.eventLinkedSales)[0];
  const latestGap = data.underlyingTrend.at(-1)?.gapToBaseline ?? 0;

  return [
    {
      title: "Event-linked support",
      value: formatCurrency(totalEventSupport),
      note: "Temporary sales uplift across the recent monthly view that supported topline performance.",
    },
    {
      title: "Largest distortion month",
      value: strongestEventMonth ? monthLabel(strongestEventMonth.monthStart) : "None",
      note: strongestEventMonth
        ? `${formatCurrency(strongestEventMonth.eventLinkedSales)} of event-linked sales landed in the strongest distortion month.`
        : "No notable distortion is visible in the recent period.",
    },
    {
      title: "Latest reported gap",
      value: formatCurrency(Math.abs(latestGap)),
      note:
        latestGap >= 0
          ? "Reported sales still sit above the baseline, suggesting some temporary support remains."
          : "Reported sales have slipped below the baseline, indicating weaker underlying demand.",
    },
    {
      title: "Recent context",
      value: `${data.eventTimeline.length} event months`,
      note: "The timeline highlights where promotions, bulk orders, or structural shifts overlap with sales movement.",
    },
  ];
}

function buildRiskInsight(data: DashboardData) {
  const filteredRiskRows = data.riskRows.filter((row) => row.severity !== "Normal");
  const topThree = filteredRiskRows.slice(0, 3);
  const topCustomers = Array.from(new Set(topThree.map((row) => row.customer)));
  const topCauses = Array.from(new Set(topThree.map((row) => row.possibleRiskFactor)));
  const structuralCount = filteredRiskRows.filter((row) => row.possibleRiskFactor === "Structural shift / New normal").length;

  return [
    {
      title: "Risk concentration",
      value: topCustomers.length > 0 ? topCustomers.join(", ") : "No active risks",
      note: "Top priority issues are concentrated in a small number of customer positions.",
    },
    {
      title: "Primary causes",
      value: topCauses.length > 0 ? topCauses.join(" / ") : "No active risks",
      note: "Causes are assigned after checking event distortion and multi-period baseline performance.",
    },
    {
      title: "Structural share",
      value: `${structuralCount}`,
      note: structuralCount > 0
        ? "A meaningful part of the current risk view is driven by structural decline rather than temporary event noise."
        : "Current risks are not dominated by structural shift signals.",
    },
  ];
}
