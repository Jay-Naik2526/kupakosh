"use client";
import { useEffect, useState } from "react";
import { get } from "@/lib/api";
import { formationColor } from "@/lib/palette";
import { LithologyPatterns, hatchUrl } from "@/components/kk/LithologyPatterns";

type Top = { formation: string; label: string; level: string; top_md_m: number; base_md_m: number | null; lithology: string | null; source_ref: string };
type Well = { id: number; name: string; field: string | null; country: string | null; td_md_m: number | null; source: string; tops: Top[] };

/** A real well's formation column, turned on its side and drawn to scale: the Home page's banner.
 *  Every band is a recorded formation top (no invented layers); colour = formation, hatch = lithology. */
export function StrataBanner({ wellName = "15/9-19 S", caption }: { wellName?: string; caption: (w: Well, td: number) => string }) {
  const [well, setWell] = useState<Well | null>(null);

  useEffect(() => {
    let live = true;
    get<{ id: number }[]>("/api/wells", { q: wellName, limit: 1 })
      .then((r) => (r[0] ? get<Well>(`/api/wells/${r[0].id}`) : null))
      .then((w) => { if (live && w) setWell(w); })
      .catch(() => {});
    return () => { live = false; };
  }, [wellName]);

  if (!well || !well.tops?.length) return <div style={{ height: 118 }} aria-hidden="true" />;

  // Unknown rock type is drawn as plain paper (honest), not given an invented colour.
  // Tops in depth order; a group top is dropped where a formation top starts at the same depth (finer level wins).
  const sorted = [...well.tops].sort((a, b) => a.top_md_m - b.top_md_m);
  const fmTops = new Set(sorted.filter((t) => t.level !== "GROUP").map((t) => Math.round(t.top_md_m)));
  const kept = sorted.filter((t) => t.level !== "GROUP" || !fmTops.has(Math.round(t.top_md_m)));
  const bottom = well.td_md_m ?? kept[kept.length - 1].base_md_m ?? kept[kept.length - 1].top_md_m;
  const segs = kept.map((t, i) => ({ ...t, end: kept[i + 1]?.top_md_m ?? bottom })).filter((t) => t.end > t.top_md_m);
  const td = Math.max(...segs.map((s) => s.end));
  const W = 1000, H = 64;
  const x = (m: number) => (m / td) * W;
  const ticks = Array.from({ length: Math.floor(td / 500) + 1 }, (_, i) => i * 500);

  return (
    <figure style={{ margin: 0 }}>
      <svg viewBox={`0 0 ${W} ${H + 34}`} width="100%" role="img" aria-label={`Formation column of well ${well.name}`} style={{ display: "block" }}>
        <LithologyPatterns />
        {segs.map((s) => (
          <g key={s.formation + s.top_md_m}>
            <rect x={x(s.top_md_m)} y={18} width={x(s.end) - x(s.top_md_m)} height={H - 18} fill={s.lithology ? formationColor(s.formation, s.lithology) : "var(--surface-2)"} />
            <rect x={x(s.top_md_m)} y={18} width={x(s.end) - x(s.top_md_m)} height={H - 18} fill={hatchUrl(s.lithology)} />
            <line x1={x(s.top_md_m)} x2={x(s.top_md_m)} y1={18} y2={H} stroke="var(--text)" strokeOpacity={0.55} strokeWidth={1} />
            {x(s.end) - x(s.top_md_m) > 70 && (
              <text x={x(s.top_md_m) + 4} y={12} fontSize={11} fill="var(--text)" style={{ fontFamily: "var(--font-plex)" }}>{s.label}</text>
            )}
          </g>
        ))}
        <rect x={0} y={18} width={W} height={H - 18} fill="none" stroke="var(--text)" strokeWidth={1.2} />
        {ticks.map((m) => (
          <g key={m}>
            <line x1={x(m)} x2={x(m)} y1={H} y2={H + 6} stroke="var(--text)" strokeWidth={1} />
            <text x={Math.min(x(m) + 2, W - 44)} y={H + 18} fontSize={10.5} fill="var(--text-2)" style={{ fontFamily: "var(--font-plex-mono)" }}>{m.toLocaleString()} m</text>
          </g>
        ))}
      </svg>
      <figcaption className="label mt-1">{caption(well, td)}</figcaption>
    </figure>
  );
}
