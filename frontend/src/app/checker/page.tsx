"use client";
import { useEffect, useState } from "react";
import { get, post } from "@/lib/api";
import { useApp } from "@/lib/state";
import { Register } from "@/components/kk/Register";
import { EmptyState } from "@/components/kk/EmptyState";

const RULE: Record<string, string> = {
  R1_ddr_loss_vs_pit: "DDR losses vs sensor pit volume",
  R2_casing_shoe: "Casing shoe: text vs table",
  R3_formation_top: "Formation top: text vs table",
  R4_same_quantity_differs: "Same quantity, different reports",
  R6_ddr_depth_vs_sensor: "Report depth vs sensor depth",
};

export default function Checker() {
  const { user } = useApp();
  const [flags, setFlags] = useState<any[]>([]);
  const [status, setStatus] = useState<string>("open");
  const [sel, setSel] = useState<number | null>(null);
  const [a, setA] = useState<any>(null);
  const [b, setB] = useState<any>(null);
  const [note, setNote] = useState("");
  const [trust, setTrust] = useState<number | null>(null);
  const load = () => get("/api/audit").then(setFlags);
  useEffect(() => { load(); get("/api/wiki").then((p) => { const v = p.map((x: any) => x.trust).filter((x: any) => x !== null); setTrust(v.length ? v.reduce((s: number, x: number) => s + x, 0) / v.length : null); }); }, []);
  const rows = flags.filter((f) => (status === "open" ? f.status === "open" : f.status !== "open"));
  const cur = sel !== null ? rows[sel] : null;
  useEffect(() => {
    setA(null); setB(null);
    if (!cur) return;
    get("/api/source", { ref: cur.ref_a }).then(setA);
    get("/api/source", { ref: cur.ref_b }).then(setB);
  }, [cur?.id]); // eslint-disable-line
  const resolve = async (decision: string) => {
    if (!cur || !user) return;
    await post(`/api/audit/${cur.id}/resolve`, { decision, reviewer: user.name, note: note || null });
    setNote(""); setSel(null); load();
  };
  const open = flags.filter((f) => f.status === "open").length;

  return (
    <div>
      {/* Zone A — summary line */}
      <section className="flex flex-wrap gap-6 items-baseline rule-b pb-3" aria-label="summary">
        <div><span className="label">Open</span> <span className="num text-2xl">{open}</span></div>
        <div><span className="label">Resolved</span> <span className="num text-2xl">{flags.length - open}</span></div>
        <div><span className="label">Avg trust (wiki pages)</span> <span className="num text-2xl">{trust === null ? "—" : `${Math.round(trust * 100)}%`}</span></div>
        <div className="ml-auto flex gap-1">
          <button className="chip" aria-pressed={status === "open"} onClick={() => { setStatus("open"); setSel(null); }}>Open</button>
          <button className="chip" aria-pressed={status !== "open"} onClick={() => { setStatus("done"); setSel(null); }}>Resolved</button>
        </div>
      </section>

      <div className="grid gap-8 mt-5" style={{ gridTemplateColumns: cur ? "minmax(0,1fr) minmax(0,1.2fr)" : "1fr" }}>
        {/* Zone B — conflicts register */}
        <section aria-label="conflicts">
          {rows.length === 0 ? <EmptyState title={status === "open" ? "No open conflicts" : "Nothing resolved yet"} why="The auditor compares report text, Sodir tables and rig sensor data; each disagreement beyond tolerance becomes a row here." /> :
            <Register rows={rows} onRow={(_, i) => setSel(i)} selected={sel} cols={[
              { key: "w", head: "Well", cell: (f: any) => f.well },
              { key: "r", head: "Check", cell: (f: any) => RULE[f.rule] ?? f.rule },
              { key: "d", head: "Difference", num: true, cell: (f: any) => f.delta },
              { key: "s", head: "Severity", cell: (f: any) => f.severity === "medium" ? <b>● medium</b> : "○ low" },
              ...(status !== "open" ? [{ key: "st", head: "Decision", cell: (f: any) => `${f.status} — ${f.resolved_by}` }] : []),
            ]} />}
        </section>

        {/* Zone C — selected conflict, two excerpts side by side */}
        {cur && (
          <section aria-label="selected conflict">
            <h3 className="font-semibold">{RULE[cur.rule] ?? cur.rule} — {cur.well} <span className="label">({cur.delta})</span></h3>
            <div className="grid grid-cols-2 gap-3 mt-3">
              {[{ k: "A", claim: cur.claim_a, ref: cur.ref_a, src: a }, { k: "B", claim: cur.claim_b, ref: cur.ref_b, src: b }].map((s) => (
                <div key={s.k} className="bg-card border border-rule rounded-kk p-3 small">
                  <div className="font-semibold">Source {s.k}</div>
                  <p className="mt-1">{s.claim}</p>
                  {s.src?.text && s.src.text !== s.claim && <p className="mt-2 text-ink2 italic">“{s.src.text}”</p>}
                  <div className="label mono mt-2 break-all">{s.ref}</div>
                  {s.src?.title && <div className="label">{s.src.title}{s.src.report_date ? ` · ${s.src.report_date}` : ""}</div>}
                </div>
              ))}
            </div>
            {cur.status === "open" ? (
              <div className="mt-4 space-y-2">
                {!user && <p className="small">Select a demo user (top right) to record a decision.</p>}
                <textarea className="input w-full" rows={2} placeholder="Reviewer note" value={note} onChange={(e) => setNote(e.target.value)} disabled={!user} />
                <div className="flex gap-2">
                  <button className="btn" disabled={!user} onClick={() => resolve("accept_a")}>Accept A</button>
                  <button className="btn" disabled={!user} onClick={() => resolve("accept_b")}>Accept B</button>
                  <button className="btn" disabled={!user} onClick={() => resolve("uncertain")}>Mark uncertain</button>
                </div>
              </div>
            ) : <p className="mt-3 small">Decision: <b>{cur.status}</b> by {cur.resolved_by}{cur.reviewer_note ? ` — “${cur.reviewer_note}”` : ""}</p>}
          </section>
        )}
      </div>
    </div>
  );
}
