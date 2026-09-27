/** Map style + tile source constants (V4/V5). All verified reachable with curl on 2026-09-27 (200 OK). */
import type * as maplibregl from "maplibre-gl";

// OpenFreeMap vector styles, no API key. "liberty" is the colourful default (streets/terrain shading,
// parks, water, buildings); "dark" is a muted control-room variant used for the Dark base style.
export const MAP_STYLES = {
  light: "https://tiles.openfreemap.org/styles/positron",
  dark: "https://tiles.openfreemap.org/styles/dark",
  liberty: "https://tiles.openfreemap.org/styles/liberty",
} as const;

// AWS public Terrarium elevation tiles (open, no key) — used for 3D terrain + hillshade.
export const TERRAIN_TILE_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png";
export const TERRAIN_ATTRIBUTION = "Terrain: AWS Terrain Tiles (Terrarium, Mapzen/Amazon)";

// Esri World Imagery — public XYZ raster tiles, no API key required. Used as the default Satellite base
// style. If NEXT_PUBLIC_MAPTILER_KEY is set, that (higher-res) source is preferred instead.
export const ESRI_SATELLITE_TILE_URL =
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";
export const ESRI_SATELLITE_ATTRIBUTION =
  "Esri, Maxar, Earthstar Geographics, and the GIS User Community";

export function satelliteTileUrl(): string {
  const key = process.env.NEXT_PUBLIC_MAPTILER_KEY;
  return key ? `https://api.maptiler.com/tiles/satellite/{z}/{x}/{y}.jpg?key=${key}` : ESRI_SATELLITE_TILE_URL;
}
export function satelliteAttribution(): string {
  return process.env.NEXT_PUBLIC_MAPTILER_KEY ? "© MapTiler © OpenStreetMap contributors" : ESRI_SATELLITE_ATTRIBUTION;
}
// Kept for callers that only care whether the (non-key) satellite source exists — it always does now.
export const SATELLITE_ATTRIBUTION = ESRI_SATELLITE_ATTRIBUTION;

export type BaseStyleId = "streets" | "terrain" | "satellite" | "dark";

/** A minimal raster-only style object for the Satellite base (Esri imagery has no vector style of its own). */
export function satelliteStyle(): maplibregl.StyleSpecification {
  return {
    version: 8,
    sources: { esri: { type: "raster", tiles: [satelliteTileUrl()], tileSize: 256, attribution: satelliteAttribution() } },
    layers: [{ id: "esri", type: "raster", source: "esri" }],
    glyphs: "https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf",
  } as unknown as maplibregl.StyleSpecification;
}

/** Resolve a base-style id to the vector/raster style URL or object MapLibre should load.
 * "terrain" reuses the colourful liberty vector style — the 3D relief + hillshade are layered on top of it
 * by enableTerrain() in layers.ts, not baked into a separate style. */
export function styleFor(base: BaseStyleId): string | maplibregl.StyleSpecification {
  switch (base) {
    case "dark": return MAP_STYLES.dark;
    case "satellite": return satelliteStyle();
    case "terrain":
    case "streets":
    default: return MAP_STYLES.liberty;
  }
}
