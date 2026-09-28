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
  learned?: {
    config?: { alert_budget_per_well: number; folds: number };
    learned_live?: LearnedMode; learned_blind?: LearnedMode;
  } | null;
  lift_other_mode?: { mode: string; model: Rate; baseline: Rate };
  method: string;
};
type LearnedMode = {
  lift: Rate; baseline: Rate; alerts_per_well: number | null;
  forewarned: HindsightSummary["forewarned"]; forewarned_ci: [number, number] | null;
  baseline_forewarned: number; baseline_forewarned_share: number | null;
  watchlist: { k: number; hits: number; events: number; share: number | null }[];
};

const pct = (x: number | null) => (x === null ? "unknown" : `${Math.round(x * 100)}%`);

/** Zone A headline: problems forewarned by the learned live policy, against a fair same-budget baseline. */
export function HindsightTiles({ s, lang }: { s: HindsightSummary; lang: Lang }) {
  const t = (en: string, hi: string) => tr(lang, en, hi);
  const live = s.learned?.learned_live, blind = s.learned?.learned_blind;
  if (!live || !blind) return <LegacyTiles s={s} lang={lang} />;
  const f = live.forewarned;
  const strict = s.lift_other_mode?.model;
  const strictFw = s.operating_points?.find((o) => o.threshold >= 0.4);
  const bars: { label: string; share: number | null; n: number; color: string }[] = [
    { label: t("Kupakosh live (own reports above the bit only)", "कूपकोश लाइव (केवल बिट के ऊपर की अपनी रिपोर्ट)"), share: f.forewarned_share, n: f.forewarned, color: BRAND.via },
    { label: t("Kupakosh blind pre-drill (other wells only)", "कूपकोश अंध पूर्व-ड्रिल (केवल अन्य कूप)"), share: blind.forewarned.forewarned_share, n: blind.forewarned.forewarned, color: "#2563EB" },
    { label: t("Field average, same number of alerts", "क्षेत्र औसत, उतनी ही चेतावनियाँ"), share: live.baseline_forewarned_share, n: live.baseline_forewarned, color: "#94A3B8" },
    ...(strictFw ? [{ label: t("Strict alerts only (≥ 40%)", "केवल सख़्त चेतावनियाँ (≥ 40%)"), share: strictFw.forewarned_share, n: strictFw.forewarned, color: "#D97706" }] : []),
  ];
  return (
    <div className="grid gap-4" style={{ gridTemplateColumns: "minmax(0,1.3fr) minmax(0,1fr)" }}>
      <Card style={{ borderColor: BRAND.via, borderTopWidth: 4 }}>
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div className="label">{t("Real problems forewarned before the bit reached them", "बिट के पहुँचने से पहले पूर्व-चेतावनी दी गई वास्तविक समस्याएँ")}</div>
          {live.lift.lift !== null && (
            <span className="num" style={{ background: BRAND.via, color: "#fff", borderRadius: 999, padding: "2px 10px", fontSize: 13, fontWeight: 700 }}>
              {live.lift.lift.toFixed(1)}× {t("vs silent layers", "मौन परतों की तुलना में")}
            </span>
          )}
        </div>
        <div className="mt-1 flex items-baseline gap-3 flex-wrap">
          <span className="num" style={{ fontSize: 44, fontWeight: 800, background: `linear-gradient(90deg, ${BRAND.from}, ${BRAND.to})`, WebkitBackgroundClip: "text", backgroundClip: "text", color: "transparent" }}>
            {f.forewarned} / {f.events}
          </span>
          <span className="num" style={{ fontSize: 24, fontWeight: 700, color: BRAND.via }}>{pct(f.forewarned_share)}</span>
          {live.forewarned_ci && <span className="label num">95% {t("range", "सीमा")} {pct(live.forewarned_ci[0])}–{pct(live.forewarned_ci[1])}</span>}
        </div>
        <div className="mt-2 grid gap-3" style={{ gridTemplateColumns: "repeat(3, minmax(0,1fr))" }}>
          <Mini v={f.median_lead_m !== null ? `${Math.round(f.median_lead_m)} m` : t("unknown", "अज्ञात")} l={t("median warning ahead", "माध्यिका अग्रिम चेतावनी")} c="#10B981" />
          <Mini v={live.alerts_per_well !== null ? `${live.alerts_per_well.toFixed(1)}` : "—"} l={t("alerts per well", "प्रति कूप चेतावनियाँ")} c="#8B5CF6" />
          <Mini v={live.lift.rate_flagged !== null ? `1 in ${Math.round(1 / Math.max(live.lift.rate_flagged, 1e-6))}` : "—"} l={t("alerts matched a record", "चेतावनियाँ अभिलेख से मिलीं")} c="#F59E0B" />
        </div>
        <div className="mt-3 grid gap-2" role="list" aria-label={t("forewarned share by method", "विधि अनुसार पूर्व-चेतावनी")}>
          {bars.map((b) => (
            <div key={b.label} role="listitem" className="grid items-center gap-2" style={{ gridTemplateColumns: "minmax(0,1.4fr) minmax(0,1fr) 92px" }}>
              <span className="label" style={{ color: "var(--text)" }}>{b.label}</span>
              <div style={{ height: 14, background: "var(--surface-2)", borderRadius: 7, overflow: "hidden" }}>
                <div style={{ width: `${(b.share ?? 0) * 100}%`, height: "100%", background: b.color, borderRadius: 7 }} />
              </div>
              <span className="num" style={{ fontWeight: 700, textAlign: "right" }}>{b.n} <span className="label">({pct(b.share)})</span></span>
            </div>
          ))}
        </div>
        <p className="label mt-3">
          {t(
            `Same blind test, same ${f.events} recorded problems in ${s.n_testable} wells. With the same number of alerts, ranking layers by the field average alone forewarns ${live.baseline_forewarned}. ${strict ? `Strict ≥40% alerts are right ${pct(strict.rate_flagged)} of the time but rare.` : ""} An alert with no matching record is "no recorded event", not a false alarm — reports under-record problems.`,
            `वही अंध परीक्षण, ${s.n_testable} कूपों में वही ${f.events} दर्ज समस्याएँ। उतनी ही चेतावनियों के साथ केवल क्षेत्र औसत से ${live.baseline_forewarned} की पूर्व-चेतावनी होती है। बिना अभिलेख वाली चेतावनी "कोई दर्ज घटना नहीं" है, झूठी चेतावनी नहीं।`
          )}
        </p>
      </Card>
      {s.watchlist && s.watchlist.rows.length > 0 ? <WatchlistCard s={s} lang={lang} /> : <StrictCard s={s} lang={lang} />}
      <div className="label" style={{ gridColumn: "1 / -1" }}>
        {t(
          `Method: ${s.n_testable} of ${s.n_candidates} documented wells testable, ${s.n_cells.toLocaleString()} layer×hazard cells. A learned ranker is trained on other wells only (grouped ${s.learned?.config?.folds ?? 5}-fold cross-validation — a well and its sidetracks never train the model that scores them). "Live" also uses the well's own reports, but only for depths shallower than the alert point, as a rig would. The alert threshold is set on the training wells for about ${s.learned?.config?.alert_budget_per_well ?? 6} alerts per well; the tested wells never set it. Assumes the planned formation column equals the recorded one.`,
          `विधि: ${s.n_candidates} में से ${s.n_testable} कूप परीक्षण-योग्य, ${s.n_cells.toLocaleString()} परत×खतरा कोशिकाएँ। सीखा गया क्रमक केवल अन्य कूपों पर प्रशिक्षित (समूहित क्रॉस-वैलिडेशन)। "लाइव" कूप की अपनी रिपोर्ट केवल चेतावनी बिंदु से ऊपर की गहराई के लिए उपयोग करता है। सीमा प्रशिक्षण कूपों पर तय होती है।`
        )}
      </div>
    </div>
  );
}

function Mini({ v, l, c }: { v: string; l: string; c: string }) {
  return (
    <div style={{ borderRadius: 10, padding: "8px 10px", background: `color-mix(in srgb, ${c} 12%, var(--surface))`, borderLeft: `4px solid ${c}` }}>
      <div className="num" style={{ fontSize: 20, fontWeight: 800, color: "var(--text)" }}>{v}</div>
      <div className="label">{l}</div>
    </div>
  );
}

/** Pre-round-3 layout (posterior-only summary without a learned block). */
function LegacyTiles({ s, lang }: { s: HindsightSummary; lang: Lang }) {
  const t = (en: string, hi: string) => tr(lang, en, hi);
  const m = s.lift.model, b = s.lift.baseline;
  return (
    <div className="grid gap-4" style={{ gridTemplateColumns: "1.3fr 1fr" }}>
      <Card style={{ borderColor: "var(--ok)" }}>
        <div className="label">{t("When Kupakosh raised an alert…", "जब कूपकोश ने चेतावनी दी…")}</div>
        <div className="mt-1 num" style={{ fontSize: 30, fontWeight: 700 }}>{m.k_flagged} / {m.n_flagged}</div>
        <p className="label mt-2">{m.headline} · {t("fair baseline", "निष्पक्ष आधार")} {b.headline}</p>
      </Card>
      {s.watchlist && s.watchlist.rows.length > 0 ? <WatchlistCard s={s} lang={lang} /> : <StrictCard s={s} lang={lang} />}
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
        <div className="label">{t(`Pre-drill watch-list — top ${main.k} layer risks per well (posterior only)`, `पूर्व-ड्रिल निगरानी-सूची — प्रति कूप शीर्ष ${main.k} परत जोखिम`)}</div>
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
          `Honest note: ranking by the field-wide rate of each layer alone catches ${main.base_rate_hits}/${main.events} — the value is Kupakosh's compiled memory of every layer, not a nearby-well trick. ${w.n_events_without_cell} problems sat in layers missing from the well's column and could not be listed. Strict ≥${Math.round((ops[0]?.threshold ?? 0.4) * 100)}% alerts forewarned ${ops[0]?.forewarned ?? f.forewarned}/${f.events}.`,
          `ईमानदार टिप्पणी: केवल प्रत्येक परत की क्षेत्र-व्यापी दर से क्रम देने पर ${main.base_rate_hits}/${main.events} पकड़ी जाती हैं — मूल्य कूपकोश की हर परत की संकलित स्मृति में है। ${w.n_events_without_cell} समस्याएँ उन परतों में थीं जो कूप के स्तंभ में नहीं थीं। सख़्त चेतावनियों ने ${ops[0]?.forewarned ?? f.forewarned}/${f.events} की पूर्व-चेतावनी दी।`
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
