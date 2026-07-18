"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useMedicationSearch, useSubstitutions } from "@/lib/queries";
import { Card, Spinner, EmptyState } from "@/components/ui";
import { Search, ShieldCheck } from "lucide-react";
import type { Medication } from "@/lib/types";

export default function SubstitutionsPage() {
  const t = useTranslations("pharmacy");
  const [q, setQ] = useState("");
  const [selected, setSelected] = useState<Medication | null>(null);
  const searchQ = useMedicationSearch(q);
  const subsQ = useSubstitutions(selected?.id ?? "");

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold">{t("suggestedAlternatives")}</h1>

      <Card>
        <div className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2">
          <Search className="h-4 w-4 text-slate-400" />
          <input
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setSelected(null);
            }}
            placeholder="Rechercher un médicament en rupture…"
            className="flex-1 bg-transparent text-sm outline-none"
          />
        </div>
        {!selected && q.length >= 2 && searchQ.data?.items.length ? (
          <ul className="mt-2 divide-y divide-slate-100">
            {searchQ.data.items.map((m) => (
              <li
                key={m.id}
                onClick={() => setSelected(m)}
                className="cursor-pointer py-2 text-sm hover:bg-slate-50"
              >
                <span className="font-medium">{m.brand_name}</span>{" "}
                <span className="text-slate-400">
                  · {m.dci} · {m.form} {m.dosage}
                </span>
              </li>
            ))}
          </ul>
        ) : null}
      </Card>

      {selected && (
        <Card>
          <h2 className="mb-1 text-lg font-semibold">
            Alternatives pour {selected.brand_name}
          </h2>
          <p className="mb-3 flex items-center gap-1.5 text-xs text-amber-700">
            <ShieldCheck className="h-4 w-4" /> {t("validatedByPharmacist")}
          </p>
          {subsQ.isLoading ? (
            <Spinner />
          ) : subsQ.data?.length ? (
            <ul className="divide-y divide-slate-100">
              {subsQ.data.map((s) => (
                <li key={s.id} className="flex items-center justify-between py-3">
                  <div>
                    <div className="font-medium">{s.target.brand_name}</div>
                    <div className="text-sm text-slate-500">{s.notes_fr}</div>
                  </div>
                  <div className="text-end">
                    <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-500">
                      ATC niv. {s.atc_match_level}
                    </span>
                    {s.ddd_ratio && (
                      <div className="mt-1 text-xs text-slate-400">
                        Ratio DDD ≈ {s.ddd_ratio}
                      </div>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState>Aucune substitution disponible.</EmptyState>
          )}
        </Card>
      )}
    </div>
  );
}
