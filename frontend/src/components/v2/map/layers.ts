/** Source/layer setup for WellMap.tsx — kept out of the component so the effect blocks stay short.
 * Every function is idempotent: safe to call again after a style reload (e.g. light/dark toggle). */
import type * as maplibregl from "maplibre-gl";
import { TERRAIN_TILE_URL, TERRAIN_ATTRIBUTION, satelliteTileUrl, SATELLITE_ATTRIBUTION } from "./styles";
import { squareIcon } from "./geo";

const HAZARD = "#DC2626";      // --hazard fallback (state colour, paired with the ring + tooltip text)
const HAZARD_RING = "#7F1D1D";
const NEUTRAL = "#94A3B8";
const NEUTRAL_RING = "#475569";
const ACCENT = "#0F766E";

export function ensureWellsSource(map: maplibregl.Map, data: GeoJSON.FeatureCollection) {
  const src = map.getSource("wells") as maplibregl.GeoJSONSource | undefined;
  if (src) { src.setData(data as any); return; }
  map.addSource("wells", { type: "geojson", data: data as any, cluster: true, clusterRadius: 40, clusterMaxZoom: 14 });
  map.addLayer({
    id: "well-clusters", type: "circle", source: "wells", filter: ["has", "point_count"],
    paint: {
      "circle-color": ["step", ["get", "point_count"], "#3B82F6", 50, "#2563EB", 500, ACCENT, 5000, "#0B4F49"],
      "circle-radius": ["step", ["get", "point_count"], 14, 50, 18, 500, 24, 5000, 32],
      "circle-stroke-width": 2, "circle-stroke-color": "#FFFFFF",
    },
  });
  map.addLayer({
    id: "well-cluster-count", type: "symbol", source: "wells", filter: ["has", "point_count"],
    layout: { "text-field": ["get", "point_count_abbreviated"], "text-size": 12, "text-font": ["Noto Sans Regular"] },
    paint: { "text-color": "#0B1220" },
  });
  map.addLayer({
    id: "well-points", type: "circle", source: "wells", filter: ["!", ["has", "point_count"]],
    paint: {
      "circle-radius": ["case", ["==", ["get", "has_events"], 1], 6, ["==", ["get", "documented"], 1], 4.5, 3],
      "circle-color": ["case", ["==", ["get", "has_events"], 1], HAZARD, NEUTRAL],
      "circle-stroke-color": ["case", ["==", ["get", "has_events"], 1], HAZARD_RING, NEUTRAL_RING],
      "circle-stroke-width": 1.2,
    },
  });
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

export function ensureBasinsLayer(map: maplibregl.Map, data: GeoJSON.FeatureCollection) {
  const src = map.getSource("basins") as maplibregl.GeoJSONSource | undefined;
  if (src) { src.setData(data as any); return; }
  map.addSource("basins", { type: "geojson", data: data as any });
  map.addLayer({ id: "basin-fill", type: "fill", source: "basins", paint: { "fill-color": ACCENT, "fill-opacity": 0.06 } });
  map.addLayer({ id: "basin-line", type: "line", source: "basins", paint: { "line-color": ACCENT, "line-width": 1.5, "line-dasharray": [2, 2] } });
  map.addLayer({ id: "basin-label", type: "symbol", source: "basins",
    layout: { "symbol-placement": "point", "text-field": ["get", "name"], "text-size": 11, "text-font": ["Noto Sans Regular"] },
    paint: { "text-color": ACCENT, "text-halo-color": "#FFFFFF", "text-halo-width": 1.4 } });
}

export function ensureRadiusLayer(map: maplibregl.Map, data: GeoJSON.FeatureCollection | null) {
  const empty = { type: "FeatureCollection", features: [] } as GeoJSON.FeatureCollection;
  const src = map.getSource("radius") as maplibregl.GeoJSONSource | undefined;
  if (src) { src.setData((data ?? empty) as any); return; }
  map.addSource("radius", { type: "geojson", data: (data ?? empty) as any });
  map.addLayer({ id: "radius-fill", type: "fill", source: "radius", paint: { "fill-color": ACCENT, "fill-opacity": 0.05 } });
  map.addLayer({ id: "radius-line", type: "line", source: "radius", paint: { "line-color": ACCENT, "line-width": 1.5, "line-dasharray": [3, 2] } });
}

export function ensureActiveWellLayer(map: maplibregl.Map, data: GeoJSON.FeatureCollection | null) {
  const empty = { type: "FeatureCollection", features: [] } as GeoJSON.FeatureCollection;
  const src = map.getSource("active-well") as maplibregl.GeoJSONSource | undefined;
  if (src) { src.setData((data ?? empty) as any); return; }
  map.addSource("active-well", { type: "geojson", data: (data ?? empty) as any });
  map.addLayer({ id: "active-well-point", type: "circle", source: "active-well",
    paint: { "circle-radius": 9, "circle-color": "transparent", "circle-stroke-color": ACCENT, "circle-stroke-width": 2.5 } });
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
}

export function ensureSatelliteLayer(map: maplibregl.Map, visible: boolean) {
  const url = satelliteTileUrl();
  if (!url) return false;
  if (!map.getSource("satellite")) {
    map.addSource("satellite", { type: "raster", tiles: [url], tileSize: 256, attribution: SATELLITE_ATTRIBUTION });
    const firstSymbol = map.getStyle()?.layers?.[0]?.id;
    map.addLayer({ id: "satellite-layer", type: "raster", source: "satellite", layout: { visibility: visible ? "visible" : "none" } }, firstSymbol);
  } else {
    map.setLayoutProperty("satellite-layer", "visibility", visible ? "visible" : "none");
  }
  return true;
}
