"use client";
import { useEffect, useState } from "react";
import { get, post } from "@/lib/api";
import { useApp } from "@/lib/state";
import { Register } from "@/components/kk/Register";
import { EmptyState } from "@/components/kk/EmptyState";
import { CountryFilter } from "@/components/kk/CountryFilter";
import { EventReviewDrawer } from "@/components/kk/EventReview";
import { t } from "@/lib/i18n";

// A = blue, B = violet, per the ROUND 3 colour brief. "#8B5CF6" (violet-500) is only ~3:1 on white, short of AA as text/borders at this
// size — "#6D28D9" (violet-700) keeps the same hue family and clears 4.5:1.
const ACC = { A: "#2563EB", B: "#6D28D9" };
function StatTileC({ v, l, c }: { v: React.ReactNode; l: string; c: string }) {
  return (
    <div className="kk-stat-tile" style={{ borderTop: `3px solid ${c}`, background: `color-mix(in srgb, ${c} 6%, var(--surface))` }}>
      <div className="kk-stat-value num" style={{ color: c }}>{v}</div>
      <div className="kk-stat-label">{l}</div>
    </div>
  );
}

const RULE: Record<string, string> = {
  R1_ddr_loss_vs_pit: "DDR losses vs sensor pit volume",
  R2_casing_shoe: "Casing shoe: text vs table",
  R3_formation_top: "Formation top: text vs table",
  R4_same_quantity_differs: "Same quantity, different reports",
  R6_ddr_depth_vs_sensor: "Report depth vs sensor depth",
};
const RULE_HI: Record<string, string> = {
  R1_ddr_loss_vs_pit: "DDR लॉस बनाम सेंसर पिट आयतन",
  R2_casing_shoe: "केसिंग शू: पाठ बनाम तालिका",
  R3_formation_top: "संरचना शीर्ष: पाठ बनाम तालिका",
  R4_same_quantity_differs: "समान मात्रा, भिन्न रिपोर्ट",
  R6_ddr_depth_vs_sensor: "रिपोर्ट गहराई बनाम सेंसर गहराई",
};

export default function Checker() {
  const { user, country, lang } = useApp();
  const ruleLabel = (r: string) => (lang === "hi" ? RULE_HI[r] ?? RULE[r] ?? r : RULE[r] ?? r);
  const [flags, setFlags] = useState<any[]>([]);
  const [status, setStatus] = useState<string>("open");
  const [sel, setSel] = useState<number | null>(null);
  const [a, setA] = useState<any>(null);
  const [b, setB] = useState<any>(null);
  const [note, setNote] = useState("");
  const [trust, setTrust] = useState<number | null>(null);
  const load = () => get("/api/audit", { country: country ?? undefined }).then(setFlags);
  useEffect(() => { load(); get("/api/wiki").then((p) => { const v = p.map((x: any) => x.trust).filter((x: any) => x !== null); setTrust(v.length ? v.reduce((s: number, x: number) => s + x, 0) / v.length : null); }); }, []); // eslint-disable-line
  useEffect(() => { setSel(null); load(); }, [country]); // eslint-disable-line
  const rows = flags.filter((f) => (status === "open" ? f.status === "open" : f.status !== "open"));
  const cur = sel !== null ? rows[sel] : null;
  useEffect(() => {
    setA(null); setB(null);
    if (!cur) return;
    get("/api/source", { ref: cur.ref_a }).then(setA);
    get("/api/source", { ref: cur.ref_b }).then(setB);
  }, [cur?.id]); // eslint-disable-line
  const resolve = async (decision: string) => {
    if (!cur || !user) return;
    await post(`/api/audit/${cur.id}/resolve`, { decision, reviewer: user.name, note: note || null });
    setNote(""); setSel(null); load();
  };
  const open = flags.filter((f) => f.status === "open").length;

  return (
    <div>
      {/* Zone A — summary tiles + filters */}
      <section className="mb-6" aria-label="summary">
        <div className="grid gap-3 sm:grid-cols-4">
          <StatTileC v={open} l={t("chkOpen", lang)} c="var(--hazard)" />
          <StatTileC v={flags.length - open} l={t("chkResolved", lang)} c="var(--ok)" />
          <StatTileC v={trust === null ? "—" : `${Math.round(trust * 100)}%`} l={t("chkAvgTrust", lang)} c="var(--info)" />
          <EventReviewDrawer variant="tile" />
        </div>
        <div className="flex flex-wrap items-center gap-3 mt-4">
          <CountryFilter label={t("countryLabel", lang)} />
          <div className="flex gap-1 ml-auto">
            <button className="chip" aria-pressed={status === "open"} onClick={() => { setStatus("open"); setSel(null); }}>{t("chkOpen", lang)}</button>
            <button className="chip" aria-pressed={status !== "open"} onClick={() => { setStatus("done"); setSel(null); }}>{t("chkResolved", lang)}</button>
          </div>
        </div>
      </section>

      <div className="grid gap-6" style={{ gridTemplateColumns: cur ? "minmax(0,1fr) minmax(0,1.2fr)" : "1fr" }}>
        {/* Zone B — conflicts, a clean table */}
        <section aria-label="conflicts">
          {rows.length === 0 ? <EmptyState title={status === "open" ? t("chkNoOpenTitle", lang) : t("chkNoneResolvedTitle", lang)} why={t("chkWhy", lang)} /> :
            <Register rows={rows} onRow={(_, i) => setSel(i)} selected={sel} cols={[
              { key: "w", head: t("chkCol_well", lang), cell: (f: any) => f.well },
              { key: "r", head: t("chkCol_check", lang), cell: (f: any) => ruleLabel(f.rule) },
              { key: "d", head: t("chkCol_diff", lang), num: true, cell: (f: any) => f.delta },
              { key: "s", head: t("chkCol_severity", lang), cell: (f: any) => {
                const c = f.severity === "medium" ? "var(--caution-ink)" : "var(--text-2)";
                const tint = f.severity === "medium" ? "var(--caution)" : "var(--text-2)";
                return (
                  <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-kk text-[0.78rem] font-semibold"
                        style={{ color: c, background: `color-mix(in srgb, ${tint} 16%, var(--surface))`, border: `1px solid color-mix(in srgb, ${tint} 45%, transparent)` }}>
                    ● {f.severity === "medium" ? t("chkMedium", lang) : t("chkLow", lang)}
                  </span>
                );
              } },
              ...(status !== "open" ? [{ key: "st", head: t("chkCol_decision", lang), cell: (f: any) => `${f.status} — ${f.resolved_by}` }] : []),
            ]} />}
        </section>

        {/* Zone C — selected conflict, two source excerpts side by side */}
        {cur && (
          <section aria-label="selected conflict" className="kk-card h-fit">
            <h3 className="font-semibold">{ruleLabel(cur.rule)} — {cur.well} <span className="label">({cur.delta})</span></h3>
            <div className="grid grid-cols-2 gap-3 mt-3">
              {[{ k: "A", claim: cur.claim_a, ref: cur.ref_a, src: a }, { k: "B", claim: cur.claim_b, ref: cur.ref_b, src: b }].map((s) => (
                <div key={s.k} className="rounded-[var(--radius-md)] p-3 small" style={{
                  border: `1px solid color-mix(in srgb, ${ACC[s.k as "A" | "B"]} 40%, var(--border))`,
                  background: `color-mix(in srgb, ${ACC[s.k as "A" | "B"]} 7%, var(--surface-2))`,
                  borderLeft: `3px solid ${ACC[s.k as "A" | "B"]}`,
                }}>
                  <div className="font-semibold" style={{ color: ACC[s.k as "A" | "B"] }}>{s.k === "A" ? t("chkSourceA", lang) : t("chkSourceB", lang)}</div>
                  <p className="mt-1">{s.claim}</p>
                  {s.src?.text && s.src.text !== s.claim && <p className="mt-2 text-[var(--text-2)] italic">“{s.src.text}”</p>}
                  <div className="label mono mt-2 break-all">{s.ref}</div>
                  {s.src?.title && <div className="label">{s.src.title}{s.src.report_date ? ` · ${s.src.report_date}` : ""}</div>}
                </div>
              ))}
            </div>
            {cur.status === "open" ? (
              <div className="mt-4 space-y-2">
                {!user && <p className="small">{t("selectDemoUserDecision", lang)}</p>}
                <textarea className="input w-full" rows={2} placeholder={t("chkReviewerNote", lang)} value={note} onChange={(e) => setNote(e.target.value)} disabled={!user} />
                <div className="flex gap-2 flex-wrap">
                  <button className="btn" disabled={!user} title={!user ? t("selectDemoUserDecision", lang) : undefined} onClick={() => resolve("accept_a")}
                          style={{ borderColor: ACC.A, color: ACC.A }}>{t("chkAcceptA", lang)}</button>
                  <button className="btn" disabled={!user} title={!user ? t("selectDemoUserDecision", lang) : undefined} onClick={() => resolve("accept_b")}
                          style={{ borderColor: ACC.B, color: ACC.B }}>{t("chkAcceptB", lang)}</button>
                  <button className="btn" disabled={!user} title={!user ? t("selectDemoUserDecision", lang) : undefined} onClick={() => resolve("uncertain")}>{t("chkMarkUncertain", lang)}</button>
                </div>
              </div>
            ) : <p className="mt-3 small">{t("chkDecisionBy", lang)} <b>{cur.status}</b> {t("chkBy", lang)} {cur.resolved_by}{cur.reviewer_note ? ` — “${cur.reviewer_note}”` : ""}</p>}
          </section>
        )}
      </div>
    </div>
  );
}
