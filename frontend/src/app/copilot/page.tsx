"use client";
import { useState } from "react";
import { post } from "@/lib/api";
import { SourceFootnote } from "@/components/kk/SourceFootnote";
import { CountryFilter } from "@/components/kk/CountryFilter";
import { useApp } from "@/lib/state";
import { t } from "@/lib/i18n";
import { Card } from "@/components/v2/ui";
import { WELL_SERIES } from "@/lib/palette";

const tr = (lang: string, en: string, hi: string) => (lang === "hi" ? hi : en);
// Suggested questions get a rotating colour so the chip row itself feels lively (decoration only, no meaning attached to which colour).
// WELL_SERIES_TEXT are darker ("-700") variants of the same hues (WELL_SERIES stays "-500/600", used for the background tint only) —
// the "-500/600" hues read fine as a light background but are too light to use as small text and clear AA (4.5:1) on their own tint.
const WELL_SERIES_TEXT = ["#1D4ED8", "#B45309", "#047857", "#BE185D", "#6D28D9", "#B91C1C", "#0F766E", "#C2410C", "#4338CA", "#4D7C0F", "#0E7490", "#A21CAF"];
const chipStyle = (i: number) => {
  const c = WELL_SERIES[i % WELL_SERIES.length];
  const tc = WELL_SERIES_TEXT[i % WELL_SERIES_TEXT.length];
  return { borderColor: `color-mix(in srgb, ${c} 45%, var(--border))`, background: `color-mix(in srgb, ${c} 8%, var(--surface))`, color: tc };
};

const SUGGEST = [
  "Which wells were drilled in the Himalayan foreland basin and how deep?",
  "How many exploratory wells have been drilled in the Krishna Godavari basin?",
  "What are the reservoirs in the Assam Arakan basin?",
  "What worked against stuck pipe in the Draupne Formation?",
  "Which offset wells near 15/9-19 S had losses?",
  "What is the mud weight window near 15/9-19 S?",
  "Where was a gas kick taken in the Hordaland Group?",
  "What happened at the granite contact in 16A(78)-32?",
  "What is the unconfined compressive strength of the Hugin Formation?",
];

export default function Copilot() {
  const { country, lang } = useApp();
  const [q, setQ] = useState("");
  const [thread, setThread] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);
  const ask = async (question: string) => {
    if (!question.trim()) return;
    setBusy(true);
    try {
      const r = await post("/api/copilot", { question, context_well: null, country });
      setThread((t) => [r, ...t]);
    } catch (e: any) { setThread((t) => [{ question, refused: true, answer: `Error: ${e.message}`, method: [], sources: [] }, ...t]); }
    setBusy(false); setQ("");
  };
  const last = thread[0];

  return (
    <div className="grid gap-4" style={{ gridTemplateColumns: "minmax(0,7fr) minmax(0,3fr)" }}>
      {/* Zone A — question box + suggested-question chips + answers as document-style cards */}
      <section aria-label="questions and answers" className="space-y-4">
        <Card>
          <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); ask(q); }}>
            <input className="input flex-1" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("cpQuestionPlaceholder", lang)} aria-label="question" />
            <button className="btn btn-primary" disabled={busy}>{busy ? t("cpSearching", lang) : t("cpAsk", lang)}</button>
          </form>
          <div className="mt-3"><CountryFilter label={t("searchRecordsFrom", lang)} /></div>
          <p className="label mt-2">{t("cpModeNote", lang)}</p>
          {thread.length === 0 && (
            <div className="flex flex-wrap gap-2 mt-3">
              {SUGGEST.map((s, i) => <button key={s} type="button" className="chip" style={chipStyle(i)} onClick={() => ask(s)}>{s}</button>)}
            </div>
          )}
        </Card>

        {thread.length === 0 && <p className="text-ink2 label">{t("cpAskOrPick", lang)}</p>}

        <div className="space-y-4">
          {thread.map((a, i) => (
            <Card key={i} as="article" className={i ? "opacity-80" : ""}>
              <h2 className="font-semibold">Q. {a.question}</h2>
              {a.refused ? (
                <div className="mt-2 border border-ink rounded-kk p-3">{a.answer}</div>
              ) : (
                <div className="mt-2 space-y-2 leading-relaxed">
                  {a.answer.split("\n\n").map((p: string, k: number) => <p key={k}>{withCites(p, a.sources)}</p>)}
                </div>
              )}
              {a.wiki?.length > 0 && (
                <p className="small mt-2">
                  {t("cpWikiPages", lang)} {a.wiki.map((w: any) => <a key={w.slug} className="link mr-2" href={`/wiki?page=${encodeURIComponent(w.slug)}`}>{w.title} ({w.status})</a>)}
                </p>
              )}
              <details className="mt-3 small">
                <summary className="cursor-pointer label">{t("cpMethod", lang)} ({a.method?.length ?? 0} {t("cpToolSteps", lang)})</summary>
                <ol className="list-decimal pl-5 mt-1">
                  {(a.method ?? []).map((s: any, k: number) => <li key={k}><span className="mono">{s.tool}</span>({Object.entries(s.args).map(([x, v]) => `${x}=${JSON.stringify(v)}`).join(", ")}) → {s.result}</li>)}
                </ol>
              </details>
            </Card>
          ))}
        </div>
      </section>

      {/* Zone B — sources used + suggested questions */}
      <aside aria-label="sources and suggestions" style={{ alignSelf: "start", position: "sticky", top: 12 }}>
        <Card>
          <h3 className="font-semibold">{t("cpSourcesUsed", lang)}</h3>
          {!last || last.refused ? <p className="label mt-1">—</p> : (
            <ol className="mt-1 small space-y-1">
              {last.sources.map((s: any, k: number) => <li key={k} className="flex gap-2"><SourceFootnote refId={s.ref} n={k + 1} /><span className="mono break-all">{s.label ? `${s.label} · ` : ""}{s.ref}</span></li>)}
            </ol>
          )}
          <h3 className="font-semibold mt-6">{t("cpSuggestedQuestions", lang)}</h3>
          <ul className="mt-1 space-y-1">
            {SUGGEST.map((s) => <li key={s}><button className="text-left link small" onClick={() => ask(s)}>{s}</button></li>)}
          </ul>
          <p className="label mt-6">{tr(lang, "Research-style: every claim is cited, and out-of-scope questions are refused rather than guessed.", "अनुसंधान-शैली: हर दावे का उद्धरण है, और दायरे-से-बाहर प्रश्नों को अटकल के बजाय अस्वीकार किया जाता है।")}</p>
        </Card>
      </aside>
    </div>
  );
}

function withCites(p: string, sources: any[]) {
  return p.split(/(\[\d+\])/g).map((part, i) => {
    const m = part.match(/^\[(\d+)\]$/);
    if (m && sources[Number(m[1]) - 1]) return <SourceFootnote key={i} refId={sources[Number(m[1]) - 1].ref} n={m[1]} />;
    return <span key={i}>{part}</span>;
  });
}
