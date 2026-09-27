"use client";
import { useEffect, useMemo, useState } from "react";
import { scaleLinear } from "d3-scale";
import { get } from "@/lib/api";
import { useApp } from "@/lib/state";
import { Lang } from "@/lib/i18n";
import { glyph, hazardLabel, hazardText, m } from "@/lib/format";
import { t } from "@/lib/i18n";
import { Card, Tabs } from "@/components/v2/ui";
import { Subsurface3D } from "@/components/v2/Subsurface3D";
import { LithologyColumn } from "@/components/kk/LithologyColumn";
import { DepthAxis } from "@/components/kk/CurveTrack";
import { Drawer } from "@/components/kk/Drawer";
import { EmptyState } from "@/components/kk/EmptyState";
import { MiniMap } from "@/components/kk/MiniMap";
import { SourceFootnote } from "@/components/kk/SourceFootnote";
import { CountryFilter } from "@/components/kk/CountryFilter";
import { formationColor, wellColor } from "@/lib/palette";

const H = 560, COLW = 120, GAP = 44;
const HAZ = Object.keys(hazardLabel);

/** Bilingual copy local to this page (docs/PLAN_V2.md scope keeps lib/i18n.ts to nav keys so parallel agents don't collide). */
const tr = (lang: Lang, en: string, hi: string) => (lang === "hi" ? hi : en);

export default function Offsets() {
  const { wellId, setWellId, ready, country, lang } = useApp();
  const [radius, setRadius] = useState(10000);
  const [align, setAlign] = useState<"md" | "formation">("md");
  const [flatOn, setFlatOn] = useState<string>("");
  const [filter, setFilter] = useState<Set<string>>(new Set(HAZ));
  const [sec, setSec] = useState<any>(null);
  const [view, setView] = useState<"correlation" | "map" | "3d">("correlation");
  const [mapWells, setMapWells] = useState<any[]>([]);
  const [sel, setSel] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  // Note: the *active* well is picked once, globally, in the top bar (useApp().wellId) — this
  // page just falls back to a documented well the first time it loads with none chosen.
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
  const activeName = cols[0]?.well?.name ?? null;

  return (
    <div>
      {/* Zone A — toolbar */}
      <section aria-label="toolbar" className="mb-5">
        <Card>
          <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
            <div className="small">
              <span className="label">{tr(lang, "Active well", "सक्रिय कूप")}: </span>
              <span className="font-semibold">{activeName ?? "—"}</span>
              <button className="btn ml-2" style={{ padding: "1px 9px" }} onClick={() => document.getElementById("wellq")?.focus()}>
                {tr(lang, "Change ▸", "बदलें ▸")}
              </button>
            </div>
            <CountryFilter label={t("countryLabel", lang)} />
          </div>
          <div className="flex flex-wrap items-center gap-x-5 gap-y-2 mt-3 pt-3" style={{ borderTop: "1px solid var(--border)" }}>
            <label className="label" htmlFor="rad">{t("radius", lang)}</label>
            <select id="rad" className="input" value={radius} onChange={(e) => setRadius(Number(e.target.value))}>
              {[2000, 5000, 10000, 20000, 50000].map((r) => <option key={r} value={r}>{r / 1000} km</option>)}
            </select>
            <span className="label">{t("offsAlign", lang)}</span>
            <span role="group" aria-label="Align" className="inline-flex gap-1">
              <button className="chip" aria-pressed={align === "md"} onClick={() => setAlign("md")}>MD</button>
              <button className="chip" disabled title="TVD needs surveys; Sodir exploration wells have no public survey here" aria-disabled>TVD</button>
              <button className="chip" aria-pressed={align === "formation"} onClick={() => setAlign("formation")}>{t("offsFormationLbl", lang)}</button>
            </span>
            {align === "formation" && (
              <select className="input" aria-label="Flatten on formation" value={flatOn} onChange={(e) => setFlatOn(e.target.value)}>
                {commonTops.map((f) => <option key={f} value={f}>{f}</option>)}
              </select>
            )}
            <span className="flex flex-wrap gap-1" role="group" aria-label="Hazard filter">
              {HAZ.map((h) => (
                <button key={h} className="chip" aria-pressed={filter.has(h)} onClick={() => { const n = new Set(filter); if (n.has(h)) n.delete(h); else n.add(h); setFilter(n); }}>
                  {glyph[h]} {hazardText(h, lang)}
                </button>
              ))}
            </span>
            <div className="ml-auto">
              <Tabs
                items={[
                  { key: "correlation", label: t("offsCorrelation", lang) },
                  { key: "map", label: t("offsMap", lang) },
                  { key: "3d", label: tr(lang, "3D", "3D") },
                ]}
                active={view}
                onChange={(k) => setView(k as any)}
              />
            </div>
          </div>
        </Card>
      </section>

      {/* Zone B — correlation panel, map, or 3D */}
      <section aria-label="correlation panel" className="mt-2">
        {!wellId && <EmptyState title={t("cmdNoWellSelected", lang)} why={t("offsNoWellWhy", lang)} />}
        {loading && <div className="label">{t("loadingOffsets", lang)}</div>}
        {view === "map" && sec && (
          <Card className="p-0 overflow-hidden">
            <MiniMap height={560} radius_m={radius} center={[cols[0].well.lat, cols[0].well.lon]}
              wells={[{ ...cols[0].well, active: true }, ...mapWells.map((o) => ({ id: o.well_id, name: o.name, lat: o.lat, lon: o.lon, documented: o.documented, n_events: o.n_events }))]} />
          </Card>
        )}
        {view === "3d" && wellId && <Subsurface3D wellId={wellId} radius={radius} height={560} />}
        {view === "correlation" && sec && cols.length === 1 && <EmptyState title={t("offsNoDocTitle", lang)} why={t("offsNoDocWhy", lang)} />}
        {view === "correlation" && sec && (
          <Card>
            <div className="overflow-x-auto">
              <div className="flex">
                <div className="pt-[74px]"><DepthAxis y={y} height={H} /></div>
                <div className="relative" style={{ width: cols.length * (COLW + GAP) }}>
                  <svg className="absolute left-0" style={{ top: 74 }} width={cols.length * (COLW + GAP)} height={H} aria-hidden="true">
                    {cols.slice(0, -1).map((c: any, i: number) => c.tops.map((t: any) => {
                      const n = cols[i + 1].tops.find((x: any) => x.formation === t.formation);
                      if (!n) return null;
                      return <line key={`${i}-${t.formation}-${t.top_md_m}`} x1={i * (COLW + GAP) + 50} x2={(i + 1) * (COLW + GAP)} y1={y(t.top_md_m - shift(c))} y2={y(n.top_md_m - shift(cols[i + 1]))}
                        stroke={formationColor(t.formation, t.lithology)} strokeDasharray="3 3" strokeWidth={1.4} opacity={0.85} />;
                    }))}
                  </svg>
                  <div className="flex relative" style={{ gap: GAP }}>
                    {cols.map((c: any, i: number) => {
                      const s = shift(c);
                      const ys = scaleLinear().domain([y.domain()[0] + s, y.domain()[1] + s]).range([0, H]);
                      return (
                        <div key={c.well.id} style={{ width: COLW }}>
                          <div className="small" style={{ height: 74 }}>
                            <div className="font-semibold flex items-center gap-1.5">
                              <span aria-hidden="true" style={{ width: 9, height: 9, borderRadius: 999, background: wellColor(i), flex: "0 0 auto" }} />
                              {i === 0 ? "▶ " : ""}{c.well.name}
                            </div>
                            {c.offset ? <div className="label num">{m(c.offset.raw.distance_m)} · sim {c.offset.sim.toFixed(2)}</div> : <div className="label">{t("offsActiveWellTag", lang)}</div>}
                            <div className="label">{c.events.length} {t("cmdEvents", lang)} · TD {m(c.well.td_md_m)}</div>
                          </div>
                          <LithologyColumn intervals={c.tops} y={ys} height={H} width={COLW} labels
                            glyphs={c.events.filter((e: any) => filter.has(e.hazard)).map((e: any) => ({ md_m: e.md_m, hazard: e.hazard, dim: e.needs_review, onClick: () => setSel({ ...e, well: c.well.name }) }))} />
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
              <p className="label mt-2">{t("offsGlyphsPrefix", lang)} {HAZ.map((h) => `${glyph[h]} ${hazardText(h, lang)}`).join(" · ")}. {t("offsGreyNote", lang)}</p>
            </div>
          </Card>
        )}
      </section>

      {/* Zone C — selected event */}
      <Drawer open={!!sel} onClose={() => setSel(null)} title={sel ? `${glyph[sel.hazard]} ${hazardText(sel.hazard, lang)} — ${sel.well}` : ""}>
        {sel && (
          <div>
            <div className="small"><span className="label">{t("offsDepthLbl", lang)}</span> <span className="num">{m(sel.md_m)}</span> · <span className="label">{t("offsFormationLbl", lang)}</span> {sel.formation ?? t("offsUnknown", lang)} · <span className="label">{t("offsConfidenceLbl", lang)}</span> <span className="num">{sel.confidence.toFixed(2)}</span>{sel.needs_review && <b> · {t("offsNeedsReview", lang)}</b>}</div>
            <blockquote className="mt-3 border-l-2 border-ink pl-3 italic">“{sel.evidence}”<SourceFootnote refId={sel.source_ref} n={1} /></blockquote>
            <div className="label mt-2 mono">{sel.source_ref}</div>
          </div>
        )}
      </Drawer>
    </div>
  );
}
