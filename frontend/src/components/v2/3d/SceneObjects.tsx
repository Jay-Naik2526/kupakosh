"use client";
import { useMemo, useState, type CSSProperties } from "react";
import { Html, Line } from "@react-three/drei";
import { SceneEvent, SceneFormationTop, SceneWell, SEVERE_HAZARDS } from "./types";
import { lithColor, ThemeColors } from "./useThemeColors";
import { hazardText } from "@/lib/format";
import type { Lang } from "@/lib/i18n";

export const SCALE = 0.01; // 1 scene unit = 100 m (keeps the camera / controls at a sane numeric range)

// Inline (not global CSS) since this component doesn't own globals.css — kept theme-aware via CSS vars.
export const tipStyle: CSSProperties = {
  background: "var(--surface, #fff)", color: "var(--text, #101828)", border: "1px solid var(--border, #E4E7EC)",
  borderRadius: 8, padding: "6px 9px", fontSize: 12, lineHeight: 1.4, whiteSpace: "nowrap",
  boxShadow: "var(--shadow-md, 0 4px 12px rgba(16,24,40,.08))",
};
const tickStyle: CSSProperties = { color: "var(--text-2, #5D6673)", fontSize: 10, fontFamily: "var(--font-plex-mono), ui-monospace, monospace" };

export function toScene(x: number, y: number, z: number, vertExag: number): [number, number, number] {
  // three.js: Y is "up". Scene y (screen-vertical) = depth; scene z (screen-depth) = geographic north.
  return [x * SCALE, z * SCALE * vertExag, y * SCALE];
}

export function WellPath({ well, colors, vertExag }: { well: SceneWell; colors: ThemeColors; vertExag: number }) {
  const points = useMemo(
    () => well.trajectory.map((p) => toScene(p.x, p.y, p.z, vertExag)) as [number, number, number][],
    [well.trajectory, vertExag],
  );
  if (points.length < 2) return null;
  const color = well.is_active ? colors.accent : colors.text2;
  return <Line points={points} color={color} lineWidth={well.is_active ? 3.5 : 1.6} dashed={well.assumed_vertical} dashSize={0.15} gapSize={0.1} />;
}

export function WellheadMarker({ well, colors }: { well: SceneWell; colors: ThemeColors }) {
  const [x, y, z] = toScene(well.x, well.y, 0, 1);
  const [hover, setHover] = useState(false);
  return (
    <group position={[x, y, z]}>
      <mesh onPointerOver={() => setHover(true)} onPointerOut={() => setHover(false)}>
        <cylinderGeometry args={[0.05, 0.05, 0.02, 16]} />
        <meshStandardMaterial color={well.is_active ? colors.accent : colors.text2} />
      </mesh>
      {hover && (
        <Html distanceFactor={12} style={{ pointerEvents: "none" }}>
          <div style={tipStyle}>
            <strong>{well.name}</strong>{well.is_active ? " (active)" : ""}
            {well.distance_m !== undefined && <div>{Math.round(well.distance_m)} m away</div>}
            {well.assumed_vertical && <div>assumed vertical — no survey</div>}
          </div>
        </Html>
      )}
    </group>
  );
}

export function FormationTopMarker({ top, colors, vertExag }: { top: SceneFormationTop; colors: ThemeColors; vertExag: number }) {
  const [hover, setHover] = useState(false);
  const pos = toScene(top.x, top.y, top.z, vertExag);
  const color = lithColor(top.lithology, colors);
  return (
    <group position={pos}>
      <mesh rotation={[-Math.PI / 2, 0, 0]} onPointerOver={(e) => { e.stopPropagation(); setHover(true); }} onPointerOut={() => setHover(false)}>
        <ringGeometry args={[0.07, 0.11, 24]} />
        <meshBasicMaterial color={color} side={2} />
      </mesh>
      {hover && (
        <Html distanceFactor={10} style={{ pointerEvents: "none" }}>
          <div style={tipStyle}>
            <strong>{top.label ?? top.formation}</strong>
            <div>{Math.round(top.md)} m MD{top.z_is_approx_md ? " (TVD not recorded — MD shown)" : ""}</div>
            {top.lithology && <div>{top.lithology}</div>}
          </div>
        </Html>
      )}
    </group>
  );
}

export function EventGlyph({ ev, colors, vertExag, lang, onSelect }: {
  ev: SceneEvent; colors: ThemeColors; vertExag: number; lang: Lang; onSelect: (ev: SceneEvent) => void;
}) {
  const [hover, setHover] = useState(false);
  const pos = toScene(ev.x, ev.y, ev.z, vertExag);
  const severe = SEVERE_HAZARDS.has(ev.hazard);
  const color = severe ? colors.hazard : colors.caution;
  return (
    <group position={pos}>
      <mesh
        onPointerOver={(e) => { e.stopPropagation(); setHover(true); }}
        onPointerOut={() => setHover(false)}
        onClick={(e) => { e.stopPropagation(); onSelect(ev); }}
      >
        {severe ? <coneGeometry args={[0.09, 0.2, 12]} /> : <octahedronGeometry args={[0.1, 0]} />}
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={hover ? 0.6 : 0.15} />
      </mesh>
      {hover && (
        <Html distanceFactor={10} style={{ pointerEvents: "none" }}>
          <div style={tipStyle}>
            <strong style={{ color }}>{hazardText(ev.hazard, lang)}</strong>
            <div>{Math.round(ev.md)} m{ev.formation ? ` · ${ev.formation}` : ""}</div>
            <div className="small">click for source</div>
          </div>
        </Html>
      )}
    </group>
  );
}

export function GroundPlane({ size, colors }: { size: number; colors: ThemeColors }) {
  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.002, 0]}>
        <planeGeometry args={[size, size]} />
        <meshBasicMaterial color={colors.surface} transparent opacity={0.35} />
      </mesh>
      <gridHelper args={[size, Math.min(40, Math.max(8, Math.round(size / 2))), colors.border, colors.border]} />
      <NorthArrow size={size} colors={colors} />
    </group>
  );
}

function NorthArrow({ size, colors }: { size: number; colors: ThemeColors }) {
  const len = size * 0.08;
  const base: [number, number, number] = [-size / 2 + len * 0.6, 0.01, -size / 2 + len * 0.6];
  // scene z = geographic north (see toScene), so the arrow points along +z
  const tip: [number, number, number] = [base[0], base[1], base[2] + len];
  return (
    <group>
      <Line points={[base, tip]} color={colors.text} lineWidth={2} />
      <mesh position={tip} rotation={[Math.PI / 2, 0, 0]}>
        <coneGeometry args={[len * 0.12, len * 0.3, 8]} />
        <meshBasicMaterial color={colors.text} />
      </mesh>
      <Html position={[tip[0], tip[1], tip[2] + len * 0.15]} distanceFactor={10} style={{ pointerEvents: "none" }}>
        <div style={{ ...tipStyle, fontWeight: 700 }}>N</div>
      </Html>
    </group>
  );
}

/** Depth tick labels along a vertical rule near the scene's edge. */
export function DepthTicks({ maxDepthM, x, zPos, colors, vertExag }: { maxDepthM: number; x: number; zPos: number; colors: ThemeColors; vertExag: number }) {
  const step = maxDepthM > 4000 ? 1000 : maxDepthM > 1500 ? 500 : 250;
  const ticks = useMemo(() => {
    const out: number[] = [];
    for (let d = 0; d <= maxDepthM + step; d += step) out.push(d);
    return out;
  }, [maxDepthM, step]);
  return (
    <group>
      {ticks.map((d) => (
        <Html key={d} position={[x, -d * SCALE * vertExag, zPos]} distanceFactor={14} style={{ pointerEvents: "none" }}>
          <div style={tickStyle}>{d.toLocaleString("en-IN")} m</div>
        </Html>
      ))}
    </group>
  );
}
