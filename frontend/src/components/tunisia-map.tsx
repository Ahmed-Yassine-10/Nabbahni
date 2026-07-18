"use client";

import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { RiskFeatureCollection } from "@/lib/types";

const SEVERITY_LABEL: Record<string, string> = {
  green: "Normal",
  yellow: "Surveillance",
  orange: "Tendu",
  red: "Critique",
  critical: "Rupture imminente",
};

/**
 * National risk choropleth over OpenStreetMap raster tiles.
 *
 * Fill colour encodes the governorate's own risk level — the SHARE of tracked
 * medications under pressure, not the single worst one. Using the worst
 * medication saturated the whole country red and destroyed the gradient.
 *
 * A hover tooltip carries the numbers, so the map is readable without
 * clicking; clicking drills through to the filtered shortage list.
 */
export function TunisiaMap({
  data,
  onSelect,
}: {
  data: RiskFeatureCollection;
  onSelect?: (governorateId: string, name: string) => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const popupRef = useRef<maplibregl.Popup | null>(null);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: {
        version: 8,
        sources: {
          osm: {
            type: "raster",
            tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            tileSize: 256,
            attribution: "© OpenStreetMap",
          },
        },
        layers: [{ id: "osm", type: "raster", source: "osm" }],
      },
      // Framed to Tunisia's bounds rather than a fixed centre/zoom, so the
      // country fills the panel at any container width.
      bounds: [
        [7.4, 30.2],
        [11.7, 37.6],
      ],
      fitBoundsOptions: { padding: 16 },
      attributionControl: { compact: true },
    });
    mapRef.current = map;
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");

    const popup = new maplibregl.Popup({
      closeButton: false,
      closeOnClick: false,
      offset: 8,
      className: "sentinelle-popup",
    });
    popupRef.current = popup;

    map.on("load", () => {
      map.addSource("risk", {
        type: "geojson",
        data: data as unknown as maplibregl.GeoJSONSourceSpecification["data"],
      });
      map.addLayer({
        id: "risk-fill",
        type: "fill",
        source: "risk",
        paint: { "fill-color": ["get", "color"], "fill-opacity": 0.6 },
      });
      map.addLayer({
        id: "risk-outline",
        type: "line",
        source: "risk",
        paint: { "line-color": "#475569", "line-width": 0.8 },
      });
      // Emphasised outline for the polygon under the cursor.
      map.addLayer({
        id: "risk-hover",
        type: "line",
        source: "risk",
        paint: { "line-color": "#0f172a", "line-width": 2.5 },
        filter: ["==", ["get", "governorate_id"], ""],
      });

      map.on("mousemove", "risk-fill", (e) => {
        const f = e.features?.[0];
        if (!f) return;
        const p = f.properties ?? {};
        map.getCanvas().style.cursor = "pointer";
        map.setFilter("risk-hover", [
          "==",
          ["get", "governorate_id"],
          p.governorate_id as string,
        ]);

        const sev = (p.severity as string) ?? "green";
        const ratio = Number(p.risk_ratio ?? 0);
        popup
          .setLngLat(e.lngLat)
          .setHTML(
            `<div style="font-family:var(--font-sans);min-width:170px">
               <div style="font-weight:600;font-size:13px;color:#0f172a">${p.name_fr}</div>
               <div style="display:flex;align-items:center;gap:6px;margin-top:4px">
                 <span style="width:8px;height:8px;border-radius:2px;background:${p.color}"></span>
                 <span style="font-size:12px;color:#334155">${SEVERITY_LABEL[sev] ?? sev}</span>
               </div>
               <div style="margin-top:6px;font-size:11px;color:#64748b;line-height:1.5">
                 ${p.at_risk_count ?? 0} / ${p.total ?? 0} médicaments en tension
                 (${Math.round(ratio * 100)} %)
               </div>
               <div style="margin-top:4px;font-size:10px;color:#94a3b8">
                 Cliquer pour filtrer la liste
               </div>
             </div>`
          )
          .addTo(map);
      });

      map.on("mouseleave", "risk-fill", () => {
        map.getCanvas().style.cursor = "";
        map.setFilter("risk-hover", ["==", ["get", "governorate_id"], ""]);
        popup.remove();
      });

      map.on("click", "risk-fill", (e) => {
        const f = e.features?.[0];
        if (f && onSelectRef.current) {
          onSelectRef.current(
            f.properties?.governorate_id as string,
            f.properties?.name_fr as string
          );
        }
      });
    });

    return () => {
      popup.remove();
      map.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const src = map.getSource("risk") as maplibregl.GeoJSONSource | undefined;
    if (src) src.setData(data as unknown as maplibregl.GeoJSONSourceSpecification["data"]);
  }, [data]);

  return (
    <div
      ref={containerRef}
      role="img"
      aria-label="Carte des risques de rupture par gouvernorat"
      className="h-[460px] w-full overflow-hidden rounded-md"
    />
  );
}
