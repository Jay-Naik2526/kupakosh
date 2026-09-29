"use client";
import { useState } from "react";
import { tipStyle } from "./SceneObjects";
import type { Lang } from "@/lib/i18n";

export type ViewMode = "3d" | "top" | "side" | "section";
export type LayerToggles = {
  activeWell: boolean; offsetWells: boolean; formations: boolean; riskBands: boolean;
  labels: boolean; depthMarkers: boolean; grid: boolean;
};
export const DEFAULT_TOGGLES: LayerToggles = {
  activeWell: true, offsetWells: true, formations: true, riskBands: true, labels: true, depthMarkers: false, grid: true,
};

const tr = (lang: Lang, en: string, hi: string) => (lang === "hi" ? hi : en);

const rowStyle = { display: "flex", alignItems: "center", gap: 6, fontSize: 12, cursor: "pointer" as const, userSelect: "none" as const };
const groupTitle = { fontSize: 11, fontWeight: 700, opacity: 0.7, marginTop: 8, marginBottom: 3, textTransform: "uppercase" as const, letterSpacing: 0.3 };
const btnStyle = (active: boolean) => ({
  padding: "3px 8px", borderRadius: 6, fontSize: 12, border: "1px solid var(--border,#E4E7EC)",
  background: active ? "var(--accent,#0F766E)" : "var(--surface,#fff)", color: active ? "#fff" : "var(--text,#101828)", cursor: "pointer",
});

export function Controls({ lang, toggles, setToggles, viewMode, setViewMode, opacity, setOpacity, vertExag, setVertExag, onReset, compact }: {
  lang: Lang; toggles: LayerToggles; setToggles: (t: LayerToggles) => void;
  viewMode: ViewMode; setViewMode: (v: ViewMode) => void;
  opacity: number; setOpacity: (n: number) => void; vertExag: number; setVertExag: (n: number) => void;
  onReset: () => void; compact: boolean;
}) {
  const [open, setOpen] = useState(!compact);
  const toggle = (k: keyof LayerToggles) => setToggles({ ...toggles, [k]: !toggles[k] });

  if (compact && !open) {
    return (
      <button type="button" style={{ ...tipStyle, cursor: "pointer" }} onClick={() => setOpen(true)} aria-label={tr(lang, "Show 3D controls", "3D नियंत्रण दिखाएँ")}>
        ⚙ {tr(lang, "Controls", "नियंत्रण")}
      </button>
    );
  }

  return (
    <div style={{ ...tipStyle, whiteSpace: "normal", width: compact ? 190 : 210, maxHeight: compact ? 260 : 420, overflowY: "auto" }}>
      {compact && (
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <strong style={{ fontSize: 12 }}>{tr(lang, "Controls", "नियंत्रण")}</strong>
          <button className="btn" style={{ padding: "0 5px" }} onClick={() => setOpen(false)} aria-label="close">✕</button>
        </div>
      )}

      <div style={groupTitle}>{tr(lang, "View", "दृश्य")}</div>
      <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
        {(["3d", "top", "side", "section"] as ViewMode[]).map((v) => (
          <button key={v} type="button" style={btnStyle(viewMode === v)} onClick={() => setViewMode(v)}>
            {v === "3d" ? "3D" : v === "top" ? tr(lang, "Top", "ऊपर") : v === "side" ? tr(lang, "Side", "बगल") : tr(lang, "Section", "काट")}
          </button>
        ))}
      </div>

      <div style={groupTitle}>{tr(lang, "Layers", "परतें")}</div>
      {([
        ["activeWell", tr(lang, "Active well", "सक्रिय कूप")],
        ["offsetWells", tr(lang, "Offset wells", "निकटवर्ती कूप")],
        ["formations", tr(lang, "Formation block", "संरचना खंड")],
        ["riskBands", tr(lang, "Risk bands", "जोखिम पट्टी")],
        ["labels", tr(lang, "Labels", "लेबल")],
        ["depthMarkers", tr(lang, "Depth markers", "गहराई चिह्न")],
        ["grid", tr(lang, "Grid", "ग्रिड")],
      ] as [keyof LayerToggles, string][]).map(([key, label]) => (
        <label key={key} style={rowStyle}>
          <input type="checkbox" checked={toggles[key]} onChange={() => toggle(key)} /> {label}
        </label>
      ))}

      <div style={groupTitle}>{tr(lang, "Formation opacity", "संरचना अपारदर्शिता")}</div>
      <input type="range" min={0.15} max={0.95} step={0.05} value={opacity} style={{ width: "100%" }} onChange={(e) => setOpacity(Number(e.target.value))} />

      <div style={groupTitle}>{tr(lang, "Vertical exaggeration", "ऊर्ध्वाधर अतिशयोक्ति")}</div>
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <input type="range" min={1} max={8} step={0.5} value={vertExag} style={{ flex: 1 }} onChange={(e) => setVertExag(Number(e.target.value))} />
        <span className="mono">{vertExag}×</span>
      </div>

      <button type="button" className="btn" style={{ marginTop: 8, width: "100%" }} onClick={onReset}>{tr(lang, "Reset view", "दृश्य रीसेट")}</button>
    </div>
  );
}

/** Full-page variant: one slim toolbar above the canvas, so nothing sits on top of the 3D view.
 *  Layer switches live in a small drop-down; view buttons, the two sliders and reset stay visible. */
export function ControlsBar({ lang, toggles, setToggles, viewMode, setViewMode, opacity, setOpacity, vertExag, setVertExag, onReset }: {
  lang: Lang; toggles: LayerToggles; setToggles: (t: LayerToggles) => void;
  viewMode: ViewMode; setViewMode: (v: ViewMode) => void;
  opacity: number; setOpacity: (n: number) => void; vertExag: number; setVertExag: (n: number) => void;
  onReset: () => void;
}) {
  const toggle = (k: keyof LayerToggles) => setToggles({ ...toggles, [k]: !toggles[k] });
  const layers: [keyof LayerToggles, string][] = [
    ["activeWell", tr(lang, "Active well", "सक्रिय कूप")],
    ["offsetWells", tr(lang, "Offset wells", "निकटवर्ती कूप")],
    ["formations", tr(lang, "Formation block", "संरचना खंड")],
    ["riskBands", tr(lang, "Risk bands", "जोखिम पट्टी")],
    ["labels", tr(lang, "Labels", "लेबल")],
    ["depthMarkers", tr(lang, "Depth markers", "गहराई चिह्न")],
    ["grid", tr(lang, "Grid", "ग्रिड")],
  ];
  const on = layers.filter(([k]) => toggles[k]).length;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap", fontSize: 12.5 }}>
      <div style={{ display: "flex", gap: 4 }} role="group" aria-label={tr(lang, "View", "दृश्य")}>
        {(["3d", "top", "side", "section"] as ViewMode[]).map((v) => (
          <button key={v} type="button" aria-pressed={viewMode === v} style={btnStyle(viewMode === v)} onClick={() => setViewMode(v)}>
            {v === "3d" ? "3D" : v === "top" ? tr(lang, "Top", "ऊपर") : v === "side" ? tr(lang, "Side", "बगल") : tr(lang, "Section", "काट")}
          </button>
        ))}
      </div>
      <details style={{ position: "relative" }}>
        <summary className="btn" style={{ listStyle: "none", cursor: "pointer", padding: "3px 10px" }}>
          {tr(lang, "Layers", "परतें")} <span className="mono">{on}/{layers.length}</span> ▾
        </summary>
        <div style={{ ...tipStyle, position: "absolute", top: "calc(100% + 4px)", left: 0, zIndex: 30, display: "grid", gap: 3, minWidth: 170 }}>
          {layers.map(([key, label]) => (
            <label key={key} style={rowStyle}><input type="checkbox" checked={toggles[key]} onChange={() => toggle(key)} /> {label}</label>
          ))}
        </div>
      </details>
      <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <span className="label">{tr(lang, "Opacity", "अपारदर्शिता")}</span>
        <input type="range" min={0.15} max={0.95} step={0.05} value={opacity} style={{ width: 90, accentColor: "var(--accent)" }} onChange={(e) => setOpacity(Number(e.target.value))} />
      </label>
      <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <span className="label">{tr(lang, "Vertical ×", "ऊर्ध्वाधर ×")}</span>
        <input type="range" min={1} max={8} step={0.5} value={vertExag} style={{ width: 90, accentColor: "var(--accent)" }} onChange={(e) => setVertExag(Number(e.target.value))} />
        <span className="mono">{vertExag}×</span>
      </label>
      <button type="button" className="btn" style={{ marginLeft: "auto", padding: "3px 10px" }} onClick={onReset}>{tr(lang, "Reset view", "दृश्य रीसेट")}</button>
    </div>
  );
}
