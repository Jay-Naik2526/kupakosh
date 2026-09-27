/** Map style + tile source constants (V4). All verified reachable with curl on 2026-09-27 (200 OK). */

// OpenFreeMap vector styles, no API key. "positron"-like light and a dark control-room variant; "liberty" is
// the richer default style, kept as a fallback if the other two ever go away.
export const MAP_STYLES = {
  light: "https://tiles.openfreemap.org/styles/positron",
  dark: "https://tiles.openfreemap.org/styles/dark",
  liberty: "https://tiles.openfreemap.org/styles/liberty",
} as const;

// AWS public Terrarium elevation tiles (open, no key) — used for 3D terrain + hillshade.
export const TERRAIN_TILE_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png";
export const TERRAIN_ATTRIBUTION = "Terrain: AWS Terrain Tiles (Terrarium, Mapzen/Amazon)";

export function satelliteTileUrl(): string | null {
  const key = process.env.NEXT_PUBLIC_MAPTILER_KEY;
  return key ? `https://api.maptiler.com/tiles/satellite/{z}/{x}/{y}.jpg?key=${key}` : null;
}
export const SATELLITE_ATTRIBUTION = "© MapTiler © OpenStreetMap contributors";
