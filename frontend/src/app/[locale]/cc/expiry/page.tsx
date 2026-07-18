"use client";

import { useMemo, useState } from "react";
import { useRouter } from "@/i18n/routing";
import { useExpiryAnalysis, useRedistribution } from "@/lib/queries";
import {
  EmptyState,
  KpiCard,
  Panel,
  RiskBadge,
  SegmentedControl,
  SkeletonRows,
} from "@/components/ui";
import {
  SEVERITY_COLORS,
  formatCompact,
  formatDate,
  formatInt,
  formatTND,
} from "@/lib/utils";
import { ArrowRight, Boxes, Coins, Recycle, ShieldAlert, Trash2 } from "lucide-react";

type Tab = "batches" | "transfers";

export default function ExpiryPage() {
  const router = useRouter();
  const analysisQ = useExpiryAnalysis();
  const transfersQ = useRedistribution();
  const [tab, setTab] = useState<Tab>("batches");

  const a = analysisQ.data;
  const transfers = useMemo(() => transfersQ.data ?? [], [transfersQ.data]);

  const recoverable = useMemo(
    () => transfers.reduce((s, t) => s + t.value_saved_tnd, 0),
    [transfers]
  );

  if (analysisQ.isError) {
    return (
      <EmptyState icon={<ShieldAlert className="h-5 w-5 text-slate-300" />}>
        Réservé aux profils <strong>Admin PCT</strong> et{" "}
        <strong>Autorité régionale</strong>.
      </EmptyState>
    );
  }

  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-xl font-bold text-slate-900">Péremption &amp; gaspillage</h1>
        <p className="text-xs text-slate-500">
          Chaque lot est comparé à la consommation réelle de la pharmacie qui le
          détient. Ce qui ne sera pas écoulé avant la date de péremption est
          compté comme perte projetée.
        </p>
      </header>

      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <KpiCard
          label="Taux de gaspillage projeté"
          value={a ? a.waste_rate_pct.toFixed(1) : "—"}
          unit="%"
          hint="Part du stock qui périmera invendue"
          severity={a ? (a.waste_rate_pct > 5 ? "red" : a.waste_rate_pct > 2 ? "orange" : "green") : undefined}
          icon={<Trash2 className="h-4 w-4" />}
        />
        <KpiCard
          label="Valeur à risque"
          value={a ? formatCompact(a.at_risk_value_tnd) : "—"}
          unit="TND"
          hint={a ? `${formatInt(a.at_risk_units)} unités` : undefined}
          severity={a && a.at_risk_value_tnd > 0 ? "orange" : "green"}
          icon={<Coins className="h-4 w-4" />}
        />
        <KpiCard
          label="Déjà périmé"
          value={a ? formatCompact(a.expired_value_tnd) : "—"}
          unit="TND"
          hint={a ? `${formatInt(a.expired_units)} unités à détruire` : undefined}
          severity={a && a.expired_units > 0 ? "critical" : "green"}
          icon={<Trash2 className="h-4 w-4" />}
        />
        <KpiCard
          label="Récupérable par transfert"
          value={transfersQ.isLoading ? "…" : formatCompact(recoverable)}
          unit="TND"
          hint={`${transfers.length} transferts réalisables`}
          severity="green"
          icon={<Recycle className="h-4 w-4" />}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <Panel
          title="Stock par échéance"
          subtitle={
            a ? `${formatInt(a.total_units)} unités · ${formatTND(a.total_value_tnd)}` : undefined
          }
        >
          {analysisQ.isLoading ? (
            <SkeletonRows rows={5} />
          ) : a ? (
            <div className="space-y-2.5">
              {a.bands.map((b) => {
                const max = Math.max(1, ...a.bands.map((x) => x.units));
                return (
                  <div key={b.label}>
                    <div className="mb-1 flex items-baseline justify-between text-xs">
                      <span className="text-slate-600">{b.label}</span>
                      <span className="font-figure text-2xs text-slate-500">
                        {formatCompact(b.units)} u · {formatCompact(b.value_tnd)} TND
                      </span>
                    </div>
                    <span
                      className="block h-4 rounded-sm"
                      style={{
                        width: `${(b.units / max) * 100}%`,
                        backgroundColor: SEVERITY_COLORS[b.severity],
                        minWidth: b.units > 0 ? "3px" : "0",
                      }}
                    />
                  </div>
                );
              })}
              <p className="pt-1 text-2xs leading-relaxed text-slate-400">
                Un lot périmé ne peut plus être dispensé : sa valeur est une perte
                sèche, pas un stock.
              </p>
            </div>
          ) : null}
        </Panel>

        <Panel
          className="xl:col-span-2"
          title={tab === "batches" ? "Lots les plus exposés" : "Transferts proposés"}
          subtitle={
            tab === "batches"
              ? "Classés par valeur de perte projetée"
              : "Uniquement les lots qui survivent au transport et seront vendus à l'arrivée"
          }
          bodyClassName="p-0"
          actions={
            <SegmentedControl<Tab>
              ariaLabel="Vue"
              value={tab}
              onChange={setTab}
              options={[
                { value: "batches", label: "Lots à risque" },
                { value: "transfers", label: "Redistribution" },
              ]}
            />
          }
        >
          {tab === "batches" ? (
            analysisQ.isLoading ? (
              <div className="p-4">
                <SkeletonRows rows={8} />
              </div>
            ) : a?.worst_batches.length ? (
              <div className="max-h-[520px] overflow-auto">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Médicament</th>
                      <th>Pharmacie</th>
                      <th>Lot</th>
                      <th className="text-end">Échéance</th>
                      <th className="text-end">Conso/j</th>
                      <th className="text-end">Perte</th>
                      <th>Niveau</th>
                    </tr>
                  </thead>
                  <tbody>
                    {a.worst_batches.map((b) => (
                      <tr
                        key={b.batch_id}
                        className="cursor-pointer"
                        onClick={() => router.push(`/cc/medications/${b.medication_id}`)}
                      >
                        <td>
                          <div className="font-medium text-slate-900">{b.brand_name}</div>
                          <div className="text-2xs text-slate-500">{b.dci}</div>
                        </td>
                        <td className="text-xs text-slate-600">{b.pharmacy_name}</td>
                        <td className="font-figure text-2xs text-slate-400">
                          {b.lot_number}
                        </td>
                        <td className="text-end">
                          <div className="font-figure text-xs">
                            {b.days_to_expiry < 0
                              ? `périmé (${-b.days_to_expiry} j)`
                              : `${b.days_to_expiry} j`}
                          </div>
                          <div className="text-2xs text-slate-400">
                            {formatDate(b.expiry_date)}
                          </div>
                        </td>
                        <td className="text-end font-figure text-xs text-slate-500">
                          {b.daily_rate.toFixed(1)}
                        </td>
                        <td className="text-end">
                          <div className="font-figure text-xs font-semibold">
                            {formatCompact(b.at_risk_value_tnd)} TND
                          </div>
                          <div className="text-2xs text-slate-400">
                            {formatInt(b.at_risk_quantity)} / {formatInt(b.quantity)} u
                          </div>
                        </td>
                        <td>
                          <RiskBadge
                            severity={b.severity}
                            label={b.days_to_expiry < 0 ? "Périmé" : "À risque"}
                            size="sm"
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState icon={<Boxes className="h-5 w-5 text-slate-300" />}>
                Aucun lot à risque.
              </EmptyState>
            )
          ) : transfersQ.isLoading ? (
            <div className="p-4">
              <SkeletonRows rows={8} />
            </div>
          ) : transfers.length ? (
            <div className="max-h-[520px] overflow-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Médicament</th>
                    <th>Transfert proposé</th>
                    <th className="text-end">Quantité</th>
                    <th className="text-end">Échéance</th>
                    <th className="text-end">Valeur sauvée</th>
                  </tr>
                </thead>
                <tbody>
                  {transfers.map((t, i) => (
                    <tr key={`${t.medication_id}-${i}`}>
                      <td className="font-medium text-slate-900">{t.brand_name}</td>
                      <td>
                        <div className="flex items-center gap-1.5 text-xs text-slate-600">
                          <span className="truncate">{t.from_pharmacy_name}</span>
                          <ArrowRight aria-hidden className="h-3 w-3 shrink-0 text-slate-400" />
                          <span className="truncate font-medium text-slate-800">
                            {t.to_pharmacy_name}
                          </span>
                        </div>
                        <div className="mt-0.5 text-2xs text-slate-400">{t.rationale}</div>
                      </td>
                      <td className="text-end font-figure text-xs font-semibold">
                        {formatInt(t.quantity)}
                      </td>
                      <td className="text-end font-figure text-xs">{t.days_to_expiry} j</td>
                      <td className="text-end font-figure text-xs font-semibold text-emerald-700">
                        {formatCompact(t.value_saved_tnd)} TND
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState icon={<Recycle className="h-5 w-5 text-slate-300" />}>
              Aucun transfert réalisable : les lots à risque expirent trop tôt
              pour être déplacés et revendus.
            </EmptyState>
          )}
        </Panel>
      </div>

      <Panel title="Comment la perte est calculée" subtitle="Note méthodologique">
        <div className="grid gap-3 text-xs sm:grid-cols-3">
          <div className="rounded-md border border-slate-100 bg-slate-50 p-3">
            <p className="font-semibold text-slate-800">Rotation FEFO</p>
            <p className="mt-1 leading-relaxed text-slate-500">
              Les lots se vendent par date de péremption croissante. Un lot ne
              reçoit que la consommation restante une fois les lots plus courts
              écoulés — sinon chaque lot supposerait la vente complète et la
              perte serait largement sous-estimée.
            </p>
          </div>
          <div className="rounded-md border border-slate-100 bg-slate-50 p-3">
            <p className="font-semibold text-slate-800">Consommation estimée</p>
            <p className="mt-1 leading-relaxed text-slate-500">
              Les ventes sont remontées par gouvernorat, pas par comptoir. La
              consommation d&apos;une pharmacie est donc estimée au prorata de sa
              part du stock régional.
            </p>
          </div>
          <div className="rounded-md border border-slate-100 bg-slate-50 p-3">
            <p className="font-semibold text-slate-800">Transferts réalistes</p>
            <p className="mt-1 leading-relaxed text-slate-500">
              Un lot doit conserver au moins 21 jours (7 j de transport + 14 j de
              vente) et la quantité est plafonnée par ce que la pharmacie
              destinataire peut réellement écouler.
            </p>
          </div>
        </div>
      </Panel>
    </div>
  );
}
