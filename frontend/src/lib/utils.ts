import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Reserved 5-level status ramp. These are the *only* colours that may encode
 * shortage severity, and severity is the only thing they may encode. Every
 * use must be accompanied by a text label — colour alone never carries the
 * meaning (CVD + print + forced-colors).
 */
export const SEVERITY_COLORS: Record<string, string> = {
  green: "#15803d",
  yellow: "#ca8a04",
  orange: "#ea580c",
  red: "#dc2626",
  critical: "#7f1d1d",
};

/** Tint used for row/cell backgrounds — must keep text at >= 4.5:1. */
export const SEVERITY_TINTS: Record<string, string> = {
  green: "#f0fdf4",
  yellow: "#fefce8",
  orange: "#fff7ed",
  red: "#fef2f2",
  critical: "#fee2e2",
};

export const SEVERITY_ORDER = ["green", "yellow", "orange", "red", "critical"];

export function severityRank(s: string): number {
  return SEVERITY_ORDER.indexOf(s);
}

export function formatTND(value: number): string {
  return new Intl.NumberFormat("fr-TN", {
    style: "currency",
    currency: "TND",
    maximumFractionDigits: 0,
  }).format(value);
}

/** Compact form for KPI tiles: 515 344 319 -> "515,3 M". */
export function formatCompact(value: number): string {
  return new Intl.NumberFormat("fr-FR", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

export function formatInt(value: number): string {
  return new Intl.NumberFormat("fr-FR").format(Math.round(value));
}

export function formatPct(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("fr-FR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(iso));
}

/** Days from today until `iso`, negative if past. */
export function daysUntil(iso: string | null | undefined): number | null {
  if (!iso) return null;
  const ms = new Date(iso).getTime() - Date.now();
  return Math.round(ms / 86_400_000);
}
