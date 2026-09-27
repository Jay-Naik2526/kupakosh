import { ReactNode, useState } from "react";
import { pct } from "@/lib/format";
import { useApp } from "@/lib/state";
import { t } from "@/lib/i18n";
import { Posterior, WhyPanel } from "@/components/v2/WhyPanel";
import { hazardColor } from "@/lib/palette";

const TAG: Record<string, { en: string; hi: string }> = {
  escalated: { en: "ESCALATED · live signal matches", hi: "उग्र (ESCALATED) · लाइव संकेत मेल खाता है" },
  alert: { en: "ALERT", hi: "चेतावनी (ALERT)" },
  notice: { en: "NOTICE", hi: "सूचना (NOTICE)" },
};
const tr = (lang: string, en: string, hi: string) => (lang === "hi" ? hi : en);

/** Hazard card: 3px left rule (colour = state), title, big mono probability, range + n_eff line, actions.
 *  `posterior`, when given, is the full backend hazard.posterior() object — powers the "Why this number?" panel. */
export function NoticeSlip({ level, title, where, mean, ci, neff, nWells, nWithEvent, status, posterior, hazard, children, actions }: {
  level: "alert" | "escalated" | "notice"; title: string; where: string; mean: number; ci: [number, number]; neff: number;
  nWells: number; nWithEvent: number; status: string; posterior?: Posterior; hazard?: string; children?: ReactNode; actions?: ReactNode;
}) {
  const { lang } = useApp();
  const [why, setWhy] = useState(false);
  const bandColor = hazard ? hazardColor(hazard) : level === "notice" ? "var(--caution)" : "var(--hazard)";
  const color = level === "escalated" ? "var(--hazard)" : level === "alert" ? "var(--hazard)" : "var(--caution)";
  const tag = lang === "hi" ? TAG[level].hi : TAG[level].en;
  const ok = status === "ok";
  return (
    <section className="bg-card border border-rule rounded-kk overflow-hidden" style={{ borderLeft: `3px solid ${color}` }} aria-live="polite">
      <div style={{ background: bandColor, color: "#fff", padding: "8px 20px" }}>
        <div className="label mono" style={{ color: "#fff", opacity: 0.92 }}>{level === "notice" ? "○" : "▲"} {tag}</div>
        <h2 className="font-semibold mt-1 uppercase tracking-wide" style={{ color: "#fff" }}>{title}</h2>
      </div>
      <div className="p-5">
      <div className="text-ink2">{where}</div>
      {ok ? (
        <>
          <div className="num mt-3" style={{ fontSize: 40, lineHeight: 1, color: bandColor }}>{pct(mean)}</div>
          <div className="small mt-1">range {pct(ci[0])}–{pct(ci[1])} (80%) · evidence {neff.toFixed(1)} wells ({nWithEvent} of {nWells} with a record)</div>
          <svg width="100%" height={10} viewBox="0 0 200 10" preserveAspectRatio="none" className="mt-2" role="img" aria-label={`range ${pct(ci[0])} to ${pct(ci[1])}`}>
            <rect x={0} y={3} width={200} height={4} rx={2} fill="var(--border)" />
            <rect x={ci[0] * 200} y={3} width={Math.max(2, (ci[1] - ci[0]) * 200)} height={4} rx={2} fill={bandColor} opacity={0.55} />
            <circle cx={mean * 200} cy={5} r={4} fill={bandColor} stroke="#fff" strokeWidth={1} />
          </svg>
        </>
      ) : (
        <>
          <div className="num mt-3" style={{ fontSize: 22 }}>{t("insufficient", lang)}</div>
          <div className="small mt-1">effective evidence {neff.toFixed(1)} well{neff === 1 ? "" : "s"} — below the minimum; {nWithEvent} of {nWells} offset well{nWells === 1 ? "" : "s"} recorded this problem here.</div>
        </>
      )}
      {posterior && (
        <button className="btn mt-3" aria-expanded={why} onClick={() => setWhy((w) => !w)}>
          {why ? tr(lang, "Hide why ▾", "क्यों — छुपाएँ ▾") : tr(lang, "Why this number? ▸", "यह संख्या क्यों? ▸")}
        </button>
      )}
      {posterior && why && <WhyPanel posterior={posterior} />}
      {children && <div className="mt-4">{children}</div>}
      {actions && <div className="mt-4 flex gap-2 flex-wrap">{actions}</div>}
      </div>
    </section>
  );
}
