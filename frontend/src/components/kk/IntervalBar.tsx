/** Point estimate + lower-bound whisker on a 0–100% scale. No fat bars (SPEC.md §11.5).
 *  Success is a state (an outcome resolved), so it stays tied to --ok, flat — no gradient. */
export function IntervalBar({ rate, lb, width = 140, anecdotal }: { rate: number | null; lb: number | null; width?: number; anecdotal?: boolean }) {
  if (rate === null) return <span className="label">no known outcome</span>;
  const x = (v: number) => 4 + v * (width - 8);
  return (
    <svg width={width} height={18} role="img" aria-label={`success ${Math.round(rate * 100)}%, lower bound ${Math.round((lb ?? 0) * 100)}%`}>
      <line x1={4} x2={width - 4} y1={9} y2={9} stroke="var(--border)" />
      {[0, 0.5, 1].map((t) => <line key={t} x1={x(t)} x2={x(t)} y1={6} y2={12} stroke="var(--border)" />)}
      {lb !== null && <line x1={x(lb)} x2={x(rate)} y1={9} y2={9} stroke="var(--ok)" strokeWidth={2.5} strokeDasharray={anecdotal ? "2 2" : undefined} />}
      {lb !== null && <line x1={x(lb)} x2={x(lb)} y1={4} y2={14} stroke="var(--ok)" strokeWidth={2} />}
      <circle cx={x(rate)} cy={9} r={4} fill={anecdotal ? "var(--surface)" : "var(--ok)"} stroke="var(--ok)" strokeWidth={1.5} />
    </svg>
  );
}
