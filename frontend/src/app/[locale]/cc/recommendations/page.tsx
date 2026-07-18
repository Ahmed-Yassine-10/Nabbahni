"use client";

import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "@/i18n/routing";
import { useRecommendations, useRecommendationAction } from "@/lib/queries";
import {
  Button,
  EmptyState,
  EssentialTag,
  KpiCard,
  MeterBar,
  Panel,
  SegmentedControl,
  SkeletonRows,
} from "@/components/ui";
import { formatCompact, formatTND } from "@/lib/utils";
import { Check, X, TrendingDown, ClipboardList, Coins, ShieldCheck } from "lucide-react";

const REC_TYPE: Record<string, { label: string; tone: string }> = {
  emergency_procurement: { label: "Procédure d'urgence", tone: "#7f1d1d" },
  increase_import: { label: "Augmenter les importations", tone: "#b45309" },
  redistribute: { label: "Redistribuer les stocks", tone: "#1e40af" },
  prioritize_hospitals: { label: "Prioriser les hôpitaux", tone: "#6d28d9" },
  adjust_order: { label: "Ajuster les commandes", tone: "#0f766e" },
};

type StatusTab = "proposed" | "validated" | "rejected";

export default function RecommendationsPage() {
  const t = useTranslations("recommendations");
  const router = useRouter();
  const [tab, setTab] = useState<StatusTab>("proposed");
  const { data, isLoading, isError } = useRecommendations(tab);
  const action = useRecommendationAction();

  const items = useMemo(
    () => [...(data?.items ?? [])].sort((a, b) => b.confidence - a.confidence),
    [data]
  );

  const totals = useMemo(
    () => ({
      value: items.reduce((a, r) => a + (r.financial_impact_tnd ?? 0), 0),
      units: items.reduce((a, r) => a + (r.suggested_quantity ?? 0), 0),
      avgConfidence: items.length
        ? items.reduce((a, r) => a + r.confidence, 0) / items.length
        : 0,
    }),
    [items]
  );

  if (isError) {
    return (
      <EmptyState>
        Les recommandations sont réservées aux profils <strong>Admin PCT</strong> et{" "}
        <strong>Autorité régionale</strong>.
      </EmptyState>
    );
  }

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900">{t("title")}</h1>
          <p className="text-xs text-slate-500">
            Aide à la décision générée par règles explicites à partir des
            prédictions. Un officier PCT valide chaque action.
          </p>
        </div>
        <SegmentedControl<StatusTab>
          ariaLabel="Statut"
          value={tab}
          onChange={setTab}
          options={[
            { value: "proposed", label: "À valider" },
            { value: "validated", label: "Validées" },
            { value: "rejected", label: "Rejetées" },
          ]}
        />
      </header>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard
          label="Recommandations"
          value={data?.total ?? 0}
          icon={<ClipboardList className="h-4 w-4" />}
        />
        <KpiCard
          label="Impact financier"
          value={formatCompact(totals.value)}
          unit="TND"
          hint={formatTND(totals.value)}
          icon={<Coins className="h-4 w-4" />}
        />
        <KpiCard
          label="Unités proposées"
          value={formatCompact(totals.units)}
          icon={<ClipboardList className="h-4 w-4" />}
        />
        <KpiCard
          label="Confiance moyenne"
          value={`${Math.round(totals.avgConfidence * 100)}`}
          unit="%"
          icon={<ShieldCheck className="h-4 w-4" />}
        />
      </div>

      {isLoading ? (
        <Panel title="Chargement">
          <SkeletonRows rows={6} />
        </Panel>
      ) : items.length ? (
        <div className="grid gap-3 lg:grid-cols-2 2xl:grid-cols-3">
          {items.map((r) => {
            const meta = REC_TYPE[r.rec_type] ?? { label: r.rec_type, tone: "#475569" };
            return (
              <article
                key={r.id}
                className="flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-card"
              >
                <div className="flex items-start justify-between gap-2">
                  <span
                    className="rounded px-1.5 py-0.5 text-2xs font-semibold uppercase tracking-wide"
                    style={{ color: meta.tone, backgroundColor: `${meta.tone}14` }}
                  >
                    {meta.label}
                  </span>
                  <span className="text-2xs text-slate-400">
                    {r.governorate_name ?? "National"}
                  </span>
                </div>

                <button
                  onClick={() => router.push(`/cc/medications/${r.medication_id}`)}
                  className="cursor-pointer text-start"
                >
                  <span className="flex items-center gap-1.5">
                    <span className="text-sm font-semibold text-slate-900 hover:underline">
                      {r.medication?.brand_name ?? r.title_fr}
                    </span>
                    {r.medication?.is_essential && <EssentialTag label="Ess." />}
                  </span>
                  {r.medication?.dci && (
                    <span className="mt-0.5 block text-2xs text-slate-500">
                      {r.medication.dci}
                    </span>
                  )}
                </button>

                <p className="text-xs leading-relaxed text-slate-600">{r.detail_fr}</p>

                <dl className="grid grid-cols-3 gap-2 rounded-md bg-slate-50 p-2.5 text-center">
                  <div>
                    <dd className="font-figure text-sm font-semibold text-slate-900">
                      {r.suggested_quantity != null
                        ? formatCompact(r.suggested_quantity)
                        : "—"}
                    </dd>
                    <dt className="text-2xs uppercase text-slate-400">Unités</dt>
                  </div>
                  <div>
                    <dd className="font-figure text-sm font-semibold text-slate-900">
                      {r.financial_impact_tnd > 0
                        ? formatCompact(r.financial_impact_tnd)
                        : "—"}
                    </dd>
                    <dt className="text-2xs uppercase text-slate-400">TND</dt>
                  </div>
                  <div>
                    <dd className="flex items-center justify-center gap-0.5 font-figure text-sm font-semibold text-emerald-700">
                      <TrendingDown aria-hidden className="h-3 w-3" />
                      {Math.round(r.expected_shortage_reduction_pct)}%
                    </dd>
                    <dt className="text-2xs uppercase text-slate-400">Risque</dt>
                  </div>
                </dl>

                <div>
                  <div className="mb-1 flex items-center justify-between text-2xs text-slate-500">
                    <span>{t("confidence")}</span>
                    <span className="font-figure font-semibold">
                      {Math.round(r.confidence * 100)}%
                    </span>
                  </div>
                  <MeterBar value={r.confidence} color="var(--portal-accent)" />
                </div>

                {r.status === "proposed" ? (
                  <div className="flex gap-2">
                    <Button
                      disabled={action.isPending}
                      onClick={() => action.mutate({ id: r.id, action: "validate" })}
                      className="flex-1 bg-emerald-600 hover:bg-emerald-700"
                    >
                      <Check aria-hidden className="h-4 w-4" /> {t("validate")}
                    </Button>
                    <Button
                      variant="secondary"
                      disabled={action.isPending}
                      onClick={() => action.mutate({ id: r.id, action: "reject" })}
                      className="flex-1"
                    >
                      <X aria-hidden className="h-4 w-4" /> {t("reject")}
                    </Button>
                  </div>
                ) : (
                  <p className="text-2xs text-slate-400">
                    {r.status === "validated" ? "Validée" : "Rejetée"}
                    {r.validated_at ? ` le ${new Date(r.validated_at).toLocaleDateString("fr-FR")}` : ""}
                  </p>
                )}
              </article>
            );
          })}
        </div>
      ) : (
        <EmptyState>
          {tab === "proposed"
            ? "Aucune recommandation en attente de validation."
            : `Aucune recommandation ${tab === "validated" ? "validée" : "rejetée"}.`}
        </EmptyState>
      )}
    </div>
  );
}
