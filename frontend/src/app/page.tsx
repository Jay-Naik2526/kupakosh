"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { scaleLinear } from "d3-scale";
import { get, WS } from "@/lib/api";
import { useApp } from "@/lib/state";
import { actionLabel, m, pct } from "@/lib/format";
import { Stamp } from "@/components/kk/Stamp";
import { NoticeSlip } from "@/components/kk/NoticeSlip";
import { LithologyColumn } from "@/components/kk/LithologyColumn";
import { CurveTrack, DepthAxis, Pt } from "@/components/kk/CurveTrack";
import { IntervalBar } from "@/components/kk/IntervalBar";
import { Drawer } from "@/components/kk/Drawer";
import { EmptyState } from "@/components/kk/EmptyState";
import { MiniMap } from "@/components/kk/MiniMap";
import { WellPicker } from "@/components/kk/WellPicker";

type Sample = { t: string; md_m: number | null; bit_md_m: number | null; torque: number | null; pit_vol: number | null; mw_ppg: number | null; flow_in: number | null; spp: number | null; hookload: number | null; flag?: boolean };
const H = 520;
const WINDOW_ABOVE = 260, WINDOW_BELOW = 190;

export default function Command() {
  const { wellId, setWellId, lang, openSource, ready } = useApp();
  const [well, setWell] = useState<any>(null);
  const [survey, setSurvey] = useState<any[]>([]);
  const [range, setRange] = useState<any>(null);
  const [speed, setSpeed] = useState(120);
  const [startMd, setStartMd] = useState<number | "">("");
  const [running, setRunning] = useState(false);
  const [samples, setSamples] = useState<Sample[]>([]);
  const [la, setLa] = useState<any>(null);
  const [anomaly, setAnomaly] = useState<any>(null);
  const [rig, setRig] = useState(false);
  const [drawer, setDrawer] = useState<null | "offsets" | "alerts">(null);
  const [offsets, setOffsets] = useState<any[]>([]);
  const [ended, setEnded] = useState(false);
  const ws = useRef<WebSocket | null>(null);

  // default to a replayable well
  useEffect(() => { if (!ready) return; get("/api/replay/wells").then((ws) => { if (!ws.some((w: any) => w.id === wellId) && ws.length) setWellId(ws.find((w: any) => w.name.startsWith("16B"))?.id ?? ws[0].id); }); }, [ready]); // eslint-disable-line
  useEffect(() => {
    if (!wellId) return;
    stop(); setSamples([]); setLa(null); setEnded(false);
    get(`/api/wells/${wellId}`).then(setWell);
    get(`/api/wells/${wellId}/survey`).then(setSurvey);
    get(`/api/replay/${wellId}/range`).then(setRange);
    get(`/api/wells/${wellId}/offsets`).then((o) => setOffsets(o.offsets));
  }, [wellId]); // eslint-disable-line

  const stop = useCallback(() => { ws.current?.close(); ws.current = null; setRunning(false); }, []);
  const start = () => {
    if (!wellId) return;
    stop(); setSamples([]); setLa(null); setEnded(false);
    const s = new WebSocket(`${WS}/ws/replay/${wellId}?speed=${speed}${startMd !== "" ? `&start_md=${startMd}` : ""}`);
    s.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.type === "samples") {
        const batch: Sample[] = msg.samples.map((x: any, i: number) => ({ ...x, flag: !!msg.anomaly && i === msg.samples.length - 1 }));
        setSamples((prev) => [...prev, ...batch].slice(-4000));
        if (msg.anomaly) setAnomaly({ ...msg.anomaly, t: msg.t });
        if (msg.lookahead) setLa(msg.lookahead);
      } else if (msg.type === "end") { setEnded(true); setRunning(false); }
    };
    s.onclose = () => setRunning(false);
    ws.current = s; setRunning(true);
  };
  useEffect(() => () => stop(), [stop]);

  const last = samples[samples.length - 1];
  const bit = last ? (last.md_m ?? null) : null;
  const tvd = useMemo(() => interpTvd(survey, bit), [survey, bit]);
  const y = useMemo(() => {
    const c = bit ?? (startMd === "" ? 0 : Number(startMd));
    const lo = Math.max(0, c - WINDOW_ABOVE);
    return scaleLinear().domain([lo, lo + WINDOW_ABOVE + WINDOW_BELOW]).range([0, H]);
  }, [bit, startMd]);
  const tops = well?.tops?.filter((t: any) => t.level !== "GROUP" || !well.tops.some((x: any) => x.level === "FORMATION")) ?? [];
  // mud-log convention: plot a value once per new hole depth (samples while off-bottom / tripping are skipped)
  const drilled = useMemo(() => {
    const out: Sample[] = []; let maxMd = -1;
    for (const s of samples) if (s.md_m !== null && s.md_m > maxMd + 0.05) { out.push(s); maxMd = s.md_m; } else if (s.flag && out.length) out[out.length - 1] = { ...out[out.length - 1], flag: true };
    return out;
  }, [samples]);
  const trackPts = (k: keyof Sample): Pt[] => drilled.map((s) => ({ y: s.md_m as number, v: (s[k] as number) ?? null, flag: s.flag }));
  const top = la?.alerts?.[0] ?? la?.notices?.[0] ?? null;
  const more = (la?.alerts?.length ?? 0) + (la?.notices?.length ?? 0) - (top ? 1 : 0);
  const nextTop = la?.ahead?.[0] ?? null;
  const hazardTarget = top && !top.in_formation ? { md: top.distance_m + (bit ?? 0), text: top.formation_label } : nextTop ? { md: nextTop.top_md_m, text: nextTop.label } : null;
  const jumpTargets: any[] = tops.filter((t: any) => t.top_md_m > 50);

  return (
    <div data-rig={rig ? "on" : "off"}>
      <div className="rig-scope" style={rig ? { background: "var(--paper)", color: "var(--ink)", padding: 12, borderRadius: 2 } : undefined}>
        {/* Zone A — status line */}
        <section aria-label="status" className="flex flex-wrap items-center gap-x-5 gap-y-2 rule-b pb-3">
          <WellPicker onlyReplay label="Well" />
          <Stamp kind="replay" text={lang === "hi" ? "पुनःचलन · REPLAY" : "REPLAY"} sub="recorded data, not live" />
          <div><span className="label">Bit depth </span><span className="num" style={{ fontSize: rig ? 26 : 20 }}>{bit !== null ? `${Math.round(bit).toLocaleString()} m MD` : "—"}</span>
            <span className="label"> · </span><span className="num">{tvd !== null ? `${Math.round(tvd).toLocaleString()} m TVD` : "TVD unknown"}</span></div>
          <div><span className="label">Formation </span><span className="font-semibold">{la?.current?.label ?? "—"}</span></div>
          <div className="small label">{last ? new Date(last.t).toLocaleString("en-IN") : range?.t_min ? `recorded ${range.t_min.slice(0, 10)} → ${range.t_max.slice(0, 10)}` : ""}</div>
          <div className="ml-auto flex items-center gap-2 flex-wrap">
            <label className="label" htmlFor="startmd">Start at</label>
            <select id="startmd" className="input" value={startMd} onChange={(e) => setStartMd(e.target.value === "" ? "" : Number(e.target.value))}>
              <option value="">spud</option>
              {jumpTargets.map((t: any) => <option key={t.formation} value={Math.max(0, Math.round(t.top_md_m - 150))}>150 m above {t.label} ({Math.round(t.top_md_m - 150)} m)</option>)}
              {[500, 1000, 1500, 2000, 2500, 3000].map((d) => <option key={d} value={d}>{d} m</option>)}
            </select>
            <label className="label" htmlFor="spd">Speed</label>
            <select id="spd" className="input" value={speed} onChange={(e) => setSpeed(Number(e.target.value))}>
              {[30, 60, 120, 300, 600].map((s) => <option key={s} value={s}>{s}×</option>)}
            </select>
            {running ? <button className="btn" onClick={stop}>■ Pause</button> : <button className="btn btn-primary" onClick={start} disabled={!wellId}>▶ Start replay</button>}
            <button className="chip" aria-pressed={rig} onClick={() => setRig(!rig)}>Rig mode</button>
          </div>
        </section>

        {!wellId && <div className="mt-6"><EmptyState title="No well selected" why="Choose a well that has recorded rig-sensor data to replay." /></div>}
        {wellId && (
          <div className="grid gap-8 mt-5" style={{ gridTemplateColumns: "minmax(0, 3fr) minmax(0, 2fr)" }}>
            {/* Zone B — mud-log view */}
            <section aria-label="mud log" className="overflow-x-auto">
              <div className="flex gap-3 items-start">
                <div><div className="small rule-b pb-0.5 mb-1">m MD</div><DepthAxis y={y} height={H} /></div>
                <div><div className="small rule-b pb-0.5 mb-1">Formation</div>
                  <LithologyColumn intervals={tops} y={y} height={H} width={132} bit={bit} target={hazardTarget} /></div>
                <CurveTrack title="Torque" unit="kft·lb" pts={trackPts("torque")} y={y} height={H} width={rig ? 150 : 118} />
                <CurveTrack title="Pit volume" unit="bbl" pts={trackPts("pit_vol")} y={y} height={H} width={rig ? 150 : 118} />
                <CurveTrack title="Mud weight" unit="ppg" pts={trackPts("mw_ppg")} y={y} height={H} width={rig ? 120 : 96} />
              </div>
              <p className="label mt-2">Sensor: {well?.name} Pason rig data (CC-BY 4.0). Mud weight: daily report mud checks. Red dots: abnormal-behaviour samples.
                {anomaly && <> Last abnormal behaviour: <b>{anomaly.channels.join(", ")}</b> at {anomaly.t?.slice(11, 16)}.</>}</p>
              {ended && <p className="small mt-1">Replay reached the end of the recorded data.</p>}
            </section>

            {/* Zone C — top look-ahead hazard */}
            <section aria-label="look-ahead">
              {!la && <EmptyState title={running ? "Reading ahead…" : "Replay not started"} why={`Start the replay. Every tick, Kupakosh looks ${150} m ahead of the bit and checks offset-well records for the formations coming up.`} />}
              {la && !top && <EmptyState title="Nothing recorded ahead" why={`No offset well recorded a problem in ${la.current?.label ?? "this formation"} or in the formations within 150 m below the bit (${la.n_offsets} offsets in radius). Absence of a record is not proof of safety.`} />}
              {top && (
                <NoticeSlip level={top.level} title={`${top.label} · ${top.formation_label}`}
                  where={top.in_formation ? "in the current formation" : `in ${Math.round(top.distance_m)} m`}
                  mean={top.mean} ci={top.ci} neff={top.n_eff} nWells={top.n_wells} nWithEvent={top.n_with_event} status={top.status}
                  actions={<>
                    <button className="btn" onClick={() => { const e = top.evidence.find((x: any) => x.events.length); if (e) openSource(e.events[0].source_ref); }}>{lang === "hi" ? "स्रोत देखें" : "View sources"}</button>
                    <Link className="btn" href={`/wiki?page=${encodeURIComponent("formations/" + slugF(top.formation))}`}>{lang === "hi" ? "ज्ञानकोश खोलें" : "Open wiki"}</Link>
                  </>}>
                  <div className="label mb-1">What worked before {top.fixes?.scope ? `(${top.fixes.scope})` : ""}</div>
                  {(top.fixes?.rows ?? []).length === 0 && <div className="small text-ink2">No episode with a stated outcome.</div>}
                  <ul className="space-y-1">
                    {(top.fixes?.rows ?? []).map((r: any) => (
                      <li key={r.action} className="grid items-center gap-x-3 small rule-b pb-1" style={{ gridTemplateColumns: "minmax(0,1fr) auto auto" }}>
                        <span>{actionLabel[r.action] ?? r.action}{r.anecdotal ? <span className="label"> · anecdotal</span> : null}
                          {r.worsened > 0 && <span className="num" style={{ color: "var(--hazard)" }}> · ▲ {r.worsened} made worse</span>}</span>
                        <span className="num">{fmtK(r.k)}/{r.n}</span>
                        <IntervalBar rate={r.rate} lb={r.lb} width={96} anecdotal={r.anecdotal} />
                      </li>
                    ))}
                  </ul>
                  <div className="label mt-2">Evidence: {top.evidence.filter((e: any) => e.y).map((e: any) => e.name).join(", ") || "none"} · prior {pct(top.prior.base_rate)} ({top.prior.scope.replace("_", " ")})</div>
                </NoticeSlip>
              )}
              <div className="flex gap-2 mt-4 flex-wrap">
                <button className="btn" onClick={() => setDrawer("offsets")}>Offset wells ({offsets.length}) ▸</button>
                {more > 0 && <button className="btn" onClick={() => setDrawer("alerts")}>Further alerts ({more}) ▸</button>}
              </div>
            </section>
          </div>
        )}
      </div>

      <Drawer open={drawer === "offsets"} onClose={() => setDrawer(null)} title={`Offset wells within ${m(10000)}`} width={560}>
        {well && <MiniMap center={[well.lat, well.lon]} radius_m={10000} height={260}
          wells={[{ ...well, active: true }, ...offsets.map((o) => ({ id: o.well_id, name: o.name, lat: o.lat, lon: o.lon, documented: o.documented, n_events: o.n_events }))]} />}
        <ul className="mt-3">
          {offsets.map((o) => (
            <li key={o.well_id} className="rule-b py-2 small flex justify-between gap-3">
              <span>{o.name} <span className="label">{o.documented ? "reports" : "no reports"} · {o.n_events} events</span></span>
              <span className="num">{o.raw.distance_m.toLocaleString()} m · sim {o.sim.toFixed(2)}</span>
            </li>
          ))}
          {offsets.length === 0 && <li className="small">No wells within the radius.</li>}
        </ul>
      </Drawer>
      <Drawer open={drawer === "alerts"} onClose={() => setDrawer(null)} title="All look-ahead items">
        {[...(la?.alerts ?? []), ...(la?.notices ?? [])].slice(1).map((a: any, i: number) => (
          <div key={i} className="rule-b py-2 small">
            <div className="font-semibold">{a.label} · {a.formation_label} <span className="label">{a.level}</span></div>
            <div>{a.status === "ok" ? `${pct(a.mean)} (range ${pct(a.ci[0])}–${pct(a.ci[1])})` : "insufficient evidence"} · n_eff {a.n_eff.toFixed(1)} · {a.in_formation ? "current formation" : `in ${Math.round(a.distance_m)} m`}</div>
          </div>
        ))}
      </Drawer>
    </div>
  );
}

function fmtK(k: number) { return Number.isInteger(k) ? String(k) : k.toFixed(1); }
function slugF(f: string) { return f.toLowerCase().replace(/ø/g, "o").replace(/å/g, "a").replace(/æ/g, "ae").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""); }
function interpTvd(sv: any[], md: number | null): number | null {
  if (md === null || !sv.length) return null;
  if (md <= sv[0].md_m) return md;
  for (let i = 1; i < sv.length; i++) if (sv[i].md_m >= md) {
    const a = sv[i - 1], b = sv[i], f = (md - a.md_m) / (b.md_m - a.md_m || 1);
    return a.tvd_m + f * (b.tvd_m - a.tvd_m);
  }
  return null;
}
