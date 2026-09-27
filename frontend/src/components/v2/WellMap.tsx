"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { get } from "@/lib/api";
import { MAP_STYLES, satelliteTileUrl } from "./map/styles";
import { decodeGeoWells, wellsToGeoJSON, bboxOf, circleGeoJSON, type MapWell } from "./map/geo";
import { ensureWellsSource, ensureAggregatesLayer, ensureBasinsLayer, ensureRadiusLayer, ensureActiveWellLayer,
         enableTerrain, disableTerrain, ensureSatelliteLayer } from "./map/layers";

// MapLibre v6 worker as a separate ES module; served from /public (same pattern as components/kk/MiniMap.tsx).
if (typeof window !== "undefined") maplibregl.setWorkerUrl("/maplibre/maplibre-gl-worker.mjs");

export type SelectedWell = { id: number; name: string; country: string; lat: number; lon: number; has_events: boolean; n_events: number; documented: boolean };
export type SelectedBasin = { name: string; slug: string; url: string; category: string | null };
export type FlyTarget = { id: number; lat: number; lon: number } | null;

export function WellMap({
  activeWell, radiusKm = 10, country = null, flyTo = null, theme = "light",
  onSelectWell, onSelectBasin, className, height = "100%",
}: {
  activeWell?: { lat: number; lon: number } | null;
  radiusKm?: number;
  country?: string | null;
  flyTo?: FlyTarget;
  theme?: "light" | "dark";
  onSelectWell?: (w: SelectedWell) => void;
  onSelectBasin?: (b: SelectedBasin) => void;
  className?: string;
  height?: number | string;
}) {
  const el = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const wellsRef = useRef<MapWell[]>([]);
  const basinsRef = useRef<GeoJSON.FeatureCollection | null>(null);
  const popupRef = useRef<maplibregl.Popup | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [dataLoaded, setDataLoaded] = useState(false);
  const [is3D, setIs3D] = useState(false);
  const [satOn, setSatOn] = useState(false);
  const [n, setN] = useState(0);
  const [err, setErr] = useState<string | null>(null);
  const canSatellite = !!satelliteTileUrl();

  const draw = useCallback(() => {
    const m = map.current;
    if (!m) return;
    const wells = wellsRef.current.filter((w) => !country || w.country === country);
    setN(wells.length);
    ensureWellsSource(m, wellsToGeoJSON(wells, "well"));
    ensureAggregatesLayer(m, wellsToGeoJSON(wells, "other"));
    if (basinsRef.current) ensureBasinsLayer(m, basinsRef.current);
    ensureRadiusLayer(m, activeWell ? (circleGeoJSON([activeWell.lat, activeWell.lon], radiusKm * 1000) as any) : null);
    ensureActiveWellLayer(m, activeWell
      ? { type: "FeatureCollection", features: [{ type: "Feature", properties: {}, geometry: { type: "Point", coordinates: [activeWell.lon, activeWell.lat] } }] }
      : null);
    if (canSatellite) ensureSatelliteLayer(m, satOn);
  }, [country, activeWell, radiusKm, satOn, canSatellite]);

  // Init map + load data once.
  useEffect(() => {
    if (!el.current || map.current) return;
    const m = new maplibregl.Map({
      container: el.current, style: theme === "dark" ? MAP_STYLES.dark : MAP_STYLES.light,
      center: [80, 22], zoom: 3.4, attributionControl: false,
    });
    map.current = m;
    m.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");
    m.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
    m.addControl(new maplibregl.FullscreenControl(), "top-right");
    m.addControl(new maplibregl.AttributionControl({ compact: false }), "bottom-right");

    m.on("load", () => { setLoaded(true); draw(); });
    // A style swap (e.g. system theme change) wipes runtime-added sources/layers — redraw after it settles.
    m.on("style.load", () => draw());

    const onClusterClick = (e: maplibregl.MapMouseEvent) => {
      const f = m.queryRenderedFeatures(e.point, { layers: ["well-clusters"] })[0];
      if (!f) return;
      const src = m.getSource("wells") as maplibregl.GeoJSONSource;
      const clusterId = (f.properties as any).cluster_id;
      src.getClusterExpansionZoom(clusterId).then((zoom) => {
        m.easeTo({ center: (f.geometry as any).coordinates, zoom });
      });
    };
    const onWellClick = (e: maplibregl.MapMouseEvent) => {
      const f = m.queryRenderedFeatures(e.point, { layers: ["well-points"] })[0];
      if (!f) return;
      const p = f.properties as any;
      const [lon, lat] = (f.geometry as any).coordinates;
      onSelectWell?.({ id: p.id, name: p.name, country: p.country, lat, lon, has_events: p.has_events === 1, n_events: p.n_events, documented: p.documented === 1 });
    };
    const onAggClick = (e: maplibregl.MapMouseEvent) => {
      const f = m.queryRenderedFeatures(e.point, { layers: ["aggregate-points"] })[0];
      if (!f) return;
      popupRef.current?.remove();
      const p = f.properties as any;
      popupRef.current = new maplibregl.Popup({ closeButton: true })
        .setLngLat((f.geometry as any).coordinates)
        .setHTML(`<div style="font:13px IBM Plex Sans, sans-serif;max-width:220px"><b>${escapeHtml(p.name)}</b><br/>block aggregate — not a single well</div>`)
        .addTo(m);
    };
    const onBasinClick = (e: maplibregl.MapMouseEvent) => {
      const f = m.queryRenderedFeatures(e.point, { layers: ["basin-fill"] })[0];
      if (!f) return;
      const p = f.properties as any;
      onSelectBasin?.({ name: p.name, slug: p.slug, url: p.url, category: p.category ?? null });
    };
    const cursorOn = () => { m.getCanvas().style.cursor = "pointer"; };
    const cursorOff = () => { m.getCanvas().style.cursor = ""; };
    for (const layer of ["well-clusters", "well-points", "aggregate-points", "basin-fill"]) {
      m.on("mouseenter", layer, cursorOn);
      m.on("mouseleave", layer, cursorOff);
    }
    m.on("click", "well-clusters", onClusterClick);
    m.on("click", "well-points", onWellClick);
    m.on("click", "aggregate-points", onAggClick);
    m.on("click", "basin-fill", onBasinClick);

    Promise.all([
      get<any>("/api/geo/wells").then((r) => { wellsRef.current = decodeGeoWells(r); }),
      get<any>("/api/geo/basins").then((r) => { basinsRef.current = r; }),
    ]).then(() => { if (m.isStyleLoaded()) draw(); setDataLoaded(true); }).catch((e) => setErr(String(e?.message ?? e)));

    return () => { m.remove(); map.current = null; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Redraw when filters/props that affect layers change (cheap: sources already loaded, this just calls setData).
  useEffect(() => { if (loaded) draw(); }, [loaded, draw]);

  // Theme toggle after init: swap the base style; the "style.load" listener registered above redraws our layers.
  const themeRef = useRef(theme);
  useEffect(() => {
    const m = map.current;
    if (!m || !loaded || themeRef.current === theme) return;
    themeRef.current = theme;
    m.setStyle(theme === "dark" ? MAP_STYLES.dark : MAP_STYLES.light);
  }, [theme, loaded]);

  // Fit bounds to the data: once all wells are in (open fitted to every located well, not centred on India),
  // and again whenever the country filter changes (fit to that country's wells).
  useEffect(() => {
    const m = map.current;
    if (!m || !loaded || !dataLoaded) return;
    const wells = wellsRef.current.filter((w) => !country || w.country === country);
    const b = bboxOf(wells);
    if (b) m.fitBounds(b, { padding: 48, duration: 600, maxZoom: 8 });
  }, [country, loaded, dataLoaded]);

  // Fly to a searched well and open its popup context (selection itself is left to the caller via onSelectWell).
  useEffect(() => {
    const m = map.current;
    if (!m || !flyTo) return;
    m.flyTo({ center: [flyTo.lon, flyTo.lat], zoom: 10, duration: 800 });
  }, [flyTo]);

  const toggle3D = () => {
    const m = map.current;
    if (!m) return;
    const next = !is3D;
    setIs3D(next);
    if (next) { enableTerrain(m); m.easeTo({ pitch: 60, bearing: -10, duration: 600 }); }
    else { disableTerrain(m); m.easeTo({ pitch: 0, bearing: 0, duration: 600 }); }
  };
  const toggleSat = () => setSatOn((v) => !v);

  return (
    <div className={className} style={{ position: "relative", height, width: "100%" }}>
      <div ref={el} style={{ position: "absolute", inset: 0, borderRadius: "var(--radius-lg, 12px)", overflow: "hidden",
                              border: "1px solid var(--border, #E4E7EC)" }} role="img" aria-label="map of wells" />
      <div style={{ position: "absolute", left: 12, top: 12, display: "flex", flexDirection: "column", gap: 6, zIndex: 1 }}>
        <MapButton active={is3D} onClick={toggle3D} label="3D terrain toggle">3D</MapButton>
        {canSatellite && <MapButton active={satOn} onClick={toggleSat} label="satellite imagery toggle">SAT</MapButton>}
      </div>
      <div style={{ position: "absolute", left: 12, bottom: 28, zIndex: 1, fontSize: 12, color: "var(--text, #1B1A17)",
                    background: "var(--surface, #FBFAF6)", border: "1px solid var(--border, #E4E7EC)", borderRadius: 8,
                    padding: "8px 10px", boxShadow: "var(--shadow-sm, 0 1px 2px rgba(0,0,0,.08))" }}>
        <div style={{ fontWeight: 600, marginBottom: 4 }}>{loaded ? `${n.toLocaleString()} located wells` : "Loading wells…"}</div>
        <LegendRow color="#DC2626" ring="#7F1D1D" shape="circle" label="Wells with recorded events" />
        <LegendRow color="#94A3B8" ring="#475569" shape="circle" label="Other wells" />
        <LegendRow color="#64748B" shape="square" label="Block / field aggregates" />
        <LegendRow color="transparent" ring="#0F766E" shape="dashed" label="Indian sedimentary basins" />
      </div>
      {err && <div role="alert" style={{ position: "absolute", left: 12, right: 12, top: 52, background: "#FEF2F2", color: "#991B1B",
                                          border: "1px solid #FCA5A5", borderRadius: 6, padding: "6px 10px", fontSize: 13 }}>{err}</div>}
    </div>
  );
}

function MapButton({ active, onClick, label, children }: { active: boolean; onClick: () => void; label: string; children: React.ReactNode }) {
  return (
    <button type="button" onClick={onClick} aria-pressed={active} aria-label={label}
      style={{ font: "600 11px IBM Plex Mono, monospace", padding: "6px 10px", borderRadius: 6, cursor: "pointer",
               border: `1px solid ${active ? "var(--accent, #0F766E)" : "var(--border, #E4E7EC)"}`,
               background: active ? "var(--accent, #0F766E)" : "var(--surface, #FBFAF6)",
               color: active ? "#FFFFFF" : "var(--text, #1B1A17)" }}>
      {children}
    </button>
  );
}

function LegendRow({ color, ring, shape, label }: { color: string; ring?: string; shape: "circle" | "square" | "dashed"; label: string }) {
  const swatch =
    shape === "square" ? (
      <span style={{ width: 9, height: 9, background: color, display: "inline-block", flex: "0 0 auto" }} />
    ) : shape === "dashed" ? (
      <span style={{ width: 12, height: 8, border: `1.5px dashed ${ring}`, borderRadius: 2, display: "inline-block", flex: "0 0 auto" }} />
    ) : (
      <span style={{ width: 10, height: 10, borderRadius: 999, background: color, border: ring ? `1.5px solid ${ring}` : undefined, display: "inline-block", flex: "0 0 auto" }} />
    );
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 2, whiteSpace: "nowrap" }}>
      {swatch}
      <span style={{ color: "var(--text-2, #5E5A50)" }}>{label}</span>
    </div>
  );
}

function escapeHtml(s: string) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c] as string));
}
