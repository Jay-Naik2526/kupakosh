"use client";
import { useState } from "react";
import { post } from "@/lib/api";
import { useApp } from "@/lib/state";
import { SourceFootnote } from "@/components/kk/SourceFootnote";

const SUGGEST = [
  "What worked against stuck pipe in the Draupne Formation?",
  "Which offset wells near 15/9-19 S had losses?",
  "What is the mud weight window near 15/9-19 S?",
  "Where was a gas kick taken in the Hordaland Group?",
  "What happened at the granite contact in 16A(78)-32?",
  "What is the unconfined compressive strength of the Hugin Formation?",
];

export default function Copilot() {
  const { wellId } = useApp();
  const [q, setQ] = useState("");
  const [thread, setThread] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);
  const ask = async (question: string) => {
    if (!question.trim()) return;
    setBusy(true);
    try {
      const r = await post("/api/copilot", { question, context_well: null });
      setThread((t) => [r, ...t]);
    } catch (e: any) { setThread((t) => [{ question, refused: true, answer: `Error: ${e.message}`, method: [], sources: [] }, ...t]); }
    setBusy(false); setQ("");
  };
  const last = thread[0];

  return (
    <div className="grid gap-8" style={{ gridTemplateColumns: "minmax(0,7fr) minmax(0,3fr)" }}>
      {/* Zone A — Q&A as document text */}
      <section aria-label="questions and answers">
        <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); ask(q); }}>
          <input className="input flex-1" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ask the records, e.g. what worked against losses in the Utsira Formation?" aria-label="question" />
          <button className="btn btn-primary" disabled={busy}>{busy ? "Searching…" : "Ask"}</button>
        </form>
        <p className="label mt-1">Mode: extractive — answers are assembled only from tool outputs and quoted report lines; no language model is configured. Numbers come from the database.</p>
        <div className="mt-6 space-y-8">
          {thread.length === 0 && <p className="text-ink2">Ask a question, or pick one on the right.</p>}
          {thread.map((a, i) => (
            <article key={i} className={i ? "opacity-80" : ""}>
              <h2 className="font-semibold">Q. {a.question}</h2>
              {a.refused ? (
                <div className="mt-2 border border-ink rounded-kk p-3">{a.answer}</div>
              ) : (
                <div className="mt-2 space-y-2 leading-relaxed">
                  {a.answer.split("\n\n").map((p: string, k: number) => <p key={k}>{withCites(p, a.sources)}</p>)}
                </div>
              )}
              {a.wiki?.length > 0 && <p className="small mt-2">Wiki pages: {a.wiki.map((w: any) => <a key={w.slug} className="link mr-2" href={`/wiki?page=${encodeURIComponent(w.slug)}`}>{w.title} ({w.status})</a>)}</p>}
              <details className="mt-2 small">
                <summary className="cursor-pointer label">Method ({a.method?.length ?? 0} tool steps)</summary>
                <ol className="list-decimal pl-5 mt-1">
                  {(a.method ?? []).map((s: any, k: number) => <li key={k}><span className="mono">{s.tool}</span>({Object.entries(s.args).map(([x, v]) => `${x}=${JSON.stringify(v)}`).join(", ")}) → {s.result}</li>)}
                </ol>
              </details>
            </article>
          ))}
        </div>
      </section>
      {/* Zone B — sources used + suggestions */}
      <aside aria-label="sources and suggestions">
        <h3 className="font-semibold">Sources used</h3>
        {!last || last.refused ? <p className="label mt-1">—</p> : (
          <ol className="mt-1 small space-y-1">
            {last.sources.map((s: any, k: number) => <li key={k} className="flex gap-2"><SourceFootnote refId={s.ref} n={k + 1} /><span className="mono break-all">{s.label ? `${s.label} · ` : ""}{s.ref}</span></li>)}
          </ol>
        )}
        <h3 className="font-semibold mt-6">Suggested questions</h3>
        <ul className="mt-1 space-y-1">
          {SUGGEST.map((s) => <li key={s}><button className="text-left link small" onClick={() => ask(s)}>{s}</button></li>)}
        </ul>
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
