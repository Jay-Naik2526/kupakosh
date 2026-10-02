"use client";
import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { Box, Play, Pause, Gauge, Ruler, Layers, Clock, Radio } from "lucide-react";
import { formationColor } from "@/lib/palette";
import { scaleLinear } from "d3-scale";
import { get, post, WS } from "@/lib/api";
import { useApp } from "@/lib/state";
import { Lang } from "@/lib/i18n";
import { actionText, m, pct } from "@/lib/format";
import { t } from "@/lib/i18n";
import { Card } from "@/components/v2/ui";
import { NoticeSlip } from "@/components/kk/NoticeSlip";
import { LithologyColumn } from "@/components/kk/LithologyColumn";
import { CurveTrack, DepthAxis, Pt } from "@/components/kk/CurveTrack";
import { IntervalBar } from "@/components/kk/IntervalBar";
import { Drawer } from "@/components/kk/Drawer";
import { EmptyState } from "@/components/kk/EmptyState";
import { WellPicker } from "@/components/kk/WellPicker";
import { HandoverNote } from "@/components/v2/HandoverNote";
import { AlertFeedback } from "@/components/v2/AlertFeedback";
const Subsurface3D = dynamic(() => import("@/components/v2/Subsurface3D").then((m) => m.Subsurface3D), { ssr: false, loading: () => <div className="kk-card" style={{ minHeight: 240, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-2)" }}>Loading…</div> });
const MiniMap = dynamic(() => import("@/components/kk/MiniMap").then((m) => m.MiniMap), { ssr: false, loading: () => <div className="kk-card" style={{ minHeight: 240, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-2)" }}>Loading…</div> });

type Sample = { t: string; md_m: number | null; bit_md_m: number | null; torque: number | null; pit_vol: number | null; mw_ppg: number | null; flow_in: number | null; spp: number | null; hookload: number | null; flag?: boolean };
const H = 520;
const WINDOW_ABOVE = 260, WINDOW_BELOW = 190;

/** Bilingual copy local to this page (docs/PLAN_V2.md scope keeps lib/i18n.ts to nav keys so parallel agents don't collide). */
const tr = (lang: Lang, en: string, hi: string) => (lang === "hi" ? hi : en);

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
  const [show3d, setShow3d] = useState(false);
  const [drawer, setDrawer] = useState<null | "offsets" | "alerts" | "handover" | "connect">(null);
  const [mode, setMode] = useState<"replay" | "live">("replay");
  const [feed, setFeed] = useState<any>(null); // live feed info from the server (source, freshness, channels)
  const [liveErr, setLiveErr] = useState<string | null>(null);
  const [offsets, setOffsets] = useState<any[]>([]);
  const [handoverMd, setHandoverMd] = useState(0); // bit depth frozen when the note is opened (the replay keeps moving)
  const [ended, setEnded] = useState(false);
  const ws = useRef<WebSocket | null>(null);

  // default to a replayable well
  useEffect(() => { if (!ready) return; get("/api/replay/wells").then((ws) => { if (!ws.some((w: any) => w.id === wellId) && ws.length) setWellId(ws.find((w: any) => w.name.startsWith("16B"))?.id ?? ws[0].id); }); }, [ready]); // eslint-disable-line
  useEffect(() => {
    if (!wellId) return;
    stop(); setSamples([]); setLa(null); setEnded(false); setFeed(null);
    get(`/api/wells/${wellId}`).then(setWell);
    get(`/api/wells/${wellId}/survey`).then(setSurvey);
    get(`/api/replay/${wellId}/range`).then(setRange);
    get(`/api/wells/${wellId}/offsets`).then((o) => setOffsets(o.offsets));
  }, [wellId]); // eslint-disable-line

  const stop = useCallback(() => { ws.current?.close(); ws.current = null; setRunning(false); }, []);
  const start = () => {
    if (!wellId) return;
    stop(); setSamples([]); setLa(null); setEnded(false); setFeed(null); setLiveErr(null);
    const s = new WebSocket(mode === "live" ? `${WS}/ws/live/${wellId}`
      : `${WS}/ws/replay/${wellId}?speed=${speed}${startMd !== "" ? `&start_md=${startMd}` : ""}`);
    s.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.feed !== undefined) setFeed(msg.feed);
      if (msg.type === "snapshot") {
        setSamples(msg.samples ?? []);
        if (msg.lookahead) setLa(msg.lookahead);
      } else if (msg.type === "samples") {
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
  // live: ask the server to re-send a recorded well as WITSML documents (labelled demo source), then watch it arrive
  const startDemo = async () => {
    if (!wellId) return;
    if (!running) start();
    try { await post(`/api/live/${wellId}/demo`, { speed, start_md: startMd === "" ? null : startMd }); setLiveErr(null); }
    catch (e: any) { setLiveErr(String(e.message ?? e)); }
  };
  const stopDemo = () => { post("/api/live/demo/stop", {}).catch(() => {}); };

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

  // step hint: 1 pick a well/depth -> 2 start replay -> 3 watch the alert
  const step = !wellId ? 1 : running || samples.length > 0 ? 3 : 2;

  return (
    <div data-rig={rig ? "on" : "off"}>
      <div className="rig-scope" style={rig ? { background: "var(--paper)", color: "var(--ink)", padding: 16, borderRadius: "var(--radius-lg, 12px)" } : undefined}>
        {/* Zone A — step hint + status + controls */}
        <section aria-label="status" className="mb-5">
          <Card>
            <StepHint step={step} lang={lang} live={mode === "live"} />
            <div className="flex flex-wrap items-end gap-x-6 gap-y-3 mt-4">
              <WellPicker onlyReplay label={tr(lang, "Replay well (has sensor data)", "पुनःचलन कूप (सेंसर डेटा सहित)")} />
              {mode === "replay" ? <ReplayBadge label={t("replay", lang)} sub={t("cmdReplaySub", lang)} />
                : <LiveBadge feed={feed} connected={running} lang={lang} />}
              <StatusFigure label={t("bitDepth", lang)} value={bit !== null ? `${Math.round(bit).toLocaleString()} m MD` : "—"} rig={rig} icon={Gauge} />
              <StatusFigure label="TVD" value={tvd !== null ? `${Math.round(tvd).toLocaleString()} m` : "—"} rig={rig} icon={Ruler} />
              <StatusFigure label={t("formationLabel", lang)} value={la?.current?.label ?? "—"} rig={rig} mono={false} icon={Layers} valueColor={la?.current?.label ? formationColor(la.current.label) : undefined} />
              <StatusFigure label={tr(lang, "Time", "समय")} value={last ? new Date(last.t).toLocaleString("en-IN") : range?.t_min ? `${range.t_min.slice(0, 10)} → ${range.t_max.slice(0, 10)}` : "—"} rig={rig} mono={false} icon={Clock} />
            </div>
            <div className="flex items-end gap-3 flex-wrap mt-4 pt-4" style={{ borderTop: "1px solid var(--border)" }}>
              <div role="group" aria-label={tr(lang, "data source", "डेटा स्रोत")}>
                <div className="label mb-1">{tr(lang, "Data", "डेटा")}</div>
                <div className="flex gap-1">
                  {(["replay", "live"] as const).map((md) => (
                    <button key={md} className="chip" aria-pressed={mode === md}
                      onClick={() => { if (mode !== md) { stop(); setSamples([]); setLa(null); setFeed(null); setEnded(false); setMode(md); } }}>
                      {md === "replay" ? tr(lang, "Replay (recorded)", "पुनःचलन (दर्ज)") : <><Radio size={13} className="inline -mt-0.5 mr-1" aria-hidden="true" />{tr(lang, "Live feed (WITSML)", "लाइव फ़ीड (WITSML)")}</>}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="label block mb-1" htmlFor="startmd">{t("startAt", lang)}</label>
                <select id="startmd" className="input" value={startMd} onChange={(e) => setStartMd(e.target.value === "" ? "" : Number(e.target.value))}>
                  <option value="">{t("spudOpt", lang)}</option>
                  {jumpTargets.map((jt: any) => <option key={jt.formation} value={Math.max(0, Math.round(jt.top_md_m - 150))}>150 m above {jt.label} ({Math.round(jt.top_md_m - 150)} m)</option>)}
                  {[500, 1000, 1500, 2000, 2500, 3000].map((d) => <option key={d} value={d}>{d} m</option>)}
                </select>
              </div>
              <div>
                <label className="label block mb-1" htmlFor="spd">{t("speedLabel", lang)}</label>
                <select id="spd" className="input" value={speed} onChange={(e) => setSpeed(Number(e.target.value))}>
                  {[30, 60, 120, 300, 600].map((s) => <option key={s} value={s}>{s}×</option>)}
                </select>
              </div>
              {mode === "replay" && (running
                ? <button className="btn" onClick={stop}><Pause size={14} className="inline -mt-0.5 mr-1" aria-hidden="true" />{t("pauseBtn", lang)}</button>
                : <button className="btn btn-primary" onClick={start} disabled={!wellId}><Play size={14} className="inline -mt-0.5 mr-1" aria-hidden="true" />{t("startReplay", lang)}</button>)}
              {mode === "live" && <>
                {running
                  ? <button className="btn" onClick={stop}>{tr(lang, "Disconnect", "डिस्कनेक्ट")}</button>
                  : <button className="btn" onClick={start} disabled={!wellId}>{tr(lang, "Connect to live feed", "लाइव फ़ीड से जुड़ें")}</button>}
                {feed?.demo && feed && !feed.stale
                  ? <button className="btn" onClick={stopDemo}>{tr(lang, "Stop demo feeder", "डेमो फ़ीडर रोकें")}</button>
                  : <button className="btn btn-primary" onClick={startDemo} disabled={!wellId}><Play size={14} className="inline -mt-0.5 mr-1" aria-hidden="true" />{tr(lang, "Start demo feeder", "डेमो फ़ीडर शुरू करें")}</button>}
                <button className="btn" onClick={() => setDrawer("connect")}>{tr(lang, "How a rig system connects", "रिग सिस्टम कैसे जुड़ता है")} ▸</button>
              </>}
              <button className="chip" aria-pressed={rig} onClick={() => setRig(!rig)}>{t("rigMode", lang)}</button>
              <button className="chip ml-auto" aria-pressed={show3d} onClick={() => setShow3d((s) => !s)}>
                <Box size={13} className="inline -mt-0.5 mr-1" aria-hidden="true" />{tr(lang, "3D mini-view", "3D लघु-दृश्य")}
              </button>
            </div>
            {mode === "live" && (
              <p className="label mt-3">
                {feed?.source
                  ? <>{tr(lang, "Source", "स्रोत")}: <b>{feed.source}</b> · {feed.samples.toLocaleString()} {tr(lang, "rows in", "पंक्तियाँ")} {feed.posts.toLocaleString()} {tr(lang, "posts", "पोस्ट")} · {tr(lang, "channels", "चैनल")}: {feed.channels.join(", ") || "—"}{feed.ignored?.length ? ` · ${tr(lang, "ignored (unknown name or unit)", "अनदेखा")}: ${feed.ignored.join(", ")}` : ""}</>
                  : tr(lang, "No data received for this well yet. A rig system (eRTMAC or any WITSML 1.4 / WITS0 sender) posts to this well's live address; or start the demo feeder, which re-sends recorded Utah FORGE data as WITSML documents through the same reader.",
                         "इस कूप के लिए अभी कोई डेटा नहीं आया। रिग सिस्टम (eRTMAC या कोई WITSML 1.4 / WITS0 प्रेषक) इस कूप के लाइव पते पर भेजता है; या डेमो फ़ीडर शुरू करें।")}
                {liveErr && <span style={{ color: "var(--hazard)" }}> · {liveErr}</span>}
              </p>
            )}
          </Card>
        </section>

        {!wellId && <EmptyState title={t("cmdNoWellSelected", lang)} why={t("cmdNoWellWhy", lang)} />}
        {wellId && (
          <div className="grid gap-6" style={{ gridTemplateColumns: "minmax(0, 3fr) minmax(0, 2fr)" }}>
            {/* Zone B — mud-log view (+ optional 3D mini-view) */}
            <section aria-label="mud log">
              <Card>
                {show3d && (
                  <div className="mb-4">
                    <div className="label mb-1">{tr(lang, "3D subsurface — bit position live", "3D उपसतह — बिट स्थिति लाइव")}</div>
                    <Subsurface3D wellId={wellId} radius={10000} bitMd={bit} height={380} />
                  </div>
                )}
                <div className="overflow-x-auto">
                  <div className="flex gap-3 items-start">
                    <div><div className="small rule-b pb-0.5 mb-1">{t("cmdMdAxis", lang)}</div><DepthAxis y={y} height={H} /></div>
                    <div><div className="small rule-b pb-0.5 mb-1">{t("formationLabel", lang)}</div>
                      <LithologyColumn intervals={tops} y={y} height={H} width={132} bit={bit} target={hazardTarget} /></div>
                    <CurveTrack title="Torque" unit="kft·lb" pts={trackPts("torque")} y={y} height={H} width={rig ? 150 : 118} />
                    <CurveTrack title="Pit volume" unit="bbl" pts={trackPts("pit_vol")} y={y} height={H} width={rig ? 150 : 118} />
                    <CurveTrack title="Mud weight" unit="ppg" pts={trackPts("mw_ppg")} y={y} height={H} width={rig ? 120 : 96} />
                  </div>
                </div>
                <p className="label mt-2">{t("cmdSensorNote1", lang)} {well?.name} {t("cmdSensorNote2", lang)}
                  {anomaly && <> {t("cmdLastAbnormal", lang)} <b>{anomaly.channels.join(", ")}</b> {anomaly.t?.slice(11, 16)}.</>}</p>
                {ended && <p className="small mt-1">{t("cmdReplayEnded", lang)}</p>}
              </Card>
            </section>

            {/* Zone C — top look-ahead hazard */}
            <section aria-label="look-ahead">
              {!la && <EmptyState title={mode === "live" ? (running ? tr(lang, "Waiting for data from the rig feed", "रिग फ़ीड से डेटा की प्रतीक्षा") : tr(lang, "Not connected to the live feed", "लाइव फ़ीड से नहीं जुड़ा"))
                  : running ? t("cmdReadingAhead", lang) : t("cmdReplayNotStarted", lang)}
                why={mode === "live" ? "Each batch the rig sends goes through the same anomaly check and 150 m look-ahead as the replay. No data means no assessment, never 'all clear'."
                  : `Start the replay. Every tick, Kupakosh looks ${150} m ahead of the bit and checks offset-well records for the formations coming up.`} />}
              {la && !top && <EmptyState title={t("cmdNothingAhead", lang)} why={`No offset well recorded a problem in ${la.current?.label ?? "this formation"} or in the formations within 150 m below the bit (${la.n_offsets} offsets in radius). Absence of a record is not proof of safety.`} />}
              {top && (
                <NoticeSlip level={top.level} title={`${top.label} · ${top.formation_label}`}
                  where={top.in_formation ? t("cmdInCurrentFormation", lang) : `in ${Math.round(top.distance_m)} m`}
                  mean={top.mean} ci={top.ci} neff={top.n_eff} nWells={top.n_wells} nWithEvent={top.n_with_event} status={top.status}
                  posterior={top} hazard={top.hazard}
                  actions={<>
                    <button className="btn" onClick={() => { const e = top.evidence.find((x: any) => x.events.length); if (e) openSource(e.events[0].source_ref); }}>{t("sources", lang)}</button>
                    <Link className="btn" href={`/wiki?page=${encodeURIComponent("formations/" + slugF(top.formation))}`}>{t("openWiki", lang)}</Link>
                  </>}>
                  <div className="label mb-1">{t("cmdWhatWorkedBefore", lang)} {top.fixes?.scope ? `(${top.fixes.scope})` : ""}</div>
                  {(top.fixes?.rows ?? []).length === 0 && <div className="small text-ink2">{t("cmdNoEpisodeOutcome", lang)}</div>}
                  <ul className="space-y-1">
                    {(top.fixes?.rows ?? []).map((r: any) => (
                      <li key={r.action} className="grid items-center gap-x-3 small rule-b pb-1" style={{ gridTemplateColumns: "minmax(0,1fr) auto auto" }}>
                        <span>{actionText(r.action, lang)}{r.anecdotal ? <span className="label"> · {t("cmdAnecdotal", lang)}</span> : null}
                          {r.worsened > 0 && <span className="num" style={{ color: "var(--hazard)" }}> · ▲ {r.worsened} {t("cmdMadeWorse", lang)}</span>}</span>
                        <span className="num">{fmtK(r.k)}/{r.n}</span>
                        <IntervalBar rate={r.rate} lb={r.lb} width={96} anecdotal={r.anecdotal} />
                      </li>
                    ))}
                  </ul>
                  <div className="label mt-2">{t("cmdEvidencePrefix", lang)} {top.evidence.filter((e: any) => e.y).map((e: any) => e.name).join(", ") || t("cmdNone", lang)} · {t("cmdPrior", lang)} {pct(top.prior.base_rate)} ({top.prior.scope.replace("_", " ")})</div>
                  {wellId && <AlertFeedback key={`${top.formation}|${top.hazard}`} wellId={wellId} formation={top.formation} hazard={top.hazard} mdM={bit} />}
                </NoticeSlip>
              )}
              <div className="flex gap-2 mt-4 flex-wrap">
                <button className="btn" onClick={() => setDrawer("offsets")}>{t("cmdOffsetWellsBtn", lang)} ({offsets.length}) ▸</button>
                {more > 0 && <button className="btn" onClick={() => setDrawer("alerts")}>{t("cmdFurtherAlertsBtn", lang)} ({more}) ▸</button>}
                <button className="btn" onClick={() => { setHandoverMd(bit ?? (startMd === "" ? 0 : Number(startMd))); setDrawer("handover"); }}>{tr(lang, "Shift handover note", "शिफ्ट हैंडओवर नोट")} ▸</button>
              </div>
            </section>
          </div>
        )}
      </div>

      <Drawer open={drawer === "offsets"} onClose={() => setDrawer(null)} title={`${t("cmdOffsetWellsWithin", lang)} ${m(10000)}`} width={560}>
        {well && <MiniMap center={[well.lat, well.lon]} radius_m={10000} height={260}
          wells={[{ ...well, active: true }, ...offsets.map((o) => ({ id: o.well_id, name: o.name, lat: o.lat, lon: o.lon, documented: o.documented, n_events: o.n_events }))]} />}
        <ul className="mt-3">
          {offsets.map((o) => (
            <li key={o.well_id} className="rule-b py-2 small flex justify-between gap-3">
              <span>{o.name} <span className="label">{o.documented ? t("cmdReports", lang) : t("cmdNoReports", lang)} · {o.n_events} {t("cmdEvents", lang)}</span></span>
              <span className="num">{o.raw.distance_m.toLocaleString()} m · sim {o.sim.toFixed(2)}</span>
            </li>
          ))}
          {offsets.length === 0 && <li className="small">{t("cmdNoWellsInRadius", lang)}</li>}
        </ul>
      </Drawer>
      <Drawer open={drawer === "handover"} onClose={() => setDrawer(null)} title={tr(lang, "Shift handover note", "शिफ्ट हैंडओवर नोट")} width={560}>
        {wellId && drawer === "handover" && <HandoverNote wellId={wellId} bitMd={handoverMd} lang={lang} />}
      </Drawer>
      <Drawer open={drawer === "connect"} onClose={() => setDrawer(null)} title={tr(lang, "Connecting a rig system (eRTMAC, WITSML, WITS0)", "रिग सिस्टम जोड़ना (eRTMAC, WITSML, WITS0)")} width={600}>
        <ConnectHelp wellId={wellId} wellName={well?.name} />
      </Drawer>
      <Drawer open={drawer === "alerts"} onClose={() => setDrawer(null)} title={t("cmdAllLookahead", lang)}>
        {[...(la?.alerts ?? []), ...(la?.notices ?? [])].slice(1).map((a: any, i: number) => (
          <div key={i} className="rule-b py-2 small">
            <div className="font-semibold">{a.label} · {a.formation_label} <span className="label">{a.level}</span></div>
            <div>{a.status === "ok" ? `${pct(a.mean)} (range ${pct(a.ci[0])}–${pct(a.ci[1])})` : t("insufficient", lang)} · n_eff {a.n_eff.toFixed(1)} · {a.in_formation ? t("cmdInCurrentFormation", lang) : `in ${Math.round(a.distance_m)} m`}</div>
          </div>
        ))}
      </Drawer>
    </div>
  );
}

/** A simple numbered text stepper — no gradient/pill chips (DESIGN_V3.md). The active step is filled in
 *  this page's section colour (operate = rust, DESIGN_V3_COLOUR.md), not a tint or gradient. */
function StepHint({ step, lang, live = false }: { step: 1 | 2 | 3; lang: Lang; live?: boolean }) {
  const steps: { n: 1 | 2 | 3; en: string; hi: string }[] = [
    { n: 1, en: "Pick a start depth", hi: "प्रारंभ गहराई चुनें" },
    live ? { n: 2, en: "Connect the feed", hi: "फ़ीड जोड़ें" } : { n: 2, en: "Start replay", hi: "पुनःचलन प्रारंभ करें" },
    { n: 3, en: "Watch the alert", hi: "चेतावनी देखें" },
  ];
  return (
    <div className="flex items-center gap-2 flex-wrap" aria-label="steps">
      {steps.map((s, i) => {
        const active = s.n === step;
        return (
          <span key={s.n} className="inline-flex items-center gap-2">
            <span className="small" style={{
              display: "inline-flex", alignItems: "center", gap: 6, padding: "2px 10px", borderRadius: "var(--radius-md)",
              border: `1px solid ${active ? "var(--sec-operate)" : "var(--border)"}`,
              color: active ? "var(--surface)" : "var(--text)",
              fontWeight: active ? 600 : 500,
              background: active ? "var(--sec-operate)" : "transparent",
            }}>
              <span className="num" style={{ fontSize: "0.78rem" }}>{s.n}</span> {tr(lang, s.en, s.hi)}
            </span>
            {i < steps.length - 1 && <span className="label" aria-hidden="true">→</span>}
          </span>
        );
      })}
    </div>
  );
}

/** Local REPLAY indicator: kk/Stamp and v2 Badge both use --caution-ink text on a tinted --caution
 *  background, which measures 4.44:1 (just under the 4.5:1 AA minimum) — a pre-existing token issue
 *  in shared tokens.css/Stamp.tsx (outside this page's owned files). This keeps the same caution
 *  colour as an accent (border + dot) but the label text stays --text, which is already AA-safe. */
function ReplayBadge({ label, sub }: { label: string; sub?: string }) {
  return (
    <span
      className="inline-flex items-center gap-2 px-3 py-1.5 select-none"
      style={{ border: "1px solid color-mix(in srgb, var(--caution) 45%, transparent)", background: "var(--surface-2)", borderRadius: "var(--radius-lg, 12px)" }}
    >
      <span aria-hidden="true" style={{ width: 8, height: 8, borderRadius: 999, background: "var(--caution)", flex: "0 0 auto" }} />
      <span className="flex flex-col leading-tight">
        <span className="text-[0.82rem] font-semibold tracking-wide">{label}</span>
        {sub && <span className="text-[0.7rem] label">{sub}</span>}
      </span>
    </span>
  );
}

/** Plain grey icon (no tinted chip background) — the value itself may still carry a meaningful
 *  data colour (e.g. the current formation) via its own inline style at the call site. */
function StatusFigure({ label, value, rig, mono = true, icon: Icon, valueColor }: { label: string; value: string; rig: boolean; mono?: boolean; icon?: any; valueColor?: string }) {
  return (
    <div className="flex items-center gap-2">
      {Icon && !rig && (
        <span aria-hidden="true" className="kk-icon-chip" style={{ flex: "0 0 auto" }}>
          <Icon size={16} strokeWidth={1.75} />
        </span>
      )}
      <div>
        <div className="label">{label}</div>
        <div className={`${mono ? "num" : "font-semibold"} flex items-center gap-2`} style={{ fontSize: rig ? 26 : 22, lineHeight: 1.15 }}>
          {valueColor && <span aria-hidden="true" style={{ width: 14, height: 14, borderRadius: 2, background: valueColor, border: "1px solid var(--border)", flex: "0 0 auto" }} />}
          {value}
        </div>
      </div>
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

/** LIVE indicator. Receiving = --ok dot + "LIVE FEED"; no data for livefeed.stale_s = --caution dot + age; the text always
 *  says which, so colour is never the only signal. The demo source is named in the sub-line. */
function LiveBadge({ feed, connected, lang }: { feed: any; connected: boolean; lang: Lang }) {
  const receiving = connected && feed && !feed.stale;
  const c = receiving ? "var(--ok)" : "var(--caution)";
  const sub = !connected ? tr(lang, "not connected", "जुड़ा नहीं")
    : !feed ? tr(lang, "connected · no data yet", "जुड़ा · अभी डेटा नहीं")
    : feed.stale ? `${tr(lang, "no data for", "डेटा नहीं")} ${Math.round(feed.seconds_since_data ?? 0)} s`
    : feed.demo ? tr(lang, "demo feeder · recorded data as WITSML", "डेमो फ़ीडर · दर्ज डेटा WITSML के रूप में")
    : tr(lang, "receiving", "प्राप्त हो रहा");
  return (
    <span className="inline-flex items-center gap-2 px-3 py-1.5 select-none"
      style={{ border: `1px solid color-mix(in srgb, ${c} 45%, transparent)`, background: "var(--surface-2)", borderRadius: "var(--radius-lg, 12px)" }}>
      <span aria-hidden="true" style={{ width: 8, height: 8, borderRadius: 999, background: c, flex: "0 0 auto" }} />
      <span className="flex flex-col leading-tight">
        <span className="text-[0.82rem] font-semibold tracking-wide">{receiving ? "LIVE FEED" : tr(lang, "LIVE FEED · waiting", "लाइव फ़ीड · प्रतीक्षा")}</span>
        <span className="text-[0.7rem] label">{sub}</span>
      </span>
    </span>
  );
}

function ConnectHelp({ wellId, wellName }: { wellId: number | null; wellName?: string }) {
  const origin = typeof window === "undefined" ? "" : window.location.origin;
  const id = wellId ?? "{well_id}";
  return (
    <div className="space-y-3 small">
      <p>Kupakosh sits beside eRTMAC and reads the same real-time data. A rig system sends batches of sensor rows to this well&apos;s live address; every viewer of the well sees them within a second, with the same anomaly check and 150 m look-ahead as the replay.</p>
      <div className="label">WITSML 1.4.1 log documents (XML){wellName ? ` — well ${wellName}` : ""}</div>
      <pre className="num" style={{ whiteSpace: "pre-wrap", background: "var(--surface-2)", padding: 8, border: "1px solid var(--border)" }}>{`POST ${origin}/api/live/${id}/witsml
Authorization: Bearer <feed token>
X-Feed-Source: <name shown to viewers>
Content-Type: application/xml

<logs xmlns="http://www.witsml.org/schemas/1series" version="1.4.1.1">
  <log> … <logData>
    <mnemonicList>TIME,DEPT,DBTM,TQA,SPPA,MFIA,TVA,HKLA</mnemonicList>
    <unitList>s,m,m,kft.lbf,psi,gal/min,bbl,klbf</unitList>
    <data>2023-05-11T19:14:20Z,1500.7,1500.7,9.8,2510,612,402.1,188</data>
  </logData></log>
</logs>`}</pre>
      <div className="label">WITS Level 0 (ASCII, record 01)</div>
      <pre className="num" style={{ whiteSpace: "pre-wrap", background: "var(--surface-2)", padding: 8, border: "1px solid var(--border)" }}>{`POST ${origin}/api/live/${id}/wits0?units=metric   (or imperial)
&&
0105230511
0106191420
0110 1500.7
0118 13.3
!!`}</pre>
      <p>Mnemonics and units are converted using <span className="num">config/default.yaml → livefeed</span> (feet, bar, kPa, kN·m, m³ and L/min are understood). A channel with an unknown name or unit is listed as ignored, never guessed. The feed token is set on the server (<span className="num">KK_FEED_TOKEN</span>); without it a post is refused.</p>
      <p>Try it from a terminal: <span className="num">python -m scripts.witsml_feeder --well 16B --start-md 1500</span> sends recorded data the way a rig system would. The <b>Start demo feeder</b> button does the same on the server. Both are labelled as recorded data, not a live rig.</p>
    </div>
  );
}
