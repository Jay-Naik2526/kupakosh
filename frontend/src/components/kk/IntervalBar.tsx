import { useId } from "react";

/** Point estimate + lower-bound whisker on a 0–100% scale. No fat bars (SPEC.md §11.5).
 *  ROUND 3: success side rendered with a green gradient (--ok, darker toward the estimate). */
export function IntervalBar({ rate, lb, width = 140, anecdotal }: { rate: number | null; lb: number | null; width?: number; anecdotal?: boolean }) {
  const gid = useId().replace(/:/g, "");
  if (rate === null) return <span className="label">no known outcome</span>;
  const x = (v: number) => 4 + v * (width - 8);
  return (
    <svg width={width} height={18} role="img" aria-label={`success ${Math.round(rate * 100)}%, lower bound ${Math.round((lb ?? 0) * 100)}%`}>
      <defs>
        <linearGradient id={`ib-${gid}`} x1="0" x2="1" y1="0" y2="0">
          <stop offset="0" stopColor="var(--ok)" stopOpacity={0.45} />
          <stop offset="1" stopColor="var(--ok)" stopOpacity={1} />
        </linearGradient>
      </defs>
      <line x1={4} x2={width - 4} y1={9} y2={9} stroke="var(--border)" />
      {[0, 0.5, 1].map((t) => <line key={t} x1={x(t)} x2={x(t)} y1={6} y2={12} stroke="var(--border)" />)}
      {lb !== null && <line x1={x(lb)} x2={x(rate)} y1={9} y2={9} stroke={`url(#ib-${gid})`} strokeWidth={2.5} strokeDasharray={anecdotal ? "2 2" : undefined} />}
      {lb !== null && <line x1={x(lb)} x2={x(lb)} y1={4} y2={14} stroke="var(--ok)" strokeWidth={2} />}
      <circle cx={x(rate)} cy={9} r={4} fill={anecdotal ? "var(--surface)" : "var(--ok)"} stroke="var(--ok)" strokeWidth={1.5} />
    </svg>
  );
}
