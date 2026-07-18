"use client";

import { useMemo, useState } from "react";
import { useRouter } from "@/i18n/routing";
import { useNationalStock, useStockAnalysis } from "@/lib/queries";
import {
  EmptyState,
  EssentialTag,
  KpiCard,
  Panel,
  RiskBadge,
  SegmentedControl,
  SkeletonRows,
} from "@/components/ui";
import { SEVERITY_COLORS, formatCompact, formatInt, formatTND } from "@/lib/utils";
import type { NationalStockRow, Severity } from "@/lib/types";
import { Boxes, Coins, ShieldAlert, Timer } from "lucide-react";

type Filter = "all" | "essential" | "at_risk";

/** Coverage days -> reserved status level. Mirrors the backend bands. */
function coverageSeverity(days: number | null): Severity {
  if (days == null) return "green";
  if (days < 5) return "critical";
  if (days < 15) return "red";
  if (days < 30) return "orange";
  if (days < 60) return "yellow";
  return "green";
}

const SEVERITY_LABEL: Record<Severity, string> = {
  critical: "Rupture imminente",
  red: "Critique",
  orange: "Tendu",
  yellow: "Surveillance",
  green: "Confortable",
};

export default function StockAnalysisPage() {
  const router = useRouter();
  const analysisQ = useStockAnalysis();
  const stockQ = useNationalStock();
  const [filter, setFilter] = useState<Filter>("all");
  const [sort, setSort] = useState<"coverage" | "value" | "quantity">("coverage");

  const rows = useMemo(() => {
    let list: NationalStockRow[] = stockQ.data ?? [];
    if (filter === "essential") list = list.filter((r) => r.is_essential);
    if (filter === "at_risk")
      list = list.filter((r) => r.coverage_days != null && r.coverage_days < 30);

    return [...list].sort((a, b) => {
      if (sort === "coverage") {
        // Nulls last — an unknown coverage isn't an urgent one.
        if (a.coverage_days == null) return 1;
        if (b.coverage_days == null) return -1;
        return a.coverage_days - b.coverage_days;
      }
      if (sort === "value")
        return b.quantity * b.unit_price_tnd - a.quantity * a.unit_price_tnd;
      return b.quantity - a.quantity;
    });
  }, [stockQ.data, filter, sort]);

  const a = analysisQ.data;

  if (analysisQ.isError || stockQ.isError) {
    return (
      <EmptyState icon={<ShieldAlert className="h-5 w-5 text-slate-300" />}>
        Cette analyse est réservée aux profils <strong>Admin PCT</strong> et{" "}
        <strong>Autorité régionale</strong>. Changez de profil en haut à droite.
      </EmptyState>
    );
  }

  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-xl font-bold text-slate-900">Analyse des stocks nationaux</h1>
        <p className="text-xs text-slate-500">
          Inventaire PCT rapproché de la demande prévue — la couverture est le
          nombre de jours que le stock actuel peut absorber.
        </p>
      </header>

      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <KpiCard
          label="Médicaments suivis"
          value={a ? a.total_medications : "—"}
          icon={<Boxes className="h-4 w-4" />}
        />
        <KpiCard
          label="Unités en stock"
          value={a ? formatCompact(a.total_units) : "—"}
          hint={a ? `${formatInt(a.total_units)} unités` : undefined}
          icon={<Boxes className="h-4 w-4" />}
        />
        <KpiCard
          label="Valeur d'inventaire"
          value={a ? formatCompact(a.total_value_tnd) : "—"}
          unit="TND"
          hint={a ? formatTND(a.total_value_tnd) : undefined}
          icon={<Coins className="h-4 w-4" />}
        />
        <KpiCard
          label="Essentiels en tension"
          value={a ? a.essential_at_risk : "—"}
          hint="Couverture < 15 jours"
          severity={a && a.essential_at_risk > 0 ? "red" : "green"}
          icon={<ShieldAlert className="h-4 w-4" />}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <Panel
          title="Répartition par couverture"
          subtitle={
            a ? `Couverture médiane : ${a.median_coverage_days} jours` : undefined
          }
        >
          {analysisQ.isLoading ? (
            <SkeletonRows rows={5} />
          ) : a ? (
            <div className="space-y-2.5">
              {a.buckets.map((b) => {
                const max = Math.max(1, ...a.buckets.map((x) => x.count));
                return (
                  <div key={b.label} className="flex items-center gap-3">
                    <span className="w-32 shrink-0 text-xs text-slate-600">
                      {b.label}
                    </span>
                    <span className="flex-1">
                      <span
                        className="block h-4 rounded-sm"
                        style={{
                          width: `${(b.count / max) * 100}%`,
                          backgroundColor: SEVERITY_COLORS[b.severity],
                          minWidth: b.count > 0 ? "3px" : "0",
                        }}
                      />
                    </span>
                    <span className="w-8 shrink-0 text-end font-figure text-xs text-slate-700">
                      {b.count}
                    </span>
                  </div>
                );
              })}
            </div>
          ) : null}
        </Panel>

        <Panel
          className="xl:col-span-2"
          title="Couvertures les plus faibles"
          subtitle="Les 15 médicaments dont le stock s'épuisera en premier"
          bodyClassName="p-0"
        >
          {analysisQ.isLoading ? (
            <div className="p-4">
              <SkeletonRows rows={6} />
            </div>
          ) : a?.lowest_coverage.length ? (
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Médicament</th>
                    <th className="text-end">Stock</th>
                    <th className="text-end">Couverture</th>
                    <th>Niveau</th>
                  </tr>
                </thead>
                <tbody>
                  {a.lowest_coverage.map((r) => {
                    const sev = coverageSeverity(r.coverage_days);
                    return (
                      <tr
                        key={r.medication_id}
                        className="cursor-pointer"
                        onClick={() => router.push(`/cc/medications/${r.medication_id}`)}
                      >
                        <td>
                          <div className="flex items-center gap-1.5">
                            <span className="font-medium text-slate-900">
                              {r.brand_name}
                            </span>
                            {r.is_essential && <EssentialTag label="Ess." />}
                          </div>
                          <div className="text-2xs text-slate-500">{r.dci}</div>
                        </td>
                        <td className="text-end font-figure text-xs">
                          {formatCompact(r.quantity)}
                        </td>
                        <td className="text-end font-figure text-xs font-semibold">
                          {r.coverage_days != null ? `${r.coverage_days.toFixed(0)} j` : "—"}
                        </td>
                        <td>
                          <RiskBadge severity={sev} label={SEVERITY_LABEL[sev]} size="sm" />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState>Aucune donnée de couverture.</EmptyState>
          )}
        </Panel>
      </div>

      <Panel
        title="Inventaire national complet"
        subtitle={`${rows.length} lignes`}
        bodyClassName="p-0"
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <SegmentedControl<Filter>
              ariaLabel="Filtrer l'inventaire"
              value={filter}
              onChange={setFilter}
              options={[
                { value: "all", label: "Tous" },
                { value: "essential", label: "Essentiels" },
                { value: "at_risk", label: "En tension" },
              ]}
            />
            <SegmentedControl<"coverage" | "value" | "quantity">
              ariaLabel="Trier l'inventaire"
              value={sort}
              onChange={setSort}
              options={[
                { value: "coverage", label: "Couverture" },
                { value: "value", label: "Valeur" },
                { value: "quantity", label: "Quantité" },
              ]}
            />
          </div>
        }
      >
        {stockQ.isLoading ? (
          <div className="p-4">
            <SkeletonRows rows={10} />
          </div>
        ) : rows.length ? (
          <div className="max-h-[520px] overflow-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Médicament</th>
                  <th>DCI</th>
                  <th className="text-end">Quantité</th>
                  <th className="text-end">Prix unit.</th>
                  <th className="text-end">Valeur</th>
                  <th className="text-end">Couverture</th>
                  <th>Niveau</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => {
                  const sev = coverageSeverity(r.coverage_days);
                  return (
                    <tr
                      key={r.medication_id}
                      className="cursor-pointer"
                      onClick={() => router.push(`/cc/medications/${r.medication_id}`)}
                    >
                      <td>
                        <div className="flex items-center gap-1.5">
                          <span className="font-medium text-slate-900">{r.brand_name}</span>
                          {r.is_essential && <EssentialTag label="Ess." />}
                        </div>
                      </td>
                      <td className="text-xs text-slate-500">{r.dci}</td>
                      <td className="text-end font-figure text-xs">
                        {formatInt(r.quantity)}
                      </td>
                      <td className="text-end font-figure text-xs text-slate-500">
                        {r.unit_price_tnd.toFixed(2)}
                      </td>
                      <td className="text-end font-figure text-xs">
                        {formatCompact(r.quantity * r.unit_price_tnd)}
                      </td>
                      <td className="text-end font-figure text-xs font-semibold">
                        {r.coverage_days != null ? `${r.coverage_days.toFixed(0)} j` : "—"}
                      </td>
                      <td>
                        <RiskBadge severity={sev} label={SEVERITY_LABEL[sev]} size="sm" />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState icon={<Timer className="h-5 w-5 text-slate-300" />}>
            Aucune ligne pour ce filtre.
          </EmptyState>
        )}
      </Panel>
    </div>
  );
}
