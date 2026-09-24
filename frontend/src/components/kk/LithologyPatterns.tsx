/** SVG hatch patterns (§11.2): sandstone=dots, shale=short dashes, limestone=brick, claystone=fine lines, chalk=sparse blocks. */
export function LithologyPatterns() {
  return (
    <svg width="0" height="0" style={{ position: "absolute" }} aria-hidden="true">
      <defs>
        <pattern id="lith-sand" width="8" height="8" patternUnits="userSpaceOnUse"><rect width="8" height="8" fill="var(--lith-sand)" /><circle cx="2" cy="2" r="0.9" fill="#6d5d33" /><circle cx="6" cy="6" r="0.9" fill="#6d5d33" /></pattern>
        <pattern id="lith-shale" width="12" height="6" patternUnits="userSpaceOnUse"><rect width="12" height="6" fill="var(--lith-shale)" /><line x1="1" y1="3" x2="6" y2="3" stroke="#4f574a" strokeWidth="0.9" /></pattern>
        <pattern id="lith-lime" width="16" height="8" patternUnits="userSpaceOnUse"><rect width="16" height="8" fill="var(--lith-lime)" /><path d="M0 0H16M0 4H16M4 0V4M12 4V8" stroke="#56646d" strokeWidth="0.7" fill="none" /></pattern>
        <pattern id="lith-clay" width="8" height="4" patternUnits="userSpaceOnUse"><rect width="8" height="4" fill="var(--lith-clay)" /><line x1="0" y1="2" x2="8" y2="2" stroke="#6e5a44" strokeWidth="0.5" /></pattern>
        <pattern id="lith-chalk" width="16" height="12" patternUnits="userSpaceOnUse"><rect width="16" height="12" fill="var(--lith-chalk)" /><rect x="3" y="3" width="4" height="3" fill="none" stroke="#8a877e" strokeWidth="0.6" /></pattern>
        <pattern id="lith-granite" width="10" height="10" patternUnits="userSpaceOnUse"><rect width="10" height="10" fill="var(--lith-granite)" /><path d="M2 3l2 -1M6 7l2 1M7 2l1 2" stroke="#6b5f57" strokeWidth="0.8" /></pattern>
        <pattern id="lith-unknown" width="10" height="10" patternUnits="userSpaceOnUse"><rect width="10" height="10" fill="var(--card)" /></pattern>
      </defs>
    </svg>
  );
}
export const lithFill = (l?: string | null) => `url(#lith-${l && ["sand", "shale", "lime", "clay", "chalk", "granite"].includes(l) ? l : "unknown"})`;
