import { ScaleLinear } from "d3-scale";
import { glyph, hazardLabel } from "@/lib/format";
import { hatchUrl } from "./LithologyPatterns";
import { formationColor, hazardColor } from "@/lib/palette";

export type Interval = { formation: string; label: string; top_md_m: number; base_md_m: number | null; lithology?: string | null };
export type Glyph = { md_m: number; hazard: string; id?: number; onClick?: () => void; dim?: boolean };

/** Depth-scaled formation column with hatch patterns, bit marker, target bracket and event glyphs. */
export function LithologyColumn({ intervals, y, width = 120, height, bit, target, glyphs = [], labels = true, header }: {
  intervals: Interval[]; y: ScaleLinear<number, number>; width?: number; height: number; bit?: number | null;
  target?: { md: number; text: string } | null; glyphs?: Glyph[]; labels?: boolean; header?: React.ReactNode;
}) {
  const [d0, d1] = y.domain();
  const colW = labels ? Math.min(46, width * 0.4) : width - 18;
  return (
    <svg width={width} height={height} role="img" aria-label="formation column">
      {intervals.map((it, i) => {
        const top = Math.max(it.top_md_m, d0), base = Math.min(it.base_md_m ?? d1, d1);
        if (base <= d0 || top >= d1 || base <= top) return null;
        const y0 = y(top), h = y(base) - y0;
        const fill = formationColor(it.formation ?? it.label, it.lithology);
        return (
          <g key={i}>
            <rect x={1} y={y0} width={colW} height={h} fill={fill} stroke="var(--ink)" strokeWidth={0.6}><title>{`${it.label}: ${Math.round(it.top_md_m)}–${it.base_md_m ? Math.round(it.base_md_m) : "?"} m${it.lithology ? " · " + it.lithology : " · lithology not recorded"}`}</title></rect>
            <rect x={1} y={y0} width={colW} height={h} fill={hatchUrl(it.lithology)} pointerEvents="none" />
            {labels && h > 11 && <text x={colW + 5} y={y0 + 11} fontSize={11} fontWeight={600} fill="var(--ink)">{it.label.length > 18 ? it.label.slice(0, 17) + "…" : it.label}</text>}
            {labels && h > 24 && <text x={colW + 5} y={y0 + 23} fontSize={10} fill="var(--ink-2)" className="num">{Math.round(it.top_md_m)} m</text>}
          </g>
        );
      })}
      {target && target.md >= d0 && target.md <= d1 && (
        <g aria-label={target.text}>
          <path d={`M${colW + 1} ${y(target.md) - 6} h6 v12 h-6`} fill="none" stroke="var(--hazard)" strokeWidth={2} />
          <line x1={1} x2={colW + 1} y1={y(target.md)} y2={y(target.md)} stroke="var(--hazard)" strokeWidth={2} />
        </g>
      )}
      {bit !== null && bit !== undefined && bit >= d0 && bit <= d1 && (
        <g aria-label={`bit at ${Math.round(bit)} m`}>
          <line x1={0} x2={colW + 2} y1={y(bit)} y2={y(bit)} stroke="var(--hazard)" strokeWidth={2.5} />
          <path d={`M${colW + 2} ${y(bit)} l7 -5 v10z`} fill="var(--hazard)" />
        </g>
      )}
      {glyphs.filter((g) => g.md_m >= d0 && g.md_m <= d1).map((g, i) => (
        <text key={i} x={colW / 2} y={y(g.md_m) + 4} textAnchor="middle" fontSize={13} fontWeight={700} fill={g.dim ? "var(--ink-2)" : hazardColor(g.hazard)} stroke="var(--card)" strokeWidth={3} paintOrder="stroke"
              style={{ cursor: g.onClick ? "pointer" : undefined }} onClick={g.onClick}>
          {glyph[g.hazard] ?? "•"}<title>{`${hazardLabel[g.hazard]} at ${Math.round(g.md_m)} m${g.dim ? " (needs review)" : ""}`}</title>
        </text>
      ))}
      {header}
    </svg>
  );
}
