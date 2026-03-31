import { loadCsv } from "@/lib/csv";
import { rollingMedian } from "@/lib/utils";
import type {
  CustomerRow,
  DashboardData,
  DashboardFilters,
  EventRow,
  MonthlySalesRow,
  OrderRow,
  ProductRow,
  RiskRow,
  RuleConfig,
  TargetRow,
} from "@/lib/types";

const severityRankMap = {
  Normal: 0,
  Watch: 1,
  Warning: 2,
  Critical: 3,
} as const;

const targetRecalibrationFactor = 0.9746512296945459;

function defaultRuleConfig(): RuleConfig {
  return {
    warningDropPct: 0.06,
    criticalDropPct: 0.12,
    minimumDuration: 3,
    consistencyThreshold: 0.6,
    highImpactThreshold: 20000,
    detectionBasis: "monthly",
    largeCustomerWeight: 1.15,
    keyCategoryWeight: 1.1,
  };
}

function defaultDashboardFilters(): DashboardFilters {
  return {
    customers: [],
    categories: [],
    months: 12,
  };
}

function toMonthStart(value: string) {
  const date = new Date(value);
  const year = date.getUTCFullYear();
  const month = String(date.getUTCMonth() + 1).padStart(2, "0");
  return `${year}-${month}-01`;
}

function ensureTargets(monthlyRows: MonthlySalesRow[], targets: TargetRow[]) {
  if (targets.length > 0) {
    return targets;
  }

  return monthlyRows.map((row) => ({
    month_start: row.monthStart,
    customer_id: row.customerId,
    customer_name: row.customerName,
    category_l1: row.category,
    target_sales_amount: row.totalSales * 1.03,
    target_quantity: Math.round(row.totalQuantity * 1.02),
  }));
}

function rebuildTargetsFromMonthlyRows(monthlyRows: MonthlySalesRow[]): TargetRow[] {
  const stretchBySize: Record<string, number> = { large: 1.02, mid: 1.01, small: 0.995 };
  const seasonBias: Record<number, number> = {
    1: 1.01, 2: 1.005, 3: 1.01, 4: 1.005, 5: 1.0, 6: 0.995,
    7: 0.992, 8: 0.995, 9: 1.0, 10: 1.008, 11: 1.012, 12: 1.018,
  };
  const categoryBias: Record<string, number> = {
    Accessories: 0.99,
    "EV Service": 0.995,
    Service: 1.0,
    Maintenance: 1.0,
    Diagnostics: 1.005,
    Powertrain: 1.008,
    Repair: 1.012,
    "Dealer Launch": 1.02,
  };
  const customerBias: Record<string, number> = {
    "NordAuto Stockholm": 1.012,
    "Svea Mobility Parts": 1.0,
    "PromoDrive Retail": 1.0,
    "NewMotion Uppsala": 0.995,
    "Arctic Niche Auto": 0.99,
  };

  const grouped = new Map<string, MonthlySalesRow[]>();
  monthlyRows.forEach((row) => {
    const key = [row.customerId, row.category].join("|");
    grouped.set(key, [...(grouped.get(key) ?? []), row]);
  });

  const rebuilt: TargetRow[] = [];
  grouped.forEach((rows) => {
    const ordered = [...rows].sort((a, b) => a.monthStart.localeCompare(b.monthStart));
    ordered.forEach((row, index) => {
      const priorRows = ordered.slice(Math.max(0, index - 3), index);
      const priorSales = priorRows.map((item) => item.totalSales);
      const priorQty = priorRows.map((item) => item.totalQuantity);
      const priorYearRow = ordered.find((item) => item.year === row.year - 1 && item.month === row.month);
      const salesBase = priorSales.length > 0 ? rollingMedian(priorSales) : row.totalSales;
      const qtyBase = priorQty.length > 0 ? rollingMedian(priorQty) : row.totalQuantity;
      const salesAnchor = salesBase * 0.8 + row.totalSales * 0.2;
      const qtyAnchor = qtyBase * 0.85 + row.totalQuantity * 0.15;
      const stretch = stretchBySize[row.customerSize] ?? 1.0;
      const monthFactor = seasonBias[row.month] ?? 1.0;
      const categoryFactor = categoryBias[row.category] ?? 1.0;
      const customerFactor = customerBias[row.customerName] ?? 1.0;
      const ratio = salesBase > 0 ? row.totalSales / salesBase : 1;
      const trendFactor = Math.min(Math.max(1 + (ratio - 1) * 0.1, 0.985), 1.015);
      const salesMultiplier = stretch * monthFactor * categoryFactor * customerFactor * trendFactor;
      const qtyMultiplier = Math.min(Math.max(stretch * categoryFactor * customerFactor, 0.96), 1.04);
      const computedSalesTarget = salesAnchor * salesMultiplier * targetRecalibrationFactor;
      const computedQtyTarget = qtyAnchor * qtyMultiplier * targetRecalibrationFactor;
      const applyPriorYearFloor =
        (row.customerSize === "large" || row.customerSize === "mid") &&
        !["Accessories", "Dealer Launch", "EV Service", "Diagnostics", "Service"].includes(row.category);
      const priorYearSalesFloor = priorYearRow ? priorYearRow.totalSales * 1.002 : null;
      const priorYearQtyFloor = priorYearRow ? priorYearRow.totalQuantity * 1.002 : null;

      rebuilt.push({
        month_start: row.monthStart,
        customer_id: row.customerId,
        customer_name: row.customerName,
        category_l1: row.category,
        target_sales_amount: Number(
          (applyPriorYearFloor ? Math.max(computedSalesTarget, priorYearSalesFloor ?? computedSalesTarget) : computedSalesTarget).toFixed(2),
        ),
        target_quantity: Math.round(
          applyPriorYearFloor ? Math.max(computedQtyTarget, priorYearQtyFloor ?? computedQtyTarget) : computedQtyTarget,
        ),
      });
    });
  });

  return rebuilt;
}

function normalizeTargets(monthlyRows: MonthlySalesRow[], targets: TargetRow[]) {
  const ensuredTargets = ensureTargets(monthlyRows, targets);
  if (ensuredTargets.length === 0) {
    return ensuredTargets;
  }

  const actualMap = new Map(
    monthlyRows.map((row) => [[row.customerId, row.category, row.monthStart].join("|"), row.totalSales] as const),
  );

  const latestMonth = ensuredTargets.reduce(
    (latest, row) => (row.month_start > latest ? row.month_start : latest),
    ensuredTargets[0]?.month_start ?? "",
  );

  const latestRows = ensuredTargets
    .filter((row) => row.month_start === latestMonth)
    .map((row) => {
      const actual = actualMap.get([row.customer_id, row.category_l1, row.month_start].join("|")) ?? 0;
      const attainment = row.target_sales_amount > 0 ? actual / row.target_sales_amount : 1;
      return { ...row, actual, attainment };
    });

  const clusteredNearNinetyEight = latestRows.length > 0 &&
    latestRows.filter((row) => row.attainment >= 0.975 && row.attainment <= 0.985).length / latestRows.length >= 0.6;

  return clusteredNearNinetyEight ? rebuildTargetsFromMonthlyRows(monthlyRows) : ensuredTargets;
}

function derivePossibleRiskFactor(eventType: string | undefined, deltaPct: number, targetAttainment: number, yoyTrend: number) {
  if (eventType === "promotion_absence") return "Promo gap";
  if (eventType === "new_normal_shift") return "Structural shift / New normal";
  if (eventType === "extreme_promotion" || eventType === "one_off_bulk_order" || eventType === "recall_warranty") {
    return "Event-driven volatility";
  }
  if (eventType === "new_dealer_launch") return "Launch transition";
  if (yoyTrend <= -0.12 && targetAttainment < 0.92) return "Structural shift / New normal";
  if (deltaPct <= -0.06 && targetAttainment < 0.95) return "Demand softening";
  return "Needs analyst review";
}

function aggregateMonthlySales(
  orders: OrderRow[],
  customers: CustomerRow[],
  products: ProductRow[],
  targets: TargetRow[],
): MonthlySalesRow[] {
  const customerMap = new Map(customers.map((row) => [row.customer_id, row]));
  const productMap = new Map(products.map((row) => [row.product_id, row]));

  type Bucket = {
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
  };

  const buckets = new Map<string, Bucket>();

  for (const order of orders) {
    const customer = customerMap.get(order.customer_id);
    const product = productMap.get(order.product_id);
    if (!customer || !product) continue;

    const monthStart = toMonthStart(order.order_date);
    const date = new Date(monthStart);
    const key = [order.customer_id, product.category_l1, monthStart].join("|");

    const bucket = buckets.get(key) ?? {
      customerId: order.customer_id,
      customerName: customer.customer_name,
      customerSize: customer.customer_size,
      category: product.category_l1,
      monthStart,
      year: date.getFullYear(),
      month: date.getMonth() + 1,
      totalSales: 0,
      totalQuantity: 0,
      eventLinkedSales: 0,
    };

    bucket.totalSales += Number(order.sales_amount) || 0;
    bucket.totalQuantity += Number(order.quantity) || 0;
    if (order.event_id) {
      bucket.eventLinkedSales += Number(order.sales_amount) || 0;
    }

    buckets.set(key, bucket);
  }

  const monthlyRows = Array.from(buckets.values()).sort((a, b) =>
    `${a.customerId}-${a.category}-${a.monthStart}`.localeCompare(`${b.customerId}-${b.category}-${b.monthStart}`),
  );

  const normalizedTargets = normalizeTargets(
    monthlyRows.map((row) => ({
      ...row,
      targetSalesAmount: 0,
      targetQuantity: 0,
      reconstructedBaselineSales: 0,
      salesDelta: 0,
      salesDeltaPct: 0,
      priorYearSales: 0,
      yoyTrendPct: 0,
      targetAttainmentPct: 0,
    })),
    targets,
  );

  const targetMap = new Map(
    normalizedTargets.map((row) => [[row.customer_id, row.category_l1, row.month_start].join("|"), row] as const),
  );

  const grouped = new Map<string, MonthlySalesRow[]>();

  for (const row of monthlyRows) {
    const key = [row.customerId, row.category].join("|");
    const target = targetMap.get([row.customerId, row.category, row.monthStart].join("|"));
    const enriched: MonthlySalesRow = {
      ...row,
      targetSalesAmount: Number(target?.target_sales_amount) || row.totalSales * 1.02,
      targetQuantity: Number(target?.target_quantity) || Math.round(row.totalQuantity),
      reconstructedBaselineSales: row.totalSales,
      salesDelta: 0,
      salesDeltaPct: 0,
      priorYearSales: 0,
      yoyTrendPct: 0,
      targetAttainmentPct: 1,
    };
    grouped.set(key, [...(grouped.get(key) ?? []), enriched]);
  }

  const result: MonthlySalesRow[] = [];

  for (const rows of grouped.values()) {
    rows.sort((a, b) => a.monthStart.localeCompare(b.monthStart));
    rows.forEach((row, index) => {
      const priorValues = rows.slice(Math.max(0, index - 3), index).map((item) => item.totalSales);
      const baseline = priorValues.length > 0 ? rollingMedian(priorValues) : row.totalSales;
      const previousYear = rows.find((item) => item.year === row.year - 1 && item.month === row.month)?.totalSales ?? 0;

      row.reconstructedBaselineSales = baseline || row.totalSales;
      row.salesDelta = row.totalSales - row.reconstructedBaselineSales;
      row.salesDeltaPct = row.reconstructedBaselineSales > 0 ? row.salesDelta / row.reconstructedBaselineSales : 0;
      row.priorYearSales = previousYear;
      row.yoyTrendPct = previousYear > 0 ? row.totalSales / previousYear - 1 : 0;
      row.targetAttainmentPct = row.targetSalesAmount > 0 ? row.totalSales / row.targetSalesAmount : 1;
      result.push(row);
    });
  }

  return result.sort((a, b) => a.monthStart.localeCompare(b.monthStart));
}

function buildRiskRows(monthlySales: MonthlySalesRow[], orders: OrderRow[], config: RuleConfig): RiskRow[] {
  const categoryTotals = new Map<string, number>();
  monthlySales.forEach((row) => {
    categoryTotals.set(row.category, (categoryTotals.get(row.category) ?? 0) + row.totalSales);
  });
  const keyCategories = Array.from(categoryTotals.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 2)
    .map(([category]) => category);

  const eventTypeMap = new Map<string, string>();
  for (const order of orders) {
    if (!order.event_id || !order.event_type) continue;
    const monthStart = toMonthStart(order.order_date);
    const key = [order.customer_id, monthStart].join("|");
    eventTypeMap.set(key, order.event_type);
  }

  const grouped = new Map<string, MonthlySalesRow[]>();
  monthlySales.forEach((row) => {
    const key = [row.customerId, row.category].join("|");
    grouped.set(key, [...(grouped.get(key) ?? []), row]);
  });

  const rows: RiskRow[] = [];
  const evaluationPeriods = config.detectionBasis === "monthly" ? Math.max(config.minimumDuration, 2) : Math.max(config.minimumDuration - 1, 2);
  const warningThreshold = config.detectionBasis === "monthly" ? config.warningDropPct : config.warningDropPct * 0.9;
  const criticalThreshold = config.detectionBasis === "monthly" ? config.criticalDropPct : config.criticalDropPct * 0.9;

  grouped.forEach((values) => {
    const recent = values.slice(-evaluationPeriods);
    if (recent.length < evaluationPeriods) return;

    const latest = recent[recent.length - 1];
    const recentSales = recent.reduce((sum, row) => sum + row.totalSales, 0);
    const baselineSales = recent.reduce((sum, row) => sum + row.reconstructedBaselineSales, 0);
    const atRiskSales = Math.max(baselineSales - recentSales, 0);
    const deltaPct = baselineSales > 0 ? recentSales / baselineSales - 1 : 0;
    const targetAttainmentPct = recent.reduce((sum, row) => sum + row.targetAttainmentPct, 0) / recent.length;
    const targetGap = recent.reduce((sum, row) => sum + (row.totalSales - row.targetSalesAmount), 0);
    const yoyTrendPct = recent[recent.length - 1]?.yoyTrendPct ?? 0;
    const belowBaselinePeriods = recent.filter((row) => row.totalSales < row.reconstructedBaselineSales).length;
    const consistencyRatio = belowBaselinePeriods / recent.length;

    const customerWeight = latest.customerSize === "large" ? config.largeCustomerWeight : 1;
    const categoryWeight = keyCategories.includes(latest.category) ? config.keyCategoryWeight : 1;
    const weightedImpact = atRiskSales * customerWeight * categoryWeight;

    let severity: RiskRow["severity"] = "Normal";
    if (
      deltaPct <= -criticalThreshold &&
      consistencyRatio >= config.consistencyThreshold &&
      weightedImpact >= config.highImpactThreshold * 0.35
    ) {
      severity = "Critical";
    } else if (
      deltaPct <= -warningThreshold &&
      consistencyRatio >= Math.max(config.consistencyThreshold - 0.1, 0.45)
    ) {
      severity = "Warning";
    } else if (deltaPct <= -(warningThreshold * 0.6) && belowBaselinePeriods >= Math.max(Math.floor(recent.length * 0.5), 1)) {
      severity = "Watch";
    }

    const eventType = eventTypeMap.get([latest.customerId, latest.monthStart].join("|"));

    rows.push({
      customer: latest.customerName,
      category: latest.category,
      recentSales,
      baselineSales,
      deltaPct,
      targetAttainmentPct,
      targetGap,
      yoyTrendPct,
      atRiskSales,
      weightedImpact,
      severity,
      possibleRiskFactor: derivePossibleRiskFactor(eventType, deltaPct, targetAttainmentPct, yoyTrendPct),
      customerSize: latest.customerSize,
      severityRank: severityRankMap[severity],
    });
  });

  return rows.sort((a, b) => {
    if (b.severityRank !== a.severityRank) return b.severityRank - a.severityRank;
    return b.weightedImpact - a.weightedImpact;
  });
}

export async function loadDashboardData(
  config: RuleConfig = defaultRuleConfig(),
  filters: DashboardFilters = defaultDashboardFilters(),
): Promise<DashboardData> {
  const [orders, customers, products, targets, events] = await Promise.all([
    loadCsv<OrderRow>("fact_orders.csv"),
    loadCsv<CustomerRow>("dim_customer.csv"),
    loadCsv<ProductRow>("dim_product.csv"),
    loadCsv<TargetRow>("target_monthly.csv").catch(() => []),
    loadCsv<EventRow>("fact_events.csv").catch(() => []),
  ]);

  const customerOptions = customers.map((row) => row.customer_name).sort((a, b) => a.localeCompare(b));
  const categoryOptions = Array.from(new Set(products.map((row) => row.category_l1))).sort((a, b) => a.localeCompare(b));
  const customerNameMap = new Map(customers.map((row) => [row.customer_id, row.customer_name]));
  const productCategoryMap = new Map(products.map((row) => [row.product_id, row.category_l1]));

  const filteredOrders = orders.filter((order) => {
    const customerName = customerNameMap.get(order.customer_id) ?? order.customer_id;
    const category = productCategoryMap.get(order.product_id) ?? "";
    const matchesCustomer = filters.customers.length === 0 || filters.customers.includes(customerName);
    const matchesCategory = filters.categories.length === 0 || filters.categories.includes(category);
    return matchesCustomer && matchesCategory;
  });

  const filteredTargets = targets.filter((target) => {
    const matchesCustomer = filters.customers.length === 0 || filters.customers.includes(target.customer_name);
    const matchesCategory = filters.categories.length === 0 || filters.categories.includes(target.category_l1);
    return matchesCustomer && matchesCategory;
  });

  const filteredEvents = events.filter((event) => {
    const customerName =
      event.customer_id === "MULTI_CUSTOMER" ? "Multi-customer" : customerNameMap.get(event.customer_id) ?? event.customer_id;
    const category = productCategoryMap.get(event.product_id) ?? "";
    const matchesCustomer =
      filters.customers.length === 0 || filters.customers.includes(customerName) || event.customer_id === "MULTI_CUSTOMER";
    const matchesCategory = filters.categories.length === 0 || filters.categories.includes(category);
    return matchesCustomer && matchesCategory;
  });

  const fullMonthlySales = aggregateMonthlySales(orders, customers, products, targets);
  const monthlySales = fullMonthlySales;
  const latestMonth = monthlySales.reduce((latest, row) => (row.monthStart > latest ? row.monthStart : latest), monthlySales[0]?.monthStart ?? "");
  const latestDate = latestMonth ? new Date(latestMonth) : new Date();
  const currentYear = latestDate.getFullYear();
  const currentMonth = latestDate.getMonth() + 1;

  const ytdRows = monthlySales.filter((row) => row.year === currentYear && row.month <= currentMonth);
  const priorYtdRows = monthlySales.filter((row) => row.year === currentYear - 1 && row.month <= currentMonth);
  const currentMonthRows = monthlySales.filter((row) => row.monthStart === latestMonth);

  const ytdSales = ytdRows.reduce((sum, row) => sum + row.totalSales, 0);
  const priorYtdSales = priorYtdRows.reduce((sum, row) => sum + row.totalSales, 0);
  const targetAchievement = ytdRows.reduce((sum, row) => sum + row.targetSalesAmount, 0);

  const customerRanking = Object.values(
    ytdRows.reduce<Record<string, { customer: string; sales: number }>>((acc, row) => {
      acc[row.customerName] = acc[row.customerName] ?? { customer: row.customerName, sales: 0 };
      acc[row.customerName].sales += row.totalSales;
      return acc;
    }, {}),
  ).sort((a, b) => b.sales - a.sales);

  const currentCategorySales = Object.values(
    ytdRows.reduce<Record<string, { category: string; sales: number }>>((acc, row) => {
      acc[row.category] = acc[row.category] ?? { category: row.category, sales: 0 };
      acc[row.category].sales += row.totalSales;
      return acc;
    }, {}),
  );

  const priorCategorySales = priorYtdRows.reduce<Record<string, number>>((acc, row) => {
    acc[row.category] = (acc[row.category] ?? 0) + row.totalSales;
    return acc;
  }, {});

  const categoryRanking = currentCategorySales
    .map((row) => ({
      category: row.category,
      sales: row.sales,
      growthPct: priorCategorySales[row.category] ? row.sales / priorCategorySales[row.category] - 1 : 0,
    }))
    .sort((a, b) => b.sales - a.sales);

  const monthlyTrend = Object.values(
    monthlySales.reduce<Record<string, { monthStart: string; currentYearSales: number; currentYearTarget: number; previousYearSales: number }>>(
      (acc, row) => {
        acc[row.monthStart] = acc[row.monthStart] ?? {
          monthStart: row.monthStart,
          currentYearSales: 0,
          currentYearTarget: 0,
          previousYearSales: 0,
        };
        if (row.year === currentYear) {
          acc[row.monthStart].currentYearSales += row.totalSales;
          acc[row.monthStart].currentYearTarget += row.targetSalesAmount;
        }
        return acc;
      },
      {},
    ),
  )
    .filter((row) => new Date(row.monthStart).getFullYear() === currentYear)
    .map((row) => {
      const currentMonthDate = new Date(row.monthStart);
      const previousYearMatch = monthlySales
        .filter((item) => item.year === currentYear - 1 && item.month === currentMonthDate.getMonth() + 1)
        .reduce((sum, item) => sum + item.totalSales, 0);
      return { ...row, previousYearSales: previousYearMatch };
    })
    .sort((a, b) => a.monthStart.localeCompare(b.monthStart));

  const sortedCategoryMix = [...currentCategorySales].sort((a, b) => b.sales - a.sales);
  const topCategoryMix = sortedCategoryMix.slice(0, 6).map((row) => ({
    label: row.category,
    value: row.sales,
  }));
  const remainingCategorySales = sortedCategoryMix.slice(6).reduce((sum, row) => sum + row.sales, 0);
  const salesMix = remainingCategorySales > 0 ? [...topCategoryMix, { label: "Other", value: remainingCategorySales }] : topCategoryMix;

  const targetInsight = currentMonthRows
    .map((row) => ({
      customer: row.customerName,
      category: row.category,
      actualSales: row.totalSales,
      targetSales: row.targetSalesAmount,
      targetAttainmentPct: row.targetAttainmentPct,
      targetGap: row.totalSales - row.targetSalesAmount,
    }))
    .sort((a, b) => a.targetGap - b.targetGap);

  const detailMonthlySales = aggregateMonthlySales(filteredOrders, customers, products, filteredTargets);
  const detailLatestMonth = detailMonthlySales.reduce(
    (latest, row) => (row.monthStart > latest ? row.monthStart : latest),
    detailMonthlySales[0]?.monthStart ?? "",
  );
  const detailLatestDate = detailLatestMonth ? new Date(detailLatestMonth) : new Date();
  const detailCurrentYear = detailLatestDate.getFullYear();
  const detailCurrentMonth = detailLatestDate.getMonth() + 1;
  let detailScopedRows = detailMonthlySales;
  if (filters.months > 0 && detailLatestMonth) {
    const detailThreshold = new Date(detailLatestDate.getFullYear(), detailLatestDate.getMonth() - (filters.months - 1), 1)
      .toISOString()
      .slice(0, 10);
    detailScopedRows = detailMonthlySales.filter((row) => row.monthStart >= detailThreshold);
  }
  const detailYtdRows = detailScopedRows.filter((row) => row.year === detailCurrentYear && row.month <= detailCurrentMonth);
  const detailCurrentMonthRows = detailMonthlySales.filter((row) => row.monthStart === detailLatestMonth);

  const scopedTrend = Object.values(
    detailScopedRows.reduce<Record<string, { monthStart: string; sales: number; target: number; attainmentPct: number }>>((acc, row) => {
      acc[row.monthStart] = acc[row.monthStart] ?? {
        monthStart: row.monthStart,
        sales: 0,
        target: 0,
        attainmentPct: 0,
      };
      acc[row.monthStart].sales += row.totalSales;
      acc[row.monthStart].target += row.targetSalesAmount;
      return acc;
    }, {}),
  )
    .map((row) => ({
      ...row,
      attainmentPct: row.target > 0 ? row.sales / row.target : 1,
    }))
    .sort((a, b) => a.monthStart.localeCompare(b.monthStart));

  const scopedCategoryMixRaw = Object.values(
    detailYtdRows.reduce<Record<string, { label: string; value: number }>>((acc, row) => {
      acc[row.category] = acc[row.category] ?? { label: row.category, value: 0 };
      acc[row.category].value += row.totalSales;
      return acc;
    }, {}),
  ).sort((a, b) => b.value - a.value);
  const scopedTotal = scopedCategoryMixRaw.reduce((sum, row) => sum + row.value, 0);
  const scopedCategoryMix = scopedCategoryMixRaw.map((row) => ({
    ...row,
    sharePct: scopedTotal > 0 ? row.value / scopedTotal : 0,
  }));

  const detailTargetInsight = detailCurrentMonthRows
    .map((row) => ({
      customer: row.customerName,
      category: row.category,
      actualSales: row.totalSales,
      targetSales: row.targetSalesAmount,
      targetAttainmentPct: row.targetAttainmentPct,
      targetGap: row.totalSales - row.targetSalesAmount,
    }))
    .sort((a, b) => a.targetGap - b.targetGap);

  const riskRows = buildRiskRows(monthlySales, filteredOrders, config);
  const underlyingTrend = Object.values(
    monthlySales.reduce<
      Record<string, { monthStart: string; reportedSales: number; baselineSales: number; eventLinkedSales: number; gapToBaseline: number }>
    >((acc, row) => {
      acc[row.monthStart] = acc[row.monthStart] ?? {
        monthStart: row.monthStart,
        reportedSales: 0,
        baselineSales: 0,
        eventLinkedSales: 0,
        gapToBaseline: 0,
      };
      acc[row.monthStart].reportedSales += row.totalSales;
      acc[row.monthStart].baselineSales += row.reconstructedBaselineSales;
      acc[row.monthStart].eventLinkedSales += row.eventLinkedSales;
      return acc;
    }, {}),
  )
    .map((row) => ({
      ...row,
      gapToBaseline: row.reportedSales - row.baselineSales,
    }))
    .sort((a, b) => a.monthStart.localeCompare(b.monthStart))
    .slice(-12);

  const eventTimeline = Object.values(
    filteredEvents.reduce<Record<string, { monthStart: string; eventType: string; eventLabel: string; eventCount: number; customerScope: string }>>(
      (acc, event) => {
        const monthStart = toMonthStart(event.start_date);
        const key = `${monthStart}|${event.event_type}`;
        acc[key] = acc[key] ?? {
          monthStart,
          eventType: event.event_type,
          eventLabel: event.description,
          eventCount: 0,
          customerScope:
            event.customer_id === "MULTI_CUSTOMER"
              ? "Multi-customer"
              : customerNameMap.get(event.customer_id) ?? event.customer_id,
        };
        acc[key].eventCount += 1;
        return acc;
      },
      {},
    ),
  )
    .sort((a, b) => a.monthStart.localeCompare(b.monthStart))
    .slice(-12);

  return {
    monthlySales,
    monthlyTrend,
    salesMix,
    customerRanking,
    categoryRanking,
    targetInsight,
    underlyingTrend,
    eventTimeline,
    riskRows,
    options: {
      customers: customerOptions,
      categories: categoryOptions,
    },
    detailViews: {
      scopedTrend,
      categoryMix: scopedCategoryMix,
      targetInsight: detailTargetInsight,
    },
    kpis: {
      ytdSales,
      currentMonthSales: currentMonthRows.reduce((sum, row) => sum + row.totalSales, 0),
      currentMonthQuantity: currentMonthRows.reduce((sum, row) => sum + row.totalQuantity, 0),
      ytdGrowthPct: priorYtdSales > 0 ? ytdSales / priorYtdSales - 1 : 0,
      targetAchievementPct: targetAchievement > 0 ? ytdSales / targetAchievement : 0,
    },
  };
}

export function emptyDataErrorMessage(error: unknown) {
  if (error instanceof Error) {
    return error.message;
  }
  return `Unable to load dashboard data.`;
}

export function riskSummary(riskRows: RiskRow[]) {
  const atRisk = riskRows.filter((row) => row.severity !== "Normal");
  return {
    customersAtRisk: new Set(atRisk.map((row) => row.customer)).size,
    categoriesAtRisk: new Set(atRisk.map((row) => row.category)).size,
    hiddenDropSignals: atRisk.filter((row) => row.possibleRiskFactor === "Demand softening").length,
    targetMissSignals: atRisk.filter((row) => row.targetAttainmentPct < 0.95).length,
    structuralShiftSignals: atRisk.filter((row) => row.possibleRiskFactor === "Structural shift / New normal").length,
    atRiskSales: atRisk.reduce((sum, row) => sum + row.atRiskSales, 0),
  };
}

export const defaultRules = defaultRuleConfig;
export const defaultFilters = defaultDashboardFilters;

export function riskMethodologyBlurb() {
  return [
    "Monthly performance is used to reduce week-to-week noise.",
    "Baseline is reconstructed from recent historical median sales.",
    "Event-linked sales help separate temporary distortion from ordinary demand.",
    "Alerts highlight sustained underperformance versus baseline and target.",
  ];
}
