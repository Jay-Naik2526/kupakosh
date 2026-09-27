"use client";
import { useEffect, useMemo, useState } from "react";
import { scaleLinear } from "d3-scale";
import { get } from "@/lib/api";
import { useApp } from "@/lib/state";
import { m, ppg } from "@/lib/format";
import { LithologyColumn } from "@/components/kk/LithologyColumn";
import { Register } from "@/components/kk/Register";
import { EmptyState } from "@/components/kk/EmptyState";
import { SourceFootnote } from "@/components/kk/SourceFootnote";
import { Tabs } from "@/components/v2/ui";
import { t } from "@/lib/i18n";

const H = 560, W = 560, PAD = { l: 52, r: 12, t: 22, b: 30 };
const NEAR = 0.3; // mirrors config mudwindow.near_edge_ppg (display only)

/** Focus the global top-bar well combobox, so "Active well: X · change" doesn't need its own picker. */
function focusTopBarWellPicker() {
  const el = document.getElementById("wellq") as HTMLInputElement | null;
  el?.scrollIntoView({ behavior: "smooth", block: "center" });
  el?.focus();
}

export default function MudWindow() {
  const { wellId, setWellId, ready, openSource, lang } = useApp();
  const [radius, setRadius] = useState(10000);
  const [d, setD] = useState<any>(null);
  const [well, setWell] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<"formation" | "casing">("formation");
  useEffect(() => { if (ready && !wellId) get("/api/wells", { q: "15/9-19", documented: true, limit: 1 }).then((w) => w[0] && setWellId(w[0].id)); }, [ready]); // eslint-disable-line
  useEffect(() => { if (!wellId) { setWell(null); return; } get(`/api/wells/${wellId}`).then(setWell).catch(() => setWell(null)); }, [wellId]);
  useEffect(() => { if (!wellId) return; setLoading(true); get("/api/mudwindow", { well: wellId, radius_m: radius }).then((x) => { setD(x); setLoading(false); }); }, [wellId, radius]);

  const rows = d?.formations ?? [];
  const pts = rows.flatMap((r: any) => [...r.upper_evidence.map((e: any) => ({ ...e, side: "upper" })), ...r.lower_evidence.map((e: any) => ({ ...e, side: "lower" }))]).filter((e: any) => e.md_m);
  const active = (d?.active_well_mw ?? []) as any[];
  const maxD = Math.max(1000, ...pts.map((p: any) => p.md_m), ...active.map((a) => a.md_m), ...rows.map((r: any) => r.base_md_m ?? 0));
  const y = useMemo(() => scaleLinear().domain([0, maxD]).range([PAD.t, H - PAD.b]).nice(), [maxD]);
  const allP = [...pts.map((p: any) => p.ppg), ...active.map((a) => a.ppg)];
  const x = scaleLinear().domain([Math.min(8, ...allP) - 0.5, Math.max(16, ...allP) + 0.5]).range([PAD.l, W - PAD.r]).nice();
  const winAt = (md: number) => rows.find((r: any) => r.top_md_m !== null && r.base_md_m !== null && md >= r.top_md_m && md < r.base_md_m && r.status === "window");
  const G: Record<string, string> = { LOT: "△", FIT: "△", lost_circulation: "▲", kick: "◆", overpressure: "◇" };

  return (
    <div>
      {/* Zone A — controls, in a toolbar card */}
      <section className="kk-card flex flex-wrap gap-4 items-center" aria-label="controls">
        <div className="flex items-center gap-2">
          <span className="label">{t("activeWell", lang)}:</span>
          <span className="font-semibold">{well ? well.name : lang === "hi" ? "कोई नहीं चुना" : "none selected"}</span>
          <button className="link small" onClick={focusTopBarWellPicker}>{lang === "hi" ? "बदलें" : "change"}</button>
        </div>
        <label className="label" htmlFor="r">{t("offsetRadius", lang)}</label>
        <select id="r" className="input" value={radius} onChange={(e) => setRadius(Number(e.target.value))}>
          {[5000, 10000, 20000, 50000].map((r) => <option key={r} value={r}>{r / 1000} km</option>)}
        </select>
        {d && <span className="small text-[var(--text-2)]">{d.n_offset_wells} {t("mwWellsCount", lang)} · {pts.length} {t("mwEvidencePoints", lang)} · {active.length} {t("mwMudChecksActive", lang)}</span>}
      </section>

      {loading && <p className="label mt-4">{t("loading", lang)}</p>}
      {!wellId && <div className="mt-5"><EmptyState title={t("cmdNoWellSelected", lang)} why={t("offsNoWellWhy", lang)} /></div>}
      {d && rows.length === 0 && <div className="mt-5"><EmptyState title={t("mwInsufficientTitle", lang)} why={t("mwInsufficientWhy", lang)} /></div>}
      {d && rows.length > 0 && (
        <div className="flex flex-wrap gap-6 mt-6 items-start">
          {/* Zone B — depth vs ppg chart, in a card, with the lithology column aligned to the same depth scale */}
          <section aria-label="mud weight window chart" className="kk-card flex gap-3 items-start">
            <div>
              <svg width={W} height={H} className="rounded-[var(--radius-md)]" style={{ background: "var(--surface-2)" }} role="img" aria-label="Depth versus mud weight: safe band, evidence and active well">
                <defs><pattern id="safe" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" stroke="var(--ok)" strokeWidth="1.2" /></pattern></defs>
                {rows.filter((r: any) => r.top_md_m !== null && r.base_md_m !== null).map((r: any) => (
                  <g key={r.formation}>
                    {r.status === "window" && <rect x={x(r.lower_ppg)} width={x(r.upper_ppg) - x(r.lower_ppg)} y={y(r.top_md_m)} height={Math.max(2, y(r.base_md_m) - y(r.top_md_m))} fill="url(#safe)" stroke="var(--ok)" strokeWidth={0.8}><title>{`${r.label}: safe band ${ppg(r.lower_ppg)}–${ppg(r.upper_ppg)} ppg`}</title></rect>}
                    {r.status === "upper_only" && <line x1={x(r.upper_ppg)} x2={x(r.upper_ppg)} y1={y(r.top_md_m)} y2={y(r.base_md_m)} stroke="var(--ok)" strokeWidth={2} strokeDasharray="4 2"><title>{`${r.label}: upper bound only`}</title></line>}
                    {r.status === "lower_only" && <line x1={x(r.lower_ppg)} x2={x(r.lower_ppg)} y1={y(r.top_md_m)} y2={y(r.base_md_m)} stroke="var(--ok)" strokeWidth={2} strokeDasharray="4 2"><title>{`${r.label}: lower bound only`}</title></line>}
                    {r.status === "conflict" && <rect x={x(r.upper_ppg)} width={x(r.lower_ppg) - x(r.upper_ppg)} y={y(r.top_md_m)} height={Math.max(2, y(r.base_md_m) - y(r.top_md_m))} fill="none" stroke="var(--hazard)" strokeDasharray="2 2"><title>{`${r.label}: evidence conflicts (lower > upper)`}</title></rect>}
                  </g>
                ))}
                {active.length > 1 && active.slice(1).map((a, i) => {
                  const p = active[i]; const w = winAt(a.md_m);
                  const near = w && (Math.abs(a.ppg - w.lower_ppg) <= NEAR || Math.abs(a.ppg - w.upper_ppg) <= NEAR || a.ppg < w.lower_ppg || a.ppg > w.upper_ppg);
                  return <path key={i} d={`M${x(p.ppg)} ${y(p.md_m)} V${y(a.md_m)} H${x(a.ppg)}`} fill="none" stroke={near ? "var(--caution)" : "var(--text)"} strokeWidth={near ? 3 : 1.6} />;
                })}
                {pts.map((p: any, i: number) => (
                  <text key={i} x={x(p.ppg)} y={y(p.md_m) + 4} textAnchor="middle" fontSize={12} fill="var(--text)" stroke="var(--surface-2)" strokeWidth={3} paintOrder="stroke" style={{ cursor: "pointer" }}
                    onClick={() => openSource(p.source_ref)}>{G[p.kind] ?? "•"}<title>{`${p.kind} ${ppg(p.ppg)} ppg at ${Math.round(p.md_m)} m — ${p.well}`}</title></text>
                ))}
                {x.ticks(6).map((tk) => <text key={tk} x={x(tk)} y={H - 10} fontSize={11} textAnchor="middle" className="num" fill="var(--text-2)">{tk}</text>)}
                {y.ticks(8).map((tk) => <text key={tk} x={PAD.l - 6} y={y(tk) + 4} fontSize={11} textAnchor="end" className="num" fill="var(--text-2)">{tk}</text>)}
                <text x={W - PAD.r} y={14} fontSize={11} textAnchor="end" fill="var(--text-2)">mud weight, ppg →</text>
                <text x={6} y={14} fontSize={11} fill="var(--text-2)">m MD ↓</text>
              </svg>
              <p className="label mt-3 max-w-[520px]">{t("mwLegend", lang)} {NEAR} {t("mwLegendSuffix", lang)} {d.note}</p>
            </div>
            <LithologyColumn intervals={d.tops} y={y} height={H} width={110} />
          </section>

          {/* Zone C — per-formation window and casing/cement lessons, as tabs so only one table shows at a time */}
          <section aria-label="mud window detail" className="kk-card min-w-[380px] flex-1">
            <Tabs
              items={[{ key: "formation", label: t("mwWindowByFormation", lang) }, { key: "casing", label: t("mwCasingCement", lang) }]}
              active={tab}
              onChange={(k) => setTab(k as "formation" | "casing")}
            />
            <div className="mt-4">
              {tab === "formation" && (
                <Register rows={rows} cols={[
                  { key: "f", head: t("mwCol_formation", lang), cell: (r: any) => r.label },
                  { key: "lo", head: t("mwCol_lower", lang), num: true, cell: (r: any) => ppg(r.lower_ppg) },
                  { key: "hi", head: t("mwCol_upper", lang), num: true, cell: (r: any) => ppg(r.upper_ppg) },
                  { key: "s", head: t("mwCol_status", lang), cell: (r: any) => (r.status === "conflict" ? <b style={{ color: "var(--hazard)" }}>✕ {t("mwConflict", lang)}</b> : r.status.replace("_", " ")) },
                  { key: "u", head: t("mwCol_used", lang), num: true, cell: (r: any) => (r.used_p10_p90 ? `${r.used_p10_p90[0]}–${r.used_p10_p90[1]}` : "—") },
                ]} />
              )}
              {tab === "casing" && (
                <Register rows={d.casing_lessons.filter((c: any) => c.cement_issues.length).slice(0, 12)} empty={t("mwNoCementIssue", lang)}
                  cols={[
                    { key: "w", head: t("mwCol_well", lang), cell: (c: any) => c.well },
                    { key: "c", head: t("mwCol_casing", lang), cell: (c: any) => `${c.od_in ?? "?"}″ at ${m(c.shoe_md_m)}` },
                    { key: "f", head: t("mwCol_formation", lang), cell: (c: any) => c.label ?? t("offsUnknown", lang) },
                    { key: "i", head: t("mwCol_issue", lang), cell: (c: any) => <span>“{c.cement_issues[0].text.slice(0, 140)}…”<SourceFootnote refId={c.cement_issues[0].source_ref} n="src" /></span> },
                  ]} />
              )}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
