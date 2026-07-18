"use client";

import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "@/i18n/routing";
import { useAlerts } from "@/lib/queries";
import {
  EmptyState,
  EssentialTag,
  KpiCard,
  Panel,
  RiskBadge,
  SegmentedControl,
  SkeletonRows,
} from "@/components/ui";
import { SEVERITY_COLORS, severityRank } from "@/lib/utils";
import type { Severity } from "@/lib/types";
import { Bell, BellRing, CheckCircle2 } from "lucide-react";

type Filter = "all" | "unacked" | "severe";

export default function AlertsPage() {
  const tsev = useTranslations("severity");
  const router = useRouter();
  const { data, isLoading } = useAlerts();
  const [filter, setFilter] = useState<Filter>("all");

  // Memoised so the derived lists below get a stable dependency.
  const alerts = useMemo(() => data ?? [], [data]);
  const unacked = useMemo(
    () => alerts.filter((a) => !a.acknowledged_at),
    [alerts]
  );
  const severe = useMemo(
    () => alerts.filter((a) => severityRank(a.severity) >= 3),
    [alerts]
  );

  const visible = useMemo(() => {
    const list =
      filter === "unacked" ? unacked : filter === "severe" ? severe : alerts;
    return [...list].sort(
      (a, b) =>
        severityRank(b.severity) - severityRank(a.severity) ||
        +new Date(b.created_at) - +new Date(a.created_at)
    );
  }, [alerts, filter, unacked, severe]);

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Alertes</h1>
          <p className="text-xs text-slate-500">
            Générées automatiquement à chaque cycle de scoring, portée nationale
            ou régionale.
          </p>
        </div>
        <SegmentedControl<Filter>
          ariaLabel="Filtrer les alertes"
          value={filter}
          onChange={setFilter}
          options={[
            { value: "all", label: "Toutes" },
            { value: "unacked", label: "Non traitées" },
            { value: "severe", label: "Graves" },
          ]}
        />
      </header>

      <div className="grid grid-cols-3 gap-3">
        <KpiCard label="Total" value={alerts.length} icon={<Bell className="h-4 w-4" />} />
        <KpiCard
          label="Non traitées"
          value={unacked.length}
          severity={unacked.length > 0 ? "orange" : "green"}
          icon={<BellRing className="h-4 w-4" />}
        />
        <KpiCard
          label="Graves (rouge / critique)"
          value={severe.length}
          severity={severe.length > 0 ? "red" : "green"}
          icon={<CheckCircle2 className="h-4 w-4" />}
        />
      </div>

      <Panel title={`${visible.length} alertes`} bodyClassName="p-0">
        {isLoading ? (
          <div className="p-4">
            <SkeletonRows rows={10} />
          </div>
        ) : visible.length ? (
          <ul className="divide-y divide-slate-100">
            {visible.map((a) => (
              <li key={a.id} className="flex items-start gap-3 px-4 py-3">
                <span
                  aria-hidden
                  className="mt-0.5 h-10 w-1 shrink-0 rounded-full"
                  style={{ backgroundColor: SEVERITY_COLORS[a.severity as Severity] }}
                />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <RiskBadge severity={a.severity} label={tsev(a.severity)} size="sm" />
                    <span className="text-2xs uppercase tracking-wide text-slate-400">
                      {a.scope === "national" ? "National" : a.governorate_name ?? a.scope}
                    </span>
                    {a.medication?.is_essential && <EssentialTag label="Essentiel" />}
                    {!a.acknowledged_at && (
                      <span className="rounded bg-amber-50 px-1.5 py-0.5 text-2xs font-semibold text-amber-700">
                        non traitée
                      </span>
                    )}
                  </div>
                  <button
                    onClick={() =>
                      a.medication_id && router.push(`/cc/medications/${a.medication_id}`)
                    }
                    disabled={!a.medication_id}
                    className="mt-1 block text-start text-sm font-medium text-slate-900 enabled:cursor-pointer enabled:hover:underline"
                  >
                    {a.medication?.brand_name ?? a.title_fr}
                  </button>
                  <p className="mt-0.5 text-xs leading-relaxed text-slate-500">
                    {a.body_fr}
                  </p>
                </div>
                <time
                  dateTime={a.created_at}
                  className="shrink-0 font-figure text-2xs text-slate-400"
                >
                  {new Date(a.created_at).toLocaleDateString("fr-FR", {
                    day: "2-digit",
                    month: "2-digit",
                  })}
                </time>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState>Aucune alerte pour ce filtre.</EmptyState>
        )}
      </Panel>
    </div>
  );
}
