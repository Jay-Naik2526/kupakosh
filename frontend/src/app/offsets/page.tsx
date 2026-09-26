"use client";
import { useEffect, useMemo, useState } from "react";
import { scaleLinear } from "d3-scale";
import { get } from "@/lib/api";
import { useApp } from "@/lib/state";
import { glyph, hazardLabel, m } from "@/lib/format";
import { WellPicker } from "@/components/kk/WellPicker";
import { LithologyColumn } from "@/components/kk/LithologyColumn";
import { DepthAxis } from "@/components/kk/CurveTrack";
import { Drawer } from "@/components/kk/Drawer";
import { EmptyState } from "@/components/kk/EmptyState";
import { MiniMap } from "@/components/kk/MiniMap";
import { SourceFootnote } from "@/components/kk/SourceFootnote";
import { CountryFilter } from "@/components/kk/CountryFilter";

const H = 560, COLW = 120, GAP = 44;
const HAZ = Object.keys(hazardLabel);

export default function Offsets() {
  const { wellId, setWellId, ready, country } = useApp();
  const [radius, setRadius] = useState(10000);
  const [align, setAlign] = useState<"md" | "formation">("md");
  const [flatOn, setFlatOn] = useState<string>("");
  const [filter, setFilter] = useState<Set<string>>(new Set(HAZ));
  const [sec, setSec] = useState<any>(null);
  const [mapView, setMapView] = useState(false);
  const [mapWells, setMapWells] = useState<any[]>([]);
  const [sel, setSel] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => { if (ready && !wellId) get("/api/wells", { q: "15/9-19", documented: true, limit: 1 }).then((w) => w[0] && setWellId(w[0].id)); }, [ready]); // eslint-disable-line
  useEffect(() => {
    if (!wellId) return;
    setLoading(true);
    get(`/api/wells/${wellId}/section`, { radius_m: radius, n: 6 }).then((s) => { setSec(s); setLoading(false); });
    get(`/api/wells/${wellId}/offsets`, { radius_m: radius, country: country ?? undefined }).then((o) => setMapWells(o.offsets));
  }, [wellId, radius, country]);

  const cols = sec?.columns ?? [];
  const commonTops: string[] = useMemo(() => {
    if (!cols.length) return [];
    const sets = cols.map((c: any) => new Set(c.tops.map((t: any) => t.formation)));
    return [...sets[0]].filter((f) => sets.every((s: Set<unknown>) => s.has(f))) as string[];
  }, [cols]);
  useEffect(() => { if (commonTops.length && !commonTops.includes(flatOn)) setFlatOn(commonTops[Math.min(2, commonTops.length - 1)]); }, [commonTops]); // eslint-disable-line

  const shift = (c: any) => {
    if (align !== "formation" || !flatOn) return 0;
    const t = c.tops.find((x: any) => x.formation === flatOn);
    return t ? t.top_md_m : 0;
  };
  const maxD = Math.max(500, ...cols.map((c: any) => (c.well.td_md_m ?? 0) - shift(c)));
  const minD = align === "formation" ? Math.min(0, ...cols.map((c: any) => -shift(c))) : 0;
  const y = scaleLinear().domain([minD, maxD]).range([0, H]);

  return (
    <div>
      {/* Zone A — toolbar */}
      <section aria-label="toolbar" className="flex flex-wrap items-center gap-x-5 gap-y-2 rule-b pb-3">
        <CountryFilter />
        <WellPicker label="Active well" />
        <label className="label" htmlFor="rad">Radius</label>
        <select id="rad" className="input" value={radius} onChange={(e) => setRadius(Number(e.target.value))}>
          {[2000, 5000, 10000, 20000, 50000].map((r) => <option key={r} value={r}>{r / 1000} km</option>)}
        </select>
        <span className="label">Align</span>
        <span role="group" aria-label="Align" className="inline-flex gap-1">
          <button className="chip" aria-pressed={align === "md"} onClick={() => setAlign("md")}>MD</button>
          <button className="chip" disabled title="TVD needs surveys; Sodir exploration wells have no public survey here" aria-disabled>TVD</button>
          <button className="chip" aria-pressed={align === "formation"} onClick={() => setAlign("formation")}>Formation</button>
        </span>
        {align === "formation" && (
          <select className="input" aria-label="Flatten on formation" value={flatOn} onChange={(e) => setFlatOn(e.target.value)}>
            {commonTops.map((f) => <option key={f} value={f}>{f}</option>)}
          </select>
        )}
        <span className="flex flex-wrap gap-1" role="group" aria-label="Hazard filter">
          {HAZ.map((h) => (
            <button key={h} className="chip" aria-pressed={filter.has(h)} onClick={() => { const n = new Set(filter); if (n.has(h)) n.delete(h); else n.add(h); setFilter(n); }}>
              {glyph[h]} {hazardLabel[h]}
            </button>
          ))}
        </span>
        <button className="btn ml-auto" onClick={() => setMapView(!mapView)}>{mapView ? "Correlation view" : "Map view"}</button>
      </section>

      {/* Zone B — correlation panel (or map) */}
      <section aria-label="correlation panel" className="mt-5">
        {!wellId && <EmptyState title="No well selected" why="Pick a well with reports to see its offsets." />}
        {loading && <div className="label">Loading offsets…</div>}
        {mapView && sec && (
          <MiniMap height={560} radius_m={radius} center={[cols[0].well.lat, cols[0].well.lon]} onPick={(id) => setWellId(id)}
            wells={[{ ...cols[0].well, active: true }, ...mapWells.map((o) => ({ id: o.well_id, name: o.name, lat: o.lat, lon: o.lon, documented: o.documented, n_events: o.n_events }))]} />
        )}
        {!mapView && sec && cols.length === 1 && <EmptyState title="No documented offset wells in this radius" why="Only wells with a report or history text can contribute evidence. Increase the radius." />}
        {!mapView && sec && (
          <div className="overflow-x-auto">
            <div className="flex">
              <div className="pt-[74px]"><DepthAxis y={y} height={H} /></div>
              <div className="relative" style={{ width: cols.length * (COLW + GAP) }}>
                <svg className="absolute left-0" style={{ top: 74 }} width={cols.length * (COLW + GAP)} height={H} aria-hidden="true">
                  {cols.slice(0, -1).map((c: any, i: number) => c.tops.map((t: any) => {
                    const n = cols[i + 1].tops.find((x: any) => x.formation === t.formation);
                    if (!n) return null;
                    return <line key={`${i}-${t.formation}-${t.top_md_m}`} x1={i * (COLW + GAP) + 50} x2={(i + 1) * (COLW + GAP)} y1={y(t.top_md_m - shift(c))} y2={y(n.top_md_m - shift(cols[i + 1]))}
                      stroke="var(--ink-2)" strokeDasharray="3 3" strokeWidth={0.8} />;
                  }))}
                </svg>
                <div className="flex relative" style={{ gap: GAP }}>
                  {cols.map((c: any, i: number) => {
                    const s = shift(c);
                    const ys = scaleLinear().domain([y.domain()[0] + s, y.domain()[1] + s]).range([0, H]);
                    return (
                      <div key={c.well.id} style={{ width: COLW }}>
                        <div className="small" style={{ height: 74 }}>
                          <div className="font-semibold">{i === 0 ? "▶ " : ""}{c.well.name}</div>
                          {c.offset ? <div className="label num">{m(c.offset.raw.distance_m)} · sim {c.offset.sim.toFixed(2)}</div> : <div className="label">active well</div>}
                          <div className="label">{c.events.length} events · TD {m(c.well.td_md_m)}</div>
                        </div>
                        <LithologyColumn intervals={c.tops} y={ys} height={H} width={COLW} labels
                          glyphs={c.events.filter((e: any) => filter.has(e.hazard)).map((e: any) => ({ md_m: e.md_m, hazard: e.hazard, dim: e.needs_review, onClick: () => setSel({ ...e, well: c.well.name }) }))} />
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
            <p className="label mt-2">Glyphs: {HAZ.map((h) => `${glyph[h]} ${hazardLabel[h]}`).join(" · ")}. Grey glyphs need review. Patterns: dominant lithology from reports (FORGE) or the Norwegian lexicon (approximate); blank = not recorded.</p>
          </div>
        )}
      </section>

      {/* Zone C — selected event */}
      <Drawer open={!!sel} onClose={() => setSel(null)} title={sel ? `${glyph[sel.hazard]} ${hazardLabel[sel.hazard]} — ${sel.well}` : ""}>
        {sel && (
          <div>
            <div className="small"><span className="label">Depth</span> <span className="num">{m(sel.md_m)}</span> · <span className="label">Formation</span> {sel.formation ?? "unknown"} · <span className="label">confidence</span> <span className="num">{sel.confidence.toFixed(2)}</span>{sel.needs_review && <b> · needs review</b>}</div>
            <blockquote className="mt-3 border-l-2 border-ink pl-3 italic">“{sel.evidence}”<SourceFootnote refId={sel.source_ref} n={1} /></blockquote>
            <div className="label mt-2 mono">{sel.source_ref}</div>
          </div>
        )}
      </Drawer>
    </div>
  );
}
