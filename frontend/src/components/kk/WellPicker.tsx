"use client";
import { useEffect, useState } from "react";
import { get } from "@/lib/api";
import { useApp } from "@/lib/state";

/** Search + pick the active well (shared across screens). */
export function WellPicker({ onlyReplay = false, label = "Well" }: { onlyReplay?: boolean; label?: string }) {
  const { wellId, setWellId } = useApp();
  const [q, setQ] = useState("");
  const [opts, setOpts] = useState<any[]>([]);
  const [cur, setCur] = useState<any>(null);
  useEffect(() => { if (wellId) get(`/api/wells/${wellId}`).then(setCur).catch(() => setCur(null)); }, [wellId]);
  useEffect(() => {
    if (onlyReplay) { get("/api/replay/wells").then(setOpts); return; }
    const h = setTimeout(() => get("/api/wells", { q, documented: true, limit: 12 }).then(setOpts).catch(() => {}), 150);
    return () => clearTimeout(h);
  }, [q, onlyReplay]);
  return (
    <div className="flex items-center gap-2 flex-wrap">
      <label className="label" htmlFor="wellq">{label}</label>
      {!onlyReplay && <input id="wellq" className="input w-40" placeholder="search e.g. 15/9" value={q} onChange={(e) => setQ(e.target.value)} />}
      <select className="input min-w-[12rem]" aria-label="Select well" value={wellId ?? ""} onChange={(e) => setWellId(e.target.value ? Number(e.target.value) : null)}>
        <option value="">— select —</option>
        {cur && !opts.some((o) => o.id === cur.id) && <option value={cur.id}>{cur.name}</option>}
        {opts.map((o) => <option key={o.id} value={o.id}>{o.name} · {o.field ?? ""} · {o.n_events} ev</option>)}
      </select>
    </div>
  );
}
