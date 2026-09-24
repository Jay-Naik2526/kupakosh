import { ScaleLinear, scaleLinear } from "d3-scale";
import { line } from "d3-shape";

export type Pt = { y: number; v: number | null; flag?: boolean };

/** Mud-log style parallel curve track sharing the depth axis; normal band shaded; abnormal points in --hazard. */
export function CurveTrack({ title, unit, pts, y, width = 150, height, band, domain }: {
  title: string; unit: string; pts: Pt[]; y: ScaleLinear<number, number>; width?: number; height: number;
  band?: [number, number] | null; domain?: [number, number];
}) {
  const vals = pts.map((p) => p.v).filter((v): v is number => v !== null && Number.isFinite(v));
  const lo = domain?.[0] ?? (vals.length ? Math.min(...vals) : 0), hi = domain?.[1] ?? (vals.length ? Math.max(...vals) : 1);
  const x = scaleLinear().domain([lo, hi === lo ? lo + 1 : hi]).range([4, width - 4]).nice();
  const path = line<Pt>().defined((p) => p.v !== null && Number.isFinite(p.v as number)).x((p) => x(p.v as number)).y((p) => y(p.y))(pts);
  const last = [...pts].reverse().find((p) => p.v !== null);
  return (
    <figure className="m-0" style={{ width }}>
      <figcaption className="flex justify-between small rule-b pb-0.5 mb-1">
        <span>{title} <span className="label">{unit}</span></span>
        <span className="num">{last?.v !== undefined && last?.v !== null ? (last.v as number).toFixed(unit === "ppg" ? 2 : 1) : "—"}</span>
      </figcaption>
      <svg width={width} height={height} role="img" aria-label={`${title} track`}>
        {x.ticks(3).map((t) => <line key={t} x1={x(t)} x2={x(t)} y1={0} y2={height} stroke="var(--grid)" />)}
        {band && <rect x={x(band[0])} width={Math.max(0, x(band[1]) - x(band[0]))} y={0} height={height} fill="var(--grid)" opacity={0.7}><title>normal band</title></rect>}
        {path && <path d={path} fill="none" stroke="var(--ink)" strokeWidth={1.3} />}
        {pts.filter((p) => p.flag && p.v !== null).map((p, i) => <circle key={i} cx={x(p.v as number)} cy={y(p.y)} r={2.6} fill="var(--hazard)"><title>abnormal</title></circle>)}
        <text x={2} y={height - 3} fontSize={10} fill="var(--ink-2)" className="num">{x.domain()[0]}</text>
        <text x={width - 2} y={height - 3} fontSize={10} fill="var(--ink-2)" className="num" textAnchor="end">{x.domain()[1]}</text>
      </svg>
    </figure>
  );
}

export function DepthAxis({ y, height, width = 46 }: { y: ScaleLinear<number, number>; height: number; width?: number }) {
  return (
    <svg width={width} height={height} role="img" aria-label="depth axis (m MD)">
      {y.ticks(Math.max(4, Math.floor(height / 60))).map((t) => (
        <g key={t}><line x1={width - 6} x2={width} y1={y(t)} y2={y(t)} stroke="var(--ink)" /><text x={width - 8} y={y(t) + 4} fontSize={11} textAnchor="end" className="num" fill="var(--ink)">{t}</text></g>
      ))}
      <line x1={width - 0.5} x2={width - 0.5} y1={0} y2={height} stroke="var(--ink)" />
    </svg>
  );
}
