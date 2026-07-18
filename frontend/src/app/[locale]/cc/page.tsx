"use client";

import dynamic from "next/dynamic";
import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "@/i18n/routing";
import {
  useAlerts,
  useRecommendations,
  useShortageMap,
  useShortages,
  useStockAnalysis,
} from "@/lib/queries";
import {
  EmptyState,
  KpiCard,
  MeterBar,
  Panel,
  RiskBadge,
  SegmentedControl,
  SeverityLegend,
  SkeletonRows,
  EssentialTag,
} from "@/components/ui";
import {
  SEVERITY_COLORS,
  formatCompact,
  formatDate,
  formatTND,
  severityRank,
} from "@/lib/utils";
import type { Severity } from "@/lib/types";
import { AlertTriangle, Boxes, ClipboardList, Activity } from "lucide-react";

const TunisiaMap = dynamic(
  () => import("@/components/tunisia-map").then((m) => m.TunisiaMap),
  { ssr: false, loading: () => <div className="skeleton h-[460px] w-full" /> }
);

type HorizonFilter = 7 | 14 | 30 | 90;

export default function CommandCenterDashboard() {
  const t = useTranslations("commandCenter");
  const tsev = useTranslations("severity");
  const router = useRouter();

  const [horizon, setHorizon] = useState<HorizonFilter>(30);

  const mapQ = useShortageMap();
  const shortagesQ = useShortages();
  const recsQ = useRecommendations("proposed");
  const stockQ = useStockAnalysis();
  const alertsQ = useAlerts();

  /** National rows (governorate_id === null) at the selected horizon. */
  const national = useMemo(() => {
    return (shortagesQ.data?.items ?? []).filter(
      (s) => s.governorate_id === null && s.horizon_days === horizon
    );
  }, [shortagesQ.data, horizon]);

  const kpis = useMemo(() => {
    const atRisk = national.filter((s) => severityRank(s.severity) >= 2).length;
    const critical = national.filter((s) => s.severity === "critical").length;
    return {
      atRisk,
      critical,
      tracked: national.length,
      openRecs: recsQ.data?.total ?? 0,
      recValue: (recsQ.data?.items ?? []).reduce(
        (a, r) => a + (r.financial_impact_tnd ?? 0),
        0
      ),
    };
  }, [national, recsQ.data]);

  const board = useMemo(
    () =>
      [...national]
        .sort(
          (a, b) =>
            severityRank(b.severity) - severityRank(a.severity) ||
            b.probability - a.probability
        )
        .slice(0, 14),
    [national]
  );

  const unacked = (alertsQ.data ?? []).filter((a) => !a.acknowledged_at);

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900">{t("title")}</h1>
          <p className="text-xs text-slate-500">{t("subtitle")}</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-2xs font-medium uppercase tracking-wide text-slate-400">
            Horizon
          </span>
          <SegmentedControl<HorizonFilter>
            ariaLabel="Horizon de prévision"
            value={horizon}
            onChange={setHorizon}
            options={[
              { value: 7, label: "7 j" },
              { value: 14, label: "14 j" },
              { value: 30, label: "30 j" },
              { value: 90, label: "90 j" },
            ]}
          />
        </div>
      </header>

      {/* KPI strip */}
      <div className="grid grid-cols-2 gap-3 xl:grid-cols-5">
        <KpiCard
          label={t("medsAtRisk")}
          value={kpis.atRisk}
          unit={`/ ${kpis.tracked}`}
          hint={`Niveau orange ou pire · ${horizon} j`}
          severity={kpis.atRisk > 0 ? "orange" : "green"}
          icon={<AlertTriangle className="h-4 w-4" />}
        />
        <KpiCard
          label={t("criticalCount")}
          value={kpis.critical}
          hint="Action immédiate requise"
          severity={kpis.critical > 0 ? "critical" : "green"}
          icon={<Activity className="h-4 w-4" />}
        />
        <KpiCard
          label="Couverture médiane"
          value={stockQ.data ? stockQ.data.median_coverage_days : "—"}
          unit="jours"
          hint="Stock national / demande prévue"
          icon={<Boxes className="h-4 w-4" />}
        />
        <KpiCard
          label={t("openRecommendations")}
          value={kpis.openRecs}
          hint={kpis.recValue > 0 ? formatTND(kpis.recValue) : "En attente de validation"}
          icon={<ClipboardList className="h-4 w-4" />}
        />
        <KpiCard
          label="Alertes non traitées"
          value={unacked.length}
          hint={`${alertsQ.data?.length ?? 0} au total`}
          severity={unacked.length > 20 ? "red" : unacked.length > 0 ? "yellow" : "green"}
          icon={<AlertTriangle className="h-4 w-4" />}
        />
      </div>

      {/* Map + risk board */}
      <div className="grid gap-4 xl:grid-cols-3">
        <Panel
          className="xl:col-span-2"
          title={t("riskMap")}
          subtitle="Part des médicaments en tension par gouvernorat — cliquez pour filtrer"
          actions={<SeverityLegend labelFor={(s) => tsev(s)} />}
          bodyClassName="p-3"
        >
          {mapQ.isLoading ? (
            <div className="skeleton h-[460px] w-full" />
          ) : mapQ.data ? (
            <TunisiaMap
              data={mapQ.data}
              onSelect={(gid) => router.push(`/cc/shortages?governorate=${gid}`)}
            />
          ) : (
            <EmptyState>
              Carte réservée aux profils Admin PCT et Autorité régionale.
            </EmptyState>
          )}
        </Panel>

        <Panel
          title={t("riskBoard")}
          subtitle={`${board.length} médicaments · horizon ${horizon} jours`}
          bodyClassName="p-0"
          className="max-h-[560px]"
        >
          {shortagesQ.isLoading ? (
            <div className="p-4">
              <SkeletonRows rows={8} />
            </div>
          ) : board.length ? (
            <ul className="divide-y divide-slate-100 overflow-y-auto">
              {board.map((s) => (
                <li key={s.id}>
                  <button
                    onClick={() => router.push(`/cc/medications/${s.medication_id}`)}
                    className="flex w-full cursor-pointer items-center gap-3 px-4 py-2.5 text-start transition-colors duration-150 hover:bg-brand-50/60"
                  >
                    <span
                      aria-hidden
                      className="h-8 w-1 shrink-0 rounded-full"
                      style={{ backgroundColor: SEVERITY_COLORS[s.severity] }}
                    />
                    <span className="min-w-0 flex-1">
                      <span className="flex items-center gap-1.5">
                        <span className="truncate text-sm font-medium text-slate-900">
                          {s.medication?.brand_name ?? "Médicament inconnu"}
                        </span>
                        {s.medication?.is_essential && <EssentialTag label="Ess." />}
                      </span>
                      <span className="mt-0.5 block truncate text-2xs text-slate-500">
                        {s.medication?.dci} ·{" "}
                        {s.coverage_days != null
                          ? `${s.coverage_days.toFixed(0)} j de couverture`
                          : "couverture inconnue"}
                        {s.estimated_shortage_date &&
                          ` · rupture ~${formatDate(s.estimated_shortage_date)}`}
                      </span>
                    </span>
                    <RiskBadge severity={s.severity} label={tsev(s.severity)} size="sm" />
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState>
              Aucune prédiction à cet horizon. Lancez <code>make score</code> ou
              choisissez un autre horizon.
            </EmptyState>
          )}
        </Panel>
      </div>

      {/* Coverage distribution + top recommendations */}
      <div className="grid gap-4 xl:grid-cols-3">
        <Panel
          title="Distribution de la couverture nationale"
          subtitle={
            stockQ.data
              ? `${stockQ.data.total_medications} médicaments · ${formatCompact(
                  stockQ.data.total_units
                )} unités · ${formatTND(stockQ.data.total_value_tnd)}`
              : undefined
          }
        >
          {stockQ.isLoading ? (
            <SkeletonRows rows={5} />
          ) : stockQ.data ? (
            <CoverageBars
              buckets={stockQ.data.buckets}
              total={stockQ.data.total_medications}
              onSelect={() => router.push("/cc/stock")}
            />
          ) : (
            <EmptyState>Analyse réservée aux profils PCT / régional.</EmptyState>
          )}
        </Panel>

        <Panel
          className="xl:col-span-2"
          title="Recommandations prioritaires"
          subtitle="Aide à la décision — validation humaine obligatoire"
          bodyClassName="p-0"
        >
          {recsQ.isLoading ? (
            <div className="p-4">
              <SkeletonRows rows={5} />
            </div>
          ) : recsQ.data?.items.length ? (
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Médicament</th>
                    <th>Action</th>
                    <th className="text-end">Quantité</th>
                    <th className="text-end">Impact</th>
                    <th className="w-28">Confiance</th>
                  </tr>
                </thead>
                <tbody>
                  {[...recsQ.data.items]
                    .sort((a, b) => b.confidence - a.confidence)
                    .slice(0, 8)
                    .map((r) => (
                      <tr
                        key={r.id}
                        className="cursor-pointer"
                        onClick={() => router.push("/cc/recommendations")}
                      >
                        <td>
                          <div className="font-medium text-slate-900">
                            {r.medication?.brand_name ?? "—"}
                          </div>
                          <div className="text-2xs text-slate-500">
                            {r.governorate_name ?? "National"}
                          </div>
                        </td>
                        <td className="text-xs text-slate-600">{r.title_fr}</td>
                        <td className="text-end font-figure text-xs">
                          {r.suggested_quantity != null
                            ? formatCompact(r.suggested_quantity)
                            : "—"}
                        </td>
                        <td className="text-end font-figure text-xs">
                          {r.financial_impact_tnd > 0
                            ? formatTND(r.financial_impact_tnd)
                            : "—"}
                        </td>
                        <td>
                          <div className="flex items-center gap-2">
                            <MeterBar
                              value={r.confidence}
                              color="var(--portal-accent)"
                              className="flex-1"
                            />
                            <span className="font-figure text-2xs text-slate-500">
                              {Math.round(r.confidence * 100)}%
                            </span>
                          </div>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState>Aucune recommandation en attente.</EmptyState>
          )}
        </Panel>
      </div>
    </div>
  );
}

/**
 * Coverage distribution as a labelled bar list rather than a pie: the reader's
 * job is comparing band sizes, which lengths do better than angles.
 */
function CoverageBars({
  buckets,
  total,
  onSelect,
}: {
  buckets: { label: string; count: number; severity: Severity; min_days: number; max_days: number | null }[];
  total: number;
  onSelect: () => void;
}) {
  const max = Math.max(1, ...buckets.map((b) => b.count));
  return (
    <div className="space-y-2.5">
      {buckets.map((b) => (
        <button
          key={b.label}
          onClick={onSelect}
          className="flex w-full cursor-pointer items-center gap-3 rounded px-1 py-0.5 text-start transition-colors duration-150 hover:bg-slate-50"
        >
          <span className="w-32 shrink-0 text-xs text-slate-600">{b.label}</span>
          <span className="flex-1">
            <span
              className="block h-4 rounded-sm transition-[width] duration-300"
              style={{
                width: `${(b.count / max) * 100}%`,
                backgroundColor: SEVERITY_COLORS[b.severity],
                minWidth: b.count > 0 ? "3px" : "0",
              }}
            />
          </span>
          <span className="w-16 shrink-0 text-end font-figure text-xs text-slate-700">
            {b.count}
            <span className="text-slate-400">
              {" "}
              ({total ? Math.round((b.count / total) * 100) : 0}%)
            </span>
          </span>
        </button>
      ))}
      <p className="pt-1 text-2xs text-slate-400">
        Bandes en jours de couverture : &lt;5, 5–15, 15–30, 30–60, 60+.
      </p>
    </div>
  );
}
