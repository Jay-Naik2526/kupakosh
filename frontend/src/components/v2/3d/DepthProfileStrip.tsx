"use client";
// Bottom "depth profile" strip: the active well's own formations laid out along MD, with its
// recorded events marked in place and (when replaying) the bit position. All real data — no
// planned path or invented corridor.
import { useMemo } from "react";
import type { SceneWell } from "./types";
import { formationColor, hazardColor } from "@/lib/palette";
import { hazardText } from "@/lib/format";
import type { Lang } from "@/lib/i18n";

const tr = (lang: Lang, en: string, hi: string) => (lang === "hi" ? hi : en);

export function DepthProfileStrip({ well, bitMd, lang }: { well: SceneWell; bitMd?: number | null; lang: Lang }) {
  const maxMd = well.td_md_m ?? (well.trajectory.length ? well.trajectory[well.trajectory.length - 1].md : 0);
  const tops = useMemo(() => [...well.formation_tops].sort((a, b) => a.md - b.md), [well.formation_tops]);
  if (!maxMd || !tops.length) return null;

  const bands = tops.map((t, i) => {
    const start = t.md;
    const end = i < tops.length - 1 ? tops[i + 1].md : maxMd;
    return { ...t, start, end, pct: Math.max(0, ((end - start) / maxMd) * 100) };
  });

  return (
    <div className="kk-card" style={{ padding: "8px 10px" }}>
      <div className="label" style={{ marginBottom: 4 }}>{tr(lang, "Depth profile", "गहराई प्रोफ़ाइल")} · {well.name} · {tr(lang, "MD", "MD")} 0–{Math.round(maxMd).toLocaleString("en-IN")} m</div>
      <div style={{ position: "relative", height: 34, borderRadius: 4, overflow: "hidden", border: "1px solid var(--border,#E4E7EC)", display: "flex" }}>
        {bands.map((b, i) => (
          <div
            key={i}
            title={`${b.label ?? b.formation} · ${Math.round(b.start)}–${Math.round(b.end)} m`}
            style={{
              width: `${b.pct}%`, minWidth: 2, background: formationColor(b.formation, b.lithology), position: "relative",
              borderRight: "1px solid rgba(0,0,0,.12)", display: "flex", alignItems: "center", justifyContent: "center",
            }}
          >
            {b.pct > 9 && <span style={{ fontSize: 10, fontWeight: 600, color: "#101828", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{b.label ?? b.formation}</span>}
          </div>
        ))}
        {well.events.map((ev) => (
          <div
            key={ev.id}
            title={`${hazardText(ev.hazard, lang)} · ${Math.round(ev.md)} m`}
            style={{
              position: "absolute", left: `${Math.min(99.3, (ev.md / maxMd) * 100)}%`, top: 0, bottom: 0, width: 3,
              background: hazardColor(ev.hazard), boxShadow: `0 0 4px ${hazardColor(ev.hazard)}`,
            }}
          />
        ))}
        {bitMd != null && bitMd <= maxMd && (
          <div style={{ position: "absolute", left: `${(bitMd / maxMd) * 100}%`, top: -3, bottom: -3, width: 2, background: "var(--text,#101828)" }}>
            <div style={{ position: "absolute", top: -14, left: -14, fontSize: 10, fontFamily: "var(--font-plex-mono)", whiteSpace: "nowrap" }}>{tr(lang, "bit", "बिट")} {Math.round(bitMd)} m</div>
          </div>
        )}
      </div>
    </div>
  );
}
