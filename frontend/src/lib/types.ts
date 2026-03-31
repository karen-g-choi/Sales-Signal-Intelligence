export type NavView = "sales-overview" | "risk-detection" | "rule-configuration";

export type Severity = "Normal" | "Watch" | "Warning" | "Critical";

export interface RuleConfig {
  warningDropPct: number;
  criticalDropPct: number;
  minimumDuration: number;
  consistencyThreshold: number;
  highImpactThreshold: number;
  detectionBasis: "monthly" | "weekly";
  largeCustomerWeight: number;
  keyCategoryWeight: number;
}

export interface DashboardFilters {
  customers: string[];
  categories: string[];
  months: number;
}

export interface OrderRow {
  customer_id: string;
  product_id: string;
  quantity: number;
  sales_amount: number;
  event_id?: string;
  event_type?: string;
  event_layer: number;
  order_date: string;
}

export interface CustomerRow {
  customer_id: string;
  customer_name: string;
  customer_size: string;
}

export interface ProductRow {
  product_id: string;
  product_name: string;
  category_l1: string;
}

export interface TargetRow {
  month_start: string;
  customer_id: string;
  customer_name: string;
  category_l1: string;
  target_sales_amount: number;
  target_quantity: number;
}

export interface EventRow {
  event_id: string;
  event_type: string;
  event_layer: number;
  customer_id: string;
  product_id: string;
  start_date: string;
  end_date: string;
  description: string;
  business_reason: string;
}

export interface MonthlySalesRow {
  customerId: string;
  customerName: string;
  customerSize: string;
  category: string;
  monthStart: string;
  year: number;
  month: number;
  totalSales: number;
  totalQuantity: number;
  eventLinkedSales: number;
  targetSalesAmount: number;
  targetQuantity: number;
  reconstructedBaselineSales: number;
  salesDelta: number;
  salesDeltaPct: number;
  priorYearSales: number;
  yoyTrendPct: number;
  targetAttainmentPct: number;
}

export interface RiskRow {
  customer: string;
  category: string;
  recentSales: number;
  baselineSales: number;
  deltaPct: number;
  targetAttainmentPct: number;
  targetGap: number;
  yoyTrendPct: number;
  atRiskSales: number;
  weightedImpact: number;
  severity: Severity;
  possibleRiskFactor: string;
  customerSize: string;
  severityRank: number;
}

export interface DashboardData {
  monthlySales: MonthlySalesRow[];
  monthlyTrend: Array<{
    monthStart: string;
    currentYearSales: number;
    currentYearTarget: number;
    previousYearSales: number;
  }>;
  salesMix: Array<{
    label: string;
    value: number;
  }>;
  customerRanking: Array<{
    customer: string;
    sales: number;
  }>;
  categoryRanking: Array<{
    category: string;
    sales: number;
    growthPct: number;
  }>;
  targetInsight: Array<{
    customer: string;
    category: string;
    actualSales: number;
    targetSales: number;
    targetAttainmentPct: number;
    targetGap: number;
  }>;
  underlyingTrend: Array<{
    monthStart: string;
    reportedSales: number;
    baselineSales: number;
    eventLinkedSales: number;
    gapToBaseline: number;
  }>;
  eventTimeline: Array<{
    monthStart: string;
    eventType: string;
    eventLabel: string;
    eventCount: number;
    customerScope: string;
  }>;
  riskRows: RiskRow[];
  options: {
    customers: string[];
    categories: string[];
  };
  detailViews: {
    scopedTrend: Array<{
      monthStart: string;
      sales: number;
      target: number;
      attainmentPct: number;
    }>;
    categoryMix: Array<{
      label: string;
      value: number;
      sharePct: number;
    }>;
    targetInsight: Array<{
      customer: string;
      category: string;
      actualSales: number;
      targetSales: number;
      targetAttainmentPct: number;
      targetGap: number;
    }>;
  };
  kpis: {
    ytdSales: number;
    currentMonthSales: number;
    currentMonthQuantity: number;
    ytdGrowthPct: number;
    targetAchievementPct: number;
  };
}
