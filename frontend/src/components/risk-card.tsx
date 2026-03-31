import { AlertTriangle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { RiskRow } from "@/lib/types";
import { formatCurrency, formatPercent } from "@/lib/utils";

const severityVariant = {
  Normal: "stable",
  Watch: "watch",
  Warning: "warning",
  Critical: "critical",
} as const;

const severityBorder = {
  Normal: "border-l-stable",
  Watch: "border-l-watch",
  Warning: "border-l-warning",
  Critical: "border-l-critical",
} as const;

export function RiskCard({ row }: { row: RiskRow }) {
  return (
    <Card className={`overflow-hidden border-l-[6px] ${severityBorder[row.severity]}`}>
      <CardHeader className="space-y-2 pb-1">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="text-pretty text-[1rem] font-semibold leading-tight tracking-[-0.02em] text-ink">
              {row.customer}
            </div>
            <div className="mt-0.5 text-[13px] leading-5 text-muted">{row.category}</div>
          </div>
          <AlertTriangle className="mt-0.5 h-4.5 w-4.5 shrink-0 text-muted" />
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-2.5">
        <div className="text-[clamp(1.55rem,2vw,2rem)] font-bold leading-none tracking-[-0.04em] text-ink">
          {formatPercent(row.deltaPct)}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={severityVariant[row.severity]}>{row.severity}</Badge>
          <span className="text-[13px] leading-5 text-muted text-pretty">{row.possibleRiskFactor}</span>
        </div>
        <div className="space-y-1.5 border-t border-slate-100 pt-2.5 text-[13px] leading-5 text-muted">
          <div className="flex items-start justify-between gap-4">
            <span>At-risk sales</span>
            <span className="shrink-0 font-semibold text-ink">{formatCurrency(row.atRiskSales)}</span>
          </div>
          <div className="flex items-start justify-between gap-4">
            <span>Target attainment</span>
            <span className="shrink-0 font-semibold text-ink">{formatPercent(row.targetAttainmentPct)}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
