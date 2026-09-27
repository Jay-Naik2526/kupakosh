"use client";
import type { Lang } from "@/lib/i18n";
import { Card } from "@/components/v2/ui";
import { tr } from "./trLocal";

type Rate = {
  n_flagged: number; k_flagged: number; rate_flagged: number | null; rate_flagged_ci: [number, number] | null;
  n_unflagged: number; k_unflagged: number; rate_unflagged: number | null; rate_unflagged_ci: [number, number] | null;
  lift: number | null; lift_ci_approx: [number, number] | null; no_measured_lift_yet: boolean; note: string | null; headline: string;
};
export type HindsightSummary = {
  n_candidates: number; n_testable: number; n_cells: number; headline: string;
  alert_mode_config: string; rr_min_config: number;
  lift: { mode: string; model: Rate; baseline: Rate };
  forewarned: {
    n_wells: number; events: number; forewarned: number; missed: number; forewarned_share: number | null;
    median_lead_m: number | null; alerts: number; alerts_with_event: number; alerts_without_record: number;
    alerts_with_event_share: number | null;
  };
  method: string;
};

const pct = (x: number | null) => (x === null ? "unknown" : `${Math.round(x * 100)}%`);

/** Zone A headline: the honest lift proof, the fair baseline right next to it, and the sobering forewarned share. */
export function HindsightTiles({ s, lang }: { s: HindsightSummary; lang: Lang }) {
  const t = (en: string, hi: string) => tr(lang, en, hi);
  const m = s.lift.model, b = s.lift.baseline, f = s.forewarned;
  return (
    <div className="grid gap-4" style={{ gridTemplateColumns: "1.3fr 1fr" }}>
      <Card>
        <div className="label">{t("When Kupakosh raised an alert…", "जब कूपकोश ने चेतावनी दी…")}</div>
        <div className="mt-1 num" style={{ fontSize: 30, fontWeight: 700 }}>
          {m.k_flagged} / {m.n_flagged}
        </div>
        <p className="mt-1 max-w-prose">
          {t(
            `A problem was recorded in that layer ${m.k_flagged} of ${m.n_flagged} times a blind alert fired — ${pct(m.rate_flagged)}.`,
            `जब भी अंध चेतावनी दी गई, उस परत में ${m.k_flagged}/${m.n_flagged} बार समस्या दर्ज हुई — ${pct(m.rate_flagged)}.`
          )}
        </p>
        <p className="label mt-2">
          {t("Where it stayed silent:", "जहाँ यह चुप रहा:")} <span className="num">{pct(m.rate_unflagged)}</span>{" "}
          {t("of layers had a recorded problem.", "परतों में समस्या दर्ज हुई।")}
        </p>
        <div className="mt-3 rule-t pt-2 flex flex-wrap items-baseline gap-x-6 gap-y-1">
          <div>
            <div className="label">{t("measured lift", "मापित लिफ्ट")}</div>
            <div className="num" style={{ fontSize: 22, fontWeight: 700, color: "var(--ok)" }}>{m.headline}</div>
          </div>
          <div>
            <div className="label">{t("fair baseline — alerting on field base rate alone", "निष्पक्ष आधार — केवल क्षेत्र औसत दर पर चेतावनी")}</div>
            <div className="num" style={{ fontSize: 18, fontWeight: 600 }}>{b.headline}</div>
          </div>
        </div>
        {(m.no_measured_lift_yet || m.note) && <p className="label mt-2">{m.note}</p>}
      </Card>
      <Card style={{ borderColor: "var(--caution)" }}>
        <div className="label">{t("the sobering number", "गंभीर आँकड़ा")}</div>
        <div className="mt-1 num" style={{ fontSize: 30, fontWeight: 700, color: "var(--caution-ink, var(--caution))" }}>
          {f.forewarned} / {f.events}
        </div>
        <p className="mt-1 max-w-prose">
          {t(
            `Problems forewarned: ${f.forewarned} of ${f.events} (${pct(f.forewarned_share)}). Kupakosh stays silent when evidence is thin — it does not guess.`,
            `पूर्व-चेतावनी दी गई समस्याएँ: ${f.events} में से ${f.forewarned} (${pct(f.forewarned_share)}). जब साक्ष्य कम हो तो कूपकोश चुप रहता है — यह अनुमान नहीं लगाता।`
          )}
        </p>
        <p className="label mt-2">
          {t(
            `${f.alerts} alerts raised in this blind replay; ${f.alerts_with_event} matched a recorded event (${pct(f.alerts_with_event_share)}), ${f.alerts_without_record} had no matching record — not proof of a false alarm, since reports under-record problems.`,
            `इस अंध पुनःचलन में ${f.alerts} चेतावनियाँ दी गईं; ${f.alerts_with_event} किसी दर्ज घटना से मेल खाईं (${pct(f.alerts_with_event_share)}), ${f.alerts_without_record} का कोई अभिलेख नहीं मिला — यह झूठी चेतावनी का प्रमाण नहीं, क्योंकि रिपोर्टें समस्याओं को कम दर्ज करती हैं।`
          )}
        </p>
      </Card>
      <div className="label" style={{ gridColumn: "1 / -1" }}>
        {t(
          `Method: ${s.n_testable} of ${s.n_candidates} documented wells were testable (n = ${s.n_cells.toLocaleString()} formation×hazard cells walked). Blind: the well's own reports are hidden — every alert is computed from other wells only.`,
          `विधि: ${s.n_candidates} में से ${s.n_testable} प्रलेखित कूप परीक्षण-योग्य थे (n = ${s.n_cells.toLocaleString()} संरचना×खतरा कोशिकाएँ)। अंध: कूप की अपनी रिपोर्टें छुपाई गई हैं — प्रत्येक चेतावनी केवल अन्य कूपों से गणना की जाती है।`
        )}
      </div>
    </div>
  );
}
