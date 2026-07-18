"use client";

import { use, useMemo } from "react";
import { useTranslations, useLocale } from "next-intl";
import { useRouter } from "@/i18n/routing";
import { useForecasts, useMedication, useShortages, useSubstitutions } from "@/lib/queries";
import { ForecastChart } from "@/components/forecast-chart";
import { ExplanationPanel } from "@/components/explanation-panel";
import {
  EmptyState,
  EssentialTag,
  KpiCard,
  Panel,
  RiskBadge,
  SkeletonRows,
  Spinner,
} from "@/components/ui";
import { api } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import { formatDate, formatTND, severityRank } from "@/lib/utils";
import type { ShortageDetail } from "@/lib/types";
import { ArrowLeft, Repeat, TrendingUp } from "lucide-react";

const EQUIVALENCE_LABEL: Record<string, string> = {
  identical_dci: "Même DCI",
  same_atc4: "Même classe ATC niveau 4",
  same_atc3: "Même classe ATC niveau 3",
};

export default function MedicationDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const t = useTranslations("medication");
  const tsev = useTranslations("severity");
  const locale = useLocale();
  const router = useRouter();

  const medQ = useMedication(id);
  const forecastsQ = useForecasts(id);
  const shortagesQ = useShortages();
  const subsQ = useSubstitutions(id);

  const rowsForMed = useMemo(
    () => (shortagesQ.data?.items ?? []).filter((s) => s.medication_id === id),
    [shortagesQ.data, id]
  );

  const nationalRow = rowsForMed.find((s) => s.governorate_id === null);

  // Governorates where this medication is under pressure — the geographic
  // impact set the shortage engine produces.
  const affectedRegions = useMemo(
    () =>
      rowsForMed
        .filter((s) => s.governorate_id !== null && severityRank(s.severity) >= 2)
        .sort((a, b) => severityRank(b.severity) - severityRank(a.severity)),
    [rowsForMed]
  );

  const detailQ = useQuery({
    queryKey: ["shortage-detail", nationalRow?.id],
    queryFn: () => api<ShortageDetail>(`/api/v1/shortages/${nationalRow!.id}`),
    enabled: !!nationalRow?.id,
  });

  const med = medQ.data;

  if (medQ.isLoading) return <Spinner />;
  if (!med) return <EmptyState>Médicament introuvable.</EmptyState>;

  return (
    <div className="space-y-4">
      <button
        onClick={() => router.back()}
        className="flex cursor-pointer items-center gap-1 text-xs text-slate-500 hover:text-slate-800"
      >
        <ArrowLeft aria-hidden className="h-3.5 w-3.5" /> Retour
      </button>

      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-900">{med.brand_name}</h1>
            {med.is_essential && <EssentialTag />}
          </div>
          <p className="mt-0.5 text-xs text-slate-500">
            {med.dci} · {med.form} {med.dosage} · ATC{" "}
            <span className="font-figure">{med.atc_code}</span> ·{" "}
            {formatTND(med.unit_price_tnd)} l&apos;unité
          </p>
        </div>
        {detailQ.data && (
          <RiskBadge
            severity={detailQ.data.severity}
            label={tsev(detailQ.data.severity)}
          />
        )}
      </header>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard
          label="Probabilité de rupture"
          value={
            nationalRow ? `${(nationalRow.probability * 100).toFixed(1)}` : "—"
          }
          unit="%"
          hint={nationalRow ? `Horizon ${nationalRow.horizon_days} jours` : undefined}
          severity={nationalRow?.severity}
        />
        <KpiCard
          label="Couverture nationale"
          value={
            nationalRow?.coverage_days != null
              ? nationalRow.coverage_days.toFixed(0)
              : "—"
          }
          unit="jours"
        />
        <KpiCard
          label="Rupture estimée"
          value={
            nationalRow?.estimated_shortage_date
              ? formatDate(nationalRow.estimated_shortage_date)
              : "—"
          }
        />
        <KpiCard
          label="Gouvernorats en tension"
          value={affectedRegions.length}
          hint="Niveau orange ou pire"
          severity={affectedRegions.length > 0 ? "orange" : "green"}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Panel
          title={t("forecast")}
          subtitle="Demande nationale prévue par horizon"
          actions={<TrendingUp aria-hidden className="h-4 w-4 text-slate-300" />}
        >
          {forecastsQ.isLoading ? (
            <SkeletonRows rows={5} />
          ) : forecastsQ.data?.length ? (
            <ForecastChart forecasts={forecastsQ.data} />
          ) : (
            <EmptyState>
              Aucune prévision. Lancez <code>make score</code>.
            </EmptyState>
          )}
        </Panel>

        {detailQ.data?.explanation ? (
          <ExplanationPanel explanation={detailQ.data.explanation} locale={locale} />
        ) : (
          <Panel title={t("explanation")}>
            <EmptyState>
              {detailQ.isLoading
                ? "Chargement de l'explication…"
                : "Explication disponible après le scoring."}
            </EmptyState>
          </Panel>
        )}
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Panel
          title="Impact géographique"
          subtitle={`${affectedRegions.length} gouvernorats au niveau orange ou pire`}
          bodyClassName="p-0"
        >
          {affectedRegions.length ? (
            <div className="max-h-80 overflow-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Gouvernorat</th>
                    <th className="text-end">Probabilité</th>
                    <th className="text-end">Couverture</th>
                    <th>Niveau</th>
                  </tr>
                </thead>
                <tbody>
                  {affectedRegions.map((s) => (
                    <tr key={s.id}>
                      <td className="font-medium text-slate-900">
                        {s.governorate_name ?? "—"}
                      </td>
                      <td className="text-end font-figure text-xs">
                        {(s.probability * 100).toFixed(1)}%
                      </td>
                      <td className="text-end font-figure text-xs">
                        {s.coverage_days != null ? `${s.coverage_days.toFixed(0)} j` : "—"}
                      </td>
                      <td>
                        <RiskBadge
                          severity={s.severity}
                          label={tsev(s.severity)}
                          size="sm"
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState>
              Aucun gouvernorat en tension pour ce médicament.
            </EmptyState>
          )}
        </Panel>

        <Panel
          title="Substitutions possibles"
          subtitle="Équivalences ATC / DDD — à confirmer par un pharmacien"
          bodyClassName="p-0"
          actions={<Repeat aria-hidden className="h-4 w-4 text-slate-300" />}
        >
          {subsQ.isLoading ? (
            <div className="p-4">
              <SkeletonRows rows={4} />
            </div>
          ) : subsQ.data?.length ? (
            <ul className="max-h-80 divide-y divide-slate-100 overflow-auto">
              {subsQ.data.map((s) => (
                <li key={s.id} className="flex items-start justify-between gap-3 px-4 py-2.5">
                  <div className="min-w-0">
                    <button
                      onClick={() => router.push(`/cc/medications/${s.target.id}`)}
                      className="cursor-pointer text-sm font-medium text-slate-900 hover:underline"
                    >
                      {s.target.brand_name}
                    </button>
                    <div className="text-2xs text-slate-500">
                      {s.target.dci}
                      {s.ddd_ratio != null && ` · ratio DDD ${s.ddd_ratio.toFixed(2)}`}
                    </div>
                    {s.notes_fr && (
                      <p className="mt-0.5 text-2xs text-slate-400">{s.notes_fr}</p>
                    )}
                  </div>
                  <span className="shrink-0 rounded bg-slate-100 px-1.5 py-0.5 text-2xs text-slate-600">
                    {EQUIVALENCE_LABEL[s.equivalence] ?? `ATC ${s.atc_match_level}`}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState>Aucune substitution enregistrée.</EmptyState>
          )}
        </Panel>
      </div>
    </div>
  );
}
