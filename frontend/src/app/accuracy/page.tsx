"use client";
import { useEffect, useState } from "react";
import { get } from "@/lib/api";
import { Register } from "@/components/kk/Register";
import { Drawer } from "@/components/kk/Drawer";
import { UploadReport } from "@/components/kk/UploadReport";
import { useApp } from "@/lib/state";
import { t } from "@/lib/i18n";

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
  useEffect(() => { get("/api/status").then(setS); }, [up]);
  if (!s) return <p className="label">{t("loading", lang)}</p>;
  const c = s.counts;
  const HOW: Record<string, string> = Object.fromEntries(EXPECTED.map((e) => [e.name + "|" + e.metric, e.how]));
  const rows = [...s.evals, ...EXPECTED.filter((e) => !s.evals.some((x: any) => x.name === e.name && x.metric === e.metric)).map((e) => ({ ...e, value: null, n: null }))];
  const fmt = (r: any) => r.value === null || r.value === undefined ? <span className="text-ink2">Not evaluated</span> : r.metric.startsWith("Brier") ? r.value.toFixed(5) : `${(r.value * 100).toFixed(1)}%`;
  return (
    <div className="space-y-8">
      {/* Zone A — four figures */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-4" aria-label="figures">
        <Fig v={c.wells} l={t("acWells", lang)} sub={`${c.documented_wells.toLocaleString()} with a report or history text${c.aggregate_locations ? ` · ${c.aggregate_locations.toLocaleString()} block/field locations not counted as wells` : ""}`} />
        <Fig v={c.report_entries} l={t("acReportEntries", lang)} sub={`${c.history_documents} well histories · ${c.ddr_reports} daily reports`} />
        <Fig v={c.events} l={t("acExtractedEvents", lang)} sub={`${c.events_trusted} trusted · ${c.events_needs_review} need review · method: ${s.extraction_method}`} />
        <Fig v={c.wiki_approved} l={t("acApprovedWiki", lang)} sub={`of ${c.wiki_pages} compiled (drafts need a reviewer)`} />
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
              { key: "c", head: t("acCol_country", lang), cell: (r: any) => r.country },
              { key: "w", head: t("acWells", lang), num: true, cell: (r: any) => r.wells.toLocaleString() },
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

function Fig({ v, l, sub }: { v: number; l: string; sub: string }) {
  return (
    <div className="border border-ink rounded-kk p-4 bg-card">
      <div className="num" style={{ fontSize: 34, lineHeight: 1.1 }}>{v.toLocaleString("en-IN")}</div>
      <div className="font-semibold">{l}</div>
      <div className="label mt-1">{sub}</div>
    </div>
  );
}
