"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { get } from "@/lib/api";
import { styleFor, type BaseStyleId } from "./map/styles";
import { decodeGeoWells, wellsToGeoJSON, bboxOf, circleGeoJSON, type MapWell } from "./map/geo";
import {
  ensureWellsSource, setWellColorMode, type WellColorMode, ensureHeatmapLayer, setLayerVisible,
  ensureAggregatesLayer, ensureBasinsLayer, setBasinHover, ensureRadiusLayer, ensureActiveWellLayer,
  setActiveWellPulse, enableTerrain, disableTerrain, setHillshadeVisible, setBordersLabelsVisible,
} from "./map/layers";
import { COUNTRY_COLOR, HAZARD_COLOR, countryColor, hazardColor } from "@/lib/palette";

// MapLibre v6 worker as a separate ES module; served from /public (same pattern as components/kk/MiniMap.tsx).
if (typeof window !== "undefined") maplibregl.setWorkerUrl("/maplibre/maplibre-gl-worker.mjs");

export type SelectedWell = { id: number; name: string; country: string; lat: number; lon: number; has_events: boolean; n_events: number; documented: boolean; topHazard: string | null };
export type SelectedBasin = { name: string; slug: string; url: string; category: string | null };
export type FlyTarget = { id: number; lat: number; lon: number } | null;

const BASE_STYLES: { id: BaseStyleId; label: string }[] = [
  { id: "streets", label: "Streets" },
  { id: "terrain", label: "Terrain" },
  { id: "satellite", label: "Satellite" },
  { id: "dark", label: "Dark" },
];

type Layers = { wells: boolean; heatmap: boolean; clusters: boolean; basins: boolean; borders: boolean; terrain: boolean; radius: boolean };
const DEFAULT_LAYERS: Layers = { wells: true, heatmap: false, clusters: true, basins: true, borders: true, terrain: false, radius: true };

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
  const pulseRaf = useRef<number | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [dataLoaded, setDataLoaded] = useState(false);
  const [n, setN] = useState(0);
  const [err, setErr] = useState<string | null>(null);
  const [base, setBase] = useState<BaseStyleId>(theme === "dark" ? "dark" : "streets");
  const [layers, setLayers] = useState<Layers>(DEFAULT_LAYERS);
  const [colorMode, setColorMode] = useState<WellColorMode>("country");
  const [coords, setCoords] = useState<{ lat: number; lon: number } | null>(null);

  const is3D = base === "terrain" || layers.terrain;
  const drawRef = useRef<() => void>(() => {});
  const is3DRef = useRef(is3D);
  is3DRef.current = is3D;

  const draw = useCallback(() => {
    const m = map.current;
    if (!m) return;
    const wells = wellsRef.current.filter((w) => !country || w.country === country);
    setN(wells.length);
    const wellsGeoJSON = wellsToGeoJSON(wells, "well");
    ensureWellsSource(m, wellsGeoJSON, colorMode, layers.clusters);
    ensureAggregatesLayer(m, wellsToGeoJSON(wells, "other"));
    ensureHeatmapLayer(m, wellsGeoJSON, layers.heatmap);
    if (basinsRef.current) ensureBasinsLayer(m, basinsRef.current);
    ensureRadiusLayer(m, activeWell ? (circleGeoJSON([activeWell.lat, activeWell.lon], radiusKm * 1000) as any) : null);
    ensureActiveWellLayer(m, activeWell
      ? { type: "FeatureCollection", features: [{ type: "Feature", properties: {}, geometry: { type: "Point", coordinates: [activeWell.lon, activeWell.lat] } }] }
      : null);
    setLayerVisible(m, "well-points", layers.wells);
    setLayerVisible(m, "well-clusters", layers.wells);
    setLayerVisible(m, "well-cluster-count", layers.wells);
    setLayerVisible(m, "aggregate-points", layers.wells);
    for (const id of ["basin-fill", "basin-fill-hover", "basin-line", "basin-label"]) setLayerVisible(m, id, layers.basins);
    for (const id of ["radius-fill", "radius-line"]) setLayerVisible(m, id, layers.radius);
    setBordersLabelsVisible(m, layers.borders);
    setHillshadeVisible(m, is3D);
  }, [country, activeWell, radiusKm, colorMode, layers, is3D]);
  drawRef.current = draw;

  // Init map + load data once.
  useEffect(() => {
    if (!el.current || map.current) return;
    const m = new maplibregl.Map({
      container: el.current, style: styleFor(base) as any,
      center: [80, 22], zoom: 3.4, attributionControl: false,
    });
    map.current = m;
    m.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");
    m.addControl(new maplibregl.GeolocateControl({ positionOptions: { enableHighAccuracy: true }, trackUserLocation: false }), "top-right");
    m.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
    m.addControl(new maplibregl.FullscreenControl(), "top-right");
    m.addControl(new maplibregl.AttributionControl({ compact: false }), "bottom-right");

    // "style.load" (not "load") marks the map usable: "load" waits for every tile to finish, and with a busy
    // basemap it can arrive very late or not at all, which left the wells undrawn and the style buttons dead.
    // It also fires after every setStyle(), so runtime layers are redrawn after a base-style switch.
    m.on("style.load", () => { setLoaded(true); drawRef.current(); if (is3DRef.current) enableTerrain(m); else m.setTerrain(null); });
    m.on("mousemove", (e) => setCoords({ lat: e.lngLat.lat, lon: e.lngLat.lng }));

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
      const topHazard: string | null = p.top_hazard || null;
      popupRef.current?.remove();
      const chip = topHazard
        ? `<span style="display:inline-block;padding:2px 8px;border-radius:999px;background:${hazardColor(topHazard)};color:#fff;font:600 11px IBM Plex Sans, sans-serif;margin-top:4px">${escapeHtml(topHazard.replace(/_/g, " "))}</span>`
        : `<span style="font:12px IBM Plex Sans, sans-serif;color:#64748B">no recorded events</span>`;
      popupRef.current = new maplibregl.Popup({ closeButton: true, offset: 10 })
        .setLngLat([lon, lat])
        .setHTML(`<div style="font:13px IBM Plex Sans, sans-serif;max-width:220px">
            <b>${escapeHtml(p.name)}</b><br/>
            <span style="color:${countryColor(p.country)};font-weight:600">${escapeHtml(p.country)}</span>
            · ${p.n_events} event${p.n_events === 1 ? "" : "s"}<br/>${chip}
          </div>`)
        .addTo(m);
      onSelectWell?.({ id: p.id, name: p.name, country: p.country, lat, lon, has_events: p.has_events === 1, n_events: p.n_events, documented: p.documented === 1, topHazard });
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
    const onBasinMove = (e: maplibregl.MapMouseEvent) => {
      const f = m.queryRenderedFeatures(e.point, { layers: ["basin-fill"] })[0];
      setBasinHover(m, (f?.properties as any)?.name ?? null);
    };
    const onBasinLeave = () => setBasinHover(m, null);
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
    m.on("mousemove", "basin-fill", onBasinMove);
    m.on("mouseleave", "basin-fill", onBasinLeave);

    Promise.all([
      get<any>("/api/geo/wells").then((r) => { wellsRef.current = decodeGeoWells(r); }),
      get<any>("/api/geo/basins").then((r) => { basinsRef.current = r; }),
    ]).then(() => setDataLoaded(true)).catch((e) => setErr(String(e?.message ?? e)));

    return () => { if (pulseRaf.current) cancelAnimationFrame(pulseRaf.current); m.remove(); map.current = null; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Redraw when filters/props that affect layers change (cheap: sources already loaded, this just calls setData).
  // During a base-style swap the style is briefly not loaded; skip then — the "style.load" handler redraws.
  useEffect(() => { if (loaded && dataLoaded) { try { draw(); } catch { /* style mid-swap */ } } }, [loaded, dataLoaded, draw]);

  // Well colour mode (country vs top hazard) — cheap paint-property swap, no redraw needed.
  useEffect(() => { if (map.current && loaded) { try { setWellColorMode(map.current, colorMode); } catch { /* style mid-swap */ } } }, [colorMode, loaded]);

  // Base style switch: swap the style; "style.load" (registered above) redraws our runtime layers.
  const baseRef = useRef(base);
  useEffect(() => {
    const m = map.current;
    if (!m || !loaded || baseRef.current === base) return;
    baseRef.current = base;
    m.setStyle(styleFor(base) as any, { diff: false });
  }, [base, loaded]);

  // Keep base in sync with the app-wide light/dark theme (only when the user hasn't picked Satellite/Terrain explicitly at init time).
  useEffect(() => { setBase((prev) => (prev === "streets" || prev === "dark" ? (theme === "dark" ? "dark" : "streets") : prev)); }, [theme]);

  // 3D pitch follows either the Terrain base style or the standalone terrain layer toggle.
  useEffect(() => {
    const m = map.current;
    if (!m || !loaded) return;
    if (is3D) { try { enableTerrain(m); } catch { /* style mid-swap; style.load re-applies it */ } m.easeTo({ pitch: 60, bearing: -10, duration: 600 }); }
    else { try { disableTerrain(m); } catch { /* style mid-swap: the new style starts without terrain anyway */ } m.easeTo({ pitch: 0, bearing: 0, duration: 600 }); }
  }, [is3D, loaded]);

  // Pulsing active-well marker (real location, animation only — no invented data).
  useEffect(() => {
    const m = map.current;
    if (!m || !activeWell) return;
    const t0 = performance.now();
    const tick = (t: number) => {
      const phase = ((t - t0) / 1400) % 1;
      try { setActiveWellPulse(m, 9 + phase * 10, 0.9 * (1 - phase)); } catch { /* style mid-swap */ }
      pulseRaf.current = requestAnimationFrame(tick);
    };
    pulseRaf.current = requestAnimationFrame(tick);
    return () => { if (pulseRaf.current) cancelAnimationFrame(pulseRaf.current); };
  }, [activeWell]);

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

  const legendCountries = Object.keys(COUNTRY_COLOR).filter((c) => wellsRef.current.some((w) => w.country === c));
  const legendHazards = Object.keys(HAZARD_COLOR).filter((h) => wellsRef.current.some((w) => w.topHazard === h));

  const layerCount = [layers.wells, layers.clusters, layers.heatmap, layers.basins, layers.borders, is3D, layers.radius].filter(Boolean).length;

  return (
    <div className={className} style={{ display: "flex", flexDirection: "column", gap: 8, height, width: "100%", minWidth: 0 }}>
      {/* Toolbar above the map: nothing floats over the map except MapLibre's own zoom buttons. */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap", fontSize: 12.5 }}>
        <div style={{ display: "flex", border: "1px solid var(--border)", borderRadius: 6, padding: 2, gap: 2, background: "var(--surface)" }}
             role="group" aria-label="map base style">
          {BASE_STYLES.map((s) => (
            <button key={s.id} type="button" aria-pressed={base === s.id} onClick={() => setBase(s.id)} disabled={!loaded}
              style={{ font: "600 12px IBM Plex Sans, sans-serif", padding: "4px 10px", borderRadius: 4, cursor: loaded ? "pointer" : "wait", border: "none",
                       background: base === s.id ? "var(--text)" : "transparent",
                       color: base === s.id ? "var(--surface)" : "var(--text)" }}>
              {s.label}
            </button>
          ))}
        </div>
        <details style={{ position: "relative" }}>
          <summary className="btn" style={{ listStyle: "none", cursor: "pointer", padding: "4px 10px" }}>
            Layers <span className="mono">{layerCount}/7</span> ▾
          </summary>
          <div style={{ position: "absolute", top: "calc(100% + 4px)", left: 0, zIndex: 30, minWidth: 190, display: "flex", flexDirection: "column", gap: 5,
                        background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 6, padding: "8px 10px" }}>
            <LayerCheck label="Wells" checked={layers.wells} onChange={(v) => setLayers((l) => ({ ...l, wells: v }))} />
            <LayerCheck label="Clusters" checked={layers.clusters} onChange={(v) => setLayers((l) => ({ ...l, clusters: v }))} />
            <LayerCheck label="Event heatmap" checked={layers.heatmap} onChange={(v) => setLayers((l) => ({ ...l, heatmap: v }))} />
            <LayerCheck label="Indian basins" checked={layers.basins} onChange={(v) => setLayers((l) => ({ ...l, basins: v }))} />
            <LayerCheck label="Borders & labels" checked={layers.borders} onChange={(v) => setLayers((l) => ({ ...l, borders: v }))} />
            <LayerCheck label="Hillshade / 3D terrain" checked={is3D} onChange={(v) => { setLayers((l) => ({ ...l, terrain: v })); if (!v && base === "terrain") setBase("streets"); }} />
            <LayerCheck label="Radius circle" checked={layers.radius} onChange={(v) => setLayers((l) => ({ ...l, radius: v }))} />
          </div>
        </details>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }} role="radiogroup" aria-label="colour wells by">
          <span className="label">Colour by</span>
          <label style={{ display: "flex", gap: 4, alignItems: "center", cursor: "pointer" }}>
            <input type="radio" name="wellcolor" checked={colorMode === "country"} onChange={() => setColorMode("country")} style={{ accentColor: "var(--accent)" }} /> country
          </label>
          <label style={{ display: "flex", gap: 4, alignItems: "center", cursor: "pointer" }}>
            <input type="radio" name="wellcolor" checked={colorMode === "hazard"} onChange={() => setColorMode("hazard")} style={{ accentColor: "var(--accent)" }} /> hazard
          </label>
        </div>
        <span className="mono" style={{ marginLeft: "auto", color: "var(--text-2)" }}>
          {loaded && dataLoaded ? `${n.toLocaleString()} located wells` : "Loading wells…"}
        </span>
      </div>

      <div style={{ position: "relative", flex: "1 1 auto", minHeight: 320 }}>
        <div ref={el} style={{ position: "absolute", inset: 0, borderRadius: "var(--radius-lg, 12px)", overflow: "hidden",
                                border: "1px solid var(--border, #E4E7EC)" }} role="img" aria-label="map of wells" />
        {coords && (
          <div style={{ position: "absolute", left: 10, top: 10, zIndex: 1, font: "11px IBM Plex Mono, monospace",
                        color: "var(--text-2)", background: "var(--surface)", border: "1px solid var(--border)",
                        borderRadius: 4, padding: "2px 6px", pointerEvents: "none" }}>
            {coords.lat.toFixed(3)}, {coords.lon.toFixed(3)}
          </div>
        )}
        {err && <div role="alert" style={{ position: "absolute", left: 12, right: 12, top: 12, background: "#FEF2F2", color: "#991B1B",
                                            border: "1px solid #FCA5A5", borderRadius: 6, padding: "6px 10px", fontSize: 13 }}>{err}</div>}
      </div>

      {/* Legend strip below the map */}
      <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", columnGap: 14, rowGap: 3, fontSize: 12,
                    padding: "6px 10px", border: "1px solid var(--border)", borderRadius: "var(--radius-lg)", background: "var(--surface)" }}>
        <span className="eyebrow" style={{ fontSize: 10.5 }}>{colorMode === "country" ? "Wells by country" : "Wells by top hazard"}</span>
        {colorMode === "country" ? (
          legendCountries.length
            ? legendCountries.map((c) => <LegendRow key={c} color={countryColor(c)} shape="circle" label={c} />)
            : <LegendRow color="#94A3B8" shape="circle" label="no country data yet" />
        ) : (
          legendHazards.length
            ? legendHazards.map((h) => <LegendRow key={h} color={hazardColor(h)} shape="circle" label={h.replace(/_/g, " ")} />)
            : <LegendRow color="#94A3B8" shape="circle" label="no recorded hazards yet" />
        )}
        <span style={{ width: 1, height: 14, background: "var(--border)" }} aria-hidden="true" />
        <LegendRow color="#64748B" shape="square" label="Block / field aggregate" />
        <LegendRow color="transparent" ring="#1F5F66" shape="dashed" label="Indian sedimentary basin" />
      </div>
    </div>
  );
}

function LayerCheck({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label style={{ display: "flex", alignItems: "center", gap: 6, font: "12px IBM Plex Sans, sans-serif", cursor: "pointer", color: "var(--text, #1B1A17)" }}>
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} /> {label}
    </label>
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
    <div style={{ display: "flex", alignItems: "center", gap: 6, whiteSpace: "nowrap" }}>
      {swatch}
      <span style={{ color: "var(--text-2, #5E5A50)" }}>{label}</span>
    </div>
  );
}

function escapeHtml(s: string) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c] as string));
}
