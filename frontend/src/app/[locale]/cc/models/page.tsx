"use client";

import { useMemo } from "react";
import { useRouter } from "@/i18n/routing";
import { useModelRuns, useShortages } from "@/lib/queries";
import {
  EmptyState,
  KpiCard,
  MeterBar,
  Panel,
  RiskBadge,
  SkeletonRows,
} from "@/components/ui";
import { formatDate, severityRank } from "@/lib/utils";
import { useTranslations } from "next-intl";
import { Brain, GitBranch, ShieldAlert, Target } from "lucide-react";
import type { ModelRun } from "@/lib/types";

/** Metric display names + whether lower is better. */
const METRIC_META: Record<string, { label: string; lowerIsBetter: boolean; pct?: boolean }> = {
  wape: { label: "WAPE", lowerIsBetter: true, pct: true },
  mape: { label: "MAPE", lowerIsBetter: true, pct: true },
  rmse: { label: "RMSE", lowerIsBetter: true },
  pinball: { label: "Perte pinball", lowerIsBetter: true },
  auc: { label: "AUC", lowerIsBetter: false },
  pr_auc: { label: "PR-AUC", lowerIsBetter: false },
};

export default function ModelsPage() {
  const tsev = useTranslations("severity");
  const router = useRouter();
  const runsQ = useModelRuns();
  const shortagesQ = useShortages();

  const runs = useMemo(() => runsQ.data ?? [], [runsQ.data]);
  const champions = useMemo(() => runs.filter((r) => r.is_champion), [runs]);

  const demandChampions = champions
    .filter((r) => r.horizon_days != null)
    .sort((a, b) => (a.horizon_days ?? 0) - (b.horizon_days ?? 0));

  // Runs arrive newest-first, but don't rely on that for a headline figure.
  const latestTrainedAt = useMemo(() => {
    const stamps = runs
      .map((r) => r.trained_at)
      .filter((v): v is string => Boolean(v));
    return stamps.length ? stamps.sort().at(-1)! : null;
  }, [runs]);

  const bestWape = useMemo(() => {
    const vals = demandChampions
      .map((r) => r.metrics?.wape)
      .filter((v): v is number => typeof v === "number");
    return vals.length ? Math.min(...vals) : null;
  }, [demandChampions]);

  /** Predictions that carry a stored SHAP explanation, worst first. */
  const explained = useMemo(
    () =>
      [...(shortagesQ.data?.items ?? [])]
        .filter((s) => s.governorate_id === null)
        .sort(
          (a, b) =>
            severityRank(b.severity) - severityRank(a.severity) ||
            b.probability - a.probability
        )
        .slice(0, 10),
    [shortagesQ.data]
  );

  if (runsQ.isError) {
    return (
      <EmptyState icon={<ShieldAlert className="h-5 w-5 text-slate-300" />}>
        La gouvernance des modèles est réservée au profil <strong>Admin PCT</strong>.
      </EmptyState>
    );
  }

  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-xl font-bold text-slate-900">Modèles &amp; explicabilité</h1>
        <p className="text-xs text-slate-500">
          Quel modèle est en production, ce qu&apos;il vaut sur données de test, et
          pourquoi il a produit chaque prédiction. Aucune décision opaque.
        </p>
      </header>

      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <KpiCard
          label="Modèles entraînés"
          value={runs.length}
          hint="Toutes familles et horizons"
          icon={<Brain className="h-4 w-4" />}
        />
        <KpiCard
          label="Champions en production"
          value={champions.length}
          hint="Un par horizon + classifieur"
          icon={<GitBranch className="h-4 w-4" />}
        />
        <KpiCard
          label="Meilleur WAPE"
          value={bestWape != null ? `${(bestWape * 100).toFixed(1)}` : "—"}
          unit="%"
          hint="Erreur pondérée, horizon court"
          icon={<Target className="h-4 w-4" />}
        />
        <KpiCard
          label="Dernier entraînement"
          value={
            latestTrainedAt ? (
              <span className="text-lg">{formatDate(latestTrainedAt)}</span>
            ) : (
              "—"
            )
          }
          hint={champions.length ? `${champions.length} champions promus` : undefined}
        />
      </div>

      <Panel
        title="Champions par horizon"
        subtitle="Sélectionnés par WAPE en validation à origine glissante (3 plis)"
        bodyClassName="p-0"
      >
        {runsQ.isLoading ? (
          <div className="p-4">
            <SkeletonRows rows={4} />
          </div>
        ) : demandChampions.length ? (
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Horizon</th>
                  <th>Famille</th>
                  <th>Type</th>
                  <th className="text-end">WAPE</th>
                  <th className="text-end">MAPE</th>
                  <th className="text-end">RMSE</th>
                  <th>Entraîné le</th>
                </tr>
              </thead>
              <tbody>
                {demandChampions.map((r) => (
                  <tr key={r.id}>
                    <td className="font-figure font-semibold">{r.horizon_days} j</td>
                    <td>
                      <span className="inline-flex items-center gap-1.5">
                        <span className="rounded bg-brand-50 px-1.5 py-0.5 text-2xs font-semibold uppercase text-brand-800">
                          champion
                        </span>
                        {r.model_family}
                      </span>
                    </td>
                    <td className="text-xs text-slate-500">{r.model_type}</td>
                    <td className="text-end font-figure text-xs font-semibold">
                      {fmtMetric(r.metrics?.wape, true)}
                    </td>
                    <td className="text-end font-figure text-xs">
                      {fmtMetric(r.metrics?.mape, true)}
                    </td>
                    <td className="text-end font-figure text-xs">
                      {fmtMetric(r.metrics?.rmse, false)}
                    </td>
                    <td className="text-xs text-slate-500">{formatDate(r.trained_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState>
            Aucun modèle enregistré. Lancez <code>make train</code>.
          </EmptyState>
        )}
      </Panel>

      <div className="grid gap-4 xl:grid-cols-2">
        <Panel
          title="Toutes les exécutions"
          subtitle="Comparaison des familles candidates"
          bodyClassName="p-0"
          className="max-h-[480px]"
        >
          {runsQ.isLoading ? (
            <div className="p-4">
              <SkeletonRows rows={8} />
            </div>
          ) : runs.length ? (
            <div className="max-h-[420px] overflow-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Famille</th>
                    <th>Horizon</th>
                    <th className="text-end">WAPE</th>
                    <th>Statut</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map((r) => (
                    <tr key={r.id}>
                      <td className="font-medium">{r.model_family}</td>
                      <td className="font-figure text-xs">
                        {r.horizon_days ? `${r.horizon_days} j` : "—"}
                      </td>
                      <td className="text-end font-figure text-xs">
                        {fmtMetric(r.metrics?.wape, true)}
                      </td>
                      <td>
                        {r.is_champion ? (
                          <span className="rounded bg-brand-50 px-1.5 py-0.5 text-2xs font-semibold uppercase text-brand-800">
                            production
                          </span>
                        ) : (
                          <span className="text-2xs text-slate-400">candidat</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState>Aucune exécution.</EmptyState>
          )}
        </Panel>

        <Panel
          title="Prédictions expliquées"
          subtitle="Chaque ligne ouvre son analyse SHAP détaillée"
          bodyClassName="p-0"
          className="max-h-[480px]"
        >
          {shortagesQ.isLoading ? (
            <div className="p-4">
              <SkeletonRows rows={8} />
            </div>
          ) : explained.length ? (
            <ul className="max-h-[420px] divide-y divide-slate-100 overflow-y-auto">
              {explained.map((s) => (
                <li key={s.id}>
                  <button
                    onClick={() => router.push(`/cc/medications/${s.medication_id}`)}
                    className="flex w-full cursor-pointer items-center gap-3 px-4 py-2.5 text-start transition-colors duration-150 hover:bg-brand-50/60"
                  >
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium text-slate-900">
                        {s.medication?.brand_name ?? "—"}
                      </span>
                      <span className="mt-1 flex items-center gap-2">
                        <MeterBar
                          value={s.probability}
                          color="var(--portal-accent)"
                          className="w-24"
                        />
                        <span className="font-figure text-2xs text-slate-500">
                          p = {(s.probability * 100).toFixed(1)}%
                        </span>
                      </span>
                    </span>
                    <RiskBadge severity={s.severity} label={tsev(s.severity)} size="sm" />
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState>Aucune prédiction disponible.</EmptyState>
          )}
        </Panel>
      </div>

      <Panel title="Comment lire ces chiffres" subtitle="Note méthodologique">
        <dl className="grid gap-3 text-xs sm:grid-cols-2 lg:grid-cols-4">
          {Object.entries(METRIC_META).map(([key, m]) => (
            <div key={key} className="rounded-md border border-slate-100 bg-slate-50 p-3">
              <dt className="font-semibold text-slate-800">{m.label}</dt>
              <dd className="mt-1 leading-relaxed text-slate-500">
                {METRIC_HELP[key]}
                <span className="mt-1 block text-2xs text-slate-400">
                  {m.lowerIsBetter ? "Plus bas = meilleur" : "Plus haut = meilleur"}
                </span>
              </dd>
            </div>
          ))}
        </dl>
      </Panel>
    </div>
  );
}

const METRIC_HELP: Record<string, string> = {
  wape: "Erreur absolue totale rapportée au volume total. Robuste aux séries à faible volume, d'où son usage comme critère de champion.",
  mape: "Erreur relative moyenne par point. Instable quand la demande approche zéro.",
  rmse: "Écart quadratique moyen, exprimé en unités de boîtes. Pénalise fortement les grosses erreurs.",
  pinball: "Qualité des quantiles 0,1 / 0,5 / 0,9 — mesure la fiabilité des intervalles de confiance.",
  auc: "Capacité du classifieur à ordonner correctement les cas de rupture.",
  pr_auc: "Précision/rappel sur la classe rare (rupture) — plus informatif que l'AUC quand les ruptures sont peu fréquentes.",
};

function fmtMetric(v: number | undefined, asPct: boolean): string {
  if (v == null) return "—";
  return asPct ? `${(v * 100).toFixed(1)}%` : v.toFixed(1);
}
