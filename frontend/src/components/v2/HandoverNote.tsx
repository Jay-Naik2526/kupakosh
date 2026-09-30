"use client";
import { useEffect, useState } from "react";
import { get } from "@/lib/api";
import type { Lang } from "@/lib/i18n";

type Item = {
  hazard: string; label: string; formation: string; distance_m: number; in_formation: boolean; level: string; status: string;
  mean: number; ci: [number, number]; n_eff: number; n_with_event: number;
  fix: null | { label: string; k: number; n: number; anecdotal: boolean; median_hours: number | null; scope: string | null };
  offset_line: null | { well: string; md_m: number | null; text: string; source_ref: string };
};
type Note = { well: { name: string }; bit_md_m: number; lookahead_m: number; current: { formation: string } | null;
              ahead: { formation: string; distance_m: number }[]; items: Item[]; n_offsets: number; generated_at: string; text: string };

const tr = (lang: Lang, en: string, hi: string) => (lang === "hi" ? hi : en);
const pct = (x: number) => `${Math.round(x * 100)}%`;

/** Shift-handover note (GET /api/handover/{well}?bit_md=&lang=): one page for the next shift, English or Hindi,
 *  with a plain-text copy for a chat message. Every figure comes from the look-ahead and ledger engines. */
export function HandoverNote({ wellId, bitMd, lang }: { wellId: number; bitMd: number; lang: Lang }) {
  const [note, setNote] = useState<Note | null>(null);
  const [err, setErr] = useState(false);
  const [noteLang, setNoteLang] = useState<Lang>(lang);
  const [copied, setCopied] = useState(false);
  useEffect(() => {
    setNote(null); setErr(false);
    get(`/api/handover/${wellId}?bit_md=${Math.round(bitMd)}&lang=${noteLang}`).then(setNote).catch(() => setErr(true));
  }, [wellId, bitMd, noteLang]);
  const t = (en: string, hi: string) => tr(noteLang, en, hi);
  const copy = async () => {
    if (!note) return;
    try { await navigator.clipboard.writeText(note.text); setCopied(true); setTimeout(() => setCopied(false), 1800); } catch { setCopied(false); }
  };
  return (
    <div>
      <div className="flex gap-2 items-center flex-wrap">
        <button className="chip" aria-pressed={noteLang === "en"} onClick={() => setNoteLang("en")}>English</button>
        <button className="chip" aria-pressed={noteLang === "hi"} onClick={() => setNoteLang("hi")}>हिंदी</button>
        <button className="btn ml-auto" onClick={copy} disabled={!note}>{copied ? t("Copied", "कॉपी हो गया") : t("Copy as text", "टेक्स्ट कॉपी करें")}</button>
      </div>
      {err && <p className="small mt-3">{t("The note could not be built for this well.", "इस कूप के लिए नोट नहीं बन सका।")}</p>}
      {!note && !err && <p className="label mt-3">{t("Preparing the note…", "नोट तैयार हो रहा है…")}</p>}
      {note && (
        <article className="mt-4" style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-md)", padding: 16, background: "var(--surface)" }}>
          <div className="eyebrow">{t("Shift handover", "शिफ्ट हैंडओवर")} · {note.generated_at}</div>
          <h3 className="serif" style={{ fontSize: 20, fontWeight: 600, marginTop: 4 }}>
            {note.well.name} · <span className="num">{Math.round(note.bit_md_m).toLocaleString()} m MD</span>
          </h3>
          <p className="small mt-1">
            {t("Current layer", "वर्तमान परत")}: <b>{note.current?.formation ?? t("unknown", "अज्ञात")}</b>
            {" · "}{t(`Next ${Math.round(note.lookahead_m)} m`, `अगले ${Math.round(note.lookahead_m)} m`)}:{" "}
            {note.ahead.length ? note.ahead.map((a) => `${a.formation} (${Math.round(a.distance_m)} m)`).join(", ") : t("no new layer", "कोई नई परत नहीं")}
          </p>
          <div className="eyebrow mt-4">{t("Watch for", "ध्यान रखें")}</div>
          {note.items.length === 0 && <p className="small mt-1">{t("No recorded problem in nearby wells within this distance. Absence of a record is not proof of safety.", "इस दूरी में निकट कूपों में कोई दर्ज समस्या नहीं। अभिलेख न होना सुरक्षा का प्रमाण नहीं।")}</p>}
          <ol className="mt-2 grid gap-3">
            {note.items.map((x, i) => (
              <li key={i} style={{ borderLeft: `3px solid ${x.level === "notice" ? "var(--border)" : "var(--hazard, #B23A1E)"}`, paddingLeft: 10 }}>
                <div className="small" style={{ fontWeight: 600 }}>
                  {x.label} · {x.in_formation ? t("in this layer", "इसी परत में") : `${x.formation}, ${Math.round(x.distance_m)} m ${t("ahead", "आगे")}`}
                </div>
                <div className="small num">
                  {x.status === "ok"
                    ? `${pct(x.mean)} · ${t("range", "सीमा")} ${pct(x.ci[0])}–${pct(x.ci[1])} · ${t("evidence", "प्रमाण")} ${x.n_eff.toFixed(1)} ${t("wells", "कूप")}`
                    : t(`insufficient evidence (recorded in ${x.n_with_event} nearby wells)`, `अपर्याप्त प्रमाण (${x.n_with_event} निकट कूपों में दर्ज)`)}
                </div>
                {x.fix && (
                  <div className="small">
                    {t("What worked before", "पहले क्या काम आया")}: <b>{x.fix.label}</b> — {t(`${x.fix.k} of ${x.fix.n}`, `${x.fix.n} में से ${x.fix.k}`)}
                    {x.fix.anecdotal && <span className="label"> · {t("anecdotal", "कम उदाहरण")}</span>}
                  </div>
                )}
                {x.offset_line && (
                  <div className="label mt-1">“{x.offset_line.text}” — {x.offset_line.well} · <span className="num">{x.offset_line.source_ref}</span></div>
                )}
              </li>
            ))}
          </ol>
          <p className="label mt-4">{t(`Based on ${note.n_offsets} nearby wells. Decision support only — the engineer decides.`, `आधार: ${note.n_offsets} निकट कूप। केवल निर्णय सहायता — निर्णय अभियंता का।`)}</p>
        </article>
      )}
    </div>
  );
}
