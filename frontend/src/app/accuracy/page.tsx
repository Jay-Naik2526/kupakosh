"use client";
import { useEffect, useState } from "react";
import { get } from "@/lib/api";
import { Register } from "@/components/kk/Register";
import { Drawer } from "@/components/kk/Drawer";
import { UploadReport } from "@/components/kk/UploadReport";
import { useApp } from "@/lib/state";
import { t } from "@/lib/i18n";
import { Card } from "@/components/v2/ui";
import { countryColor } from "@/lib/palette";

const FIG_COLORS = ["var(--info)", "#0891B2", "#8B5CF6", "var(--ok)"];

const tr = (lang: string, en: string, hi: string) => (lang === "hi" ? hi : en);

const EXPECTED = [
  { name: "extraction", metric: "event precision", how: "events_gold.csv: labelled real report lines vs rule extraction" },
  { name: "episodes", metric: "outcome precision", how: "episodes_gold.csv: labelled real problem → action → outcome chains" },
  { name: "hazard_loo", metric: "Brier score (model)", how: "leave-one-well-out over documented wells; lower is better" },
  { name: "hazard_loo", metric: "Brier score (base rate)", how: "same cases, predicting the field base rate" },
  { name: "copilot", metric: "citation accuracy", how: "copilot_questions.csv: expected sources present in answer" },
  { name: "copilot", metric: "refusal accuracy", how: "copilot_questions.csv: out-of-scope questions correctly refused" },
];

const LIMITS = [
  "Indian data: public NDR/DGH summaries of 23 sedimentary basins, 35 named Indian wells with drilled depth, and 6 NDR papers — geology and exploration facts, not daily drilling reports. Well-level Indian data needs NDR registration (student ID + HOD letter).",
  "Well-level stand-in data: public records from Norway (Sodir, FORCE 2020), USA (Utah FORGE, BSEE Gulf of Mexico), UK (NSTA), Netherlands (NLOG), Australia (SARIG, GSQ), New Zealand (NZP&M) and Canada (CNSOPB, C-NLOPB, Saskatchewan). No Oil India well data is used or claimed.",
  "UK, New Zealand and Canadian wells are headers only (location, depth, operator): their report archives need a login, so no events come from them.",
  "Scanned reports (for example 34 Queensland completion reports) are stored but not read: OCR is not installed in this build.",
  "US Gulf of Mexico records are BSEE incident summaries, not daily drilling reports; the column layout of the BSEE borehole file was inferred, and unclear columns were left out.",
  "Sodir well-history texts are summaries, not daily reports; they under-record problems. A rate here is a rate of recorded problems.",
  "Extraction is rule-based (no language-model key configured). Events below the review threshold are flagged ‘needs review’ and excluded from the hazard model.",
  "Sodir exploration wells have no public trajectory in this build, so the mud window and correlation use MD; for deviated wells this is approximate.",
  "Lithology patterns for Norwegian units come from the lithostratigraphic lexicon (dominant rock type), not from logs.",
  "Only two wells (Utah FORGE 16A, 16B) have daily reports and rig-sensor data; the live look-ahead there usually has too little offset evidence and says so.",
  "Wiki pages are compiled drafts; none is approved until a named reviewer approves it. Reviewer names shown are demo users.",
  "Relational DB is SQLite in this prototype (no Docker/PostGIS on the build machine); retrieval is keyword (BM25), not embeddings.",
];

export default function Accuracy() {
  const { lang } = useApp();
  const [s, setS] = useState<any>(null);
  const [up, setUp] = useState(false);
  const [hs, setHs] = useState<any>(null);
  const [hsErr, setHsErr] = useState(false);
  useEffect(() => { get("/api/status").then(setS); }, [up]);
  useEffect(() => { get("/api/hindsight/summary").then(setHs).catch(() => setHsErr(true)); }, []);
  if (!s) return <p className="label">{t("loading", lang)}</p>;
  const c = s.counts;
  const HOW: Record<string, string> = Object.fromEntries(EXPECTED.map((e) => [e.name + "|" + e.metric, e.how]));
  const rows = [...s.evals, ...EXPECTED.filter((e) => !s.evals.some((x: any) => x.name === e.name && x.metric === e.metric)).map((e) => ({ ...e, value: null, n: null }))];
  const fmt = (r: any) => {
    if (r.value === null || r.value === undefined) return <span className="text-ink2">Not evaluated</span>;
    if (r.metric.startsWith("Brier")) return r.value.toFixed(5);
    const pctv = r.value * 100;
    // "#166534" is a darker green than the --ok token: --ok reads well as a fill/bar but is only ~3.3:1 on white, short of AA for small text.
    const textC = pctv >= 70 ? "#166534" : pctv >= 40 ? "var(--caution-ink)" : "var(--hazard)";
    const barC = pctv >= 70 ? "var(--ok)" : pctv >= 40 ? "var(--caution)" : "var(--hazard)";
    return (
      <span className="inline-flex items-center gap-2 justify-end w-full">
        <span className="num" style={{ color: textC }}>{pctv.toFixed(1)}%</span>
        <span style={{ width: 48, height: 6, background: "var(--surface-2)", borderRadius: 3, overflow: "hidden", display: "inline-block" }}>
          <span style={{ display: "block", height: "100%", width: `${Math.min(100, pctv)}%`, background: barC }} />
        </span>
      </span>
    );
  };
  return (
    <div className="space-y-8">
      {/* Zone A — four figures */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-4" aria-label="figures">
        <Fig v={c.wells} l={t("acWells", lang)} c={FIG_COLORS[0]} sub={`${c.documented_wells.toLocaleString()} with a report or history text${c.aggregate_locations ? ` · ${c.aggregate_locations.toLocaleString()} block/field locations not counted as wells` : ""}`} />
        <Fig v={c.report_entries} l={t("acReportEntries", lang)} c={FIG_COLORS[1]} sub={`${c.history_documents} well histories · ${c.ddr_reports} daily reports`} />
        <Fig v={c.events} l={t("acExtractedEvents", lang)} c={FIG_COLORS[2]} sub={`${c.events_trusted} trusted · ${c.events_needs_review} need review · method: ${s.extraction_method}`} />
        <Fig v={c.wiki_approved} l={t("acApprovedWiki", lang)} c={FIG_COLORS[3]} sub={`of ${c.wiki_pages} compiled (drafts need a reviewer)`} />
      </section>

      {/* Zone B — data sources */}
      <section aria-label="data sources">
        <div className="flex items-baseline justify-between mb-2">
          <h2 className="font-semibold">{t("acDataSources", lang)}</h2>
          <button className="btn" onClick={() => setUp(true)}>{t("acAddReport", lang)}</button>
        </div>
        <Drawer open={up} onClose={() => setUp(false)} title={t("acAddReportTitle", lang)} width={560}><UploadReport /></Drawer>
        <Register rows={s.sources} cols={[
          { key: "n", head: t("acCol_source", lang), cell: (r: any) => <a className="link" href={r.url} target="_blank" rel="noreferrer">{r.name}</a> },
          { key: "l", head: t("acCol_licence", lang), cell: (r: any) => r.licence },
          { key: "r", head: t("acCol_records", lang), num: true, cell: (r: any) => r.records.toLocaleString() },
          { key: "d", head: t("acCol_loaded", lang), num: true, cell: (r: any) => r.loaded_at?.slice(0, 10) },
          { key: "x", head: t("acCol_notes", lang), cell: (r: any) => <span className="text-ink2">{r.notes}</span> },
        ]} />
        {s.by_country?.length > 0 && (
          <div className="mt-4">
            <h3 className="font-semibold mb-1">{t("acByCountry", lang)}</h3>
            <Register rows={s.by_country} cols={[
              { key: "c", head: t("acCol_country", lang), cell: (r: any) => (
                <span className="inline-flex items-center gap-2">
                  <span aria-hidden="true" className="inline-block rounded-full" style={{ width: 9, height: 9, background: countryColor(r.country) }} />
                  {r.country}
                </span>
              ) },
              { key: "w", head: t("acWells", lang), num: true, cell: (r: any) => {
                const max = Math.max(1, ...s.by_country.map((x: any) => x.wells));
                const c = countryColor(r.country);
                return (
                  <span className="inline-flex items-center gap-2 justify-end w-full">
                    <span className="num">{r.wells.toLocaleString()}</span>
                    <span style={{ width: 48, height: 6, background: "var(--surface-2)", borderRadius: 3, overflow: "hidden", display: "inline-block" }}>
                      <span style={{ display: "block", height: "100%", width: `${(r.wells / max) * 100}%`, background: c }} />
                    </span>
                  </span>
                );
              } },
              { key: "l", head: t("acCol_withLocation", lang), num: true, cell: (r: any) => r.located_wells.toLocaleString() },
              { key: "d", head: t("acCol_docsLinked", lang), num: true, cell: (r: any) => r.documents_linked.toLocaleString() },
              { key: "e", head: t("acCol_events", lang), num: true, cell: (r: any) => r.events.toLocaleString() },
              { key: "p", head: t("acCol_episodes", lang), num: true, cell: (r: any) => r.episodes.toLocaleString() },
            ]} />
          </div>
        )}
        <p className="label mt-2">Also loaded: {c.formation_tops.toLocaleString()} formation tops · {c.lot_fit.toLocaleString()} LOT/FIT · {c.casing_strings.toLocaleString()} casing rows · {c.mud_checks.toLocaleString()} mud checks · {c.survey_stations.toLocaleString()} survey stations · {c.realtime_samples.toLocaleString()} sensor samples · {c.audit_open} open report conflicts.</p>
      </section>

      {/* Zone C — measured accuracy + limitations */}
      <section aria-label="measured accuracy" className="grid gap-8" style={{ gridTemplateColumns: "minmax(0,3fr) minmax(0,2fr)" }}>
        <div>
          <h2 className="font-semibold mb-2">{t("acMeasuredAccuracy", lang)}</h2>
          <Register rows={rows} cols={[
            { key: "a", head: t("acCol_area", lang), cell: (r: any) => r.name.replace("_", " ") },
            { key: "m", head: t("acCol_metric", lang), cell: (r: any) => r.metric },
            { key: "v", head: t("acCol_value", lang), num: true, cell: fmt },
            { key: "n", head: "n", num: true, cell: (r: any) => r.n?.toLocaleString() ?? "—" },
            { key: "h", head: t("acCol_how", lang), cell: (r: any) => <span className="small">{HOW[r.name + "|" + r.metric] ?? ""}{r.notes ? <span className="label"> {r.notes}</span> : null}</span> },
          ]} />
          <p className="small mt-2"><b>{t("acReadingHazard", lang)}</b> the offset-well model is not measurably better than the formation base rate on this data (Brier model vs base above). Kupakosh therefore shows the rate with its range and evidence count, and says “insufficient evidence” when the evidence is thin — it does not claim predictive skill.</p>

          <h2 className="font-semibold mt-6 mb-2">{tr(lang, "Hindsight (blind leave-well-out replay)", "हिंडसाइट (अंध लीव-वन-वेल-आउट पुनःचलन)")}</h2>
          {hsErr && <p className="label">{t("notEvaluated", lang)}</p>}
          {!hsErr && !hs && <p className="label">{t("loading", lang)}</p>}
          {hs && (
            <>
              <div className="grid grid-cols-3 gap-3 mb-3">
                <HsTile v={`${hs.lift.model.lift.toFixed(1)}x`} l={tr(lang, "lift over silence", "मौन पर लाभ")} good={hs.lift.model.lift > hs.lift.baseline.lift} />
                {hs.watchlist?.rows?.length ? (() => { const w = hs.watchlist.rows.find((r: any) => r.k === 5) ?? hs.watchlist.rows[0]; return (
                  <HsTile v={`${w.hits}/${w.events}`} l={tr(lang, `on blind top-${w.k} watch-list (${w.x_random}× chance)`, `अंध शीर्ष-${w.k} सूची में (${w.x_random}× संयोग)`)} good={w.x_random > 2} />
                ); })() : (
                  <HsTile v={`${(hs.forewarned.forewarned_share * 100).toFixed(0)}%`} l={tr(lang, "problems forewarned", "पूर्व-चेतावनी समस्याएँ")} good={hs.forewarned.forewarned_share >= 0.3} />
                )}
                <HsTile v={`${hs.forewarned.median_lead_m.toFixed(0)} m`} l={tr(lang, "median lead", "माध्यिका अग्रता")} good={hs.forewarned.median_lead_m >= 50} />
              </div>
              <Register rows={hindsightRows(hs)} cols={[
                { key: "m", head: t("acCol_metric", lang), cell: (r: any) => r.metric },
                { key: "v", head: t("acCol_value", lang), num: true, cell: (r: any) => r.value },
                { key: "n", head: "n", num: true, cell: (r: any) => r.n },
                { key: "h", head: t("acCol_how", lang), cell: (r: any) => <span className="small text-ink2">{r.how}</span> },
              ]} />
              <p className="small mt-2">
                {tr(lang,
                  `Each of ${hs.n_testable.toLocaleString()} documented wells was replayed as if brand new, offset evidence from every other well only. Where the model raised an alert 150 m ahead of a formation, it was right ${(hs.lift.model.rate_flagged * 100).toFixed(0)}% of the time (${hs.lift.model.k_flagged}/${hs.lift.model.n_flagged}), against a background rate of ${(hs.lift.model.rate_unflagged * 100).toFixed(1)}% when nothing was flagged — a ${hs.lift.model.lift.toFixed(1)}x lift over staying silent. Strict alerts are rare, so most problems are not forewarned by them: ${hs.forewarned.forewarned}/${hs.forewarned.events} (${(hs.forewarned.forewarned_share * 100).toFixed(1)}%), at a median lead of ${hs.forewarned.median_lead_m.toFixed(0)} m. The base-rate-only baseline scores close behind (${hs.lift.baseline.lift.toFixed(1)}x), so most of the lift comes from simply flagging rare hazards at all, not from offset-well similarity.${hs.watchlist?.rows?.length ? ` As a ranked watch-list, though, the blind top-5 per well already held ${(hs.watchlist.rows.find((r: any) => r.k === 5) ?? hs.watchlist.rows[0]).hits}/${hs.forewarned.events} real problems.` : ""}`,
                  `${hs.n_testable.toLocaleString()} दस्तावेज़ीकृत कूपों में से प्रत्येक को नए जैसा मानकर, केवल अन्य सभी कूपों के साक्ष्य के आधार पर पुनःचलाया गया। जहाँ मॉडल ने किसी संरचना से 150 मीटर पहले चेतावनी दी, वह ${(hs.lift.model.rate_flagged * 100).toFixed(0)}% बार सही थी (${hs.lift.model.k_flagged}/${hs.lift.model.n_flagged}), जबकि बिना चेतावनी की पृष्ठभूमि दर ${(hs.lift.model.rate_unflagged * 100).toFixed(1)}% थी — चुप रहने की तुलना में ${hs.lift.model.lift.toFixed(1)}x लाभ। अधिकांश समस्याएँ अब भी पूर्व-चेतावनी रहित हैं: केवल ${hs.forewarned.forewarned}/${hs.forewarned.events} (${(hs.forewarned.forewarned_share * 100).toFixed(1)}%), माध्यिका अग्रता ${hs.forewarned.median_lead_m.toFixed(0)} मी पर। आधार-दर-मात्र आधाररेखा भी करीब है (${hs.lift.baseline.lift.toFixed(1)}x), अतः अधिकांश लाभ दुर्लभ खतरों को केवल चिह्नित करने से आता है, ऑफसेट-कूप समानता से नहीं।`
                )}
              </p>
            </>
          )}
        </div>
        <div>
          <h2 className="font-semibold mb-2">{t("acKnownLimitations", lang)}</h2>
          <ol className="list-decimal pl-5 space-y-1 small">{LIMITS.map((l) => <li key={l}>{l}</li>)}</ol>
          <p className="label mt-3">{t("acDemoUsers", lang)} ({s.demo_users.map((u: any) => u.name).join(", ")}) {t("acDemoUsersNote", lang)}</p>
        </div>
      </section>
    </div>
  );
}

function hindsightRows(hs: any) {
  const m = hs.lift.model, b = hs.lift.baseline, f = hs.forewarned;
  return [
    { metric: "alerts right vs silent (model)", value: `${(m.rate_flagged * 100).toFixed(0)}% vs ${(m.rate_unflagged * 100).toFixed(1)}%`, n: `${m.k_flagged}/${m.n_flagged}`, how: "leave-one-well-out replay; rate an alerted cell had the hazard, vs an unflagged cell" },
    { metric: "lift over staying silent (model)", value: `${m.lift.toFixed(1)}x`, n: hs.n_testable, how: "model rate_flagged / rate_unflagged, 95% CI ±" + `${((m.lift_ci_approx?.[1] - m.lift_ci_approx?.[0]) / 2).toFixed(0)}x` },
    { metric: "lift over staying silent (base-rate baseline)", value: `${b.lift.toFixed(1)}x`, n: hs.n_testable, how: "same cells, predicting only the field/formation base rate — honesty check on how much offset-similarity adds" },
    ...((hs.watchlist?.rows ?? []) as any[]).map((w) => ({ metric: `on blind top-${w.k} watch-list`, value: `${(w.share * 100).toFixed(1)}%`, n: `${w.hits}/${w.events}`, how: `per well, its own layer×hazard cells ranked by blind posterior; top ${w.k} (${(w.share_of_cells_flagged * 100).toFixed(1)}% of cells). Random pick: ${(w.random_share * 100).toFixed(1)}%; field base-rate ranking alone: ${(w.base_rate_share * 100).toFixed(1)}%` })),
    { metric: "problems forewarned (strict alerts)", value: `${(f.forewarned_share * 100).toFixed(1)}%`, n: `${f.forewarned}/${f.events}`, how: "share of recorded hazard events that had a strict (posterior ≥ alert threshold) alert at least 150 m ahead" },
    { metric: "median lead distance", value: `${f.median_lead_m.toFixed(0)} m`, n: f.forewarned, how: "median along-hole distance between the alert and the event, when forewarned" },
  ];
}

function HsTile({ v, l, good }: { v: string; l: string; good: boolean }) {
  // "#166534" (not --ok) so the big number clears AA as text; the tint background still uses the brighter --ok hue for the vivid card colour.
  const tint = good ? "var(--ok)" : "var(--caution)";
  const textC = good ? "#166534" : "var(--caution-ink)"; // green-800: #166534 was 4.499:1 on this tinted background, just under AA
  return (
    <div className="rounded-kk p-3 text-center" style={{ border: `1px solid color-mix(in srgb, ${tint} 40%, var(--border))`, background: `color-mix(in srgb, ${tint} 10%, var(--surface))` }}>
      <div className="num font-semibold" style={{ fontSize: 22, color: textC }}>{v}</div>
      <div className="label mt-0.5">{l}</div>
    </div>
  );
}

function Fig({ v, l, sub, c }: { v: number; l: string; sub: string; c: string }) {
  return (
    <div className="rounded-kk p-4" style={{ borderTop: `3px solid ${c}`, border: `1px solid var(--border)`, borderTopWidth: 3, borderTopColor: c, background: `color-mix(in srgb, ${c} 6%, var(--surface))` }}>
      <div className="num" style={{ fontSize: 34, lineHeight: 1.1, color: c }}>{v.toLocaleString("en-IN")}</div>
      <div className="font-semibold">{l}</div>
      <div className="label mt-1">{sub}</div>
    </div>
  );
}
