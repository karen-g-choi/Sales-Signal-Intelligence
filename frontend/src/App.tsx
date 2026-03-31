import { RefreshCw, TriangleAlert } from "lucide-react";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { defaultFilters, defaultRules, emptyDataErrorMessage, loadDashboardData } from "@/lib/dashboard-data";
import type { DashboardData, DashboardFilters, NavView, RuleConfig } from "@/lib/types";
import { RiskDetectionPage } from "@/pages/risk-detection";
import { RuleConfigurationPage } from "@/pages/rule-configuration";
import { SalesOverviewPage } from "@/pages/sales-overview";

export default function App() {
  const [activeView, setActiveView] = useState<NavView>("sales-overview");
  const [config, setConfig] = useState<RuleConfig>(defaultRules());
  const [filters, setFilters] = useState<DashboardFilters>(defaultFilters());
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function run() {
      setLoading(true);
      setError(null);

      try {
        const next = await loadDashboardData(config, filters);
        if (!cancelled) {
          setData(next);
        }
      } catch (caughtError) {
        if (!cancelled) {
          setError(emptyDataErrorMessage(caughtError));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    run();

    return () => {
      cancelled = true;
    };
  }, [config, filters, reloadKey]);

  useEffect(() => {
    const handleVisibility = () => {
      if (!document.hidden) {
        setReloadKey((value) => value + 1);
      }
    };

    const handleFocus = () => {
      setReloadKey((value) => value + 1);
    };

    const interval = window.setInterval(() => {
      setReloadKey((value) => value + 1);
    }, 30000);

    document.addEventListener("visibilitychange", handleVisibility);
    window.addEventListener("focus", handleFocus);

    return () => {
      window.clearInterval(interval);
      document.removeEventListener("visibilitychange", handleVisibility);
      window.removeEventListener("focus", handleFocus);
    };
  }, []);

  return (
    <AppShell activeView={activeView} onSelect={setActiveView}>
      <div className="flex items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-white px-6 py-4 shadow-soft">
        <div>
          <div className="flex items-center gap-3">
            <div className="text-sm font-medium uppercase tracking-[0.16em] text-slateblue">
              {activeView === "sales-overview" ? "Executive Summary" : "Dashboard Summary"}
            </div>
            {activeView === "risk-detection" ? <StatusPill data={data} /> : null}
          </div>
          <div className="mt-1 max-w-4xl text-sm leading-6 text-muted">
            {buildBannerSummary(activeView, data)}
          </div>
        </div>
        <div className="flex items-center gap-3">
          {data && loading ? (
            <div className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-2 text-xs font-medium text-slateblue">
              <RefreshCw className="h-3.5 w-3.5 animate-spin" />
              Updating view
            </div>
          ) : null}
          <Button variant="secondary" onClick={() => setReloadKey((value) => value + 1)}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Reload data
          </Button>
        </div>
      </div>

      {!data && loading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState error={error} />
      ) : data ? (
        <>
          {activeView === "sales-overview" ? (
            <SalesOverviewPage
              data={data}
              filters={filters}
              onFiltersChange={setFilters}
              onResetFilters={() => setFilters(defaultFilters())}
            />
          ) : null}
          {activeView === "risk-detection" ? <RiskDetectionPage data={data} /> : null}
          {activeView === "rule-configuration" ? (
            <RuleConfigurationPage config={config} onChange={setConfig} data={data} />
          ) : null}
        </>
      ) : null}
    </AppShell>
  );
}

function StatusPill({ data }: { data: DashboardData | null }) {
  const severity = getRiskStatus(data);
  const style =
    severity === "High"
      ? "bg-critical/10 text-critical"
      : severity === "Moderate"
        ? "bg-watch/10 text-watch"
        : "bg-stable/10 text-stable";

  return (
    <div className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.08em] ${style}`}>
      Risk: {severity}
    </div>
  );
}

function getRiskStatus(data: DashboardData | null) {
  if (!data) return "Moderate";
  const critical = data.riskRows.filter((row) => row.severity === "Critical").length;
  const warning = data.riskRows.filter((row) => row.severity === "Warning").length;
  if (critical > 0) return "High";
  if (warning > 0) return "Moderate";
  return "Low";
}

function buildBannerSummary(activeView: NavView, data: DashboardData | null) {
  if (!data) {
    return "Sales performance is being prepared for review across growth, target delivery, and commercial mix.";
  }

  if (activeView === "sales-overview") {
    const largestGap = data.targetInsight[0];
    const attainment = data.kpis.targetAchievementPct;
    const direction = attainment >= 1 ? "ahead of target" : "slightly below target";
    if (largestGap) {
      return `YTD sales are ${direction}, with the largest shortfall currently concentrated in ${largestGap.category} for ${largestGap.customer}.`;
    }
    return `YTD sales are ${direction}, with performance concentrated in a small number of customer and category positions.`;
  }

  if (activeView === "risk-detection") {
    return "Recent performance signals point to a limited set of customer-category combinations that require closer commercial review.";
  }

  return "Business rules can be adjusted to reflect different reporting contexts without changing the underlying data model.";
}

function LoadingState() {
  return (
    <Card>
      <CardHeader>
        <h2 className="text-xl font-semibold text-ink">Loading dashboard</h2>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-3 text-sm text-muted">
          <RefreshCw className="h-4 w-4 animate-spin" />
          Reading the latest CSV outputs and preparing the business views.
        </div>
      </CardContent>
    </Card>
  );
}

function ErrorState({ error }: { error: string }) {
  return (
    <Card className="border-critical/20">
      <CardHeader>
        <div className="flex items-center gap-3">
          <TriangleAlert className="h-5 w-5 text-critical" />
          <h2 className="text-xl font-semibold text-ink">Unable to load dashboard data</h2>
        </div>
      </CardHeader>
      <CardContent className="text-sm leading-6 text-muted">{error}</CardContent>
    </Card>
  );
}
