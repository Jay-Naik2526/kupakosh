// Kupakosh colour system — earth palette of a printed geological survey sheet, shared by 2D, maps and 3D.
// Colour is never the only signal: every coloured item also carries a label or glyph.

/** Brand colours (flat; no gradients). */
export const BRAND = { from: "#1F5F66", via: "#1F5F66", to: "#1F5F66", accent: "#C8902E" };

/** One colour per hazard (categorical). Kick/losses keep the "danger" hues. */
export const HAZARD_COLOR: Record<string, string> = {
  lost_circulation: "#B5542D",     // rust
  kick: "#8E2A24",                 // oxblood
  stuck_pipe: "#C8902E",           // ochre
  torque_spike: "#8C6D1F",         // dark mustard
  overpressure: "#6B4A6E",         // plum
  cementing_issue: "#3D5A73",      // slate
  fishing: "#2F6E73",              // teal
  wellbore_instability: "#6E8B5A", // sage
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
const FORMATION_RAMP = ["#E9D8A6", "#CFDCC0", "#C9D8DE", "#E6C9B8", "#D9CBDC", "#F0DDB4", "#C5D3C9", "#D8D0C0", "#E3C4B4", "#BCD2CF", "#DCCFE0", "#EFE0B0"];
export const formationColor = (name: string, lithology?: string | null) => {
  if (lithology) { const c = lithColor(lithology); if (c !== LITH_COLOR.unknown) return c; }
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0;
  return FORMATION_RAMP[h % FORMATION_RAMP.length];
};

/** Distinct colours for wells in a scene (active well is always BRAND.via / cyan-teal). */
export const WELL_SERIES = ["#1F5F66", "#C8902E", "#A8472A", "#6E8B5A", "#6B4A6E", "#3D5A73", "#B87333", "#8C6D1F", "#4F7C8A", "#8E2A24", "#7A8B3A", "#A0707A"];
export const wellColor = (i: number) => WELL_SERIES[i % WELL_SERIES.length];

/** One colour per country (maps, charts, chips). */
export const COUNTRY_COLOR: Record<string, string> = {
  India: "#D08A2A", Norway: "#3D5A73", "United Kingdom": "#6B4A6E", Netherlands: "#B87333",
  USA: "#A8322A", Australia: "#6E8B5A", "New Zealand": "#2F6E73", Canada: "#8E4A5E",
};
export const countryColor = (c?: string | null) => (c && COUNTRY_COLOR[c]) || "#64748B";

/** Section accents for sidebar groups and page headers. */
export const SECTION_COLOR: Record<string, string> = {
  operate: "#A8472A", explore: "#1F5F66", knowledge: "#6E8B5A", ask: "#6B4A6E", deliver: "#C8902E", trust: "#3D5A73",
};
