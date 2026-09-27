/** SVG hatch OVERLAYS (§11.2 shapes, ROUND 3: transparent backgrounds — the vivid fill comes from
 *  formationColor/lithColor underneath, drawn as a separate rect; these patterns add texture on top).
 *  sandstone=dots, shale=short dashes, limestone=brick, claystone=fine lines, chalk=sparse blocks. */
export function LithologyPatterns() {
  return (
    <svg width="0" height="0" style={{ position: "absolute" }} aria-hidden="true">
      <defs>
        <pattern id="lith-sand" width="8" height="8" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="0.9" fill="#00000055" /><circle cx="6" cy="6" r="0.9" fill="#00000055" /></pattern>
        <pattern id="lith-shale" width="12" height="6" patternUnits="userSpaceOnUse"><line x1="1" y1="3" x2="6" y2="3" stroke="#00000055" strokeWidth="0.9" /></pattern>
        <pattern id="lith-lime" width="16" height="8" patternUnits="userSpaceOnUse"><path d="M0 0H16M0 4H16M4 0V4M12 4V8" stroke="#00000040" strokeWidth="0.7" fill="none" /></pattern>
        <pattern id="lith-clay" width="8" height="4" patternUnits="userSpaceOnUse"><line x1="0" y1="2" x2="8" y2="2" stroke="#00000040" strokeWidth="0.5" /></pattern>
        <pattern id="lith-chalk" width="16" height="12" patternUnits="userSpaceOnUse"><rect x="3" y="3" width="4" height="3" fill="none" stroke="#00000040" strokeWidth="0.6" /></pattern>
        <pattern id="lith-granite" width="10" height="10" patternUnits="userSpaceOnUse"><path d="M2 3l2 -1M6 7l2 1M7 2l1 2" stroke="#00000055" strokeWidth="0.8" /></pattern>
        <pattern id="lith-unknown" width="10" height="10" patternUnits="userSpaceOnUse"><rect width="10" height="10" fill="transparent" /></pattern>
      </defs>
    </svg>
  );
}
/** Maps a free-text lithology string to one of the six textured hatch categories (or "unknown" = no texture). */
export const hatchKey = (l?: string | null): string => {
  if (!l) return "unknown";
  const k = l.toLowerCase();
  if (k.includes("sand")) return "sand";
  if (k.includes("shale") || k.includes("mud")) return "shale";
  if (k.includes("lime") || k.includes("carbonate") || k.includes("dolomite")) return "lime";
  if (k.includes("clay")) return "clay";
  if (k.includes("chalk") || k.includes("marl")) return "chalk";
  if (k.includes("granite") || k.includes("basement") || k.includes("volcanic")) return "granite";
  return "unknown";
};
export const hatchUrl = (l?: string | null) => `url(#lith-${hatchKey(l)})`;
/** @deprecated kept for compatibility; prefer formationColor (vivid fill) + hatchUrl (texture overlay). */
export const lithFill = hatchUrl;
