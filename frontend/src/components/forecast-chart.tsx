"use client";

import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Forecast } from "@/lib/types";
import { formatInt } from "@/lib/utils";

const SERIES = "#1e40af";
const BAND = "#bfdbfe";

/**
 * Demand forecast across horizons with an 80% confidence band (quantiles
 * 0.1 / 0.9 from the champion model). Each point is TOTAL predicted demand
 * over that horizon, so the curve rises by construction — the band width is
 * the interesting signal, not the slope.
 *
 * One series, so no legend box: the panel title names it. The band is labelled
 * in the tooltip and in the caption below the plot.
 */
export function ForecastChart({ forecasts }: { forecasts: Forecast[] }) {
  const data = forecasts
    .filter((f) => f.governorate_id === null)
    .sort((a, b) => a.horizon_days - b.horizon_days)
    .map((f) => ({
      horizon: `${f.horizon_days} j`,
      predicted: Math.round(f.predicted_qty),
      band: [Math.round(f.ci_lower), Math.round(f.ci_upper)] as [number, number],
      spread:
        f.predicted_qty > 0
          ? Math.round(((f.ci_upper - f.ci_lower) / f.predicted_qty) * 100)
          : 0,
      trend: f.trend,
    }));

  if (!data.length) return null;

  return (
    <div>
      <ResponsiveContainer width="100%" height={260}>
        <ComposedChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="#f1f5f9" vertical={false} />
          <XAxis
            dataKey="horizon"
            tick={{ fontSize: 11, fill: "#64748b" }}
            axisLine={{ stroke: "#e2e8f0" }}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 11, fill: "#64748b" }}
            axisLine={false}
            tickLine={false}
            width={56}
            tickFormatter={(v: number) => formatInt(v)}
          />
          <Tooltip
            cursor={{ stroke: "#94a3b8", strokeDasharray: "3 3" }}
            contentStyle={{
              fontSize: 12,
              borderRadius: 8,
              border: "1px solid #e2e8f0",
              boxShadow: "0 4px 16px -2px rgb(15 23 42 / 0.12)",
            }}
            formatter={(value: number | number[], name: string) => {
              if (Array.isArray(value)) {
                return [`${formatInt(value[0])} – ${formatInt(value[1])}`, "Intervalle 80%"];
              }
              return [formatInt(value), name === "predicted" ? "Demande prévue" : name];
            }}
          />
          <Area
            dataKey="band"
            stroke="none"
            fill={BAND}
            fillOpacity={0.55}
            isAnimationActive={false}
            name="Intervalle 80%"
          />
          <Line
            dataKey="predicted"
            stroke={SERIES}
            strokeWidth={2}
            dot={{ r: 4, fill: SERIES, stroke: "#fff", strokeWidth: 2 }}
            activeDot={{ r: 6 }}
            isAnimationActive={false}
            name="predicted"
          />
        </ComposedChart>
      </ResponsiveContainer>

      <p className="mt-2 text-2xs leading-relaxed text-slate-400">
        Demande cumulée prévue par horizon. La bande claire est l&apos;intervalle de
        confiance à 80 % (quantiles 0,1 et 0,9) — plus elle est large, plus
        l&apos;incertitude est grande.
      </p>

      {/* Table alternative to the chart. */}
      <details className="mt-2">
        <summary className="cursor-pointer text-2xs text-slate-500 hover:text-slate-700">
          Afficher les valeurs
        </summary>
        <table className="data-table mt-2">
          <thead>
            <tr>
              <th>Horizon</th>
              <th className="text-end">Prévision</th>
              <th className="text-end">Min</th>
              <th className="text-end">Max</th>
              <th className="text-end">Incertitude</th>
            </tr>
          </thead>
          <tbody>
            {data.map((d) => (
              <tr key={d.horizon}>
                <td className="text-xs">{d.horizon}</td>
                <td className="text-end font-figure text-xs font-semibold">
                  {formatInt(d.predicted)}
                </td>
                <td className="text-end font-figure text-xs text-slate-500">
                  {formatInt(d.band[0])}
                </td>
                <td className="text-end font-figure text-xs text-slate-500">
                  {formatInt(d.band[1])}
                </td>
                <td className="text-end font-figure text-xs text-slate-500">
                  ±{d.spread}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  );
}
