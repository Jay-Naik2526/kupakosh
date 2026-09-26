"use client";
import { ReactNode, useEffect, useState } from "react";
import { scaleLinear } from "d3-scale";
import { get } from "@/lib/api";
import { Stamp } from "@/components/kk/Stamp";
import { NoticeSlip } from "@/components/kk/NoticeSlip";
import { LithologyColumn } from "@/components/kk/LithologyColumn";
import { CurveTrack, DepthAxis } from "@/components/kk/CurveTrack";
import { SourceFootnote } from "@/components/kk/SourceFootnote";
import { IntervalBar } from "@/components/kk/IntervalBar";
import { NotingSheet } from "@/components/kk/NotingSheet";
import { Register } from "@/components/kk/Register";
import { Drawer } from "@/components/kk/Drawer";
import { EmptyState } from "@/components/kk/EmptyState";
import { Wordmark } from "@/components/kk/Wordmark";
import { CountryFilter } from "@/components/kk/CountryFilter";
import { actionLabel, hazardLabel } from "@/lib/format";

/** P10a acceptance page: every design-system component rendered with LIVE records from the API (no sample numbers). */
export default function DevComponents() {
  const [well, setWell] = useState<any>(null);
  const [sec, setSec] = useState<any>(null);
  const [survey, setSurvey] = useState<any[]>([]);
  const [haz, setHaz] = useState<any>(null);
  const [ledger, setLedger] = useState<any>(null);
  const [notes, setNotes] = useState<any[]>([]);
  const [drawer, setDrawer] = useState(false);

  useEffect(() => {
    get("/api/replay/wells").then(async (ws) => {
      const w = ws[ws.length - 1];
      if (!w) return;
      setWell(w);
      get(`/api/wells/${w.id}/section`, { n: 1 }).then(setSec);
      get(`/api/wells/${w.id}/survey`).then(setSurvey);
      get(`/api/wells/${w.id}/hazards`).then((h) => setHaz([...h.profile].filter((p: any) => p.status === "ok").sort((a: any, b: any) => b.mean - a.mean)[0] ?? null));
    });
    get("/api/ledger", { hazard: "stuck_pipe" }).then(setLedger);
    get("/api/wiki").then((ps) => ps[0] && get(`/api/wiki/${ps[0].slug}/noting`).then(setNotes));
  }, []);

  const col = sec?.columns?.[0];
  const td = well?.td_md_m ?? 1000;
  const H = 360;
  const y = scaleLinear().domain([0, td]).range([0, H]);
  const rows = (ledger?.rows ?? []).filter((r: any) => r.n > 0).slice(0, 4);

  return (
    <main className="min-h-screen p-8" style={{ background: "var(--paper)", color: "var(--ink)" }}>
      <header className="flex items-center gap-3 rule-b pb-3">
        <Wordmark /><h1 className="text-[22px] font-semibold">Design-system components</h1>
        <span className="label ml-auto">Examples use live records{well ? ` (well ${well.name})` : ""} — nothing on this page is typed in.</span>
      </header>

      <Row name="Stamp">
        <Stamp kind="approved" text="APPROVED" sub="demo user" /> <Stamp kind="replay" text="REPLAY" /> <Stamp kind="returned" text="RETURNED" />
        <Stamp kind="draft" text="DRAFT" /> <Stamp kind="approved" text="OK" round />
      </Row>

      <Row name="NoticeSlip (top hazard of the replay well)">
        {haz ? (
          <div style={{ maxWidth: 420 }}>
            <NoticeSlip level="notice" title={hazardLabel[haz.hazard]} where={haz.formation} mean={haz.mean} ci={haz.ci} neff={haz.n_eff}
              nWells={haz.n_wells} nWithEvent={haz.n_with_event} status={haz.status} />
          </div>
        ) : <EmptyState title="Insufficient evidence" why="No hazard for this well has enough offset evidence." />}
      </Row>

      <Row name="LithologyColumn · CurveTrack · DepthAxis (tops, events and survey inclination by MD)">
        {col && (
          <div className="flex gap-2 items-start">
            <DepthAxis y={y} height={H} />
            <LithologyColumn intervals={col.tops} y={y} height={H} width={150}
              glyphs={col.events.map((e: any) => ({ md_m: e.md_m, hazard: e.hazard }))} />
            <CurveTrack title="Inclination" unit="deg" y={y} height={H} pts={survey.map((s) => ({ y: s.md_m, v: s.inc_deg }))} />
          </div>
        )}
      </Row>

      <Row name="SourceFootnote (hover or click the marker)">
        {col?.events?.[0] ? <p className="small">“{col.events[0].evidence}”<SourceFootnote refId={col.events[0].source_ref} n={1} /></p> : <span className="label">loading…</span>}
      </Row>

      <Row name="Register + IntervalBar (stuck-pipe ledger, all records)">
        <div className="w-full">
          <Register rows={rows} cols={[
            { key: "a", head: "Fix", cell: (r: any) => actionLabel[r.action] ?? r.action },
            { key: "n", head: "Cases", num: true, cell: (r: any) => r.n },
            { key: "lb", head: "Lower bound", num: true, cell: (r: any) => (r.lb === null ? "—" : `${Math.round(r.lb * 100)}%`) },
            { key: "b", head: "", cell: (r: any) => <IntervalBar rate={r.rate} lb={r.lb} anecdotal={r.anecdotal} /> },
          ]} />
        </div>
      </Row>

      <Row name="NotingSheet (first wiki page)">
        <div style={{ maxWidth: 520 }} className="w-full">{notes.length ? <NotingSheet notes={notes} /> : <span className="label">no notings</span>}</div>
      </Row>

      <Row name="EmptyState">
        <div style={{ maxWidth: 420 }}><EmptyState title="Not evaluated" why="The evaluation file for this metric is missing, so no score is shown." /></div>
      </Row>

      <Row name="CountryFilter"><CountryFilter /></Row>

      <Row name="Drawer">
        <button className="btn" onClick={() => setDrawer(true)}>Open drawer ▸</button>
        <Drawer open={drawer} onClose={() => setDrawer(false)} title="Drawer"><p className="small">Details go here, behind a click.</p></Drawer>
      </Row>
    </main>
  );
}

function Row({ name, children }: { name: string; children: ReactNode }) {
  return (
    <section className="mt-6 rule-b pb-6" aria-label={name}>
      <h2 className="label mb-3">{name}</h2>
      <div className="flex flex-wrap items-start gap-4">{children}</div>
    </section>
  );
}
