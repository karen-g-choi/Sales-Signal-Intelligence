import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(value: number) {
  return new Intl.NumberFormat("sv-SE", {
    style: "currency",
    currency: "SEK",
    maximumFractionDigits: 0,
  }).format(Number.isFinite(value) ? value : 0);
}

export function formatCurrencyCompact(value: number) {
  const safeValue = Number.isFinite(value) ? value : 0;
  const absValue = Math.abs(safeValue);

  if (absValue >= 1_000_000) {
    return `SEK ${(safeValue / 1_000_000).toFixed(2)}M`;
  }

  if (absValue >= 1_000) {
    return `SEK ${(safeValue / 1_000).toFixed(1)}K`;
  }

  return `SEK ${safeValue.toFixed(0)}`;
}

export function formatNumberCompact(value: number) {
  const safeValue = Number.isFinite(value) ? value : 0;
  const absValue = Math.abs(safeValue);

  if (absValue >= 1_000_000) {
    return `${(safeValue / 1_000_000).toFixed(2)}M`;
  }

  if (absValue >= 1_000) {
    return `${(safeValue / 1_000).toFixed(1)}K`;
  }

  return `${safeValue.toFixed(0)}`;
}

export function formatPercent(value: number, digits = 1) {
  return `${(Number.isFinite(value) ? value * 100 : 0).toFixed(digits)}%`;
}

export function formatQuantity(value: number) {
  return new Intl.NumberFormat("sv-SE", {
    maximumFractionDigits: 0,
  }).format(Number.isFinite(value) ? value : 0);
}

export function monthLabel(value: string) {
  return new Date(value).toLocaleDateString("en-GB", {
    year: "numeric",
    month: "short",
  });
}

export function rollingMedian(values: number[]) {
  if (values.length === 0) {
    return 0;
  }
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  if (sorted.length % 2 === 0) {
    return (sorted[middle - 1] + sorted[middle]) / 2;
  }
  return sorted[middle];
}
