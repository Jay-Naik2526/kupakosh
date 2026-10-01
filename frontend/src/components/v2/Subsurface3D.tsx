"use client";
import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { Canvas, useThree } from "@react-three/fiber";
import { Bounds, OrbitControls } from "@react-three/drei";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import { get } from "@/lib/api";
import { useApp } from "@/lib/state";
import { t, type Lang } from "@/lib/i18n";
import { hazardText } from "@/lib/format";
import { hazardColor, wellColor, BRAND } from "@/lib/palette";
import { EmptyState } from "@/components/kk/EmptyState";
import { Scene, SceneEvent } from "./3d/types";
import {
  DepthTicks, EventSphere, DerrickGlyph, GroundPlane, PathDepthMarkers, RiskBand, SCALE, WellTube, tipStyle, DrillingProgress,
} from "./3d/SceneObjects";
import { GeoBlock, buildFormationLayers, type FormationLayer } from "./3d/GeoBlock";
import { DepthProfileStrip } from "./3d/DepthProfileStrip";
import { Controls, ControlsBar, DEFAULT_TOGGLES, type LayerToggles, type ViewMode } from "./3d/Controls";
import { useThemeColors } from "./3d/useThemeColors";

/** Props: reusable so the Well Room / Offsets screens can embed the same 3D room. */
export type Subsurface3DProps = {
  wellId: number | null;
  radius?: number;      // metres; falls back to the backend default (config offsets.default_radius_m)
  bitMd?: number | null; // current bit MD (m) — shows the look-ahead window when set (replay use)
  height?: number;       // canvas height in px; default fills the parent
};

const tr = (lang: Lang, en: string, hi: string) => (lang === "hi" ? hi : en);

function sceneBounds(scene: Scene) {
  let maxHoriz = 0, maxDepth = 0;
  for (const w of scene.wells) {
    maxHoriz = Math.max(maxHoriz, Math.hypot(w.x, w.y));
    for (const p of w.trajectory) { maxHoriz = Math.max(maxHoriz, Math.hypot(p.x, p.y)); maxDepth = Math.max(maxDepth, -p.z); }
    for (const e of w.events) maxDepth = Math.max(maxDepth, -e.z);
    for (const f of w.formation_tops) maxDepth = Math.max(maxDepth, -f.z);
  }
  return { maxHorizM: Math.max(maxHoriz, 200), maxDepthM: Math.max(maxDepth, 200) };
}

/** Per-formation risk band: real events, grouped by formation (never by an invented location). */
type Band = { formation: string; label: string; z: number; color: string; nWells: number; hazards: [string, number][]; sourceRef: string };
function buildRiskBands(scene: Scene): Band[] {
  const byF = new Map<string, { label: string; wells: Set<number>; zs: number[]; hazardWells: Map<string, Set<number>>; sourceRef: string; firstMd: number }>();
  for (const w of scene.wells) {
    for (const e of w.events) {
      if (!e.formation) continue;
      let rec = byF.get(e.formation);
      if (!rec) rec = { label: e.formation, wells: new Set(), zs: [], hazardWells: new Map(), sourceRef: e.source_ref, firstMd: e.md };
      byF.set(e.formation, rec);
      rec.wells.add(w.well_id);
      rec.zs.push(e.z);
      if (!rec.hazardWells.has(e.hazard)) rec.hazardWells.set(e.hazard, new Set());
      rec.hazardWells.get(e.hazard)!.add(w.well_id);
      if (e.md < rec.firstMd) { rec.firstMd = e.md; rec.sourceRef = e.source_ref; }
    }
  }
  const out: Band[] = [];
  Array.from(byF.entries()).forEach(([formation, rec]) => {
    const hazards = Array.from(rec.hazardWells.entries())
      .map(([h, wells]) => [h, wells.size] as [string, number])
      .sort((a, b) => b[1] - a[1]);
    const z = rec.zs.reduce((s: number, v: number) => s + v, 0) / rec.zs.length;
    out.push({ formation, label: rec.label, z, color: hazardColor(hazards[0][0]), nWells: rec.wells.size, hazards, sourceRef: rec.sourceRef });
  });
  return out;
}

function bandTag(b: Band, lang: Lang): string {
  const parts = b.hazards.slice(0, 2).map(([h, n]) => `${n} ${n === 1 ? tr(lang, "well", "कूप") : tr(lang, "wells", "कूप")} · ${hazardText(h, lang)}`);
  const more = b.hazards.length > 2 ? ` +${b.hazards.length - 2}` : "";
  return `${b.label}: ${parts.join(" · ")}${more}`;
}

function useIsDark(): boolean {
  const [dark, setDark] = useState(false);
  useEffect(() => {
    const read = () => setDark(document.documentElement.getAttribute("data-theme") === "dark");
    read();
    const obs = new MutationObserver(read);
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => obs.disconnect();
  }, []);
  return dark;
}

function CameraRig({ viewMode, groundSize, maxDepthM, vertExag, controlsRef, resetKey }: {
  viewMode: ViewMode; groundSize: number; maxDepthM: number; vertExag: number; controlsRef: React.RefObject<OrbitControlsImpl | null>; resetKey: number;
}) {
  const { camera } = useThree();
  useEffect(() => {
    const depthUnits = maxDepthM * SCALE * vertExag;
    const g = Math.max(groundSize, 1);
    let pos: [number, number, number];
    const target: [number, number, number] = [0, -depthUnits * 0.45, 0];
    if (viewMode === "top") pos = [0.001, g * 1.15, 0.001];
    else if (viewMode === "side" || viewMode === "section") pos = [g * 1.1, -depthUnits * 0.35, 0.001];
    else pos = [g * 0.95, -depthUnits * 0.05, g * 0.75];
    camera.position.set(...pos);
    camera.up.set(0, 1, 0);
    camera.lookAt(...target);
    const ctrl = controlsRef.current;
    if (ctrl) { ctrl.target.set(...target); ctrl.update(); }
  }, [viewMode, groundSize, maxDepthM, vertExag, resetKey]);
  return null;
}

export function Subsurface3D({ wellId, radius, bitMd, height }: Subsurface3DProps) {
  const { lang, openSource } = useApp();
  const [scene, setScene] = useState<Scene | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [vertExag, setVertExag] = useState(1);
  const [opacity, setOpacity] = useState(0.32);
  const [selected, setSelected] = useState<SceneEvent | null>(null);
  const [selectedLayer, setSelectedLayer] = useState<FormationLayer | null>(null);
  const [selectedBand, setSelectedBand] = useState<Band | null>(null);
  const [toggles, setToggles] = useState<LayerToggles>(DEFAULT_TOGGLES);
  const [viewMode, setViewMode] = useState<ViewMode>("3d");
  const [resetKey, setResetKey] = useState(0);
  const colors = useThemeColors();
  const isDark = useIsDark();
  const controlsRef = useRef<OrbitControlsImpl | null>(null);
  const compact = (height ?? 520) < 400;

  useEffect(() => {
    setScene(null); setError(null); setSelected(null); setSelectedLayer(null); setSelectedBand(null);
    if (!wellId) return;
    setLoading(true);
    const params: Record<string, any> = {};
    if (radius) params.radius_m = radius;
    // the bit depth is NOT a fetch parameter: refetching on every replay tick rebuilt the whole scene (flicker,
    // "Loading…"). The scene loads once per well; BitMarker moves along the trajectory instead.
    get<Scene>(`/api/wells/${wellId}/scene`, params)
      .then((s) => setScene(s))
      .catch((e) => setError(String(e?.message ?? e)))
      .finally(() => setLoading(false));
  }, [wellId, radius]);

  const { maxHorizM, maxDepthM } = useMemo(() => (scene ? sceneBounds(scene) : { maxHorizM: 200, maxDepthM: 200 }), [scene]);
  const half = maxHorizM * 1.15;
  // Wide, shallow scenes (10 km radius, ~3 km deep) look flat at true scale: start with a vertical
  // exaggeration that makes the block roughly cube-shaped. It is shown on the slider ("×N") and the user can reset it to 1×.
  useEffect(() => {
    if (!scene) return;
    const auto = Math.min(8, Math.max(1, Math.round(((maxHorizM * 2) / Math.max(maxDepthM, 1)) * 0.7 * 2) / 2));
    setVertExag(auto);
  }, [scene, maxHorizM, maxDepthM]);
  const groundSize = Math.max(2, half * SCALE * 2.05);
  const riskBands = useMemo(() => (scene ? buildRiskBands(scene) : []), [scene]);
  const formationLayers = useMemo(() => (scene ? buildFormationLayers(scene, half) : []), [scene, half]);
  const clipPlanes = useMemo(() => (viewMode === "section" ? [new THREE.Plane(new THREE.Vector3(0, 0, 1), 0)] : []), [viewMode]);

  if (!wellId) return <EmptyState title={t("subsurfaceNoWell", lang)} why={t("subsurfaceProjectionNote", lang)} />;
  if (error) {
    const noLocation = /422/.test(error);
    return <EmptyState title={noLocation ? t("subsurfaceNoLocation", lang) : "Could not load the 3D scene"} why={error} />;
  }
  if (loading || !scene) return <div className="kk-card" style={{ height: height ?? 480, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-2)" }}>{t("subsurfaceLoading", lang)}</div>;
  if (!scene.wells.length) return <EmptyState title={t("subsurfaceNoLocation", lang)} why={t("subsurfaceProjectionNote", lang)} />;

  const hazardsPresent = Array.from(new Set(scene.wells.flatMap((w) => w.events.map((e) => e.hazard))));
  const resetAll = () => { setViewMode("3d"); setVertExag(1); setOpacity(0.55); setResetKey((k) => k + 1); };
  const activeWell = scene.wells.find((w) => w.is_active) ?? null;
  const offsetWells = scene.wells.filter((w) => !w.is_active);
  const sky = colors.bg; // flat paper tone, no sky gradient — same in light and dark

  return (
    <div style={{ position: "relative", display: "flex", flexDirection: "column", gap: 8 }}>
      {!compact && (
        <ControlsBar
          lang={lang} toggles={toggles} setToggles={setToggles} viewMode={viewMode} setViewMode={setViewMode}
          opacity={opacity} setOpacity={setOpacity} vertExag={vertExag} setVertExag={setVertExag} onReset={resetAll}
        />
      )}
      <div style={{ position: "relative", height: height ?? 520, borderRadius: "var(--radius-lg)", overflow: "hidden", border: "1px solid var(--border)", background: sky }}>
        <Canvas
          camera={{ position: [6, 0.8, 4.5], fov: 45, near: 0.01, far: 2000 }}
          gl={{ alpha: true, localClippingEnabled: true }}
          dpr={[1, 2]}
        >
          <color attach="background" args={[sky]} />
          <fog attach="fog" args={[sky, groundSize * 1.4, groundSize * 4]} />
          <ambientLight intensity={isDark ? 0.55 : 0.85} />
          <directionalLight position={[5, 8, 3]} intensity={isDark ? 0.5 : 0.9} castShadow={false} />
          <hemisphereLight args={[isDark ? "#3B4A63" : "#BFE3FF", "#2F6F4E", 0.5]} />
          <Suspense fallback={null}>
            <Bounds fit clip observe margin={1.35} key={`${scene.active_well_id}-${resetKey}`}>
              {toggles.grid && <GroundPlane size={groundSize} colors={colors} />}

              {toggles.formations && formationLayers.length > 0 && (
                <GeoBlock scene={scene} half={half} floorZ={-maxDepthM * 1.02} vertExag={vertExag} opacity={opacity}
                  showLabels={toggles.labels} clip={clipPlanes} onSelect={setSelectedLayer} />
              )}

              {toggles.riskBands && riskBands.map((b) => (
                <RiskBand key={b.formation} half={half} z={b.z} color={b.color} vertExag={vertExag}
                  label={toggles.labels ? bandTag(b, lang) : ""} active={selectedBand?.formation === b.formation} onSelect={() => setSelectedBand(b)} />
              ))}

              {activeWell && toggles.activeWell && (
                <group>
                  <WellTube well={activeWell} color={BRAND.via} vertExag={vertExag} isActive={bitMd == null} clip={clipPlanes} />
                  <DerrickGlyph well={activeWell} color={BRAND.via} half={half * SCALE} isActive />
                  {toggles.depthMarkers && <PathDepthMarkers well={activeWell} vertExag={vertExag} />}
                  {toggles.formations && activeWell.events.map((e) => <EventSphere key={`ev-${e.id}`} ev={e} vertExag={vertExag} lang={lang} onSelect={setSelected} />)}
                </group>
              )}

              {toggles.offsetWells && offsetWells.map((w, i) => (
                <group key={w.well_id}>
                  <WellTube well={w} color={wellColor(i)} vertExag={vertExag} isActive={false} clip={clipPlanes} />
                  <DerrickGlyph well={w} color={wellColor(i)} half={half * SCALE} isActive={false} />
                  {w.events.map((e) => <EventSphere key={`ev-${e.id}`} ev={e} vertExag={vertExag} lang={lang} onSelect={setSelected} />)}
                </group>
              ))}

              <DepthTicks maxDepthM={maxDepthM} x={-half * SCALE * 1.02} zPos={-half * SCALE * 1.02} colors={colors} vertExag={vertExag} />
            </Bounds>
            {/* outside <Bounds>: the moving bit must not trigger a camera re-fit */}
            {activeWell && toggles.activeWell && bitMd != null && (
              <DrillingProgress well={activeWell} bitMd={bitMd} lookaheadM={150} vertExag={vertExag} size={half * SCALE}
                label={`${lang === "hi" ? "बिट" : "bit"} ${Math.round(bitMd)} m`} />
            )}
          </Suspense>
          <OrbitControls ref={controlsRef} makeDefault enableDamping dampingFactor={0.1} />
          <CameraRig viewMode={viewMode} groundSize={groundSize} maxDepthM={maxDepthM} vertExag={vertExag} controlsRef={controlsRef} resetKey={resetKey} />
        </Canvas>

        {/* Controls (left) — compact embeds only; the full page uses the toolbar above */}
        {compact && <div style={{ position: "absolute", top: 10, left: 10, zIndex: 20 }}>
          <Controls
            lang={lang} toggles={toggles} setToggles={setToggles} viewMode={viewMode} setViewMode={setViewMode}
            opacity={opacity} setOpacity={setOpacity} vertExag={vertExag} setVertExag={setVertExag}
            onReset={resetAll}
            compact={compact}
          />
        </div>}

        {scene.wells.some((w) => w.assumed_vertical) && !(selected || selectedLayer || selectedBand) && (
          <div style={{ position: "absolute", bottom: compact ? 10 : 46, left: 10, zIndex: 20, ...tipStyle, color: "var(--caution)" }}>
            ⚠ {t("subsurfaceAssumedVertical", lang)}: {scene.wells.filter((w) => w.assumed_vertical).length}
          </div>
        )}

        {/* Selected-event / layer / band side card (bottom-left) */}
        {(selected || selectedLayer || selectedBand) && (
          <div style={{ position: "absolute", bottom: 10, left: 10, zIndex: 20, maxWidth: 320, ...tipStyle }}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
              <strong>{selected ? hazardText(selected.hazard, lang) : selectedLayer ? selectedLayer.label : selectedBand?.label}</strong>
              <button className="btn" style={{ padding: "1px 7px" }} onClick={() => { setSelected(null); setSelectedLayer(null); setSelectedBand(null); }} aria-label="close">✕</button>
            </div>
            {selected && (
              <>
                <div>{Math.round(selected.md)} m{selected.formation ? ` · ${selected.formation}` : ""}</div>
                {selected.evidence && <p style={{ marginTop: 4, fontStyle: "italic" }}>&ldquo;{selected.evidence}&rdquo;</p>}
                <OpenSourceButton refId={selected.source_ref} openSource={openSource} />
              </>
            )}
            {selectedLayer && (
              <div>{tr(lang, "From", "स्रोत")} {selectedLayer.nTops} {tr(lang, "top(s) in", "शीर्ष,")} {selectedLayer.nWells} {tr(lang, "well(s)", "कूप")}{selectedLayer.lithology ? ` · ${selectedLayer.lithology}` : ""}</div>
            )}
            {selectedBand && (
              <>
                <div>{selectedBand.hazards.map(([h, n]) => `${n}× ${hazardText(h, lang)}`).join(" · ")}</div>
                <div className="label">{tr(lang, "across", "में")} {selectedBand.nWells} {tr(lang, "well(s)", "कूप")}</div>
                <OpenSourceButton refId={selectedBand.sourceRef} openSource={openSource} />
              </>
            )}
          </div>
        )}

      </div>
      {!compact && (
        <LegendStrip>
          <LegendGroup title={tr(lang, "Wells", "कूप")}>
            <LegendRow color={BRAND.via} label={t("subsurfaceActiveWell", lang)} />
            {offsetWells.slice(0, 6).map((w, i) => <LegendRow key={w.well_id} color={wellColor(i)} label={w.name} />)}
            {offsetWells.length > 6 && <span className="label">+{offsetWells.length - 6} {tr(lang, "more", "और")}</span>}
          </LegendGroup>
          {formationLayers.length > 0 && (
            <LegendGroup title={tr(lang, "Formations", "संरचनाएँ")}>
              {formationLayers.slice(0, 8).map((f) => <LegendRow key={f.formation} color={f.color} label={f.label} />)}
              {formationLayers.length > 8 && <span className="label">+{formationLayers.length - 8} {tr(lang, "more (click a layer)", "और (परत पर क्लिक करें)")}</span>}
            </LegendGroup>
          )}
          {hazardsPresent.length > 0 && (
            <LegendGroup title={tr(lang, "Events (spheres)", "घटनाएँ")}>
              {hazardsPresent.map((h) => <LegendRow key={h} color={hazardColor(h)} label={hazardText(h, lang)} />)}
            </LegendGroup>
          )}
          {toggles.riskBands && riskBands.length > 0 && (
            <LegendGroup title={tr(lang, "Risk layers (click)", "जोखिम परतें")}>
              {[...riskBands].sort((a, b) => b.z - a.z).map((b) => (
                <button key={b.formation} type="button" onClick={() => setSelectedBand(b)} title={bandTag(b, lang)}
                  style={{ all: "unset", cursor: "pointer", borderRadius: 4, padding: "0 3px", outline: selectedBand?.formation === b.formation ? "1.5px solid var(--text)" : "none" }}>
                  <LegendRow color={b.color} label={`${b.label} · ${b.nWells}`} />
                </button>
              ))}
            </LegendGroup>
          )}
        </LegendStrip>
      )}
      <div className="label" style={{ margin: "0 2px" }}>{scene.projection}</div>

      {activeWell && <DepthProfileStrip well={activeWell} bitMd={bitMd} lang={lang} />}
    </div>
  );
}

function LegendStrip({ children }: { children: React.ReactNode }) {
  return <div style={{ display: "grid", gap: 6, fontSize: 12, padding: "8px 10px", border: "1px solid var(--border)", borderRadius: "var(--radius-lg)", background: "var(--surface)" }}>{children}</div>;
}

function LegendGroup({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
      <span className="eyebrow" style={{ flex: "0 0 120px", fontSize: 10.5 }}>{title}</span>
      <div style={{ display: "flex", flexWrap: "wrap", columnGap: 14, rowGap: 2, alignItems: "center" }}>{children}</div>
    </div>
  );
}

function LegendRow({ color, label }: { color: string; label: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <span style={{ width: 10, height: 10, borderRadius: 3, background: color, display: "inline-block", flex: "0 0 auto", border: "1px solid rgba(0,0,0,.15)" }} />
      <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{label}</span>
    </div>
  );
}

function OpenSourceButton({ refId, openSource }: { refId: string; openSource: (ref: string) => void }) {
  return <button className="btn btn-primary" style={{ marginTop: 6 }} onClick={() => openSource(refId)}>View source</button>;
}
