"use client";

import { use, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/routing";
import { useMedication, useNearbyPharmacies } from "@/lib/queries";
import { CitizenHeader } from "@/components/citizen-header";
import { AvailabilityBadge, Card, Spinner, EmptyState } from "@/components/ui";
import { ArrowLeft, MapPin, Phone } from "lucide-react";

// Default to Tunis if geolocation is denied.
const TUNIS = { lat: 36.8065, lon: 10.1815 };

export default function CitizenMedicationPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const t = useTranslations("citizen");
  const ta = useTranslations("availability");
  const tc = useTranslations("common");
  const medQ = useMedication(id);
  const [coords, setCoords] = useState(TUNIS);

  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => setCoords({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
        () => setCoords(TUNIS),
        { timeout: 4000 }
      );
    }
  }, []);

  const nearbyQ = useNearbyPharmacies(coords.lat, coords.lon, id);

  return (
    <div className="min-h-screen">
      <CitizenHeader />
      <main className="mx-auto max-w-3xl px-4 py-6">
        <Link
          href="/"
          className="mb-4 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700"
        >
          <ArrowLeft className="h-4 w-4" /> {tc("back")}
        </Link>

        {medQ.data && (
          <div className="mb-4">
            <h1 className="text-xl font-bold">{medQ.data.brand_name}</h1>
            <p className="text-sm text-slate-500">
              {medQ.data.dci} · {medQ.data.form} {medQ.data.dosage}
            </p>
          </div>
        )}

        <Card>
          <h2 className="mb-3 flex items-center gap-1.5 text-lg font-semibold">
            <MapPin className="h-5 w-5 text-brand" /> {t("nearbyPharmacies")}
          </h2>
          {nearbyQ.isLoading ? (
            <Spinner />
          ) : nearbyQ.data?.length ? (
            <ul className="divide-y divide-slate-100">
              {nearbyQ.data.map((p) => (
                <li key={p.id} className="flex items-center justify-between gap-3 py-3">
                  <div className="min-w-0">
                    <div className="truncate font-medium">{p.name}</div>
                    <div className="flex items-center gap-2 text-xs text-slate-400">
                      <span>
                        {p.distance_km} {t("km")}
                      </span>
                      {p.phone && (
                        <span className="inline-flex items-center gap-1">
                          <Phone className="h-3 w-3" /> {p.phone}
                        </span>
                      )}
                    </div>
                  </div>
                  <AvailabilityBadge status={p.availability} label={ta(p.availability)} />
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState>{tc("noData")}</EmptyState>
          )}
        </Card>
      </main>
    </div>
  );
}
