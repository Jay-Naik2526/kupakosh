"use client";
import { useEffect, useState } from "react";
import { get } from "@/lib/api";
import type { Lang } from "@/lib/i18n";
import { tr } from "./trLocal";

type RigHoursData = {
  events_timed: number; hours: number; events_untimed: number;
  in_test: { events: number; hours: number };
  warned: { events: number; hours: number; share_of_hours: number | null };
  by_hazard: { hazard: string; label: string; events: number; hours: number; warned_events: number; warned_hours: number }[];
  examples: { event_id: number; well: string; date: string | null; label: string; md_m: number | null; hours: number; lead_m: number | null;
              formation: string | null; source_ref: string; evidence: string }[];
  method: string;
};

const SEC = "var(--sec-operate)";
const h1 = (x: number) => (Number.isInteger(x) ? `${x}` : x.toFixed(1));

/** Rig hours at stake: logged rig time of real problems in the timed Volve daily reports, and the part of it
 *  that Kupakosh had warned about blind (GET /api/hindsight/rig-hours). Hours only — no money, day rates are
 *  not in the public data. */
export function RigHours({ lang }: { lang: Lang }) {
  const t = (en: string, hi: string) => tr(lang, en, hi);
  const [d, setD] = useState<RigHoursData | null>(null);
  const [state, setState] = useState<"loading" | "ok" | "none">("loading");
  useEffect(() => {
    get("/api/hindsight/rig-hours").then((x) => { setD(x); setState("ok"); }).catch(() => setState("none"));
  }, []);
  if (state === "loading") return <div className="label mt-10">{t("Loading rig hours…", "रिग घंटे लोड हो रहे हैं…")}</div>;
  if (state === "none" || !d || d.events_timed === 0) return null;
  const share = d.warned.share_of_hours;
  return (
    <div className="mt-10" aria-label={t("rig hours at stake", "दांव पर रिग घंटे")}>
      <div className="eyebrow" style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <span aria-hidden="true" style={{ width: 8, height: 8, borderRadius: 2, background: SEC, display: "inline-block" }} />
        {t("Rig hours at stake — from real timed daily reports", "दांव पर रिग घंटे — वास्तविक समयबद्ध दैनिक रिपोर्टों से")}
      </div>
      <div className="mt-2 flex items-baseline gap-3 flex-wrap">
        <span className="num" style={{ fontSize: 40, fontWeight: 600, letterSpacing: "-.01em" }}>{h1(d.warned.hours)} h</span>
        <span className="small" style={{ color: "var(--text-2)" }}>
          {t(
            `of ${h1(d.in_test.hours)} logged problem hours in the blind test were in problems Kupakosh had warned about before the bit got there (${d.warned.events} of ${d.in_test.events} problems${share !== null ? `, ${Math.round(share * 100)}% of the hours` : ""}).`,
            `अंध परीक्षण के ${h1(d.in_test.hours)} दर्ज समस्या-घंटों में से इतने घंटे उन समस्याओं के थे जिनकी कूपकोश ने बिट पहुँचने से पहले चेतावनी दी थी (${d.in_test.events} में से ${d.warned.events})।`
          )}
        </span>
      </div>
      <div aria-hidden="true" style={{ height: 4, width: 48, background: SEC, marginTop: 6, borderRadius: 1 }} />

      <table className="mt-4" style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ borderTop: "2px solid var(--text)", borderBottom: "1px solid var(--border)" }}>
            <th className="label" style={{ textAlign: "left", fontWeight: 600, padding: "6px 8px 6px 0" }}>{t("Hazard", "खतरा")}</th>
            <th className="label" style={{ textAlign: "right", fontWeight: 600, padding: "6px 8px" }}>{t("Problems", "समस्याएँ")}</th>
            <th className="label" style={{ textAlign: "right", fontWeight: 600, padding: "6px 8px" }}>{t("Logged hours", "दर्ज घंटे")}</th>
            <th className="label" style={{ textAlign: "right", fontWeight: 600, padding: "6px 0 6px 8px" }}>{t("Hours warned about", "चेतावनी वाले घंटे")}</th>
          </tr>
        </thead>
        <tbody>
          {d.by_hazard.map((r) => (
            <tr key={r.hazard} style={{ borderBottom: "1px solid var(--border)" }}>
              <td style={{ padding: "6px 8px 6px 0" }}>{r.label}</td>
              <td className="num" style={{ textAlign: "right", padding: "6px 8px" }}>{r.events}</td>
              <td className="num" style={{ textAlign: "right", padding: "6px 8px" }}>{h1(r.hours)}</td>
              <td className="num" style={{ textAlign: "right", padding: "6px 0 6px 8px", fontWeight: 600 }}>{h1(r.warned_hours)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {d.examples.length > 0 && (
        <details className="mt-4">
          <summary className="label" style={{ cursor: "pointer" }}>{t("The longest problems it warned about, with the report line", "सबसे लंबी समस्याएँ जिनकी चेतावनी दी गई, रिपोर्ट पंक्ति सहित")}</summary>
          <ul className="mt-2 grid gap-3">
            {d.examples.map((x) => (
              <li key={x.event_id} style={{ borderLeft: `3px solid ${SEC}`, paddingLeft: 10 }}>
                <div className="small" style={{ fontWeight: 600 }}>
                  {x.well} · {x.date} · {x.label} · <span className="num">{h1(x.hours)} h</span>
                  {x.lead_m !== null && <span className="label num"> · {t("warned", "चेतावनी")} {Math.round(x.lead_m)} m {t("ahead", "पहले")}</span>}
                </div>
                <div className="small" style={{ color: "var(--text-2)" }}>“{x.evidence}”</div>
                <div className="label num">{x.source_ref}</div>
              </li>
            ))}
          </ul>
        </details>
      )}
      <p className="label mt-3">
        {t(
          `${d.events_timed} timed problems, ${h1(d.hours)} logged hours in all; ${d.events_untimed} more sit on untimed 24-hour summaries and get no hours. ${d.method}`,
          `${d.events_timed} समयबद्ध समस्याएँ, कुल ${h1(d.hours)} दर्ज घंटे। घंटे केवल उस रिपोर्ट पंक्ति की अवधि हैं जिसमें समस्या दर्ज है (न्यूनतम अनुमान)। कोई रुपया आँकड़ा नहीं: सार्वजनिक डेटा में दैनिक दर नहीं है।`
        )}
      </p>
    </div>
  );
}
