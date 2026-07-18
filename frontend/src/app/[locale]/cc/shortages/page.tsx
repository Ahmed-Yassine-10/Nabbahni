"use client";

import { Suspense, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useRouter } from "@/i18n/routing";
import { useShortages } from "@/lib/queries";
import {
  EmptyState,
  EssentialTag,
  MeterBar,
  Panel,
  RiskBadge,
  SegmentedControl,
  SkeletonRows,
} from "@/components/ui";
import { formatDate, daysUntil, severityRank } from "@/lib/utils";
import type { Severity } from "@/lib/types";
import { Search } from "lucide-react";

type Scope = "national" | "regional";

/**
 * useSearchParams() opts the subtree out of static prerendering, so it lives
 * behind a Suspense boundary and the page shell can still be generated.
 */
export default function ShortagesPage() {
  return (
    <Suspense fallback={<SkeletonRows rows={12} />}>
      <ShortagesView />
    </Suspense>
  );
}

function ShortagesView() {
  const tsev = useTranslations("severity");
  const tc = useTranslations("common");
  const router = useRouter();
  const searchParams = useSearchParams();
  const governorateFilter = searchParams.get("governorate");

  const [severity, setSeverity] = useState<string>("");
  const [scope, setScope] = useState<Scope>(governorateFilter ? "regional" : "national");
  const [query, setQuery] = useState("");

  const { data, isLoading } = useShortages({
    ...(severity ? { severity } : {}),
    ...(governorateFilter ? { governorate: governorateFilter } : {}),
  });

  const rows = useMemo(() => {
    let list = (data?.items ?? []).filter((s) =>
      scope === "national" ? s.governorate_id === null : s.governorate_id !== null
    );
    if (query.trim()) {
      const q = query.toLowerCase();
      list = list.filter(
        (s) =>
          s.medication?.brand_name.toLowerCase().includes(q) ||
          s.medication?.dci.toLowerCase().includes(q) ||
          s.governorate_name?.toLowerCase().includes(q)
      );
    }
    return [...list].sort(
      (a, b) =>
        severityRank(b.severity) - severityRank(a.severity) ||
        b.probability - a.probability
    );
  }, [data, scope, query]);

  const severities: (Severity | "")[] = ["", "critical", "red", "orange", "yellow", "green"];

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Risques de rupture</h1>
          <p className="text-xs text-slate-500">
            {governorateFilter
              ? "Filtré sur un gouvernorat — retirez le filtre pour la vue nationale."
              : "Prédictions du moteur de rupture, triées par gravité."}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <SegmentedControl<Scope>
            ariaLabel="Périmètre"
            value={scope}
            onChange={setScope}
            options={[
              { value: "national", label: "National" },
              { value: "regional", label: "Par gouvernorat" },
            ]}
          />
          {governorateFilter && (
            <button
              onClick={() => router.push("/cc/shortages")}
              className="cursor-pointer rounded-md border border-slate-200 bg-white px-2.5 py-1 text-xs text-slate-600 hover:bg-slate-50"
            >
              Retirer le filtre
            </button>
          )}
        </div>
      </header>

      <Panel
        title={`${rows.length} prédictions`}
        subtitle="Cliquez une ligne pour voir la prévision et l'explication du modèle"
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
                placeholder="Médicament, DCI, gouvernorat…"
                aria-label="Rechercher"
                className="min-h-[2.25rem] w-52 rounded-md border border-slate-200 ps-7 pe-2 text-xs outline-none placeholder:text-slate-400 focus:border-slate-300"
              />
            </div>
            <div className="flex flex-wrap gap-1">
              {severities.map((s) => (
                <button
                  key={s || "all"}
                  onClick={() => setSeverity(s)}
                  aria-pressed={severity === s}
                  className={`cursor-pointer rounded-md px-2.5 py-1 text-xs font-medium transition-colors duration-150 ${
                    severity === s
                      ? "bg-slate-900 text-white"
                      : "border border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  {s ? tsev(s) : tc("all")}
                </button>
              ))}
            </div>
          </div>
        }
      >
        {isLoading ? (
          <div className="p-4">
            <SkeletonRows rows={12} />
          </div>
        ) : rows.length ? (
          <div className="max-h-[640px] overflow-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Médicament</th>
                  {scope === "regional" && <th>Gouvernorat</th>}
                  <th className="w-32">Probabilité</th>
                  <th className="text-end">Couverture</th>
                  <th>Rupture estimée</th>
                  <th>Niveau</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((s) => {
                  const dd = daysUntil(s.estimated_shortage_date);
                  return (
                    <tr
                      key={s.id}
                      className="cursor-pointer"
                      onClick={() => router.push(`/cc/medications/${s.medication_id}`)}
                    >
                      <td>
                        <div className="flex items-center gap-1.5">
                          <span className="font-medium text-slate-900">
                            {s.medication?.brand_name ?? "—"}
                          </span>
                          {s.medication?.is_essential && <EssentialTag label="Ess." />}
                        </div>
                        <div className="text-2xs text-slate-500">
                          {s.medication?.dci}
                          {s.medication?.atc_code ? ` · ${s.medication.atc_code}` : ""}
                        </div>
                      </td>
                      {scope === "regional" && (
                        <td className="text-xs text-slate-600">
                          {s.governorate_name ?? "—"}
                        </td>
                      )}
                      <td>
                        <div className="flex items-center gap-2">
                          <MeterBar
                            value={s.probability}
                            color="var(--portal-accent)"
                            className="flex-1"
                          />
                          <span className="font-figure text-2xs text-slate-500">
                            {(s.probability * 100).toFixed(1)}%
                          </span>
                        </div>
                      </td>
                      <td className="text-end font-figure text-xs font-semibold">
                        {s.coverage_days != null ? `${s.coverage_days.toFixed(0)} j` : "—"}
                      </td>
                      <td className="text-xs text-slate-600">
                        {formatDate(s.estimated_shortage_date)}
                        {dd != null && dd >= 0 && (
                          <span className="ms-1 text-2xs text-slate-400">
                            (dans {dd} j)
                          </span>
                        )}
                      </td>
                      <td>
                        <RiskBadge severity={s.severity} label={tsev(s.severity)} size="sm" />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState>{tc("noData")}</EmptyState>
        )}
      </Panel>
    </div>
  );
}
