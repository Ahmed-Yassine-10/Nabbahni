"use client";

import type { Explanation } from "@/lib/types";
import { Panel } from "./ui";
import { Info } from "lucide-react";

/**
 * Renders the stored SHAP rationale for one shortage prediction.
 *
 * The factor chart is a centre-anchored tornado: bars grow right when the
 * feature pushed the risk UP and left when it pulled the risk DOWN, from a
 * neutral zero axis. That is a *diverging* encoding (polarity), so it uses a
 * warm/cool pair — deliberately not the reserved green→red severity ramp,
 * which means something else on this same page.
 */
const UP = "#b45309"; // warm — increased the predicted risk
const DOWN = "#0f766e"; // cool — reduced the predicted risk

export function ExplanationPanel({
  explanation,
  locale = "fr",
}: {
  explanation: Explanation | null;
  locale?: string;
}) {
  if (!explanation) return null;

  const factors = explanation.top_factors ?? [];
  const maxAbs = Math.max(1e-6, ...factors.map((f) => Math.abs(f.shap)));
  const narrative =
    locale === "ar" && explanation.narrative_ar
      ? explanation.narrative_ar
      : explanation.narrative_fr;

  return (
    <Panel
      title="Pourquoi ce risque ?"
      subtitle="Contribution de chaque facteur au score du modèle (SHAP)"
    >
      {narrative && (
        <p className="mb-4 rounded-md border border-slate-100 bg-slate-50 p-3 text-sm leading-relaxed text-slate-700">
          {narrative}
        </p>
      )}

      {factors.length > 0 && (
        <>
          <div className="mb-2 flex items-center justify-between text-2xs text-slate-500">
            <span className="flex items-center gap-1.5">
              <span aria-hidden className="h-2 w-2 rounded-sm" style={{ background: DOWN }} />
              Réduit le risque
            </span>
            <span className="font-medium text-slate-400">0</span>
            <span className="flex items-center gap-1.5">
              Augmente le risque
              <span aria-hidden className="h-2 w-2 rounded-sm" style={{ background: UP }} />
            </span>
          </div>

          <ul className="space-y-2.5">
            {factors.map((f) => {
              const pct = (Math.abs(f.shap) / maxAbs) * 50; // half-width per side
              const up = f.shap > 0;
              return (
                <li key={f.feature}>
                  <div className="mb-1 flex items-baseline justify-between gap-2 text-xs">
                    <span className="truncate text-slate-700">{f.label_fr}</span>
                    <span
                      className="shrink-0 font-figure text-2xs font-semibold"
                      style={{ color: up ? UP : DOWN }}
                    >
                      {up ? "+" : "−"}
                      {Math.abs(f.shap).toFixed(3)}
                    </span>
                  </div>
                  {/* Zero axis in the middle; bar extends to one side. */}
                  <div className="relative h-3 w-full rounded-sm bg-slate-50">
                    <span
                      aria-hidden
                      className="absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-slate-300"
                    />
                    <span
                      className="absolute inset-y-0.5 rounded-sm transition-[width] duration-300"
                      style={{
                        width: `${pct}%`,
                        left: up ? "50%" : undefined,
                        right: up ? undefined : "50%",
                        backgroundColor: up ? UP : DOWN,
                      }}
                    />
                  </div>
                </li>
              );
            })}
          </ul>

          {/* Table alternative — the chart is not the only way to read this. */}
          <details className="mt-4">
            <summary className="cursor-pointer text-2xs text-slate-500 hover:text-slate-700">
              Afficher les valeurs sous forme de tableau
            </summary>
            <table className="data-table mt-2">
              <thead>
                <tr>
                  <th>Facteur</th>
                  <th className="text-end">Valeur</th>
                  <th className="text-end">Contribution</th>
                </tr>
              </thead>
              <tbody>
                {factors.map((f) => (
                  <tr key={f.feature}>
                    <td className="text-xs">{f.label_fr}</td>
                    <td className="text-end font-figure text-xs">{f.value.toFixed(2)}</td>
                    <td
                      className="text-end font-figure text-xs font-semibold"
                      style={{ color: f.shap > 0 ? UP : DOWN }}
                    >
                      {f.shap > 0 ? "+" : "−"}
                      {Math.abs(f.shap).toFixed(3)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </details>
        </>
      )}

      <p className="mt-4 flex items-start gap-1.5 text-2xs leading-relaxed text-slate-400">
        <Info aria-hidden className="mt-0.5 h-3 w-3 shrink-0" />
        Explication calculée au moment du scoring, pas à l&apos;affichage. Aide à la
        décision : un pharmacien ou un officier PCT valide toujours l&apos;action finale.
      </p>
    </Panel>
  );
}
