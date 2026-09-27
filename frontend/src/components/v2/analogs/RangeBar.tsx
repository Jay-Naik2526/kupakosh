/** Mean point + a two-sided 80% range on a 0–100% scale (analog evidence has both bounds, unlike the ledger's lower-bound-only IntervalBar). `color` tints the range line and mean dot per-hazard. */
export function RangeBar({ mean, ci, width = 160, color = "var(--accent)" }: { mean: number; ci: [number, number]; width?: number; color?: string }) {
  const x = (v: number) => 4 + Math.min(1, Math.max(0, v)) * (width - 8);
  return (
    <svg width={width} height={18} role="img" aria-label={`mean ${Math.round(mean * 100)}%, 80% range ${Math.round(ci[0] * 100)}–${Math.round(ci[1] * 100)}%`}>
      <line x1={4} x2={width - 4} y1={9} y2={9} stroke="var(--rule, var(--border))" />
      {[0, 0.5, 1].map((t) => <line key={t} x1={x(t)} x2={x(t)} y1={6} y2={12} stroke="var(--rule, var(--border))" />)}
      <line x1={x(ci[0])} x2={x(ci[1])} y1={9} y2={9} stroke={color} strokeWidth={3} />
      <line x1={x(ci[0])} x2={x(ci[0])} y1={5} y2={13} stroke={color} strokeWidth={1.4} />
      <line x1={x(ci[1])} x2={x(ci[1])} y1={5} y2={13} stroke={color} strokeWidth={1.4} />
      <circle cx={x(mean)} cy={9} r={4.5} fill={color} stroke="var(--text, var(--ink))" strokeWidth={1} />
    </svg>
  );
}
