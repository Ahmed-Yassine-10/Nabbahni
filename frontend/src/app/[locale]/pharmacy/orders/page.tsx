"use client";

import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { useMe, usePharmacyStock } from "@/lib/queries";
import {
  Button,
  EmptyState,
  EssentialTag,
  KpiCard,
  Panel,
  SkeletonRows,
  Spinner,
} from "@/components/ui";
import { formatInt, formatTND } from "@/lib/utils";
import { ShoppingCart, Check, Coins, PackageCheck } from "lucide-react";

/**
 * Reorder proposals derived from the pharmacy's own stock position.
 *
 * The target is 2x the minimum threshold — a simple, explainable rule the
 * pharmacist can sanity-check, not a model output. Anything the model
 * contributes (coverage days) is shown alongside so the rule can be overridden.
 */
export default function PharmacyOrdersPage() {
  const t = useTranslations("pharmacy");
  const meQ = useMe();
  const stockQ = usePharmacyStock(meQ.data?.pharmacy_id);
  const [basket, setBasket] = useState<Set<string>>(new Set());

  const suggestions = useMemo(() => {
    return (stockQ.data ?? [])
      .filter((r) => r.quantity <= r.min_threshold)
      .map((r) => {
        const reorder = Math.max(1, r.min_threshold * 2 - r.quantity);
        return {
          ...r,
          reorder,
          cost: reorder * (r.medication?.unit_price_tnd ?? 0),
        };
      })
      .sort((a, b) => {
        const ca = a.coverage_days ?? Number.POSITIVE_INFINITY;
        const cb = b.coverage_days ?? Number.POSITIVE_INFINITY;
        return ca - cb || b.cost - a.cost;
      });
  }, [stockQ.data]);

  const total = suggestions.reduce((s, x) => s + x.cost, 0);
  const basketTotal = suggestions
    .filter((s) => basket.has(s.id))
    .reduce((a, s) => a + s.cost, 0);

  const toggle = (id: string) =>
    setBasket((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  if (meQ.isLoading) return <Spinner />;
  if (!meQ.data?.pharmacy_id)
    return (
      <EmptyState>
        Connectez-vous comme pharmacien pour voir vos commandes suggérées.
      </EmptyState>
    );

  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-xl font-bold text-slate-900">{t("recommendedOrders")}</h1>
        <p className="text-xs text-slate-500">
          Références sous leur seuil minimum, les plus urgentes en premier.
          Objectif de réapprovisionnement : 2× le seuil.
        </p>
      </header>

      <div className="grid grid-cols-3 gap-3">
        <KpiCard
          label="À recommander"
          value={suggestions.length}
          icon={<PackageCheck className="h-4 w-4" />}
        />
        <KpiCard
          label="Coût total estimé"
          value={formatTND(total)}
          icon={<Coins className="h-4 w-4" />}
        />
        <KpiCard
          label="Sélection"
          value={basket.size}
          hint={basket.size ? formatTND(basketTotal) : "Aucune ligne cochée"}
          icon={<ShoppingCart className="h-4 w-4" />}
        />
      </div>

      <Panel
        title="Commandes suggérées"
        subtitle={`${suggestions.length} lignes`}
        bodyClassName="p-0"
        actions={
          basket.size > 0 && (
            <Button onClick={() => setBasket(new Set())} variant="secondary">
              Vider la sélection
            </Button>
          )
        }
      >
        {stockQ.isLoading ? (
          <div className="p-4">
            <SkeletonRows rows={8} />
          </div>
        ) : suggestions.length ? (
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th className="w-10"></th>
                  <th>Médicament</th>
                  <th className="text-end">Stock</th>
                  <th className="text-end">Seuil</th>
                  <th className="text-end">Couverture</th>
                  <th className="text-end">À commander</th>
                  <th className="text-end">Coût</th>
                </tr>
              </thead>
              <tbody>
                {suggestions.map((s) => (
                  <tr key={s.id}>
                    <td>
                      <input
                        type="checkbox"
                        checked={basket.has(s.id)}
                        onChange={() => toggle(s.id)}
                        aria-label={`Sélectionner ${s.medication?.brand_name ?? "cette ligne"}`}
                        className="h-4 w-4 cursor-pointer accent-[var(--portal-accent)]"
                      />
                    </td>
                    <td>
                      <div className="flex items-center gap-1.5">
                        <span className="font-medium text-slate-900">
                          {s.medication?.brand_name ?? "—"}
                        </span>
                        {s.medication?.is_essential && <EssentialTag label="Ess." />}
                      </div>
                      <div className="text-2xs text-slate-500">{s.medication?.dci}</div>
                    </td>
                    <td className="text-end font-figure text-xs text-slate-500">
                      {formatInt(s.quantity)}
                    </td>
                    <td className="text-end font-figure text-xs text-slate-400">
                      {formatInt(s.min_threshold)}
                    </td>
                    <td className="text-end font-figure text-xs">
                      {s.coverage_days != null ? `${s.coverage_days.toFixed(0)} j` : "—"}
                    </td>
                    <td
                      className="text-end font-figure text-xs font-semibold"
                      style={{ color: "var(--portal-accent)" }}
                    >
                      +{formatInt(s.reorder)}
                    </td>
                    <td className="text-end font-figure text-xs">{formatTND(s.cost)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState icon={<Check className="h-5 w-5 text-emerald-500" />}>
            Aucune commande recommandée — vos stocks sont au-dessus des seuils.
          </EmptyState>
        )}
      </Panel>

      <p className="text-2xs text-slate-400">
        Proposition indicative : la commande finale reste à votre appréciation et
        n&apos;est pas transmise automatiquement.
      </p>
    </div>
  );
}
