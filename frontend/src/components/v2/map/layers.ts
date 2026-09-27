/** Source/layer setup for WellMap.tsx — kept out of the component so the effect blocks stay short.
 * Every function is idempotent: safe to call again after a style reload (e.g. a base-style switch). */
import type * as maplibregl from "maplibre-gl";
import { TERRAIN_TILE_URL, TERRAIN_ATTRIBUTION } from "./styles";
import { squareIcon } from "./geo";
import { COUNTRY_COLOR, HAZARD_COLOR } from "@/lib/palette";

const NEUTRAL = "#94A3B8";
const NEUTRAL_RING = "#475569";
const ACCENT = "#0F766E";

export type WellColorMode = "country" | "hazard";

/** Build a MapLibre `match` colour expression from a palette lookup table, with NEUTRAL as the fallback. */
function matchExpr(propGetter: unknown[], table: Record<string, string>): unknown[] {
  const stops: unknown[] = [];
  for (const [k, v] of Object.entries(table)) { stops.push(k, v); }
  return ["match", propGetter, ...stops, NEUTRAL];
}

function wellColorExpr(mode: WellColorMode) {
  return mode === "hazard"
    ? matchExpr(["get", "top_hazard"], HAZARD_COLOR)
    : matchExpr(["get", "country"], COUNTRY_COLOR);
}

const wellsClusterState = new WeakMap<maplibregl.Map, boolean>();

/** cluster=false rebuilds the source unclustered (every well rendered individually); toggling back re-adds
 * clustering. Rebuilding (not just setData) is required because MapLibre's `cluster` option is fixed at
 * source-creation time. */
export function ensureWellsSource(map: maplibregl.Map, data: GeoJSON.FeatureCollection, colorMode: WellColorMode = "country", cluster = true) {
  const src = map.getSource("wells") as maplibregl.GeoJSONSource | undefined;
  if (src && wellsClusterState.get(map) === cluster) { src.setData(data as any); setWellColorMode(map, colorMode); return; }
  if (src) {
    for (const id of ["well-clusters", "well-cluster-count", "well-points"]) if (map.getLayer(id)) map.removeLayer(id);
    map.removeSource("wells");
  }
  wellsClusterState.set(map, cluster);
  map.addSource("wells", { type: "geojson", data: data as any, cluster, clusterRadius: cluster ? 42 : 0, clusterMaxZoom: 14, clusterProperties: { hasEvent: ["max", ["case", ["==", ["get", "has_events"], 1], 1, 0]] } });
  map.addLayer({
    id: "well-clusters", type: "circle", source: "wells", filter: ["has", "point_count"],
    paint: {
      // Vivid size gradient; a red ring flags clusters containing at least one well with recorded events.
      "circle-color": ["step", ["get", "point_count"], "#60A5FA", 50, "#2563EB", 500, "#7C3AED", 5000, "#DB2777"],
      "circle-radius": ["step", ["get", "point_count"], 14, 50, 18, 500, 24, 5000, 32],
      "circle-stroke-width": 2.5,
      "circle-stroke-color": ["case", [">", ["get", "hasEvent"], 0], HAZARD_COLOR.lost_circulation, "#FFFFFF"],
    },
  });
  map.addLayer({
    id: "well-cluster-count", type: "symbol", source: "wells", filter: ["has", "point_count"],
    layout: { "text-field": ["get", "point_count_abbreviated"], "text-size": 12, "text-font": ["Noto Sans Bold"] },
    paint: { "text-color": "#FFFFFF" },
  });
  map.addLayer({
    id: "well-points", type: "circle", source: "wells", filter: ["!", ["has", "point_count"]],
    paint: {
      "circle-radius": ["case", ["==", ["get", "has_events"], 1], 6.5, ["==", ["get", "documented"], 1], 4.5, 3],
      "circle-color": wellColorExpr(colorMode) as any,
      // Hazard halo: wells with recorded events get a thicker ring in that hazard's colour; others get a plain dark stroke.
      "circle-stroke-color": ["case", ["!=", ["get", "top_hazard"], ""], matchExpr(["get", "top_hazard"], HAZARD_COLOR), NEUTRAL_RING] as any,
      "circle-stroke-width": ["case", ["==", ["get", "has_events"], 1], 2.5, 1],
    },
  });
  map.setLayoutProperty("well-points", "circle-sort-key" as any, ["get", "n_events"]);
}

/** Switch the well-points colour between "by country" and "by top hazard" without rebuilding the source. */
export function setWellColorMode(map: maplibregl.Map, mode: WellColorMode) {
  if (!map.getLayer("well-points")) return;
  map.setPaintProperty("well-points", "circle-color", wellColorExpr(mode) as any);
}

export function ensureHeatmapLayer(map: maplibregl.Map, data: GeoJSON.FeatureCollection, visible: boolean) {
  const src = map.getSource("events-heat") as maplibregl.GeoJSONSource | undefined;
  if (src) { src.setData(data as any); if (map.getLayer("events-heatmap")) map.setLayoutProperty("events-heatmap", "visibility", visible ? "visible" : "none"); return; }
  map.addSource("events-heat", { type: "geojson", data: data as any });
  map.addLayer({
    id: "events-heatmap", type: "heatmap", source: "events-heat",
    layout: { visibility: visible ? "visible" : "none" },
    paint: {
      "heatmap-weight": ["interpolate", ["linear"], ["get", "n_events"], 0, 0, 1, 0.4, 20, 1],
      "heatmap-intensity": 1.1,
      "heatmap-color": ["interpolate", ["linear"], ["heatmap-density"],
        0, "rgba(0,0,0,0)", 0.2, "#3B82F6", 0.4, "#22D3EE", 0.6, "#FACC15", 0.8, "#F97316", 1, "#DC2626"],
      "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 0, 8, 6, 22, 12, 36],
      "heatmap-opacity": 0.75,
    },
  }, "well-points");
}

export function setLayerVisible(map: maplibregl.Map, layerId: string, visible: boolean) {
  if (!map.getLayer(layerId)) return;
  map.setLayoutProperty(layerId, "visibility", visible ? "visible" : "none");
}

export function ensureAggregatesLayer(map: maplibregl.Map, data: GeoJSON.FeatureCollection) {
  if (!map.hasImage("kk-square")) {
    const canvas = squareIcon(16, "#64748B");
    const imgData = canvas.getContext("2d")?.getImageData(0, 0, canvas.width, canvas.height);
    if (imgData) map.addImage("kk-square", imgData, { pixelRatio: 1 });
  }
  const src = map.getSource("aggregates") as maplibregl.GeoJSONSource | undefined;
  if (src) { src.setData(data as any); return; }
  map.addSource("aggregates", { type: "geojson", data: data as any });
  map.addLayer({ id: "aggregate-points", type: "symbol", source: "aggregates",
    layout: { "icon-image": "kk-square", "icon-size": 1, "icon-allow-overlap": true } });
}

const BASIN_RAMP = ["#F97316", "#2563EB", "#7C3AED", "#DB2777", "#0891B2", "#65A30D", "#D97706", "#BE123C"];

export function ensureBasinsLayer(map: maplibregl.Map, data: GeoJSON.FeatureCollection) {
  const src = map.getSource("basins") as maplibregl.GeoJSONSource | undefined;
  if (src) { src.setData(data as any); return; }
  // Give each basin feature a stable colour index so fills are visually distinct, not one flat teal wash.
  const withIdx = { ...data, features: data.features.map((f, i) => ({ ...f, properties: { ...f.properties, _c: BASIN_RAMP[i % BASIN_RAMP.length] } })) };
  map.addSource("basins", { type: "geojson", data: withIdx as any });
  map.addLayer({ id: "basin-fill", type: "fill", source: "basins", paint: { "fill-color": ["get", "_c"], "fill-opacity": 0.22 } });
  map.addLayer({ id: "basin-fill-hover", type: "fill", source: "basins", filter: ["==", ["get", "name"], ""], paint: { "fill-color": ["get", "_c"], "fill-opacity": 0.45 } });
  map.addLayer({ id: "basin-line", type: "line", source: "basins", paint: { "line-color": ["get", "_c"], "line-width": 2 } });
  map.addLayer({ id: "basin-label", type: "symbol", source: "basins",
    layout: { "symbol-placement": "point", "text-field": ["get", "name"], "text-size": 12, "text-font": ["Noto Sans Bold"] },
    paint: { "text-color": ["get", "_c"], "text-halo-color": "#FFFFFF", "text-halo-width": 1.6 } });
}

export function setBasinHover(map: maplibregl.Map, name: string | null) {
  if (!map.getLayer("basin-fill-hover")) return;
  map.setFilter("basin-fill-hover", ["==", ["get", "name"], name ?? ""]);
}

export function ensureRadiusLayer(map: maplibregl.Map, data: GeoJSON.FeatureCollection | null) {
  const empty = { type: "FeatureCollection", features: [] } as GeoJSON.FeatureCollection;
  const src = map.getSource("radius") as maplibregl.GeoJSONSource | undefined;
  if (src) { src.setData((data ?? empty) as any); return; }
  map.addSource("radius", { type: "geojson", data: (data ?? empty) as any });
  map.addLayer({ id: "radius-fill", type: "fill", source: "radius", paint: { "fill-color": ACCENT, "fill-opacity": 0.08 } });
  map.addLayer({ id: "radius-line", type: "line", source: "radius", paint: { "line-color": ACCENT, "line-width": 2, "line-dasharray": [3, 2] } });
}

export function ensureActiveWellLayer(map: maplibregl.Map, data: GeoJSON.FeatureCollection | null) {
  const empty = { type: "FeatureCollection", features: [] } as GeoJSON.FeatureCollection;
  const src = map.getSource("active-well") as maplibregl.GeoJSONSource | undefined;
  if (src) { src.setData((data ?? empty) as any); return; }
  map.addSource("active-well", { type: "geojson", data: (data ?? empty) as any });
  // Two rings (a static outer + an animated pulsing inner, driven from WellMap's rAF loop via setActiveWellPulse)
  // so the active well reads clearly against a busy, colourful basemap.
  map.addLayer({ id: "active-well-pulse", type: "circle", source: "active-well",
    paint: { "circle-radius": 9, "circle-color": "transparent", "circle-stroke-color": "#F59E0B", "circle-stroke-width": 2, "circle-stroke-opacity": 0.9 } });
  map.addLayer({ id: "active-well-point", type: "circle", source: "active-well",
    paint: { "circle-radius": 7, "circle-color": "#F59E0B", "circle-stroke-color": "#FFFFFF", "circle-stroke-width": 2 } });
}

export function setActiveWellPulse(map: maplibregl.Map, radius: number, opacity: number) {
  if (!map.getLayer("active-well-pulse")) return;
  map.setPaintProperty("active-well-pulse", "circle-radius", radius);
  map.setPaintProperty("active-well-pulse", "circle-stroke-opacity", opacity);
}

export function enableTerrain(map: maplibregl.Map) {
  if (!map.getSource("terrain-dem")) {
    map.addSource("terrain-dem", { type: "raster-dem", tiles: [TERRAIN_TILE_URL], tileSize: 256, encoding: "terrarium", maxzoom: 15, attribution: TERRAIN_ATTRIBUTION } as any);
  }
  if (!map.getLayer("hillshade")) {
    const firstSymbol = map.getStyle()?.layers?.find((l) => l.type === "symbol")?.id;
    map.addLayer({ id: "hillshade", type: "hillshade", source: "terrain-dem", paint: { "hillshade-exaggeration": 0.5 } }, firstSymbol);
  }
  map.setTerrain({ source: "terrain-dem", exaggeration: 1.4 });
}

export function disableTerrain(map: maplibregl.Map) {
  map.setTerrain(null);
  if (map.getLayer("hillshade")) map.setLayoutProperty("hillshade", "visibility", "none");
}

export function setHillshadeVisible(map: maplibregl.Map, visible: boolean) {
  if (map.getLayer("hillshade")) map.setLayoutProperty("hillshade", "visibility", visible ? "visible" : "none");
}

/** Toggle the base style's own admin-boundary + place-label layers (country borders/labels). OpenFreeMap's
 * liberty/dark/positron styles (openmaptiles schema) name these with "boundary" and "place" substrings —
 * we match loosely on id/source-layer instead of hardcoding exact ids, so this degrades gracefully if the
 * upstream style changes layer names. */
export function setBordersLabelsVisible(map: maplibregl.Map, visible: boolean) {
  const layers = map.getStyle()?.layers ?? [];
  for (const l of layers) {
    const sl = (l as any)["source-layer"] as string | undefined;
    const hay = `${l.id} ${sl ?? ""}`.toLowerCase();
    if (hay.includes("boundary") || hay.includes("place")) {
      try { map.setLayoutProperty(l.id, "visibility", visible ? "visible" : "none"); } catch { /* not a layout-visible layer */ }
    }
  }
}
