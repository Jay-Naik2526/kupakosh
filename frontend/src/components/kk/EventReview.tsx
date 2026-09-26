"use client";
import { useEffect, useState } from "react";
import { get, post } from "@/lib/api";
import { useApp } from "@/lib/state";
import { Drawer } from "@/components/kk/Drawer";
import { Register } from "@/components/kk/Register";
import { EmptyState } from "@/components/kk/EmptyState";
import { SourceFootnote } from "@/components/kk/SourceFootnote";
import { hazardLabel } from "@/lib/format";

const HAZARDS = Object.keys(hazardLabel);

/**
 * "Events to review (N) ▸" — opens a Drawer holding the human-review queue for extracted events
 * with Event.needs_review = true (SPEC.md §9.1). Kept behind a click so the host screen stays
 * within its 3-zone budget. Filters by hazard and by the app-wide country filter; each row's
 * evidence is shown verbatim with a SourceFootnote, and a reviewer can Confirm / Reject / Relabel.
 */
export function EventReviewDrawer() {
  const { user, country } = useApp();
  const [open, setOpen] = useState(false);
  const [hazard, setHazard] = useState<string>("");
  const [total, setTotal] = useState<number>(0);
  const [rows, setRows] = useState<any[]>([]);
  const [sel, setSel] = useState<number | null>(null);
  const [note, setNote] = useState("");
  const [relabelTo, setRelabelTo] = useState<string>("");
  const [busy, setBusy] = useState(false);

  const load = () =>
    get("/api/review/events", { hazard: hazard || undefined, country: country ?? undefined, limit: 100 })
      .then((r) => { setTotal(r.total); setRows(r.events); })
      .catch(() => { setTotal(0); setRows([]); });

  // Badge count always reflects the current country filter, even while the drawer is closed.
  useEffect(() => { load(); }, [country]); // eslint-disable-line
  useEffect(() => { if (open) load(); }, [open, hazard]); // eslint-disable-line

  const cur = sel !== null ? rows[sel] : null;
  useEffect(() => { setRelabelTo(cur?.hazard ?? ""); setNote(""); }, [cur?.id]); // eslint-disable-line

  const act = async (decision: "confirm" | "reject" | "relabel") => {
    if (!cur || !user) return;
    setBusy(true);
    try {
      await post(`/api/review/events/${cur.id}`, {
        decision, hazard: decision === "relabel" ? relabelTo : undefined, reviewer: user.name, note: note || null,
      });
      setSel(null); setNote("");
      await load();
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <button className="chip" onClick={() => setOpen(true)}>
        Events to review ({total.toLocaleString()}) ▸
      </button>
      <Drawer open={open} onClose={() => { setOpen(false); setSel(null); }} title="Events to review" width={780}>
        <div className="flex flex-wrap items-center gap-2 mb-3" role="group" aria-label="hazard filter">
          <span className="label">Hazard</span>
          <button className="chip" aria-pressed={hazard === ""} onClick={() => { setHazard(""); setSel(null); }}>All</button>
          {HAZARDS.map((h) => (
            <button key={h} className="chip" aria-pressed={hazard === h} onClick={() => { setHazard(h); setSel(null); }}>
              {hazardLabel[h]}
            </button>
          ))}
        </div>

        {rows.length === 0 ? (
          <EmptyState title="Nothing needs review" why="Every extracted event either cleared the confidence threshold or has already been checked by a person." />
        ) : (
          <div className="grid gap-6" style={{ gridTemplateColumns: cur ? "minmax(0,1.3fr) minmax(0,1fr)" : "1fr" }}>
            <Register
              rows={rows}
              onRow={(_, i) => setSel(i)}
              selected={sel}
              cols={[
                { key: "w", head: "Well", cell: (e: any) => e.well },
                { key: "h", head: "Hazard", cell: (e: any) => hazardLabel[e.hazard] ?? e.hazard },
                { key: "f", head: "Formation", cell: (e: any) => e.formation_label ?? "unknown" },
                { key: "md", head: "MD", num: true, cell: (e: any) => (e.md_m != null ? `${Math.round(e.md_m)} m` : "unknown") },
                { key: "c", head: "Confidence", num: true, cell: (e: any) => `${Math.round((e.confidence ?? 0) * 100)}%` },
              ]}
            />

            {cur && (
              <div className="bg-card border border-rule rounded-kk p-3 small space-y-3" aria-label="selected event">
                <div>
                  <div className="font-semibold">
                    {cur.well} <span className="label">· {cur.country ?? "unknown"}</span>
                  </div>
                  <p className="mt-1">
                    &ldquo;{cur.evidence_span ?? "no evidence text extracted"}&rdquo;
                    {cur.source_ref && <SourceFootnote refId={cur.source_ref} n={1} />}
                  </p>
                  <div className="label mono mt-1">{cur.source_ref}</div>
                </div>

                {!user && <p className="small">Select a demo user (top right) to record a decision.</p>}

                <textarea
                  className="input w-full" rows={2} placeholder="Reviewer note (optional)"
                  value={note} onChange={(e) => setNote(e.target.value)} disabled={!user || busy}
                />

                <div className="flex flex-wrap items-center gap-2">
                  <select className="input" value={relabelTo} onChange={(e) => setRelabelTo(e.target.value)} disabled={!user || busy} aria-label="relabel hazard">
                    {HAZARDS.map((h) => (
                      <option key={h} value={h}>{hazardLabel[h]}</option>
                    ))}
                  </select>
                  <button className="btn" disabled={!user || busy} onClick={() => act("relabel")}>Relabel</button>
                  <button className="btn btn-primary" disabled={!user || busy} onClick={() => act("confirm")}>Confirm</button>
                  <button className="btn" disabled={!user || busy} onClick={() => act("reject")}>Reject</button>
                </div>
              </div>
            )}
          </div>
        )}
      </Drawer>
    </>
  );
}
