"use client";
import { useEffect, useState } from "react";
import { get } from "@/lib/api";
import type { Lang } from "@/lib/i18n";
import { tr } from "./trLocal";

type Share = { problems: number; repeats: number; share: number | null; share_ci: [number, number] | null };
type RepeatsData = Share & {
  archive: Share & { method: string };
  median_years_warning_existed: number | null;
  by_decade: { decade: number; repeats: number; problems: number; share: number | null }[];
  examples: { well: string; spud: string; label: string; formation: string; source_ref: string; evidence: string;
              earlier_well: string; earlier_spud: string; earlier_distance_m: number; years_before: number;
              earlier_source_ref: string; earlier_evidence: string; n_earlier_wells: number }[];
  method: string;
};

const SEC = "var(--sec-operate)";
const pct = (x: number | null) => (x === null ? "unknown" : `${Math.round(x * 100)}%`);

/** Preventable repeats (GET /api/hindsight/repeats): real problems that had already been recorded in the same
 *  layer by an older well. Shows that the warning existed in the records, not that the problem was preventable. */
export function Repeats({ lang }: { lang: Lang }) {
  const t = (en: string, hi: string) => tr(lang, en, hi);
  const [d, setD] = useState<RepeatsData | null>(null);
  useEffect(() => { get("/api/hindsight/repeats").then(setD).catch(() => setD(null)); }, []);
  if (!d || !d.problems) return null;
  const a = d.archive;
  const ex = d.examples[0];
  return (
    <div className="mt-10" aria-label={t("problems that had happened before", "पहले हो चुकी समस्याएँ")}>
      <div className="eyebrow" style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <span aria-hidden="true" style={{ width: 8, height: 8, borderRadius: 2, background: SEC, display: "inline-block" }} />
        {t("It had happened before — and it was in the records", "यह पहले हो चुका था — और अभिलेखों में दर्ज था")}
      </div>
      <div className="mt-2 flex items-baseline gap-3 flex-wrap">
        <span className="num" style={{ fontSize: 40, fontWeight: 600, letterSpacing: "-.01em" }}>{a.repeats} / {a.problems}</span>
        <span className="num" style={{ fontSize: 20, fontWeight: 600, color: "var(--text-2)" }}>{pct(a.share)}</span>
        {a.share_ci && <span className="label num">95% {t("range", "सीमा")} {pct(a.share_ci[0])}–{pct(a.share_ci[1])}</span>}
      </div>
      <div aria-hidden="true" style={{ height: 4, width: 48, background: SEC, marginTop: 6, borderRadius: 1 }} />
      <p className="small mt-2" style={{ color: "var(--text-2)" }}>
        {t(
          `real recorded problems had already been written down in the same rock layer, same hazard, by an older well's report. Within the offset radius of the well itself: ${d.repeats} of ${d.problems} (${pct(d.share)}), the warning sitting in the records a median ${d.median_years_warning_existed ?? "?"} years before the well was spudded.`,
          `वास्तविक दर्ज समस्याएँ पहले ही उसी चट्टान परत में, उसी खतरे के साथ, किसी पुराने कूप की रिपोर्ट में लिखी जा चुकी थीं। कूप की निकटवर्ती त्रिज्या में: ${d.problems} में से ${d.repeats} (${pct(d.share)})।`
        )}
      </p>

      <table className="mt-4" style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ borderTop: "2px solid var(--text)", borderBottom: "1px solid var(--border)" }}>
            <th className="label" style={{ textAlign: "left", fontWeight: 600, padding: "6px 8px 6px 0" }}>{t("Wells spudded in", "स्पड दशक")}</th>
            <th className="label" style={{ textAlign: "right", fontWeight: 600, padding: "6px 8px" }}>{t("Problems", "समस्याएँ")}</th>
            <th className="label" style={{ textAlign: "right", fontWeight: 600, padding: "6px 0 6px 8px" }}>{t("Already recorded by a nearby older well", "निकट पुराने कूप में पहले से दर्ज")}</th>
          </tr>
        </thead>
        <tbody>
          {d.by_decade.map((r) => (
            <tr key={r.decade} style={{ borderBottom: "1px solid var(--border)" }}>
              <td className="num" style={{ padding: "6px 8px 6px 0" }}>{r.decade}s</td>
              <td className="num" style={{ textAlign: "right", padding: "6px 8px" }}>{r.problems}</td>
              <td className="num" style={{ textAlign: "right", padding: "6px 0 6px 8px", fontWeight: 600 }}>{r.repeats} <span className="label">({pct(r.share)})</span></td>
            </tr>
          ))}
        </tbody>
      </table>

      {ex && (
        <div className="mt-4 grid gap-3" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))" }}>
          <div style={{ borderLeft: "3px solid var(--border)", paddingLeft: 10 }}>
            <div className="label">{t("First written down", "पहली बार लिखा गया")} · {ex.earlier_well} · {ex.earlier_spud.slice(0, 4)}</div>
            <div className="small" style={{ color: "var(--text-2)" }}>“{ex.earlier_evidence}”</div>
            <div className="label num">{ex.earlier_source_ref}</div>
          </div>
          <div style={{ borderLeft: `3px solid ${SEC}`, paddingLeft: 10 }}>
            <div className="label">
              {t("Happened again", "फिर हुआ")} · {ex.well} · {ex.spud.slice(0, 4)} · {ex.label} · {ex.formation} ·{" "}
              {t(`${Math.round(ex.earlier_distance_m)} m away, ${ex.years_before} years later`, `${Math.round(ex.earlier_distance_m)} m दूर, ${ex.years_before} वर्ष बाद`)}
            </div>
            <div className="small" style={{ color: "var(--text-2)" }}>“{ex.evidence}”</div>
            <div className="label num">{ex.source_ref}</div>
          </div>
        </div>
      )}
      <p className="label mt-3">
        {t(`A repeat shows the warning existed in a report; it does not prove the problem was preventable. Older well histories rarely wrote problems down, so earlier decades show fewer repeats and the true share is likely higher. ${d.method}`,
           "दोहराव दिखाता है कि चेतावनी किसी रिपोर्ट में मौजूद थी; यह सिद्ध नहीं करता कि समस्या रोकी जा सकती थी।")}
      </p>
    </div>
  );
}
