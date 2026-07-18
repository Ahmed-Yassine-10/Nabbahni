"use client";

import { useTranslations } from "next-intl";
import { useShortages } from "@/lib/queries";
import { Card, Spinner, EmptyState } from "@/components/ui";
import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Cell,
} from "recharts";
import { SEVERITY_COLORS } from "@/lib/utils";
import { useMemo } from "react";

export default function SupplyChainPage() {
  const t = useTranslations("nav");
  const { data, isLoading } = useShortages();

  // Severity distribution across national predictions (single-measure bar chart).
  const dist = useMemo(() => {
    const items = (data?.items ?? []).filter((s) => s.governorate_id === null);
    const counts: Record<string, number> = {
      green: 0,
      yellow: 0,
      orange: 0,
      red: 0,
      critical: 0,
    };
    for (const s of items) counts[s.severity] = (counts[s.severity] ?? 0) + 1;
    return Object.entries(counts).map(([severity, count]) => ({ severity, count }));
  }, [data]);

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold">{t("supplyChain")}</h1>
      <Card>
        <h2 className="mb-3 text-lg font-semibold">
          Répartition des médicaments par niveau de risque
        </h2>
        {isLoading ? (
          <Spinner />
        ) : dist.some((d) => d.count > 0) ? (
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={dist} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
              <XAxis dataKey="severity" tick={{ fontSize: 12 }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {dist.map((d) => (
                  <Cell key={d.severity} fill={SEVERITY_COLORS[d.severity]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <EmptyState>Aucune donnée. Connectez-vous et lancez le scoring.</EmptyState>
        )}
      </Card>
    </div>
  );
}
