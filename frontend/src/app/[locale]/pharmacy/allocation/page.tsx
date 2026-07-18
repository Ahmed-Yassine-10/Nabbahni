"use client";

import { useMemo, useState } from "react";
import { useMe, usePharmacyExpiry } from "@/lib/queries";
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
import { formatCompact, formatDate, formatInt, formatTND } from "@/lib/utils";
import { Coins, PackageCheck, Search, Trash2, TriangleAlert } from "lucide-react";

type View = "order" | "surplus" | "expiring";

/**
 * "Combien commander ?" — sized to what this pharmacy actually sells, not to a
 * fixed threshold. Ordering to a threshold is what produces expired stock in
 * the first place.
 */
export default function AllocationPage() {
  const meQ = useMe();
  const dataQ = usePharmacyExpiry(meQ.data?.pharmacy_id);
  const [view, setView] = useState<View>("order");
  const [query, setQuery] = useState("");

  const d = dataQ.data;

  const rows = useMemo(() => {
    const all = d?.allocations ?? [];
    let list =
      view === "order"
        ? all.filter((a) => a.recommended_quantity > 0)
        : view === "surplus"
          ? all.filter((a) => a.surplus_quantity > 0 || a.at_risk_quantity > 0)
          : all;
    if (query.trim()) {
      const q = query.toLowerCase();
      list = list.filter(
        (a) =>
          a.brand_name.toLowerCase().includes(q) || a.dci.toLowerCase().includes(q)
      );
    }
    return [...list].sort((a, b) =>
      view === "surplus"
        ? b.at_risk_value_tnd - a.at_risk_value_tnd
        : b.order_value_tnd - a.order_value_tnd
    );
  }, [d, view, query]);

  if (meQ.isLoading) return <Spinner />;
  if (!meQ.data?.pharmacy_id) {
    return (
      <EmptyState>
        Connectez-vous comme pharmacien pour voir vos quantités recommandées.
      </EmptyState>
    );
  }
  if (dataQ.isError) {
    return <EmptyState>Impossible de charger l&apos;analyse pour cette pharmacie.</EmptyState>;
  }

  const surplusCount = (d?.allocations ?? []).filter((a) => a.surplus_quantity > 0).length;

  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-xl font-bold text-slate-900">Quantités recommandées</h1>
        <p className="text-xs text-slate-500">
          Calculées sur votre consommation observée, en excluant le stock qui
          périmera avant d&apos;être vendu.
        </p>
      </header>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard
          label="À commander"
          value={dataQ.isLoading ? "…" : formatTND(d?.order_value_tnd ?? 0)}
          hint={`${rows.length} références`}
          icon={<PackageCheck className="h-4 w-4" />}
        />
        <KpiCard
          label="Périmera invendu"
          value={dataQ.isLoading ? "…" : formatCompact(d?.at_risk_value_tnd ?? 0)}
          unit="TND"
          hint={d ? `${formatInt(d.at_risk_units)} unités` : undefined}
          severity={d && d.at_risk_units > 0 ? "red" : "green"}
          icon={<Trash2 className="h-4 w-4" />}
        />
        <KpiCard
          label="Références en excédent"
          value={dataQ.isLoading ? "…" : surplusCount}
          hint="Ne pas réapprovisionner"
          severity={surplusCount > 0 ? "orange" : "green"}
          icon={<TriangleAlert className="h-4 w-4" />}
        />
        <KpiCard
          label="Lots à surveiller"
          value={dataQ.isLoading ? "…" : (d?.batches.length ?? 0)}
          hint="Échéance proche"
          icon={<Coins className="h-4 w-4" />}
        />
      </div>

      {view === "expiring" ? (
        <Panel
          title="Lots proches de la péremption"
          subtitle="Triés par échéance"
          bodyClassName="p-0"
          actions={<ViewSwitch value={view} onChange={setView} />}
        >
          {dataQ.isLoading ? (
            <div className="p-4">
              <SkeletonRows rows={8} />
            </div>
          ) : d?.batches.length ? (
            <div className="max-h-[560px] overflow-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Médicament</th>
                    <th>Lot</th>
                    <th className="text-end">Quantité</th>
                    <th className="text-end">Écoulable</th>
                    <th className="text-end">Perte</th>
                    <th className="text-end">Échéance</th>
                  </tr>
                </thead>
                <tbody>
                  {d.batches.map((b) => (
                    <tr key={b.batch_id}>
                      <td>
                        <div className="font-medium text-slate-900">{b.brand_name}</div>
                        <div className="text-2xs text-slate-500">{b.dci}</div>
                      </td>
                      <td className="font-figure text-2xs text-slate-400">{b.lot_number}</td>
                      <td className="text-end font-figure text-xs">{formatInt(b.quantity)}</td>
                      <td className="text-end font-figure text-xs text-emerald-700">
                        {formatInt(b.projected_consumption)}
                      </td>
                      <td className="text-end font-figure text-xs font-semibold text-risk-red">
                        {formatInt(b.at_risk_quantity)}
                      </td>
                      <td className="text-end">
                        <RiskBadge
                          severity={b.severity}
                          label={
                            b.days_to_expiry < 0
                              ? `Périmé`
                              : `${b.days_to_expiry} j`
                          }
                          size="sm"
                        />
                        <div className="mt-0.5 text-2xs text-slate-400">
                          {formatDate(b.expiry_date)}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState>Aucun lot à risque.</EmptyState>
          )}
        </Panel>
      ) : (
        <Panel
          title={view === "order" ? "Commande proposée" : "Excédents et pertes"}
          subtitle={`${rows.length} références`}
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
              <ViewSwitch value={view} onChange={setView} />
            </div>
          }
        >
          {dataQ.isLoading ? (
            <div className="p-4">
              <SkeletonRows rows={10} />
            </div>
          ) : rows.length ? (
            <div className="max-h-[600px] overflow-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Médicament</th>
                    <th className="text-end">Conso/j</th>
                    <th className="text-end">Stock</th>
                    <th className="text-end">Utilisable</th>
                    <th className="text-end">Cible</th>
                    <th className="text-end">
                      {view === "order" ? "À commander" : "Excédent"}
                    </th>
                    <th className="text-end">
                      {view === "order" ? "Coût" : "Perte"}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((a) => (
                    <tr key={a.medication_id}>
                      <td>
                        <div className="flex items-center gap-1.5">
                          <span className="font-medium text-slate-900">{a.brand_name}</span>
                          {a.is_essential && <EssentialTag label="Ess." />}
                        </div>
                        <div className="text-2xs text-slate-500">{a.dci}</div>
                        {a.at_risk_quantity > 0 && (
                          <div className="mt-0.5 text-2xs text-risk-red">
                            {formatInt(a.at_risk_quantity)} u périmeront invendues
                          </div>
                        )}
                      </td>
                      <td className="text-end font-figure text-xs text-slate-500">
                        {a.daily_rate.toFixed(1)}
                      </td>
                      <td className="text-end font-figure text-xs">
                        {formatInt(a.current_stock)}
                      </td>
                      <td className="text-end font-figure text-xs text-slate-500">
                        {formatInt(a.usable_stock)}
                      </td>
                      <td className="text-end font-figure text-xs text-slate-400">
                        {formatInt(a.target_stock)}
                      </td>
                      <td
                        className="text-end font-figure text-xs font-semibold"
                        style={{
                          color:
                            view === "order" ? "var(--portal-accent)" : "#ea580c",
                        }}
                      >
                        {view === "order"
                          ? `+${formatInt(a.recommended_quantity)}`
                          : formatInt(a.surplus_quantity)}
                      </td>
                      <td className="text-end font-figure text-xs">
                        {view === "order"
                          ? formatTND(a.order_value_tnd)
                          : formatTND(a.at_risk_value_tnd)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState>
              {view === "order"
                ? "Aucune commande nécessaire — vos stocks couvrent la période."
                : "Aucun excédent ni perte projetée."}
            </EmptyState>
          )}
        </Panel>
      )}

      <p className="text-2xs leading-relaxed text-slate-400">
        Cible = consommation sur 54 jours (réappro 30 j + délai 14 j + sécurité 10 j),
        diminuée du stock réellement écoulable. Proposition indicative : la
        commande finale reste à votre appréciation.
      </p>
    </div>
  );
}

function ViewSwitch({
  value,
  onChange,
}: {
  value: View;
  onChange: (v: View) => void;
}) {
  return (
    <SegmentedControl<View>
      ariaLabel="Vue"
      value={value}
      onChange={onChange}
      options={[
        { value: "order", label: "À commander" },
        { value: "surplus", label: "Excédents" },
        { value: "expiring", label: "Lots" },
      ]}
    />
  );
}
