/** Decoding + geometry helpers for the well map (V4). No React here — plain data functions, easy to unit-test. */

export type GeoWellsResponse = { n: number; countries: string[]; kinds: string[]; hazards?: string[]; fields: string[]; rows: (number | string)[][] };

export type MapWell = {
  id: number; name: string; country: string; lat: number; lon: number;
  has_events: boolean; n_events: number; documented: boolean; kind: "well" | "block_aggregate" | "field_centroid";
  topHazard: string | null;
};

/** Decode the compact index-encoded /api/geo/wells payload into plain per-well objects. */
export function decodeGeoWells(resp: GeoWellsResponse): MapWell[] {
  const hazards = resp.hazards ?? [];
  return resp.rows.map((r) => {
    const hi = (r[9] as number) ?? -1;
    return {
      id: r[0] as number,
      name: r[1] as string,
      country: resp.countries[r[2] as number] ?? "unknown",
      lat: r[3] as number,
      lon: r[4] as number,
      has_events: r[5] === 1,
      n_events: r[6] as number,
      documented: r[7] === 1,
      kind: (resp.kinds[r[8] as number] ?? "well") as MapWell["kind"],
      topHazard: hi >= 0 ? (hazards[hi] ?? null) : null,
    };
  });
}

export type WellFeatureCollection = {
  type: "FeatureCollection";
  features: { type: "Feature"; geometry: { type: "Point"; coordinates: [number, number] }; properties: Record<string, unknown> }[];
};

/** Build a GeoJSON FeatureCollection for either real wells (clustered) or non-well locations (block
 * aggregates / field centroids — drawn as hollow squares, never clustered with real wells). */
export function wellsToGeoJSON(wells: MapWell[], which: "well" | "other"): WellFeatureCollection {
  const filtered = which === "well" ? wells.filter((w) => w.kind === "well") : wells.filter((w) => w.kind !== "well");
  return {
    type: "FeatureCollection",
    features: filtered.map((w) => ({
      type: "Feature",
      geometry: { type: "Point", coordinates: [w.lon, w.lat] },
      properties: { id: w.id, name: w.name, country: w.country, has_events: w.has_events ? 1 : 0,
                    n_events: w.n_events, documented: w.documented ? 1 : 0, kind: w.kind,
                    top_hazard: w.topHazard ?? "" },
    })),
  };
}

export function bboxOf(wells: { lat: number; lon: number }[]): [[number, number], [number, number]] | null {
  if (!wells.length) return null;
  let minLon = Infinity, minLat = Infinity, maxLon = -Infinity, maxLat = -Infinity;
  for (const w of wells) {
    if (w.lon < minLon) minLon = w.lon;
    if (w.lon > maxLon) maxLon = w.lon;
    if (w.lat < minLat) minLat = w.lat;
    if (w.lat > maxLat) maxLat = w.lat;
  }
  return [[minLon, minLat], [maxLon, maxLat]];
}

/** A circle polygon (great-circle approx, fine at well-radius scale) around [lat, lon], radius in metres. */
export function circleGeoJSON([lat, lon]: [number, number], radiusM: number) {
  const pts: [number, number][] = [];
  for (let i = 0; i <= 64; i++) {
    const a = (i / 64) * 2 * Math.PI;
    const dLat = (radiusM * Math.cos(a)) / 111_320;
    const dLon = (radiusM * Math.sin(a)) / (111_320 * Math.cos((lat * Math.PI) / 180));
    pts.push([lon + dLon, lat + dLat]);
  }
  return { type: "FeatureCollection" as const, features: [{ type: "Feature" as const, properties: {}, geometry: { type: "Polygon" as const, coordinates: [pts] } }] };
}

export function ringCentroid(ring: number[][]): [number, number] {
  let lon = 0, lat = 0;
  const n = ring.length - 1; // last point repeats the first
  for (let i = 0; i < n; i++) { lon += ring[i][0]; lat += ring[i][1]; }
  return [lon / n, lat / n];
}

/** Draws a small hollow square onto a canvas, for use as a map symbol icon (block_aggregate / field_centroid). */
export function squareIcon(size = 16, stroke = "#64748B"): HTMLCanvasElement {
  const c = document.createElement("canvas");
  c.width = size; c.height = size;
  const ctx = c.getContext("2d");
  if (ctx) { ctx.lineWidth = 2; ctx.strokeStyle = stroke; ctx.strokeRect(2, 2, size - 4, size - 4); }
  return c;
}
