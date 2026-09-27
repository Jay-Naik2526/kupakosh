"use client";
import { useEffect, useState } from "react";
import { get } from "@/lib/api";
import { useApp } from "@/lib/state";
import { hazardLabel } from "@/lib/format";

// Colour a citation by the kind of record it points to (report doc, a table row, a live DB query, a sensor sample) —
// decoration only, the ref text and glyph still carry the meaning. Darker ("-700") hues so the small text clears AA (4.5:1) on its own tint.
export function sourceKindColor(refId: string): string {
  if (refId?.startsWith("doc:")) return "var(--info)";
  if (refId?.startsWith("query:")) return "#7E22CE";
  if (refId?.startsWith("sodir:") || refId?.includes(":table:")) return "#0E7490";
  if (refId?.startsWith("realtime:")) return "#166534";
  return "var(--text-2)";
}

/** Tiny superscript marker; click opens a paper slip with the verbatim source text + ref. */
export function SourceFootnote({ refId, n }: { refId: string; n: number | string }) {
  const { openSource } = useApp();
  const c = sourceKindColor(refId);
  return (
    <button type="button" onClick={(e) => { e.stopPropagation(); openSource(refId); }} title={refId}
      className="num align-super text-[0.72rem] px-0.5 rounded-kk ml-0.5 leading-none"
      style={{ border: `1px solid color-mix(in srgb, ${c} 55%, var(--border))`, background: `color-mix(in srgb, ${c} 12%, var(--card))`, color: c }}
      aria-label={`source ${n}: ${refId}`}>{n}</button>
  );
}

export function SourceSlip() {
  const { source, openSource } = useApp();
  const [d, setD] = useState<any>(null);
  const [rows, setRows] = useState<any[] | null>(null);
  useEffect(() => {
    setD(null); setRows(null);
    if (!source) return;
    if (source.startsWith("query:")) {
      const [kind, qs] = source.slice(6).split("?");
      const p = Object.fromEntries(new URLSearchParams(qs || ""));
      setD({ ref: source, kind: "QUERY", title: `Database query: ${kind}`, query: p, qkind: kind });
      if (kind === "events") {
        const params: any = { hazard: p.hazard, formation: p.formation, include_review: false, limit: 30 };
        if (p.well) get("/api/wells", { q: p.well, limit: 1 }).then((w) => w[0] && get("/api/events", { ...params, well: w[0].id }).then(setRows));
        else get("/api/events", params).then(setRows);
      }
      return;
    }
    get("/api/source", { ref: source }).then(setD).catch(() => setD({ ref: source, found: false }));
  }, [source]);
  if (!source) return null;
  return (
    <div className="fixed z-50 bottom-6 left-1/2 -translate-x-1/2 w-[min(720px,94vw)] max-h-[70vh] overflow-y-auto bg-card border border-ink rounded-kk p-5"
         role="dialog" aria-label="Source" style={{ backgroundImage: "repeating-linear-gradient(transparent 0 25px, var(--grid) 25px 26px)" }}>
      <div className="flex justify-between gap-4 items-start">
        <div>
          <div className="label">Source · <span className="mono">{source}</span></div>
          {d?.title && <div className="font-semibold mt-0.5">{d.title}{d.well ? ` — ${d.well}` : ""}</div>}
        </div>
        <button className="btn" onClick={() => openSource(null)} autoFocus>Close ✕</button>
      </div>
      {!d && <div className="mt-3 text-ink2">Loading…</div>}
      {d && d.found === false && <div className="mt-3">Source reference not found in the database.</div>}
      {d?.context && (
        <div className="mt-3 space-y-1">
          {d.context.map((c: any) => (
            <p key={c.locator} className={c.is_target ? "" : "text-ink2 small"}>
              <span className="mono label mr-2">{c.locator}</span>
              {c.is_target ? <mark style={{ background: "transparent", borderBottom: "2px solid var(--ink)" }}>{c.text}</mark> : c.text}
            </p>
          ))}
        </div>
      )}
      {d && !d.context && d.text && <p className="mt-3">{d.text}</p>}
      {d?.note && <p className="mt-2 label">{d.note}</p>}
      {d?.qkind && (
        <div className="mt-3 small">
          <div className="label">Reproducible query: {Object.entries(d.query).map(([k, v]) => `${k} = ${v}`).join(" · ")}</div>
          {rows && rows.map((r) => (
            <p key={r.id} className="mt-2"><span className="mono label">{r.well} · {hazardLabel[r.hazard]} · {r.md_m ? `${Math.round(r.md_m)} m` : "depth unknown"}</span><br />“{r.evidence}” <span className="mono label">{r.source_ref}</span></p>
          ))}
        </div>
      )}
      <div className="mt-3 label">
        {d?.report_date && <>Report date {d.report_date} · </>}{d?.licence && <>Licence {d.licence} · </>}
        {d?.url && <a className="link" href={d.url} target="_blank" rel="noreferrer">original record ↗</a>}
      </div>
    </div>
  );
}
