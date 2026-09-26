"use client";
import { useEffect, useState } from "react";
import { get, post } from "@/lib/api";
import { useApp } from "@/lib/state";
import { Register } from "@/components/kk/Register";
import { EmptyState } from "@/components/kk/EmptyState";
import { CountryFilter } from "@/components/kk/CountryFilter";
import { EventReviewDrawer } from "@/components/kk/EventReview";
import { t } from "@/lib/i18n";

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
      {/* Zone A — summary line */}
      <section className="flex flex-wrap gap-6 items-baseline rule-b pb-3" aria-label="summary">
        <div><span className="label">{t("chkOpen", lang)}</span> <span className="num text-2xl">{open}</span></div>
        <div><span className="label">{t("chkResolved", lang)}</span> <span className="num text-2xl">{flags.length - open}</span></div>
        <div><span className="label">{t("chkAvgTrust", lang)}</span> <span className="num text-2xl">{trust === null ? "—" : `${Math.round(trust * 100)}%`}</span></div>
        <CountryFilter label={t("countryLabel", lang)} />
        <EventReviewDrawer />
        <div className="ml-auto flex gap-1">
          <button className="chip" aria-pressed={status === "open"} onClick={() => { setStatus("open"); setSel(null); }}>{t("chkOpen", lang)}</button>
          <button className="chip" aria-pressed={status !== "open"} onClick={() => { setStatus("done"); setSel(null); }}>{t("chkResolved", lang)}</button>
        </div>
      </section>

      <div className="grid gap-8 mt-5" style={{ gridTemplateColumns: cur ? "minmax(0,1fr) minmax(0,1.2fr)" : "1fr" }}>
        {/* Zone B — conflicts register */}
        <section aria-label="conflicts">
          {rows.length === 0 ? <EmptyState title={status === "open" ? t("chkNoOpenTitle", lang) : t("chkNoneResolvedTitle", lang)} why={t("chkWhy", lang)} /> :
            <Register rows={rows} onRow={(_, i) => setSel(i)} selected={sel} cols={[
              { key: "w", head: t("chkCol_well", lang), cell: (f: any) => f.well },
              { key: "r", head: t("chkCol_check", lang), cell: (f: any) => ruleLabel(f.rule) },
              { key: "d", head: t("chkCol_diff", lang), num: true, cell: (f: any) => f.delta },
              { key: "s", head: t("chkCol_severity", lang), cell: (f: any) => f.severity === "medium" ? <b>● {t("chkMedium", lang)}</b> : `○ ${t("chkLow", lang)}` },
              ...(status !== "open" ? [{ key: "st", head: t("chkCol_decision", lang), cell: (f: any) => `${f.status} — ${f.resolved_by}` }] : []),
            ]} />}
        </section>

        {/* Zone C — selected conflict, two excerpts side by side */}
        {cur && (
          <section aria-label="selected conflict">
            <h3 className="font-semibold">{ruleLabel(cur.rule)} — {cur.well} <span className="label">({cur.delta})</span></h3>
            <div className="grid grid-cols-2 gap-3 mt-3">
              {[{ k: "A", claim: cur.claim_a, ref: cur.ref_a, src: a }, { k: "B", claim: cur.claim_b, ref: cur.ref_b, src: b }].map((s) => (
                <div key={s.k} className="bg-card border border-rule rounded-kk p-3 small">
                  <div className="font-semibold">{s.k === "A" ? t("chkSourceA", lang) : t("chkSourceB", lang)}</div>
                  <p className="mt-1">{s.claim}</p>
                  {s.src?.text && s.src.text !== s.claim && <p className="mt-2 text-ink2 italic">“{s.src.text}”</p>}
                  <div className="label mono mt-2 break-all">{s.ref}</div>
                  {s.src?.title && <div className="label">{s.src.title}{s.src.report_date ? ` · ${s.src.report_date}` : ""}</div>}
                </div>
              ))}
            </div>
            {cur.status === "open" ? (
              <div className="mt-4 space-y-2">
                {!user && <p className="small">{t("selectDemoUserDecision", lang)}</p>}
                <textarea className="input w-full" rows={2} placeholder={t("chkReviewerNote", lang)} value={note} onChange={(e) => setNote(e.target.value)} disabled={!user} />
                <div className="flex gap-2">
                  <button className="btn" disabled={!user} onClick={() => resolve("accept_a")}>{t("chkAcceptA", lang)}</button>
                  <button className="btn" disabled={!user} onClick={() => resolve("accept_b")}>{t("chkAcceptB", lang)}</button>
                  <button className="btn" disabled={!user} onClick={() => resolve("uncertain")}>{t("chkMarkUncertain", lang)}</button>
                </div>
              </div>
            ) : <p className="mt-3 small">{t("chkDecisionBy", lang)} <b>{cur.status}</b> {t("chkBy", lang)} {cur.resolved_by}{cur.reviewer_note ? ` — “${cur.reviewer_note}”` : ""}</p>}
          </section>
        )}
      </div>
    </div>
  );
}
