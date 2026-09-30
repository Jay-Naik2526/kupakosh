"use client";
import { useState } from "react";
import { post } from "@/lib/api";
import { useApp } from "@/lib/state";

type Result = { verdict: string; learned: boolean; note: string;
                field_rate_before: { rate: number; n_wells: number }; field_rate_after: { rate: number; n_wells: number } };

const tr = (lang: string, en: string, hi: string) => (lang === "hi" ? hi : en);
const pct1 = (x: number) => `${(x * 100).toFixed(1)}%`;

/** Self-correcting alerts: the engineer's verdict on this alert (POST /api/feedback). "Problem happened" becomes a
 *  human-labelled record that later estimates for other wells learn from; the Hindsight test never scores on it. */
export function AlertFeedback({ wellId, formation, hazard, mdM }: { wellId: number; formation: string; hazard: string; mdM: number | null }) {
  const { user, lang } = useApp();
  const [res, setRes] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(false);
  const send = async (verdict: "problem" | "no_problem" | "unsure") => {
    if (!user) return;
    setBusy(true); setErr(false);
    try {
      setRes(await post("/api/feedback", { well_id: wellId, formation, hazard, verdict, md_m: mdM, reviewer: user.name, role: user.role }));
    } catch { setErr(true); } finally { setBusy(false); }
  };
  return (
    <div className="mt-3 pt-2" style={{ borderTop: "1px solid var(--border)" }}>
      <div className="label">{tr(lang, "Engineer verdict — the model learns from it", "अभियंता निर्णय — मॉडल इससे सीखता है")}</div>
      {!res && (
        <div className="flex gap-2 mt-1 flex-wrap items-center">
          <button className="btn" disabled={!user || busy} onClick={() => send("problem")}>{tr(lang, "Problem happened", "समस्या हुई")}</button>
          <button className="btn" disabled={!user || busy} onClick={() => send("no_problem")}>{tr(lang, "No problem", "कोई समस्या नहीं")}</button>
          <button className="btn" disabled={!user || busy} onClick={() => send("unsure")}>{tr(lang, "Unsure", "अनिश्चित")}</button>
          {!user && <span className="label">{tr(lang, "Pick a demo user (top bar) to record a verdict.", "निर्णय दर्ज करने के लिए डेमो उपयोगकर्ता चुनें।")}</span>}
        </div>
      )}
      {err && <p className="small mt-1">{tr(lang, "Could not save the verdict.", "निर्णय सहेजा नहीं जा सका।")}</p>}
      {res && (
        <div className="small mt-1">
          <b>{tr(lang, "Saved", "सहेजा गया")}</b> ({user?.name}, {tr(lang, "demo user", "डेमो उपयोगकर्ता")}).{" "}
          {res.learned
            ? tr(lang, `Field rate for this layer and hazard: ${pct1(res.field_rate_before.rate)} → ${pct1(res.field_rate_after.rate)}.`,
                 `इस परत व खतरे की क्षेत्र दर: ${pct1(res.field_rate_before.rate)} → ${pct1(res.field_rate_after.rate)}।`)
            : ""}
          <div className="label mt-1">{res.note}</div>
        </div>
      )}
    </div>
  );
}
