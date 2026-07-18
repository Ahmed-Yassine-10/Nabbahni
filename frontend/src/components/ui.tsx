"use client";

import { cn, SEVERITY_COLORS, SEVERITY_TINTS } from "@/lib/utils";
import type { Availability, Severity } from "@/lib/types";
import { AlertTriangle, Check, Info, Minus, TrendingDown, TrendingUp } from "lucide-react";
import type { ReactNode } from "react";

/* ------------------------------------------------------------------ *
 * Surfaces
 * ------------------------------------------------------------------ */

export function Card({
  className,
  children,
  padded = true,
}: {
  className?: string;
  children: ReactNode;
  padded?: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-lg border border-slate-200 bg-white shadow-card",
        padded && "p-4",
        className
      )}
    >
      {children}
    </div>
  );
}

/** Card with a title bar — keeps every panel header identical. */
export function Panel({
  title,
  subtitle,
  actions,
  children,
  className,
  bodyClassName,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <section
      className={cn(
        "flex flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-card",
        className
      )}
    >
      <header className="flex items-start justify-between gap-3 border-b border-slate-100 px-4 py-3">
        <div className="min-w-0">
          <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
          {subtitle && <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>}
        </div>
        {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
      </header>
      <div className={cn("min-h-0 flex-1", bodyClassName ?? "p-4")}>{children}</div>
    </section>
  );
}

/* ------------------------------------------------------------------ *
 * Status
 * ------------------------------------------------------------------ */

/**
 * Severity chip. Colour is never the only channel: the label is always
 * rendered, and a shape (filled dot vs. ring) reinforces the two ends of the
 * ramp for colour-blind and monochrome readers.
 */
export function RiskBadge({
  severity,
  label,
  size = "md",
}: {
  severity: Severity;
  label?: string;
  size?: "sm" | "md";
}) {
  const color = SEVERITY_COLORS[severity];
  const tint = SEVERITY_TINTS[severity];
  const severe = severity === "red" || severity === "critical";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full font-semibold",
        size === "sm" ? "px-2 py-0.5 text-2xs" : "px-2.5 py-1 text-xs"
      )}
      style={{ color, backgroundColor: tint, boxShadow: `inset 0 0 0 1px ${color}33` }}
    >
      <span
        aria-hidden
        className="h-1.5 w-1.5 rounded-full"
        style={{
          backgroundColor: severe ? color : "transparent",
          boxShadow: `inset 0 0 0 1.5px ${color}`,
        }}
      />
      {label ?? severity}
    </span>
  );
}

const AVAILABILITY_STYLE: Record<
  Availability,
  { color: string; bg: string; Icon: typeof Check }
> = {
  available: { color: "#166534", bg: "#dcfce7", Icon: Check },
  tension: { color: "#92400e", bg: "#fef3c7", Icon: AlertTriangle },
  shortage: { color: "#991b1b", bg: "#fee2e2", Icon: AlertTriangle },
};

export function AvailabilityBadge({
  status,
  label,
}: {
  status: Availability;
  label: string;
}) {
  const s = AVAILABILITY_STYLE[status];
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold"
      style={{ color: s.color, backgroundColor: s.bg }}
    >
      <s.Icon aria-hidden className="h-3.5 w-3.5" />
      {label}
    </span>
  );
}

export function EssentialTag({ label = "Essentiel" }: { label?: string }) {
  return (
    <span className="inline-flex items-center rounded border border-brand-200 bg-brand-50 px-1.5 py-0.5 text-2xs font-semibold uppercase tracking-wide text-brand-800">
      {label}
    </span>
  );
}

/* ------------------------------------------------------------------ *
 * Figures
 * ------------------------------------------------------------------ */

export function KpiCard({
  label,
  value,
  unit,
  hint,
  severity,
  trend,
  icon,
}: {
  label: string;
  value: ReactNode;
  unit?: string;
  hint?: string;
  severity?: Severity;
  trend?: "rising" | "stable" | "falling";
  icon?: ReactNode;
}) {
  const color = severity ? SEVERITY_COLORS[severity] : undefined;
  const TrendIcon =
    trend === "rising" ? TrendingUp : trend === "falling" ? TrendingDown : Minus;
  return (
    <Card className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
          {label}
        </span>
        {icon && <span className="text-slate-300">{icon}</span>}
      </div>
      <div className="flex items-baseline gap-1.5">
        <span
          className="font-figure text-2xl font-semibold leading-none"
          style={{ color: color ?? "#0f172a" }}
        >
          {value}
        </span>
        {unit && <span className="text-xs font-medium text-slate-400">{unit}</span>}
        {trend && (
          <TrendIcon
            aria-hidden
            className={cn(
              "ms-1 h-3.5 w-3.5",
              trend === "rising"
                ? "text-risk-orange"
                : trend === "falling"
                  ? "text-risk-green"
                  : "text-slate-300"
            )}
          />
        )}
      </div>
      {hint && <span className="text-2xs text-slate-400">{hint}</span>}
    </Card>
  );
}

/** Horizontal proportion bar — used for coverage, confidence, SHAP weight. */
export function MeterBar({
  value,
  max = 1,
  color = "#1e40af",
  className,
}: {
  value: number;
  max?: number;
  color?: string;
  className?: string;
}) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div className={cn("h-1.5 w-full overflow-hidden rounded-full bg-slate-100", className)}>
      <div
        className="h-full rounded-full transition-[width] duration-300"
        style={{ width: `${pct}%`, backgroundColor: color }}
      />
    </div>
  );
}

/* ------------------------------------------------------------------ *
 * Legend / feedback
 * ------------------------------------------------------------------ */

export function SeverityLegend({
  labelFor,
  className,
}: {
  labelFor: (s: Severity) => string;
  className?: string;
}) {
  const order: Severity[] = ["green", "yellow", "orange", "red", "critical"];
  return (
    <div className={cn("flex flex-wrap items-center gap-x-3 gap-y-1", className)}>
      {order.map((s) => (
        <span key={s} className="flex items-center gap-1.5 text-2xs text-slate-500">
          <span
            aria-hidden
            className="h-2.5 w-2.5 rounded-sm"
            style={{ backgroundColor: SEVERITY_COLORS[s] }}
          />
          {labelFor(s)}
        </span>
      ))}
    </div>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 py-8 text-sm text-slate-400" role="status">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-200 border-t-brand" />
      {label ?? "Chargement…"}
    </div>
  );
}

/** Reserves the final layout height so content arriving doesn't shift the page. */
export function SkeletonRows({ rows = 6 }: { rows?: number }) {
  return (
    <div className="space-y-2" aria-hidden>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skeleton h-8 w-full" />
      ))}
    </div>
  );
}

export function EmptyState({
  children,
  icon,
}: {
  children: ReactNode;
  icon?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-2 py-10 text-center text-sm text-slate-400">
      {icon ?? <Info aria-hidden className="h-5 w-5 text-slate-300" />}
      <div className="max-w-sm">{children}</div>
    </div>
  );
}

/* ------------------------------------------------------------------ *
 * Controls
 * ------------------------------------------------------------------ */

export function Button({
  children,
  variant = "primary",
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger";
}) {
  const variants = {
    primary:
      "bg-[var(--portal-accent)] text-white hover:brightness-110 disabled:opacity-50",
    secondary:
      "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-50",
    ghost: "text-slate-500 hover:bg-slate-100 disabled:opacity-50",
    danger: "border border-risk-red/30 bg-white text-risk-red hover:bg-red-50",
  };
  return (
    <button
      className={cn(
        "inline-flex min-h-[2.25rem] cursor-pointer items-center justify-center gap-1.5 rounded-md px-3 text-sm font-medium transition-colors duration-150 disabled:cursor-not-allowed",
        variants[variant],
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}

/** Segmented control used for horizon / severity filters above a chart. */
export function SegmentedControl<T extends string | number>({
  options,
  value,
  onChange,
  ariaLabel,
}: {
  options: { value: T; label: string }[];
  value: T;
  onChange: (v: T) => void;
  ariaLabel: string;
}) {
  return (
    <div
      role="group"
      aria-label={ariaLabel}
      className="inline-flex rounded-md border border-slate-200 bg-slate-50 p-0.5"
    >
      {options.map((o) => (
        <button
          key={String(o.value)}
          type="button"
          aria-pressed={o.value === value}
          onClick={() => onChange(o.value)}
          className={cn(
            "cursor-pointer rounded px-2.5 py-1 text-xs font-medium transition-colors duration-150",
            o.value === value
              ? "bg-white text-slate-900 shadow-sm"
              : "text-slate-500 hover:text-slate-700"
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
