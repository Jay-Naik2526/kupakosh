"use client";
import { useEffect, useRef } from "react";
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { BRAND, countryColor } from "@/lib/palette";

// MapLibre v6 loads its worker as a separate ES module; serve it from /public (copied by `npm run maplibre-worker`).
if (typeof window !== "undefined") maplibregl.setWorkerUrl("/maplibre/maplibre-gl-worker.mjs");

export type MapWell = { id: number; name: string; lat: number; lon: number; country?: string | null; documented?: boolean; n_events?: number; active?: boolean };

/** Colourful mini map (OpenFreeMap "liberty", same style family as the full WellMap) with the radius circle
 * and wells coloured by country — used on Offsets and Brief where a small, quick-loading map is enough. */
export function MiniMap({ center, radius_m, wells, height = 300, onPick }: {
  center: [number, number] | null; radius_m: number; wells: MapWell[]; height?: number; onPick?: (id: number) => void;
}) {
  const el = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  useEffect(() => {
    if (!el.current || map.current) return;
    map.current = new maplibregl.Map({
      container: el.current,
      style: "https://tiles.openfreemap.org/styles/liberty",
      center: center ? [center[1], center[0]] : [2, 58], zoom: 9, attributionControl: { compact: true },
    });
    return () => { map.current?.remove(); map.current = null; };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    const m = map.current;
    if (!m || !center) return;
    const draw = () => {
      const circle = circlePoly(center, radius_m);
      const fc = { type: "FeatureCollection", features: wells.map((w) => ({ type: "Feature", properties: { id: w.id, name: w.name, doc: w.documented ? 1 : 0, active: w.active ? 1 : 0, ev: w.n_events ?? 0, color: w.active ? BRAND.accent : countryColor(w.country) }, geometry: { type: "Point", coordinates: [w.lon, w.lat] } })) } as any;
      for (const id of ["wells-l", "wells", "radius-l", "radius-f"]) if (m.getLayer(id)) m.removeLayer(id);
      for (const id of ["wells", "radius"]) if (m.getSource(id)) m.removeSource(id);
      m.addSource("radius", { type: "geojson", data: circle as any });
      m.addLayer({ id: "radius-f", type: "fill", source: "radius", paint: { "fill-color": BRAND.via, "fill-opacity": 0.08 } });
      m.addLayer({ id: "radius-l", type: "line", source: "radius", paint: { "line-color": BRAND.via, "line-width": 1.6, "line-dasharray": [3, 2] } });
      m.addSource("wells", { type: "geojson", data: fc });
      m.addLayer({ id: "wells", type: "circle", source: "wells", paint: {
        "circle-radius": ["case", ["==", ["get", "active"], 1], 8, ["==", ["get", "doc"], 1], 5, 3],
        "circle-color": ["get", "color"],
        "circle-stroke-color": "#FFFFFF", "circle-stroke-width": ["case", ["==", ["get", "active"], 1], 2.5, 1.4] } });
      m.addLayer({ id: "wells-l", type: "symbol", source: "wells", filter: [">", ["get", "ev"], 0], layout: { "text-field": ["get", "name"], "text-size": 11, "text-offset": [0, 1.1], "text-font": ["Noto Sans Regular"] }, paint: { "text-color": "#1B1A17", "text-halo-color": "#FFFFFF", "text-halo-width": 1.5 } });
      const b = new maplibregl.LngLatBounds();
      circle.features[0].geometry.coordinates[0].forEach((c: number[]) => b.extend(c as [number, number]));
      m.fitBounds(b, { padding: 20, duration: 0 });
    };
    if (m.isStyleLoaded()) draw(); else m.once("load", draw);
    const click = (e: any) => { const f = e.features?.[0]; if (f && onPick) onPick(f.properties.id); };
    m.on("click", "wells", click);
    return () => { m.off("click", "wells", click); };
  }, [center, radius_m, wells, onPick]);
  return <div ref={el} style={{ height, border: "1px solid var(--rule)", borderRadius: "var(--radius)" }} role="img" aria-label="map of wells within radius" />;
}

function circlePoly([lat, lon]: [number, number], r: number) {
  const pts = [];
  for (let i = 0; i <= 64; i++) {
    const a = (i / 64) * 2 * Math.PI;
    const dLat = (r * Math.cos(a)) / 111320, dLon = (r * Math.sin(a)) / (111320 * Math.cos((lat * Math.PI) / 180));
    pts.push([lon + dLon, lat + dLat]);
  }
  return { type: "FeatureCollection", features: [{ type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [pts] } }] };
}
