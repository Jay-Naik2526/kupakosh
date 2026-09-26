"use client";
import { useEffect, useState } from "react";
import { get } from "@/lib/api";
import { Register } from "@/components/kk/Register";
import { Drawer } from "@/components/kk/Drawer";
import { UploadReport } from "@/components/kk/UploadReport";

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
  "Well-level stand-in data: Norwegian (Sodir) and US (Utah FORGE) public records. No Oil India well data is used or claimed.",
  "Sodir well-history texts are summaries, not daily reports; they under-record problems. A rate here is a rate of recorded problems.",
  "Extraction is rule-based (no language-model key configured). Events below the review threshold are flagged ‘needs review’ and excluded from the hazard model.",
  "Sodir exploration wells have no public trajectory in this build, so the mud window and correlation use MD; for deviated wells this is approximate.",
  "Lithology patterns for Norwegian units come from the lithostratigraphic lexicon (dominant rock type), not from logs.",
  "Only two wells (Utah FORGE 16A, 16B) have daily reports and rig-sensor data; the live look-ahead there usually has too little offset evidence and says so.",
  "Wiki pages are compiled drafts; none is approved until a named reviewer approves it. Reviewer names shown are demo users.",
  "Relational DB is SQLite in this prototype (no Docker/PostGIS on the build machine); retrieval is keyword (BM25), not embeddings.",
];

export default function Accuracy() {
  const [s, setS] = useState<any>(null);
  const [up, setUp] = useState(false);
  useEffect(() => { get("/api/status").then(setS); }, [up]);
  if (!s) return <p className="label">Loading…</p>;
  const c = s.counts;
  const HOW: Record<string, string> = Object.fromEntries(EXPECTED.map((e) => [e.name + "|" + e.metric, e.how]));
  const rows = [...s.evals, ...EXPECTED.filter((e) => !s.evals.some((x: any) => x.name === e.name && x.metric === e.metric)).map((e) => ({ ...e, value: null, n: null }))];
  const fmt = (r: any) => r.value === null || r.value === undefined ? <span className="text-ink2">Not evaluated</span> : r.metric.startsWith("Brier") ? r.value.toFixed(5) : `${(r.value * 100).toFixed(1)}%`;
  return (
    <div className="space-y-8">
      {/* Zone A — four figures */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-4" aria-label="figures">
        <Fig v={c.wells} l="wells" sub={`${c.documented_wells.toLocaleString()} with a report or history text`} />
        <Fig v={c.report_entries} l="report entries" sub={`${c.history_documents} well histories · ${c.ddr_reports} daily reports`} />
        <Fig v={c.events} l="extracted events" sub={`${c.events_trusted} trusted · ${c.events_needs_review} need review · method: ${s.extraction_method}`} />
        <Fig v={c.wiki_approved} l="approved wiki pages" sub={`of ${c.wiki_pages} compiled (drafts need a reviewer)`} />
      </section>

      {/* Zone B — data sources */}
      <section aria-label="data sources">
        <div className="flex items-baseline justify-between mb-2">
          <h2 className="font-semibold">Data sources</h2>
          <button className="btn" onClick={() => setUp(true)}>Add a report ▸</button>
        </div>
        <Drawer open={up} onClose={() => setUp(false)} title="Add a report" width={560}><UploadReport /></Drawer>
        <Register rows={s.sources} cols={[
          { key: "n", head: "Source", cell: (r: any) => <a className="link" href={r.url} target="_blank" rel="noreferrer">{r.name}</a> },
          { key: "l", head: "Licence", cell: (r: any) => r.licence },
          { key: "r", head: "Records", num: true, cell: (r: any) => r.records.toLocaleString() },
          { key: "d", head: "Loaded", num: true, cell: (r: any) => r.loaded_at?.slice(0, 10) },
          { key: "x", head: "Notes", cell: (r: any) => <span className="text-ink2">{r.notes}</span> },
        ]} />
        {s.by_country?.length > 0 && (
          <div className="mt-4">
            <h3 className="font-semibold mb-1">By country</h3>
            <Register rows={s.by_country} cols={[
              { key: "c", head: "Country", cell: (r: any) => r.country },
              { key: "w", head: "Wells", num: true, cell: (r: any) => r.wells.toLocaleString() },
              { key: "l", head: "With location", num: true, cell: (r: any) => r.located_wells.toLocaleString() },
              { key: "d", head: "Documents linked to a well", num: true, cell: (r: any) => r.documents_linked.toLocaleString() },
              { key: "e", head: "Events", num: true, cell: (r: any) => r.events.toLocaleString() },
              { key: "p", head: "Episodes", num: true, cell: (r: any) => r.episodes.toLocaleString() },
            ]} />
          </div>
        )}
        <p className="label mt-2">Also loaded: {c.formation_tops.toLocaleString()} formation tops · {c.lot_fit.toLocaleString()} LOT/FIT · {c.casing_strings.toLocaleString()} casing rows · {c.mud_checks.toLocaleString()} mud checks · {c.survey_stations.toLocaleString()} survey stations · {c.realtime_samples.toLocaleString()} sensor samples · {c.audit_open} open report conflicts.</p>
      </section>

      {/* Zone C — measured accuracy + limitations */}
      <section aria-label="measured accuracy" className="grid gap-8" style={{ gridTemplateColumns: "minmax(0,3fr) minmax(0,2fr)" }}>
        <div>
          <h2 className="font-semibold mb-2">Measured accuracy</h2>
          <Register rows={rows} cols={[
            { key: "a", head: "Area", cell: (r: any) => r.name.replace("_", " ") },
            { key: "m", head: "Metric", cell: (r: any) => r.metric },
            { key: "v", head: "Value", num: true, cell: fmt },
            { key: "n", head: "n", num: true, cell: (r: any) => r.n?.toLocaleString() ?? "—" },
            { key: "h", head: "How measured", cell: (r: any) => <span className="small">{HOW[r.name + "|" + r.metric] ?? ""}{r.notes ? <span className="label"> {r.notes}</span> : null}</span> },
          ]} />
          <p className="small mt-2"><b>Reading the hazard numbers:</b> the offset-well model is not measurably better than the formation base rate on this data (Brier model vs base above). Kupakosh therefore shows the rate with its range and evidence count, and says “insufficient evidence” when the evidence is thin — it does not claim predictive skill.</p>
        </div>
        <div>
          <h2 className="font-semibold mb-2">Known limitations</h2>
          <ol className="list-decimal pl-5 space-y-1 small">{LIMITS.map((l) => <li key={l}>{l}</li>)}</ol>
          <p className="label mt-3">Demo users ({s.demo_users.map((u: any) => u.name).join(", ")}) are placeholders configured in config/default.yaml, not real people.</p>
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
