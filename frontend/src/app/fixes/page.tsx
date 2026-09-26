"use client";
import { useEffect, useState } from "react";
import { get } from "@/lib/api";
import { actionLabel, hazardLabel, m, pretty } from "@/lib/format";
import { Register } from "@/components/kk/Register";
import { IntervalBar } from "@/components/kk/IntervalBar";
import { SourceFootnote } from "@/components/kk/SourceFootnote";
import { EmptyState } from "@/components/kk/EmptyState";
import { useApp } from "@/lib/state";
import { CountryFilter } from "@/components/kk/CountryFilter";

const OUT_GLYPH: Record<string, string> = { resolved: "✓ resolved", partial: "◐ partial", unresolved: "✕ unresolved", worsened: "▲ worsened", unknown: "? unknown" };

export default function Fixes() {
  const { wellId, country } = useApp();
  const [hazard, setHazard] = useState("stuck_pipe");
  const [formation, setFormation] = useState("");
  const [scope, setScope] = useState<"all" | "offsets">("all");
  const [forms, setForms] = useState<any[]>([]);
  const [L, setL] = useState<any>(null);
  const [open, setOpen] = useState<number | null>(null);
  const [eps, setEps] = useState<any[]>([]);

  useEffect(() => { get("/api/formations", { hazard, min_wells: 3, country: country ?? undefined }).then((f) => setForms(f.filter((x: any) => x.n_well_events > 0))); }, [hazard, country]);
  useEffect(() => {
    setOpen(null);
    get("/api/ledger", { hazard, formation: formation || undefined, well: scope === "offsets" && wellId ? wellId : undefined, country: country ?? undefined }).then(setL);
  }, [hazard, formation, scope, wellId, country]);
  const expand = (r: any, i: number) => {
    if (open === i) { setOpen(null); return; }
    setOpen(i); setEps([]);
    get("/api/episodes", { ids: r.episode_ids.slice(0, 40).join(","), limit: 40 }).then((e) => setEps(e.filter((x: any) => x.outcome !== "unknown").concat(e.filter((x: any) => x.outcome === "unknown"))));
  };
  const rows = (L?.rows ?? []).filter((r: any) => r.n > 0 || r.unknown_outcome > 0);

  return (
    <div>
      {/* Zone A — selectors */}
      <section className="flex flex-wrap items-center gap-3 rule-b pb-3" aria-label="selectors">
        <label className="label" htmlFor="hz">Hazard</label>
        <select id="hz" className="input" value={hazard} onChange={(e) => { setHazard(e.target.value); setFormation(""); }}>
          {Object.entries(hazardLabel).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <label className="label" htmlFor="fm">Formation</label>
        <select id="fm" className="input" value={formation} onChange={(e) => setFormation(e.target.value)}>
          <option value="">All formations</option>
          {forms.map((f) => <option key={f.formation} value={f.formation}>{f.label} ({f.n_well_events} wells)</option>)}
        </select>
        <span className="label">Scope</span>
        <button className="chip" aria-pressed={scope === "all"} onClick={() => setScope("all")}>All records</button>
        <button className="chip" aria-pressed={scope === "offsets"} onClick={() => setScope("offsets")} disabled={!wellId} title={wellId ? "" : "pick a well on Offsets first"}>Active well + offsets</button>
        <CountryFilter metric="episodes" />
        {L && <span className="ml-auto small">{L.n_episodes} episodes · {L.n_known_outcome} with a stated outcome</span>}
      </section>

      {/* Zone B — register */}
      <section className="mt-5" aria-label="what worked">
        {L && rows.length === 0 && <EmptyState title="No episodes" why="No recorded problem → action → outcome chain for this selection." />}
        {L && rows.length > 0 && (
          <Register rows={rows} onRow={expand} selected={open}
            caption="Ranked by lower bound of the success rate (Wilson, 95%). Resolved = 1, partial = ½. Episodes with no stated outcome are excluded from rates."
            cols={[
              { key: "fix", head: "Fix", cell: (r: any) => <span>{actionLabel[r.action] ?? r.action}{r.anecdotal && <span className="label"> · anecdotal (n &lt; 3)</span>}</span> },
              { key: "n", head: "Cases", num: true, cell: (r: any) => r.n },
              { key: "k", head: "Worked", num: true, cell: (r: any) => (Number.isInteger(r.k) ? r.k : r.k.toFixed(1)) },
              { key: "rate", head: "Success", num: true, cell: (r: any) => (r.rate === null ? "—" : `${Math.round(r.rate * 100)}%`) },
              { key: "lb", head: "Lower bound", num: true, cell: (r: any) => (r.lb === null ? "—" : `${Math.round(r.lb * 100)}%`) },
              { key: "bar", head: "", cell: (r: any) => <IntervalBar rate={r.rate} lb={r.lb} anecdotal={r.anecdotal} /> },
              { key: "med", head: "Median time", num: true, cell: (r: any) => (r.median_hours === null ? "unknown" : `${r.median_hours} h`) },
              { key: "worse", head: "Made worse", num: true, cell: (r: any) => (r.worsened > 0 ? <span style={{ color: "var(--hazard)", fontWeight: 600 }}>▲ {r.worsened}</span> : "0") },
              { key: "unk", head: "No outcome", num: true, cell: (r: any) => <span className="text-ink2">{r.unknown_outcome}</span> },
            ]} />
        )}
      </section>

      {/* Zone C — episode timeline for the expanded row */}
      {open !== null && rows[open] && (
        <section className="mt-6" aria-label="episodes">
          <h3 className="font-semibold">Episodes for “{actionLabel[rows[open].action]}” — {hazardLabel[hazard]}{formation ? ` in ${pretty(formation)}` : ""}</h3>
          {eps.length === 0 && <p className="label mt-2">Loading…</p>}
          <div className="mt-3 space-y-3">
            {eps.map((e) => (
              <div key={e.id} className="grid gap-3" style={{ gridTemplateColumns: "1fr 1fr 1fr" }}>
                <Card title={`Problem · ${e.well}`} sub={`${m(e.md_m)}${e.formation ? " · " + pretty(e.formation) : ""}${e.event.t ? " · " + e.event.t.slice(0, 10) : ""}`} text={e.event.text} refId={e.event.source_ref} />
                <Card title="Action" sub={e.actions.map((a: any) => actionLabel[a.type] ?? a.type).filter((v: any, i: number, s: any[]) => s.indexOf(v) === i).join(", ") || "none recorded"}
                  text={e.actions[0]?.detail ? `…${e.actions[0].detail}…` : ""} refId={e.actions[0]?.source_ref} />
                <Card title={`Outcome · ${OUT_GLYPH[e.outcome]}`} sub={e.hours_to_resolve ? `${e.hours_to_resolve} h later` : e.npt_hours ? `${e.npt_hours} h lost (stated)` : ""}
                  text={e.outcome_text ?? "Nothing in the window says either way."} refId={e.outcome_ref} danger={e.outcome === "worsened"} />
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function Card({ title, sub, text, refId, danger }: { title: string; sub?: string; text?: string; refId?: string | null; danger?: boolean }) {
  return (
    <div className="bg-card border border-rule rounded-kk p-3 small" style={danger ? { borderLeft: "3px solid var(--hazard)" } : undefined}>
      <div className="font-semibold">{title}</div>
      {sub && <div className="label">{sub}</div>}
      {text && <p className="mt-1">“{text.length > 260 ? text.slice(0, 260) + "…" : text}”{refId && <SourceFootnote refId={refId} n="src" />}</p>}
    </div>
  );
}
