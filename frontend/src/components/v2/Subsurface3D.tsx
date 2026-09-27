"use client";
import { Suspense, useEffect, useMemo, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { Bounds, OrbitControls } from "@react-three/drei";
import { get } from "@/lib/api";
import { useApp } from "@/lib/state";
import { t } from "@/lib/i18n";
import { hazardText } from "@/lib/format";
import { EmptyState } from "@/components/kk/EmptyState";
import { Scene, SceneEvent } from "./3d/types";
import { DepthTicks, EventGlyph, FormationTopMarker, GroundPlane, SCALE, WellheadMarker, WellPath, tipStyle } from "./3d/SceneObjects";
import { useThemeColors } from "./3d/useThemeColors";

/** Props: reusable so the Well Room / Hindsight screens can embed the same 3D room. */
export type Subsurface3DProps = {
  wellId: number | null;
  radius?: number;      // metres; falls back to the backend default (config offsets.default_radius_m)
  bitMd?: number | null; // current bit MD (m) — shows the look-ahead window when set (replay use)
  height?: number;       // canvas height in px; default fills the parent
};

function sceneBounds(scene: Scene, vertExag: number) {
  let maxHoriz = 0, maxDepth = 0;
  for (const w of scene.wells) {
    maxHoriz = Math.max(maxHoriz, Math.hypot(w.x, w.y));
    for (const p of w.trajectory) { maxHoriz = Math.max(maxHoriz, Math.hypot(p.x, p.y)); maxDepth = Math.max(maxDepth, -p.z); }
    for (const e of w.events) maxDepth = Math.max(maxDepth, -e.z);
    for (const f of w.formation_tops) maxDepth = Math.max(maxDepth, -f.z);
  }
  return { maxHorizM: Math.max(maxHoriz, 200), maxDepthM: Math.max(maxDepth, 200) };
}

export function Subsurface3D({ wellId, radius, bitMd, height }: Subsurface3DProps) {
  const { lang } = useApp();
  const [scene, setScene] = useState<Scene | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [vertExag, setVertExag] = useState(1);
  const [selected, setSelected] = useState<SceneEvent | null>(null);
  const colors = useThemeColors();

  useEffect(() => {
    setScene(null); setError(null); setSelected(null);
    if (!wellId) return;
    setLoading(true);
    const params: Record<string, any> = {};
    if (radius) params.radius_m = radius;
    if (bitMd != null) params.bit_md = bitMd;
    get<Scene>(`/api/wells/${wellId}/scene`, params)
      .then((s) => setScene(s))
      .catch((e) => setError(String(e?.message ?? e)))
      .finally(() => setLoading(false));
  }, [wellId, radius, bitMd]);

  const { maxHorizM, maxDepthM } = useMemo(() => (scene ? sceneBounds(scene, vertExag) : { maxHorizM: 200, maxDepthM: 200 }), [scene, vertExag]);
  const groundSize = Math.max(2, maxHorizM * SCALE * 2.4);

  if (!wellId) return <EmptyState title={t("subsurfaceNoWell", lang)} why={t("subsurfaceProjectionNote", lang)} />;
  if (error) {
    const noLocation = /422/.test(error);
    return <EmptyState title={noLocation ? t("subsurfaceNoLocation", lang) : "Could not load the 3D scene"} why={error} />;
  }
  if (loading || !scene) return <div className="kk-card" style={{ height: height ?? 480, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-2)" }}>{t("subsurfaceLoading", lang)}</div>;
  if (!scene.wells.length) return <EmptyState title={t("subsurfaceNoLocation", lang)} why={t("subsurfaceProjectionNote", lang)} />;

  const activeWell = scene.wells.find((w) => w.is_active);

  return (
    <div style={{ position: "relative", height: height ?? 520, borderRadius: "var(--radius-lg)", overflow: "hidden", border: "1px solid var(--border)" }}>
      <Canvas
        camera={{ position: [6, 4, 6], fov: 45, near: 0.01, far: 1000 }}
        style={{ background: colors.bg }}
        dpr={[1, 2]}
      >
        <ambientLight intensity={0.9} />
        <directionalLight position={[5, 8, 3]} intensity={0.6} />
        <Suspense fallback={null}>
          <Bounds fit clip observe margin={1.3} key={`${scene.active_well_id}-${vertExag}`}>
            <GroundPlane size={groundSize} colors={colors} />
            {scene.wells.map((w) => (
              <group key={w.well_id}>
                <WellPath well={w} colors={colors} vertExag={vertExag} />
                <WellheadMarker well={w} colors={colors} />
                {w.formation_tops.map((f, i) => <FormationTopMarker key={`${w.well_id}-top-${i}`} top={f} colors={colors} vertExag={vertExag} />)}
                {w.events.map((e) => <EventGlyph key={`${w.well_id}-ev-${e.id}`} ev={e} colors={colors} vertExag={vertExag} lang={lang} onSelect={setSelected} />)}
              </group>
            ))}
            <DepthTicks maxDepthM={maxDepthM} x={-groundSize / 2} zPos={-groundSize / 2} colors={colors} vertExag={vertExag} />
          </Bounds>
        </Suspense>
        <OrbitControls makeDefault enableDamping dampingFactor={0.1} />
      </Canvas>

      {/* Zone controls: vertical exaggeration + assumed-vertical badges (top-left) */}
      <div style={{ position: "absolute", top: 10, left: 10, display: "flex", flexDirection: "column", gap: 6 }}>
        <div style={{ ...tipStyle, display: "flex", alignItems: "center", gap: 8 }}>
          <label htmlFor="vertexag" className="label" style={{ margin: 0 }}>{t("subsurfaceVertExag", lang)}</label>
          <input id="vertexag" type="range" min={1} max={5} step={0.5} value={vertExag} onChange={(e) => setVertExag(Number(e.target.value))} />
          <span className="mono">{vertExag}×</span>
        </div>
        {scene.wells.some((w) => w.assumed_vertical) && (
          <div style={{ ...tipStyle, color: "var(--caution)" }}>⚠ {t("subsurfaceAssumedVertical", lang)}: {scene.wells.filter((w) => w.assumed_vertical).length}</div>
        )}
      </div>

      {/* Legend (top-right) */}
      <div style={{ position: "absolute", top: 10, right: 10, ...tipStyle }}>
        <div style={{ fontWeight: 600, marginBottom: 4 }}>{t("subsurfaceLegend", lang)}</div>
        <LegendRow color="var(--accent)" label={t("subsurfaceActiveWell", lang)} />
        <LegendRow color="var(--text-2)" label={t("subsurfaceOffsetWell", lang)} />
        <LegendRow color="var(--hazard)" label={`▲ ${hazardText("kick", lang)} / ${hazardText("lost_circulation", lang)}`} />
        <LegendRow color="var(--caution)" label="◆ other hazards" />
        <LegendRow color="var(--text-2)" label={`○ ${t("subsurfaceFormationTop", lang)}`} />
      </div>

      {/* Selected-event side card (bottom-left) */}
      {selected && (
        <div style={{ position: "absolute", bottom: 10, left: 10, maxWidth: 320, ...tipStyle }}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
            <strong>{hazardText(selected.hazard, lang)}</strong>
            <button className="btn" style={{ padding: "1px 7px" }} onClick={() => setSelected(null)} aria-label="close">✕</button>
          </div>
          <div>{Math.round(selected.md)} m{selected.formation ? ` · ${selected.formation}` : ""}</div>
          {selected.evidence && <p style={{ marginTop: 4, fontStyle: "italic" }}>&ldquo;{selected.evidence}&rdquo;</p>}
          <OpenSourceButton refId={selected.source_ref} />
        </div>
      )}

      <div style={{ position: "absolute", bottom: 10, right: 10, ...tipStyle, maxWidth: 260 }}>{scene.projection}</div>
    </div>
  );
}

function LegendRow({ color, label }: { color: string; label: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 2 }}>
      <span style={{ width: 10, height: 10, borderRadius: 999, background: color, display: "inline-block", flex: "0 0 auto" }} />
      <span>{label}</span>
    </div>
  );
}

function OpenSourceButton({ refId }: { refId: string }) {
  const { openSource } = useApp();
  return <button className="btn btn-primary" style={{ marginTop: 6 }} onClick={() => openSource(refId)}>View source</button>;
}
