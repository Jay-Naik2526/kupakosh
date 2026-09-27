"use client";
import { useEffect, useRef, useState } from "react";
import { get } from "@/lib/api";
import { useApp } from "@/lib/state";
import { t } from "@/lib/i18n";

/** Search + pick the active well (shared across screens) — a single searchable combobox. */
export function WellPicker({ onlyReplay = false, label }: { onlyReplay?: boolean; label?: string }) {
  const { wellId, setWellId, country, lang } = useApp();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [opts, setOpts] = useState<any[]>([]);
  const [cur, setCur] = useState<any>(null);
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => { if (wellId) get(`/api/wells/${wellId}`).then(setCur).catch(() => setCur(null)); else setCur(null); }, [wellId]);
  useEffect(() => {
    if (onlyReplay) { get("/api/replay/wells").then(setOpts).catch(() => {}); return; }
    const h = setTimeout(() => get("/api/wells", { q: query, documented: true, limit: 12, country: country ?? undefined }).then(setOpts).catch(() => {}), 150);
    return () => clearTimeout(h);
  }, [query, onlyReplay, country]);
  useEffect(() => {
    const onDoc = (e: MouseEvent) => { if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const pick = (o: any) => { setWellId(o.id); setQuery(""); setOpen(false); };
  const clear = () => { setWellId(null); setQuery(""); setOpen(false); };
  const shownValue = open ? query : cur ? `${cur.name}${cur.field ? " · " + cur.field : ""}` : query;
  const placeholder = onlyReplay ? "— select a replay well —" : country ? `search ${country} wells` : "search e.g. 15/9";

  return (
    <div className="kk-well-combo" ref={boxRef}>
      {label && <label className="label" htmlFor="wellq">{label}</label>}
      <div className="kk-well-combo-box">
        <input
          id="wellq"
          role="combobox"
          aria-expanded={open}
          aria-autocomplete="list"
          aria-label="Select well"
          className="input kk-well-combo-input"
          placeholder={placeholder}
          value={shownValue}
          onFocus={() => setOpen(true)}
          onChange={(e) => { setQuery(e.target.value); setOpen(true); }}
          onKeyDown={(e) => { if (e.key === "Escape") setOpen(false); }}
        />
        {(cur || query) && (
          <button type="button" className="kk-well-combo-clear" aria-label="Clear well selection" onClick={clear} tabIndex={-1}>×</button>
        )}
        {open && (
          <div className="kk-popover kk-well-combo-list" role="listbox" aria-label={t("well", lang)}>
            {opts.length === 0 && <div className="label" style={{ padding: "8px 10px" }}>No matches</div>}
            {opts.map((o) => (
              <button key={o.id} type="button" role="option" aria-selected={o.id === wellId} className="kk-nav-item kk-well-combo-item" onClick={() => pick(o)}>
                <span>{o.name}</span>
                <span className="label">{o.field ?? ""} · {o.n_events} ev</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
