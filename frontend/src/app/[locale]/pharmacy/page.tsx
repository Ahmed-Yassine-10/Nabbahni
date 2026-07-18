"use client";

import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { useAlerts, useMe, usePharmacyStock } from "@/lib/queries";
import {
  EmptyState,
  EssentialTag,
  KpiCard,
  Panel,
  RiskBadge,
  SegmentedControl,
  SkeletonRows,
  Spinner,
} from "@/components/ui";
import { formatInt, formatTND } from "@/lib/utils";
import type { Severity } from "@/lib/types";
import { AlertTriangle, Package, PackageX, Search, TrendingDown } from "lucide-react";

type StockFilter = "all" | "low" | "essential";

/**
 * A pharmacist's screen is a work queue, not an analytics console: what is
 * running out, how soon, and what to do about it. Density is lower than the
 * command centre and the ordering is by urgency rather than by name.
 */
export default function PharmacyStockPage() {
  const t = useTranslations("pharmacy");
  const tsev = useTranslations("severity");
  const meQ = useMe();
  const stockQ = usePharmacyStock(meQ.data?.pharmacy_id);
  const alertsQ = useAlerts();

  const [filter, setFilter] = useState<StockFilter>("all");
  const [query, setQuery] = useState("");

  const rows = useMemo(() => stockQ.data ?? [], [stockQ.data]);

  const stats = useMemo(() => {
    const low = rows.filter((r) => r.quantity <= r.min_threshold);
    const out = rows.filter((r) => r.quantity === 0);
    const value = rows.reduce(
      (a, r) => a + r.quantity * (r.medication?.unit_price_tnd ?? 0),
      0
    );
    return { low: low.length, out: out.length, value, total: rows.length };
  }, [rows]);

  const visible = useMemo(() => {
    let list = rows;
    if (filter === "low") list = list.filter((r) => r.quantity <= r.min_threshold);
    if (filter === "essential") list = list.filter((r) => r.medication?.is_essential);
    if (query.trim()) {
      const q = query.toLowerCase();
      list = list.filter(
        (r) =>
          r.medication?.brand_name.toLowerCase().includes(q) ||
          r.medication?.dci.toLowerCase().includes(q)
      );
    }
    // Most urgent first: lowest days of cover, then furthest below threshold.
    return [...list].sort((a, b) => {
      const ca = a.coverage_days ?? Number.POSITIVE_INFINITY;
      const cb = b.coverage_days ?? Number.POSITIVE_INFINITY;
      if (ca !== cb) return ca - cb;
      return a.quantity - a.min_threshold - (b.quantity - b.min_threshold);
    });
  }, [rows, filter, query]);

  if (meQ.isLoading) return <Spinner />;
  if (!meQ.data || !meQ.data.pharmacy_id) {
    return (
      <EmptyState icon={<PackageX className="h-5 w-5 text-slate-300" />}>
        Connectez-vous comme <strong>Pharmacien d&apos;officine</strong> ou{" "}
        <strong>Pharmacien hospitalier</strong> pour voir le stock de votre
        établissement.
      </EmptyState>
    );
  }

  const localAlerts = (alertsQ.data ?? []).slice(0, 8);

  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-xl font-bold text-slate-900">{t("myStock")}</h1>
        <p className="text-xs text-slate-500">
          Trié par urgence : les références qui s&apos;épuiseront en premier
          apparaissent en haut.
        </p>
      </header>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard
          label="Références"
          value={stats.total}
          icon={<Package className="h-4 w-4" />}
        />
        <KpiCard
          label="Sous le seuil"
          value={stats.low}
          hint="À recommander"
          severity={stats.low > 0 ? "orange" : "green"}
          icon={<TrendingDown className="h-4 w-4" />}
        />
        <KpiCard
          label="En rupture"
          value={stats.out}
          hint="Stock à zéro"
          severity={stats.out > 0 ? "critical" : "green"}
          icon={<PackageX className="h-4 w-4" />}
        />
        <KpiCard
          label="Valeur du stock"
          value={formatTND(stats.value)}
          icon={<Package className="h-4 w-4" />}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Panel
          className="lg:col-span-2"
          title="Inventaire"
          subtitle={`${visible.length} / ${rows.length} références`}
          bodyClassName="p-0"
          actions={
            <div className="flex flex-wrap items-center justify-end gap-2">
              <div className="relative">
                <Search
                  aria-hidden
                  className="pointer-events-none absolute start-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400"
                />
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Rechercher…"
                  aria-label="Rechercher un médicament"
                  className="min-h-[2.25rem] w-36 rounded-md border border-slate-200 ps-7 pe-2 text-xs outline-none placeholder:text-slate-400 focus:border-slate-300"
                />
              </div>
              <SegmentedControl<StockFilter>
                ariaLabel="Filtrer le stock"
                value={filter}
                onChange={setFilter}
                options={[
                  { value: "all", label: "Tout" },
                  { value: "low", label: "En tension" },
                  { value: "essential", label: "Essentiels" },
                ]}
              />
            </div>
          }
        >
          {stockQ.isLoading ? (
            <div className="p-4">
              <SkeletonRows rows={10} />
            </div>
          ) : visible.length ? (
            <div className="max-h-[560px] overflow-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Médicament</th>
                    <th className="text-end">Quantité</th>
                    <th className="text-end">Seuil</th>
                    <th className="text-end">Couverture</th>
                    <th>État</th>
                  </tr>
                </thead>
                <tbody>
                  {visible.map((r) => {
                    const sev = stockSeverity(r.quantity, r.min_threshold, r.coverage_days);
                    return (
                      <tr key={r.id}>
                        <td>
                          <div className="flex items-center gap-1.5">
                            <span className="font-medium text-slate-900">
                              {r.medication?.brand_name ?? "—"}
                            </span>
                            {r.medication?.is_essential && <EssentialTag label="Ess." />}
                          </div>
                          <div className="text-2xs text-slate-500">
                            {r.medication?.dci}
                            {r.medication?.dosage ? ` · ${r.medication.dosage}` : ""}
                          </div>
                        </td>
                        <td className="text-end font-figure text-xs font-semibold">
                          {formatInt(r.quantity)}
                        </td>
                        <td className="text-end font-figure text-xs text-slate-400">
                          {formatInt(r.min_threshold)}
                        </td>
                        <td className="text-end font-figure text-xs">
                          {r.coverage_days != null ? `${r.coverage_days.toFixed(0)} j` : "—"}
                        </td>
                        <td>
                          <RiskBadge
                            severity={sev}
                            label={STOCK_LABEL[sev]}
                            size="sm"
                          />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState>Aucune référence ne correspond à ce filtre.</EmptyState>
          )}
        </Panel>

        <Panel
          title={t("localAlerts")}
          subtitle={`${localAlerts.length} alertes récentes`}
          bodyClassName="p-0"
        >
          {alertsQ.isLoading ? (
            <div className="p-4">
              <SkeletonRows rows={5} />
            </div>
          ) : localAlerts.length ? (
            <ul className="max-h-[560px] divide-y divide-slate-100 overflow-y-auto">
              {localAlerts.map((a) => (
                <li key={a.id} className="px-4 py-3">
                  <div className="mb-1 flex items-start justify-between gap-2">
                    <span className="text-sm font-medium leading-snug text-slate-900">
                      {a.medication?.brand_name ?? a.title_fr}
                    </span>
                    <RiskBadge severity={a.severity} label={tsev(a.severity)} size="sm" />
                  </div>
                  <p className="text-2xs leading-relaxed text-slate-500">{a.body_fr}</p>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState icon={<AlertTriangle className="h-5 w-5 text-slate-300" />}>
              Aucune alerte locale.
            </EmptyState>
          )}
        </Panel>
      </div>
    </div>
  );
}

const STOCK_LABEL: Record<Severity, string> = {
  critical: "Rupture",
  red: "Critique",
  orange: "Tension",
  yellow: "À surveiller",
  green: "OK",
};

/** Combines the pharmacy's own threshold with days-of-cover. */
function stockSeverity(
  quantity: number,
  threshold: number,
  coverage: number | null
): Severity {
  if (quantity === 0) return "critical";
  if (coverage != null && coverage < 7) return "red";
  if (quantity <= threshold) return "orange";
  if (coverage != null && coverage < 21) return "yellow";
  return "green";
}
