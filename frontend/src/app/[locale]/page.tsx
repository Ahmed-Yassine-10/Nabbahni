"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "@/i18n/routing";
import { useCitizenSearch } from "@/lib/queries";
import { CitizenHeader } from "@/components/citizen-header";
import { AvailabilityBadge, Card, EmptyState, Spinner } from "@/components/ui";
import { Search, MapPin, Pill, Info, ArrowRight } from "lucide-react";
import type { Availability } from "@/lib/types";

const SUGGESTIONS = ["Amoxicilline", "Doliprane", "Ventoline", "Metformine", "Lévothyrox"];

const AVAILABILITY_TEXT: Record<Availability, string> = {
  available: "Disponible dans la plupart des pharmacies",
  tension: "Disponibilité réduite — appelez avant de vous déplacer",
  shortage: "En rupture — demandez une alternative à votre pharmacien",
};

/**
 * Citizen portal — public, mobile-first, and deliberately the least dense
 * surface in the product. One question ("puis-je trouver ce médicament ?"),
 * one answer, and a route to a pharmacy. No jargon, no probabilities.
 */
export default function CitizenHome() {
  const t = useTranslations("citizen");
  const ta = useTranslations("availability");
  const tnav = useTranslations("nav");
  const router = useRouter();
  const [q, setQ] = useState("");
  const [submitted, setSubmitted] = useState("");
  const searchQ = useCitizenSearch(submitted);

  const runSearch = (term: string) => {
    setQ(term);
    setSubmitted(term.trim());
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-sky-50 to-slate-50">
      <CitizenHeader />
      <main className="mx-auto max-w-2xl px-4 pb-16 pt-8">
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-bold text-slate-900 sm:text-3xl">
            La météo des médicaments
          </h1>
          <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-slate-600">
            Vérifiez la disponibilité d&apos;un médicament près de chez vous, en
            temps réel, partout en Tunisie.
          </p>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            setSubmitted(q.trim());
          }}
          className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white p-2 shadow-card focus-within:border-sky-300"
        >
          <Search aria-hidden className="ms-2 h-5 w-5 shrink-0 text-slate-400" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={t("searchPlaceholder")}
            aria-label={t("searchPlaceholder")}
            // 16px minimum prevents iOS Safari from zooming on focus.
            className="min-h-[2.75rem] flex-1 bg-transparent px-1 text-base outline-none placeholder:text-slate-400"
          />
          <button
            type="submit"
            className="min-h-[2.75rem] cursor-pointer rounded-lg bg-sky-700 px-5 text-sm font-semibold text-white transition-colors duration-150 hover:bg-sky-800"
          >
            {tnav("search")}
          </button>
        </form>

        {!submitted && (
          <div className="mt-4">
            <p className="mb-2 text-xs text-slate-500">Recherches fréquentes</p>
            <div className="flex flex-wrap gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => runSearch(s)}
                  className="min-h-[2.25rem] cursor-pointer rounded-full border border-slate-200 bg-white px-3 text-sm text-slate-600 transition-colors duration-150 hover:border-sky-300 hover:text-sky-800"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="mt-6">
          {searchQ.isLoading && <Spinner label="Recherche en cours…" />}

          {searchQ.isError && (
            <Card>
              <EmptyState icon={<Pill className="h-5 w-5 text-slate-300" />}>
                Aucun médicament trouvé pour «&nbsp;{submitted}&nbsp;». Essayez le
                nom de la molécule (par exemple «&nbsp;Amoxicilline&nbsp;»).
              </EmptyState>
            </Card>
          )}

          {searchQ.data && (
            <div className="space-y-3">
              <Card>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h2 className="text-lg font-bold text-slate-900">
                      {searchQ.data.medication.brand_name}
                    </h2>
                    <p className="text-sm text-slate-500">
                      {searchQ.data.medication.dci} · {searchQ.data.medication.form}{" "}
                      {searchQ.data.medication.dosage}
                    </p>
                  </div>
                  <AvailabilityBadge
                    status={searchQ.data.national_status}
                    label={ta(searchQ.data.national_status)}
                  />
                </div>

                <p className="mt-3 rounded-lg bg-slate-50 p-3 text-sm leading-relaxed text-slate-600">
                  {AVAILABILITY_TEXT[searchQ.data.national_status]}
                </p>

                <button
                  onClick={() => router.push(`/medication/${searchQ.data!.medication.id}`)}
                  className="mt-3 flex min-h-[2.75rem] w-full cursor-pointer items-center justify-center gap-2 rounded-lg bg-sky-700 text-sm font-semibold text-white transition-colors duration-150 hover:bg-sky-800"
                >
                  <MapPin aria-hidden className="h-4 w-4" /> {t("findNearby")}
                  <ArrowRight aria-hidden className="h-4 w-4" />
                </button>
              </Card>

              <Card>
                <h3 className="mb-3 text-sm font-semibold text-slate-700">
                  Disponibilité par gouvernorat
                </h3>
                <ul className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
                  {searchQ.data.by_governorate.map((g) => (
                    <li
                      key={g.governorate}
                      className="flex items-center justify-between gap-2 rounded-lg bg-slate-50 px-3 py-2"
                    >
                      <span className="truncate text-sm text-slate-700">
                        {g.governorate}
                      </span>
                      <span className="flex shrink-0 items-center gap-1.5">
                        <span className="text-2xs text-slate-400">
                          {g.pharmacies_with_stock}/{g.total_pharmacies}
                        </span>
                        <StatusDot status={g.availability} label={ta(g.availability)} />
                      </span>
                    </li>
                  ))}
                </ul>
                <p className="mt-3 text-2xs text-slate-400">
                  Nombre de pharmacies déclarant du stock sur le total de pharmacies
                  du gouvernorat.
                </p>
              </Card>

              {searchQ.data.alternatives.length > 0 && (
                <Card>
                  <h3 className="text-sm font-semibold text-slate-700">
                    {t("alternatives")}
                  </h3>
                  <p className="mt-1 flex items-start gap-1.5 rounded-lg bg-amber-50 p-2.5 text-xs leading-relaxed text-amber-800">
                    <Info aria-hidden className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                    {t("confirmWithPharmacist")}
                  </p>
                  <ul className="mt-3 space-y-1.5">
                    {searchQ.data.alternatives.map((a) => (
                      <li
                        key={a.id}
                        className="rounded-lg border border-slate-100 px-3 py-2"
                      >
                        <div className="text-sm font-medium text-slate-900">
                          {a.target.brand_name}
                        </div>
                        <div className="text-xs text-slate-500">
                          {a.target.dci} · {a.target.form} {a.target.dosage}
                        </div>
                      </li>
                    ))}
                  </ul>
                </Card>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

/** Colour plus an accessible name — never colour alone. */
function StatusDot({ status, label }: { status: Availability; label: string }) {
  const color =
    status === "available" ? "#15803d" : status === "tension" ? "#ea580c" : "#dc2626";
  return (
    <span
      className="h-2.5 w-2.5 rounded-full"
      style={{ backgroundColor: color }}
      role="img"
      aria-label={label}
      title={label}
    />
  );
}
