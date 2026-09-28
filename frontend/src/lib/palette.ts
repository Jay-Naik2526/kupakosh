// Kupakosh v3 colour system — vivid, consistent across 2D, maps and 3D.
// Colour is never the only signal: every coloured item also carries a label or glyph.

/** Brand gradient (header, hero, primary buttons). */
export const BRAND = { from: "#1D4ED8", via: "#0E7490", to: "#0F766E", accent: "#F59E0B" };

/** One colour per hazard (categorical). Kick/losses keep the "danger" hues. */
export const HAZARD_COLOR: Record<string, string> = {
  lost_circulation: "#E11D48", // rose
  kick: "#DC2626",             // red
  stuck_pipe: "#EA580C",       // orange
  torque_spike: "#D97706",     // amber
  overpressure: "#9333EA",     // violet
  cementing_issue: "#0891B2",  // cyan
  fishing: "#4F46E5",          // indigo
  wellbore_instability: "#CA8A04", // mustard
};
export const hazardColor = (h: string) => HAZARD_COLOR[h] ?? "#64748B";

/** Lithology fills (geology-inspired, vivid enough for 3D slabs). */
export const LITH_COLOR: Record<string, string> = {
  sand: "#F4D35E", sandstone: "#F4D35E",
  shale: "#6B8F71", claystone: "#A47551", clay: "#A47551",
  lime: "#7FB7D6", limestone: "#7FB7D6", carbonate: "#7FB7D6",
  chalk: "#E8E4D8", marl: "#B5C99A",
  coal: "#3F3F46", salt: "#F0ABFC", evaporite: "#F0ABFC", anhydrite: "#F9A8D4",
  granite: "#C08497", basement: "#C08497", volcanic: "#8B5CF6",
  mixed: "#94A3B8", unknown: "#CBD5E1",
};
export const lithColor = (l?: string | null) => {
  if (!l) return LITH_COLOR.unknown;
  const k = l.toLowerCase();
  for (const key of Object.keys(LITH_COLOR)) if (k.includes(key)) return LITH_COLOR[key];
  return LITH_COLOR.unknown;
};

/** Stable colour per formation name when lithology is unknown (hash into a vivid ramp). */
const FORMATION_RAMP = ["#FDE68A", "#A7F3D0", "#BFDBFE", "#FBCFE8", "#DDD6FE", "#FED7AA", "#BBF7D0", "#C7D2FE", "#FECACA", "#99F6E4", "#E9D5FF", "#FEF08A"];
export const formationColor = (name: string, lithology?: string | null) => {
  if (lithology) { const c = lithColor(lithology); if (c !== LITH_COLOR.unknown) return c; }
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0;
  return FORMATION_RAMP[h % FORMATION_RAMP.length];
};

/** Distinct colours for wells in a scene (active well is always BRAND.via / cyan-teal). */
export const WELL_SERIES = ["#2563EB", "#F59E0B", "#10B981", "#EC4899", "#8B5CF6", "#EF4444", "#14B8A6", "#F97316", "#6366F1", "#84CC16", "#06B6D4", "#D946EF"];
export const wellColor = (i: number) => WELL_SERIES[i % WELL_SERIES.length];

/** One colour per country (maps, charts, chips). */
export const COUNTRY_COLOR: Record<string, string> = {
  India: "#F97316", Norway: "#2563EB", "United Kingdom": "#7C3AED", Netherlands: "#F59E0B",
  USA: "#DC2626", Australia: "#10B981", "New Zealand": "#0EA5E9", Canada: "#DB2777",
};
export const countryColor = (c?: string | null) => (c && COUNTRY_COLOR[c]) || "#64748B";

/** Section accents for sidebar groups and page headers. */
export const SECTION_COLOR: Record<string, string> = {
  operate: "#2563EB", explore: "#0EA5E9", knowledge: "#8B5CF6", ask: "#EC4899", deliver: "#F59E0B", trust: "#10B981",
};
