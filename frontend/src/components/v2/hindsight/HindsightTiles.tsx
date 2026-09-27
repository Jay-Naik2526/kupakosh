"use client";
import type { Lang } from "@/lib/i18n";
import { Card } from "@/components/v2/ui";
import { tr } from "./trLocal";
import { BRAND } from "@/lib/palette";

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
  watchlist?: {
    n_events: number; n_events_without_cell: number; method: string;
    rows: { k: number; events: number; hits: number; share: number | null; hits_ci: [number, number] | null;
            base_rate_hits: number; base_rate_share: number | null; random_expected: number; random_share: number | null;
            x_random: number | null; share_of_cells_flagged: number }[];
  };
  operating_points?: { threshold: number; forewarned: number; events: number; forewarned_share: number | null;
                       flagged: number; hit_rate: number | null; lift: number | null }[];
  method: string;
};

const pct = (x: number | null) => (x === null ? "unknown" : `${Math.round(x * 100)}%`);

/** Zone A headline: the honest lift proof, the fair baseline right next to it, and the sobering forewarned share. */
export function HindsightTiles({ s, lang }: { s: HindsightSummary; lang: Lang }) {
  const t = (en: string, hi: string) => tr(lang, en, hi);
  const m = s.lift.model, b = s.lift.baseline, f = s.forewarned;
  return (
    <div className="grid gap-4" style={{ gridTemplateColumns: "1.3fr 1fr" }}>
      <Card style={{ borderColor: "var(--ok)" }}>
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
      {s.watchlist && s.watchlist.rows.length > 0 ? <WatchlistCard s={s} lang={lang} /> : <StrictCard s={s} lang={lang} />}
      <div className="label" style={{ gridColumn: "1 / -1" }}>
        {t(
          `Method: ${s.n_testable} of ${s.n_candidates} documented wells were testable (n = ${s.n_cells.toLocaleString()} formation×hazard cells walked). Blind: the well's own reports are hidden — every alert is computed from other wells only.`,
          `विधि: ${s.n_candidates} में से ${s.n_testable} प्रलेखित कूप परीक्षण-योग्य थे (n = ${s.n_cells.toLocaleString()} संरचना×खतरा कोशिकाएँ)। अंध: कूप की अपनी रिपोर्टें छुपाई गई हैं — प्रत्येक चेतावनी केवल अन्य कूपों से गणना की जाती है।`
        )}
      </div>
    </div>
  );
}

const K_COLORS = ["#2563EB", "#0E7490", "#7C3AED"];

/** The honest "how much does it catch" card: per-well blind watch-list vs chance, plus the strict-alert trade-off. */
function WatchlistCard({ s, lang }: { s: HindsightSummary; lang: Lang }) {
  const t = (en: string, hi: string) => tr(lang, en, hi);
  const w = s.watchlist!;
  const main = w.rows.find((r) => r.k === 5) ?? w.rows[0];
  const f = s.forewarned;
  const ops = s.operating_points ?? [];
  return (
    <Card style={{ borderColor: BRAND.via, borderTopWidth: 4 }}>
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="label">{t(`Blind watch-list — top ${main.k} layer risks per well`, `अंध निगरानी-सूची — प्रति कूप शीर्ष ${main.k} परत जोखिम`)}</div>
        {main.x_random !== null && (
          <span className="num" style={{ background: BRAND.via, color: "#fff", borderRadius: 999, padding: "2px 10px", fontSize: 13, fontWeight: 700 }}>
            {main.x_random}× {t("chance", "संयोग")}
          </span>
        )}
      </div>
      <div className="mt-1 flex items-baseline gap-3 flex-wrap">
        <span className="num" style={{ fontSize: 40, fontWeight: 800, background: `linear-gradient(90deg, ${BRAND.from}, ${BRAND.to})`, WebkitBackgroundClip: "text", backgroundClip: "text", color: "transparent" }}>
          {main.hits} / {main.events}
        </span>
        <span className="num" style={{ fontSize: 22, fontWeight: 700, color: BRAND.via }}>{pct(main.share)}</span>
      </div>
      <p className="mt-1 max-w-prose">
        {t(
          `Real recorded problems that were on the well's blind top-${main.k} list before the bit got there (${Math.round(main.share_of_cells_flagged * 100)}% of layer×hazard cells watched). Picking ${main.k} at random would catch about ${Math.round(main.random_expected)}.`,
          `दर्ज वास्तविक समस्याएँ जो बिट के पहुँचने से पहले कूप की अंध शीर्ष-${main.k} सूची में थीं (${Math.round(main.share_of_cells_flagged * 100)}% परत×खतरा कोशिकाएँ)। यादृच्छिक ${main.k} चुनने पर लगभग ${Math.round(main.random_expected)} पकड़ी जातीं।`
        )}
      </p>
      <div className="mt-3 grid gap-2" role="list" aria-label={t("watch-list size vs chance", "सूची आकार बनाम संयोग")}>
        {w.rows.map((r, i) => (
          <div key={r.k} role="listitem" className="grid items-center gap-2" style={{ gridTemplateColumns: "64px 1fr 88px" }}>
            <span className="label">{t(`top ${r.k}`, `शीर्ष ${r.k}`)}</span>
            <div style={{ position: "relative", height: 14, background: "var(--surface-2)", borderRadius: 7, overflow: "hidden" }}>
              <div style={{ position: "absolute", inset: 0, width: `${(r.share ?? 0) * 100}%`, background: `linear-gradient(90deg, ${K_COLORS[i % 3]}, ${K_COLORS[(i + 1) % 3]})`, borderRadius: 7 }} />
              <div title={t("random pick", "यादृच्छिक")} style={{ position: "absolute", top: 0, bottom: 0, left: `${(r.random_share ?? 0) * 100}%`, width: 2, background: "var(--text)" }} />
            </div>
            <span className="num" style={{ fontWeight: 700, textAlign: "right" }}>{pct(r.share)} <span className="label">/ {pct(r.random_share)}</span></span>
          </div>
        ))}
        <div className="label">{t("bar = caught · black tick / second number = random pick", "पट्टी = पकड़ी गईं · काली रेखा / दूसरा अंक = यादृच्छिक")}</div>
      </div>
      {ops.length > 0 && (
        <div className="mt-3 rule-t pt-2">
          <div className="label mb-1">{t("Strict alerts — the sensitivity trade-off (same blind replay)", "सख़्त चेतावनियाँ — संवेदनशीलता संतुलन (वही अंध पुनःचलन)")}</div>
          <div className="flex flex-wrap gap-2">
            {ops.map((o) => (
              <div key={o.threshold} className="num" style={{ border: "1px solid var(--border)", borderRadius: 10, padding: "4px 10px", fontSize: 13 }}>
                <b>≥{Math.round(o.threshold * 100)}%</b> · {o.forewarned}/{o.events} {t("forewarned", "पूर्व-चेतावनी")} · {pct(o.hit_rate)} {t("right", "सही")}
              </div>
            ))}
          </div>
        </div>
      )}
      <p className="label mt-2">
        {t(
          `Honest note: ranking by the field-wide rate of each layer alone catches ${main.base_rate_hits}/${main.events} — the value is Kupakosh's compiled memory of every layer, not a nearby-well trick. ${w.n_events_without_cell} problems sat in layers missing from the well's column and could not be listed. Strict ≥${Math.round((ops[0]?.threshold ?? 0.4) * 100)}% alerts forewarned ${f.forewarned}/${f.events}.`,
          `ईमानदार टिप्पणी: केवल प्रत्येक परत की क्षेत्र-व्यापी दर से क्रम देने पर ${main.base_rate_hits}/${main.events} पकड़ी जाती हैं — मूल्य कूपकोश की हर परत की संकलित स्मृति में है। ${w.n_events_without_cell} समस्याएँ उन परतों में थीं जो कूप के स्तंभ में नहीं थीं। सख़्त चेतावनियों ने ${f.forewarned}/${f.events} की पूर्व-चेतावनी दी।`
        )}
      </p>
    </Card>
  );
}

/** Fallback when an older cached summary has no watch-list yet. */
function StrictCard({ s, lang }: { s: HindsightSummary; lang: Lang }) {
  const t = (en: string, hi: string) => tr(lang, en, hi);
  const f = s.forewarned;
  return (
    <Card style={{ borderColor: "var(--caution)" }}>
      <div className="label">{t("problems forewarned by strict alerts", "सख़्त चेतावनियों द्वारा पूर्व-चेतावनी")}</div>
      <div className="mt-1 num" style={{ fontSize: 30, fontWeight: 700, color: "var(--caution-ink, var(--caution))" }}>{f.forewarned} / {f.events}</div>
      <p className="label mt-2">{pct(f.forewarned_share)}</p>
    </Card>
  );
}
