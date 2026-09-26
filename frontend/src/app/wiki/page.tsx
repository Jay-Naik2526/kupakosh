"use client";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { get, post } from "@/lib/api";
import { useApp } from "@/lib/state";
import { Stamp } from "@/components/kk/Stamp";
import { NotingSheet } from "@/components/kk/NotingSheet";
import { SourceFootnote } from "@/components/kk/SourceFootnote";
import { Drawer } from "@/components/kk/Drawer";
import { EmptyState } from "@/components/kk/EmptyState";
import { t } from "@/lib/i18n";

export default function WikiPageWrap() { return <Suspense><Wiki /></Suspense>; }

function Wiki() {
  const params = useSearchParams();
  const router = useRouter();
  const { user, lang } = useApp();
  const slug = params.get("page") ?? "hazards/lost_circulation";
  const [page, setPage] = useState<any>(null);
  const [notes, setNotes] = useState<any[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [drawer, setDrawer] = useState<null | "index" | "diff" | "tray">(null);
  const [all, setAll] = useState<any[]>([]);
  const [q, setQ] = useState("");
  const [note, setNote] = useState("");
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [hist, setHist] = useState<any[]>([]);
  const [diff, setDiff] = useState<string>("");
  const [busy, setBusy] = useState(false);

  const load = () => {
    setErr(null);
    get(`/api/wiki/${slug}`).then((p) => { setPage(p); setDraft(p.body); }).catch(() => { setPage(null); setErr(lang === "hi" ? "पृष्ठ नहीं मिला।" : "Page not found."); });
    get(`/api/wiki/${slug}/noting`).then(setNotes).catch(() => setNotes([]));
    get(`/api/wiki/${slug}/history`).then(setHist).catch(() => setHist([]));
  };
  useEffect(load, [slug]); // eslint-disable-line
  useEffect(() => { get("/api/wiki").then(setAll); }, [page?.status]);

  const act = async (action: "approve" | "return" | "edit") => {
    if (!user) return;
    setBusy(true); setErr(null);
    try {
      await post(`/api/wiki/${slug}/review`, { action, reviewer: user.name, role: user.role, note: note || null, content: action === "edit" ? draft : null });
      setNote(""); setEditing(false); load();
    } catch (e: any) { setErr(String(e.message).replace(/^\d+ /, "")); }
    setBusy(false);
  };
  const showDiff = async (a: string, b: string) => { const d = await get(`/api/wiki/${slug}/diff`, { a, b }); setDiff(d.diff); setDrawer("diff"); };
  const pending = all.filter((p) => p.status !== "approved");

  return (
    <div>
      <div className="flex flex-wrap gap-2 mb-4">
        <button className="btn" onClick={() => setDrawer("index")}>{t("wikiIndexBtn", lang)}</button>
        <button className="btn" onClick={() => setDrawer("tray")}>{t("wikiPendingTray", lang)} ({pending.length}) ▸</button>
        {hist.length > 1 && <button className="btn" onClick={() => showDiff(hist[1].commit, hist[0].commit)}>{t("wikiVersionDiff", lang)}</button>}
      </div>
      {err && !page && <EmptyState title={t("wikiNotFound", lang)} why={err} />}
      {page && (
        <div className="grid gap-8" style={{ gridTemplateColumns: "minmax(0, 64fr) minmax(0, 36fr)" }}>
          {/* Zone A — the document */}
          <article aria-label="wiki page" className="bg-card border border-rule rounded-kk p-6">
            <div className="flex justify-between items-start gap-4 rule-b pb-3">
              <div>
                <div className="typewriter small">{page.ref_no} · v{page.version}</div>
                <h2 className="text-xl font-semibold mt-1">{page.title}</h2>
                <div className="label">{page.kind} {t("wikiPageSuffix", lang)} · {page.n_sources} {t("wikiSourcesSuffix", lang)} · {t("wikiCommit", lang)} <span className="mono">{page.git_commit?.slice(0, 8)}</span></div>
                <TrustBar v={page.trust} lang={lang} />
              </div>
              {page.status === "approved" && <Stamp kind="approved" round text="APPROVED" sub={`${page.approved_by} · ${page.approved_at?.slice(0, 10)}`} />}
              {page.status === "returned" && <Stamp kind="returned" text="RETURNED" />}
              {(page.status === "draft" || page.status === "in_review") && <Stamp kind="draft" text={page.status === "draft" ? "DRAFT" : "IN REVIEW"} sub={t("wikiNotApprovedKnowledge", lang)} />}
            </div>
            {!editing && <Markdown body={page.body} onLink={(s) => router.push(`/wiki?page=${encodeURIComponent(s)}`)} />}
            {editing && (
              <div className="mt-4">
                <p className="label">{t("wikiEditHelp", lang)}</p>
                <textarea className="input w-full mono small mt-2" rows={22} value={draft} onChange={(e) => setDraft(e.target.value)} aria-label="page markdown" />
              </div>
            )}
          </article>

          {/* Zone B — noting sheet + actions */}
          <aside aria-label="noting">
            <h3 className="font-semibold mb-2">{t("wikiNoting", lang)} <span className="deva label">टिप्पणी</span></h3>
            <NotingSheet notes={notes} />
            <div className="mt-4 space-y-2">
              {!user && <p className="small">{t("selectDemoUserApprove", lang)}</p>}
              <textarea className="input w-full" rows={3} placeholder={t("wikiNoteForFile", lang)} value={note} onChange={(e) => setNote(e.target.value)} aria-label="reviewer note" disabled={!user} />
              <div className="flex gap-2 flex-wrap">
                <button className="btn btn-primary" disabled={!user || busy || page.status === "approved"} onClick={() => act("approve")}>{t("wikiApprove", lang)}</button>
                {!editing ? <button className="btn" disabled={!user || busy} onClick={() => setEditing(true)}>{t("wikiEdit", lang)}</button>
                  : <><button className="btn" disabled={busy} onClick={() => act("edit")}>{t("wikiSaveEdit", lang)}</button><button className="btn" onClick={() => { setEditing(false); setDraft(page.body); }}>{t("wikiCancel", lang)}</button></>}
                <button className="btn" disabled={!user || busy} onClick={() => act("return")}>{t("wikiReturn", lang)}</button>
              </div>
              {err && <p className="small" style={{ color: "var(--hazard)" }}>✕ {err}</p>}
              <p className="label">{t("wikiReviewNote", lang)}</p>
            </div>
          </aside>
        </div>
      )}

      <Drawer open={drawer === "index" || drawer === "tray"} onClose={() => setDrawer(null)} title={drawer === "tray" ? `${t("wikiPendingTray", lang)} (${pending.length})` : t("wikiPageIndex", lang)}>
        <input className="input w-full mb-3" placeholder={t("wikiFilterPlaceholder", lang)} value={q} onChange={(e) => setQ(e.target.value)} />
        {(["basin", "hazard", "formation", "well"] as const).map((k) => {
          const rows = (drawer === "tray" ? pending : all).filter((p) => p.kind === k && p.title.toLowerCase().includes(q.toLowerCase()));
          if (!rows.length) return null;
          return (
            <div key={k} className="mb-4">
              <div className="label uppercase mb-1">{k === "basin" ? "Indian basins (NDR/DGH)" : `${k}s`} ({rows.length})</div>
              <ul>{rows.slice(0, 200).map((p) => (
                <li key={p.slug}><button className="w-full text-left rule-b py-1 small flex justify-between gap-2" onClick={() => { router.push(`/wiki?page=${encodeURIComponent(p.slug)}`); setDrawer(null); }}>
                  <span>{p.title}</span><span className="label mono">{p.status}</span></button></li>
              ))}</ul>
            </div>
          );
        })}
      </Drawer>
      <Drawer open={drawer === "diff"} onClose={() => setDrawer(null)} title={t("wikiVersionDiffTitle", lang)} width={640}>
        <div className="mb-3 small">
          {hist.map((h, i) => (
            <div key={h.commit} className="rule-b py-1 flex justify-between gap-2">
              <span><span className="mono">{h.short}</span> {h.message}</span>
              {i < hist.length - 1 && <button className="link" onClick={() => showDiff(hist[i + 1].commit, h.commit)}>{t("wikiDiffVsPrevious", lang)}</button>}
            </div>
          ))}
        </div>
        <Diff text={diff} lang={lang} />
      </Drawer>
    </div>
  );
}

function TrustBar({ v, lang }: { v: number | null; lang: "en" | "hi" }) {
  if (v === null || v === undefined) return <div className="label mt-1">{t("wikiTrustNotComputed", lang)}</div>;
  return (
    <div className="flex items-center gap-2 mt-2 small" title="share of cited report lines with no open report conflict">
      <span className="label">{t("wikiTrust", lang)}</span>
      <span className="inline-block h-2 w-40 border border-ink"><span className="block h-full" style={{ width: `${v * 100}%`, background: "var(--ink)" }} /></span>
      <span className="num">{Math.round(v * 100)}%</span>
    </div>
  );
}

function Markdown({ body, onLink }: { body: string; onLink: (slug: string) => void }) {
  const { lines, refs } = useMemo(() => {
    const refs: Record<string, string> = {};
    const lines: string[] = [];
    for (const l of body.split("\n")) {
      const m = l.match(/^\[\^s(\d+)\]:\s*(.+)$/);
      if (m) refs[m[1]] = m[2]; else lines.push(l);
    }
    return { lines, refs };
  }, [body]);
  const inline = (t: string, key: number) => {
    const parts = t.split(/(\[\^s\d+\]|\[\[[^\]]+\]\])/g);
    return parts.map((p, i) => {
      const f = p.match(/^\[\^s(\d+)\]$/);
      if (f) return <SourceFootnote key={`${key}-${i}`} refId={refs[f[1]]} n={f[1]} />;
      const w = p.match(/^\[\[([^\]]+)\]\]$/);
      if (w) return <button key={`${key}-${i}`} className="link mr-1" onClick={() => onLink(w[1])}>↗</button>;
      return <span key={`${key}-${i}`}>{p}</span>;
    });
  };
  const out: JSX.Element[] = [];
  let ul: JSX.Element[] = [];
  const flush = () => { if (ul.length) { out.push(<ul key={`u${out.length}`}>{ul}</ul>); ul = []; } };
  lines.forEach((l, i) => {
    if (l.startsWith("## ")) { flush(); out.push(<h2 key={i}>{l.slice(3)}</h2>); }
    else if (l.startsWith("- ")) ul.push(<li key={i}>{inline(l.slice(2), i)}</li>);
    else if (l.startsWith("> ")) { flush(); out.push(<blockquote key={i}>{inline(l.slice(2), i)}</blockquote>); }
    else if (l.trim()) { flush(); out.push(<p key={i}>{inline(l, i)}</p>); }
  });
  flush();
  return <div className="prose-wiki mt-2">{out}</div>;
}

function Diff({ text, lang }: { text: string; lang: "en" | "hi" }) {
  if (!text) return <p className="label">{t("wikiSelectTwo", lang)}</p>;
  const lines = text.split("\n").filter((l) => !/^(diff|index|---|\+\+\+|@@)/.test(l));
  const out: JSX.Element[] = [];
  let cur: JSX.Element[] = [];
  lines.forEach((l, i) => {
    if (l === "~") { out.push(<p key={i} className="small mb-1">{cur}</p>); cur = []; return; }
    const t = l.slice(1);
    if (l.startsWith("+")) cur.push(<span key={i} style={{ textDecoration: "underline", textDecorationColor: "var(--ok)", textDecorationThickness: 2 }}>{t}</span>);
    else if (l.startsWith("-")) cur.push(<span key={i} style={{ textDecoration: "line-through", color: "var(--hazard)" }}>{t}</span>);
    else cur.push(<span key={i}>{t}</span>);
  });
  if (cur.length) out.push(<p key="last" className="small">{cur}</p>);
  return <div className="bg-card border border-rule p-3 rounded-kk">{out}<p className="label mt-2">{t("wikiDiffLegend", lang)}</p></div>;
}
