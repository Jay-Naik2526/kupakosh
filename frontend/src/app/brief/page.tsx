"use client";
import { useEffect, useState } from "react";
import { API, get, post } from "@/lib/api";
import { useApp } from "@/lib/state";
import { m, pct, ppg } from "@/lib/format";
import { MiniMap } from "@/components/kk/MiniMap";
import { SourceFootnote } from "@/components/kk/SourceFootnote";
import { t } from "@/lib/i18n";
import { Card, PageHeader } from "@/components/v2/ui";
import { hazardColor, formationColor } from "@/lib/palette";

export default function Brief() {
  const { wellId, ready, lang } = useApp();
  const [lat, setLat] = useState<number | "">("");
  const [lon, setLon] = useState<number | "">("");
  const [td, setTd] = useState<number>(4000);
  const [radius, setRadius] = useState(10000);
  const [tops, setTops] = useState("");
  const [b, setB] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [near, setNear] = useState<any[]>([]);

  useEffect(() => {
    if (!ready) return;
    const id = wellId;
    (id ? get(`/api/wells/${id}`) : get("/api/wells", { q: "15/9-19 S", limit: 1 }).then((w) => w[0])).then((w: any) => {
      if (w) { setLat(Number(w.lat.toFixed(5))); setLon(Number(w.lon.toFixed(5))); if (w.td_md_m) setTd(Math.round(w.td_md_m)); }
    });
  }, [ready]); // eslint-disable-line
  const body = () => ({
    lat: Number(lat), lon: Number(lon), target_td_m: td, radius_m: radius,
    planned_tops: tops.trim() ? tops.trim().split("\n").map((l) => { const [f, d] = l.split(",").map((s) => s.trim()); return { formation: f.toUpperCase(), top_md_m: Number(d) }; }).filter((t) => t.formation && !isNaN(t.top_md_m)) : null,
  });
  const build = async () => {
    if (lat === "" || lon === "") return;
    setBusy(true); setErr(null);
    try { setB(await post("/api/brief", body())); } catch (e: any) { setErr(e.message); }
    setBusy(false);
  };
  useEffect(() => { if (lat !== "" && lon !== "") get("/api/wells", { bbox: `${Number(lon) - 0.15},${Number(lat) - 0.1},${Number(lon) + 0.15},${Number(lat) + 0.1}`, documented: true, limit: 60 }).then(setNear); }, [lat, lon]);
  const pdf = async () => {
    const r = await fetch(`${API}/api/brief/pdf`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body()) });
    if (!r.ok) { setErr(await r.text()); return; }
    const blob = await r.blob(); const a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = (r.headers.get("content-disposition")?.match(/filename="(.+)"/)?.[1]) ?? "brief.pdf"; a.click();
  };

  return (
    <div className="space-y-4">
      <PageHeader title={t("brPrepareBrief", lang)} subtitle={t("brClickMap", lang)} />
      <div className="grid gap-4" style={{ gridTemplateColumns: "minmax(0,35fr) minmax(0,65fr)" }}>
      {/* Zone A — form */}
      <section aria-label="brief inputs">
        <Card className="space-y-3">
        <MiniMap center={lat !== "" && lon !== "" ? [Number(lat), Number(lon)] : null} radius_m={radius} height={220}
          wells={near.map((w) => ({ id: w.id, name: w.name, lat: w.lat, lon: w.lon, documented: w.documented, n_events: w.n_events }))}
          onPick={(id) => { const w = near.find((x) => x.id === id); if (w) { setLat(Number(w.lat.toFixed(5))); setLon(Number(w.lon.toFixed(5))); } }} />
        <div className="grid grid-cols-2 gap-2">
          <label className="small">{t("brLatitude", lang)}<input className="input w-full num" value={lat} onChange={(e) => setLat(e.target.value === "" ? "" : Number(e.target.value))} /></label>
          <label className="small">{t("brLongitude", lang)}<input className="input w-full num" value={lon} onChange={(e) => setLon(e.target.value === "" ? "" : Number(e.target.value))} /></label>
          <label className="small">{t("brTargetDepth", lang)}<input className="input w-full num" type="number" value={td} onChange={(e) => setTd(Number(e.target.value))} /></label>
          <label className="small">{t("brOffsetRadius", lang)}
            <select className="input w-full" value={radius} onChange={(e) => setRadius(Number(e.target.value))}>{[5000, 10000, 20000, 50000].map((r) => <option key={r} value={r}>{r / 1000} km</option>)}</select></label>
        </div>
        <label className="small block">{t("brPlannedTops", lang)} <span className="mono">FORMATION, top_m</span>). {t("brInferredNote", lang)}
          <textarea className="input w-full mono small mt-1" rows={4} value={tops} onChange={(e) => setTops(e.target.value)} placeholder={"UTSIRA FM, 800\nDRAUPNE FM, 3100"} /></label>
        <div className="flex gap-2">
          <button className="btn btn-primary" onClick={build} disabled={busy || lat === ""}>{busy ? t("brCompiling", lang) : t("brPrepareBrief", lang)}</button>
          <button className="btn" onClick={pdf} disabled={!b}>{t("brDownloadPdf", lang)}</button>
          <button className="btn" disabled title={t("brNotBuilt", lang)}>{t("brSendForReview", lang)}</button>
        </div>
        {err && <p className="small" style={{ color: "var(--hazard)" }}>✕ {err}</p>}
        </Card>
      </section>

      {/* Zone B — A4 preview */}
      <section aria-label="A4 preview">
        <Card className="overflow-x-auto">
        {!b && <div className="bg-card border border-dashed border-rule p-10 text-ink2" style={{ aspectRatio: "210/297", maxWidth: 720 }}>{t("brPreviewPlaceholder", lang)}</div>}
        {b && (
          <div className="bg-white text-ink border border-rule p-10 small" style={{ maxWidth: 760, boxShadow: "none" }}>
            <div style={{ height: 2, background: "linear-gradient(90deg,#FF9933 33.3%,#fff 33.3% 66.6%,#138808 66.6%)" }} />
            <div className="flex justify-between items-center px-3 py-2 mt-2 rounded-kk" style={{ background: "var(--brand-gradient, linear-gradient(100deg,#1D4ED8,#0E7490 55%,#0F766E))", color: "#fff" }}>
              <span className="font-semibold">Kupakosh · {t("board", lang)}</span>
              <span className="typewriter">No. {b.ref_no} · {t("brDated", lang)} {b.date}</span>
            </div>
            <h2 className="font-semibold mt-3" style={{ fontSize: 16 }}>{t("brSubject", lang)} {b.subject}</h2>
            <p className="label mt-1">{t("brDistribution", lang)} {b.distribution.join(", ")}. {b.n_offsets} {t("brWellsInRadius", lang)} {b.n_documented} {t("brWithReports", lang)} {b.inputs.tops_inferred ? t("brTopsInferred", lang) : t("brTopsPlanned", lang)}</p>
            <Sec n={1} t={t("brSec1", lang)}>
              <table className="w-full"><tbody>{b.formations.map((f: any) => (
                <tr key={f.formation} className="rule-b">
                  <td className="num w-24">{m(f.top_md_m)}</td>
                  <td><span aria-hidden="true" className="inline-block rounded-sm mr-2 align-middle" style={{ width: 10, height: 10, background: formationColor(f.formation, f.lithology) }} />{f.label}</td>
                </tr>
              ))}</tbody></table>
            </Sec>
            <Sec n={2} t={t("brSec2", lang)}>
              {b.hazards.length === 0 ? <p>{t("brNoHazard", lang)}</p> : (
                <table className="w-full"><thead><tr className="border-b border-ink text-left"><th>{t("brTableFormation", lang)}</th><th>{t("brTableHazard", lang)}</th><th className="text-right">{t("brTableRate", lang)}</th><th className="text-right">{t("brTableRange", lang)}</th><th className="text-right">n_eff</th><th>{t("brTableWhatWorked", lang)}</th></tr></thead>
                  <tbody>{b.hazards.map((h: any, i: number) => (
                    <tr key={i} className="rule-b align-top"><td>{h.formation_label}</td>
                      <td><span aria-hidden="true" className="inline-block rounded-full mr-1.5 align-middle" style={{ width: 8, height: 8, background: hazardColor(h.hazard ?? h.label) }} />{h.label}{h.sources[0] && <SourceFootnote refId={h.sources[0].source_ref} n="src" />}</td>
                      {h.status === "ok" ? <><td className="num text-right">{pct(h.mean)}</td><td className="num text-right">{pct(h.ci[0])}–{pct(h.ci[1])}</td></> : <td colSpan={2} className="text-right italic">{t("insufficient", lang).toLowerCase()}</td>}
                      <td className="num text-right">{h.n_eff.toFixed(1)}</td>
                      <td>{h.fixes.slice(0, 2).map((f: any) => `${f.action} (${f.k}/${f.n})`).join("; ") || "—"}</td></tr>))}</tbody></table>)}
              <p className="label mt-1">{t("brRatesNote", lang)}</p>
            </Sec>
            <Sec n={3} t={t("brSec3", lang)}>
              {b.mud_window.length === 0 ? <p>{t("brInsufficientEv", lang)}</p> : <table className="w-full"><tbody>{b.mud_window.map((r: any) => <tr key={r.formation} className="rule-b"><td>{r.label}</td><td className="num">{ppg(r.lower_ppg)} – {ppg(r.upper_ppg)}</td><td>{r.status.replace("_", " ")}</td></tr>)}</tbody></table>}
            </Sec>
            <Sec n={4} t={t("brSec4", lang)}>{b.casing_lessons.length === 0 ? <p>{t("brNoneRecordedOffsets", lang)}</p> : <ul className="list-disc pl-5">{b.casing_lessons.map((l: any, i: number) => <li key={i}>{l.well}: {l.od_in}″ shoe at {m(l.shoe_md_m)} — “{l.cement_issues[0].text.slice(0, 160)}”</li>)}</ul>}</Sec>
            <Sec n={5} t={t("brSec5", lang)}>{b.audit.length === 0 ? <p>{t("brNoneOpen", lang)}</p> : <ul className="list-disc pl-5">{b.audit.map((a: any, i: number) => <li key={i}>{a.well}: {a.rule} ({a.delta})</li>)}</ul>}</Sec>
            <Sec n={6} t={t("brSec6", lang)}><ol className="list-decimal pl-5 mono" style={{ fontSize: 11 }}>{b.sources.slice(0, 20).map((s: string) => <li key={s}>{s}</li>)}</ol></Sec>
            <div className="grid grid-cols-3 gap-6 mt-10">{b.signatures.map((s: any) => <div key={s.role}><div className="border-b border-ink h-10" /><b>{s.role}</b><div>{s.name || " "}</div></div>)}</div>
            <p className="mt-6"><b>{b.disclaimer}</b> <span className="label">{b.data_note}</span></p>
          </div>
        )}
        </Card>
      </section>
      </div>
    </div>
  );
}

function Sec({ n, t, children }: { n: number; t: string; children: React.ReactNode }) {
  return <div className="mt-4"><h3 className="font-semibold border-b border-rule mb-1">{n}. {t}</h3>{children}</div>;
}
