"use client";
import { useMemo, useRef, useState, type CSSProperties } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { Html, Line } from "@react-three/drei";
import { SceneEvent, SceneWell } from "./types";
import { ThemeColors } from "./useThemeColors";
import { hazardColor } from "@/lib/palette";
import { hazardText } from "@/lib/format";
import type { Lang } from "@/lib/i18n";

export const SCALE = 0.01; // 1 scene unit = 100 m (keeps the camera / controls at a sane numeric range)

// Inline (not global CSS) since this component doesn't own globals.css — kept theme-aware via CSS vars.
export const tipStyle: CSSProperties = {
  background: "var(--surface, #fff)", color: "var(--text, #101828)", border: "1px solid var(--border, #E4E7EC)",
  borderRadius: 6, padding: "6px 9px", fontSize: 12, lineHeight: 1.4, whiteSpace: "nowrap",
};
const tickStyle: CSSProperties = { color: "var(--text-2, #5D6673)", fontSize: 10, fontFamily: "var(--font-plex-mono), ui-monospace, monospace", fontWeight: 600, whiteSpace: "nowrap", transform: "translate(6px, -50%)" };

export function toScene(x: number, y: number, z: number, vertExag: number): [number, number, number] {
  // three.js: Y is "up". Scene y (screen-vertical) = depth; scene z (screen-depth) = geographic north.
  return [x * SCALE, z * SCALE * vertExag, y * SCALE];
}

/** A real 3D tube along the well's trajectory (not a flat line) so wells read as pipes in the block. */
export function WellTube({ well, color, vertExag, isActive, clip }: { well: SceneWell; color: string; vertExag: number; isActive: boolean; clip: THREE.Plane[] }) {
  const geometry = useMemo(() => {
    const pts = well.trajectory.map((p) => new THREE.Vector3(...toScene(p.x, p.y, p.z, vertExag)));
    if (pts.length < 2) return null;
    const curve = new THREE.CatmullRomCurve3(pts);
    const radius = isActive ? 0.05 : 0.03;
    return new THREE.TubeGeometry(curve, Math.max(16, pts.length * 8), radius, 8, false);
  }, [well.trajectory, vertExag, isActive]);
  if (!geometry) return null;
  return (
    <group>
      <mesh geometry={geometry}>
        <meshStandardMaterial
          color={color} emissive={color} emissiveIntensity={isActive ? 0.55 : 0.08}
          roughness={0.35} metalness={0.25} transparent={well.assumed_vertical} opacity={well.assumed_vertical ? 0.6 : 1}
          clippingPlanes={clip}
        />
      </mesh>
      {isActive && (
        // Soft outer glow: a larger, additive, near-transparent duplicate of the same tube.
        <mesh geometry={geometry} scale={1.9}>
          <meshBasicMaterial color={color} transparent opacity={0.16} blending={THREE.AdditiveBlending} depthWrite={false} clippingPlanes={clip} />
        </mesh>
      )}
    </group>
  );
}

/** A small tapered derrick (tower + base) at the wellhead, coloured to match its tube, with a name tag.
 * `half` is the block's half-width in *scene units* (already SCALE'd), so the glyph stays proportional. */
export function DerrickGlyph({ well, color, half, isActive }: { well: SceneWell; color: string; half: number; isActive: boolean }) {
  const [hover, setHover] = useState(false);
  const [x, y, z] = toScene(well.x, well.y, 0, 1);
  const s = Math.max(half * 0.05, 0.15) * (isActive ? 1.4 : 1);
  return (
    <group position={[x, y, z]} onPointerOver={(e) => { e.stopPropagation(); setHover(true); }} onPointerOut={() => setHover(false)}>
      <mesh position={[0, s * 0.05, 0]}>
        <boxGeometry args={[s * 0.9, s * 0.1, s * 0.9]} />
        <meshStandardMaterial color={color} roughness={0.6} />
      </mesh>
      {/* Thin mast + small tip — reads as a tower silhouette from any camera angle, unlike a wide cone. */}
      <mesh position={[0, s * 1.7, 0]}>
        <cylinderGeometry args={[s * 0.05, s * 0.07, s * 3.2, 8]} />
        <meshStandardMaterial color={color} roughness={0.4} metalness={0.3} emissive={color} emissiveIntensity={isActive ? 0.35 : 0.1} />
      </mesh>
      <mesh position={[0, s * 3.45, 0]}>
        <coneGeometry args={[s * 0.11, s * 0.4, 8]} />
        <meshStandardMaterial color={color} roughness={0.4} metalness={0.3} emissive={color} emissiveIntensity={isActive ? 0.35 : 0.1} />
      </mesh>
      {(isActive || hover) && (
        <Html position={[0, s * 3.6, 0]} zIndexRange={[10, 0]} style={{ pointerEvents: "none" }}>
          <div style={{ ...tipStyle, fontWeight: isActive ? 700 : 500, borderColor: color }}>
            {well.name}{isActive ? " ★" : ""}
          </div>
        </Html>
      )}
      {hover && (
        <Html position={[0, s * 1.2, 0]} zIndexRange={[10, 0]} style={{ pointerEvents: "none" }}>
          <div style={tipStyle}>
            {well.country ?? "—"}{well.field ? ` · ${well.field}` : ""}
            {well.distance_m !== undefined && <div>{Math.round(well.distance_m).toLocaleString("en-IN")} m away</div>}
            {well.td_md_m && <div>TD {Math.round(well.td_md_m).toLocaleString("en-IN")} m</div>}
            {well.assumed_vertical && <div>assumed vertical — no survey</div>}
          </div>
        </Html>
      )}
    </group>
  );
}

/** A glowing sphere per recorded event, coloured by hazard type (palette.ts) so every hazard reads distinctly. */
export function EventSphere({ ev, vertExag, lang, onSelect }: { ev: SceneEvent; vertExag: number; lang: Lang; onSelect: (ev: SceneEvent) => void }) {
  const [hover, setHover] = useState(false);
  const pos = toScene(ev.x, ev.y, ev.z, vertExag);
  const color = hazardColor(ev.hazard);
  const r = hover ? 0.09 : 0.075;
  return (
    <group position={pos}>
      <mesh onPointerOver={(e) => { e.stopPropagation(); setHover(true); }} onPointerOut={() => setHover(false)} onClick={(e) => { e.stopPropagation(); onSelect(ev); }}>
        <sphereGeometry args={[r, 20, 20]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={hover ? 1.1 : 0.65} roughness={0.3} />
      </mesh>
      <mesh scale={2.1}>
        <sphereGeometry args={[r, 16, 16]} />
        <meshBasicMaterial color={color} transparent opacity={hover ? 0.28 : 0.16} blending={THREE.AdditiveBlending} depthWrite={false} />
      </mesh>
      {hover && (
        <Html zIndexRange={[10, 0]} style={{ pointerEvents: "none" }}>
          <div style={tipStyle}>
            <strong style={{ color }}>{hazardText(ev.hazard, lang)}</strong>
            <div>{Math.round(ev.md)} m{ev.formation ? ` · ${ev.formation}` : ""}</div>
            <div>click for source</div>
          </div>
        </Html>
      )}
    </group>
  );
}

/** A glowing translucent depth band where recorded events cluster in a formation, tagged with a real count. */
export function RiskBand({ half, z, color, label, vertExag, active, onSelect }: {
  half: number; z: number; color: string; label: string; vertExag: number; active?: boolean; onSelect?: () => void;
}) {
  const [hover, setHover] = useState(false);
  const y = z * SCALE * vertExag;
  const r = half * SCALE;
  return (
    <group position={[0, y, 0]} onClick={(e) => { e.stopPropagation(); onSelect?.(); }} onPointerOver={(e) => { e.stopPropagation(); setHover(true); }} onPointerOut={() => setHover(false)}>
      <mesh rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[r * 0.985, r * 1.03, 64]} />
        <meshBasicMaterial color={color} transparent opacity={hover ? 0.85 : 0.55} side={THREE.DoubleSide} blending={THREE.AdditiveBlending} depthWrite={false} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[r * 0.9, r * 1.08, 64]} />
        <meshBasicMaterial color={color} transparent opacity={hover ? 0.28 : 0.14} side={THREE.DoubleSide} blending={THREE.AdditiveBlending} depthWrite={false} />
      </mesh>
      {/* Label only on hover/selection: always-on labels for every band piled on top of each other. The legend lists them all. */}
      {label && (hover || active) && (
        <Html position={[r * 1.05, 0, r * 1.05]} zIndexRange={[10, 0]} style={{ pointerEvents: "none" }}>
          <div style={{ ...tipStyle, borderColor: color, fontWeight: 600 }}>{label}</div>
        </Html>
      )}
    </group>
  );
}

/** Formation-top hollow rings threaded along a well's actual trajectory (kept small and neutral so the
 * geological block's own slabs carry the colour; this just marks the well's own recorded tops). */
export function FormationTopMarker({ x, y, z, color, vertExag, hoverLabel }: { x: number; y: number; z: number; color: string; vertExag: number; hoverLabel: string }) {
  const [hover, setHover] = useState(false);
  const pos = toScene(x, y, z, vertExag);
  return (
    <group position={pos}>
      <mesh rotation={[-Math.PI / 2, 0, 0]} onPointerOver={(e) => { e.stopPropagation(); setHover(true); }} onPointerOut={() => setHover(false)}>
        <ringGeometry args={[0.05, 0.075, 20]} />
        <meshBasicMaterial color={color} side={THREE.DoubleSide} />
      </mesh>
      {hover && <Html zIndexRange={[10, 0]} style={{ pointerEvents: "none" }}><div style={tipStyle}>{hoverLabel}</div></Html>}
    </group>
  );
}

/** Depth-marker tags every 500/1000 m along the active well's own trajectory (not the edge ruler). */
export function interpAtMd(traj: { md: number; x: number; y: number; z: number }[], md: number): [number, number, number] | null {
  if (!traj.length) return null;
  if (md <= traj[0].md) return [traj[0].x, traj[0].y, traj[0].z];
  if (md >= traj[traj.length - 1].md) { const l = traj[traj.length - 1]; return [l.x, l.y, l.z]; }
  for (let i = 0; i < traj.length - 1; i++) {
    const a = traj[i], b = traj[i + 1];
    if (a.md <= md && md <= b.md) {
      const f = b.md > a.md ? (md - a.md) / (b.md - a.md) : 0;
      return [a.x + f * (b.x - a.x), a.y + f * (b.y - a.y), a.z + f * (b.z - a.z)];
    }
  }
  return null;
}

export function PathDepthMarkers({ well, vertExag }: { well: SceneWell; vertExag: number }) {
  const maxMd = well.trajectory.length ? well.trajectory[well.trajectory.length - 1].md : 0;
  const step = maxMd > 3000 ? 1000 : 500;
  const marks = useMemo(() => { const out: number[] = []; for (let d = step; d < maxMd; d += step) out.push(d); return out; }, [maxMd, step]);
  return (
    <group>
      {marks.map((md) => {
        const p = interpAtMd(well.trajectory, md);
        if (!p) return null;
        return (
          <Html key={md} position={toScene(p[0], p[1], p[2], vertExag)} zIndexRange={[10, 0]} style={{ pointerEvents: "none" }}>
            <div style={{ ...tickStyle, background: "var(--surface, #fff)", border: "1px solid var(--border,#E4E7EC)", borderRadius: 4, padding: "1px 5px" }}>{md.toLocaleString("en-IN")} m</div>
          </Html>
        );
      })}
    </group>
  );
}

/** A vivid ground/terrain slab (not a neutral theme surface) plus grid + compass. */
export function GroundPlane({ size, colors }: { size: number; colors: ThemeColors }) {
  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.004, 0]}>
        <planeGeometry args={[size, size]} />
        <meshStandardMaterial color="#2F6F4E" roughness={1} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.002, 0]}>
        <planeGeometry args={[size, size]} />
        <meshBasicMaterial color="#F59E0B" transparent opacity={0.05} />
      </mesh>
      <gridHelper args={[size, Math.min(40, Math.max(8, Math.round(size / 2))), "#F59E0B", colors.border]} position={[0, -0.001, 0]} />
      <NorthArrow size={size} colors={colors} />
    </group>
  );
}

function NorthArrow({ size, colors }: { size: number; colors: ThemeColors }) {
  const len = size * 0.08;
  const base: [number, number, number] = [-size / 2 + len * 0.6, 0.01, -size / 2 + len * 0.6];
  const tip: [number, number, number] = [base[0], base[1], base[2] + len];
  return (
    <group>
      <Line points={[base, tip]} color={colors.text} lineWidth={2} />
      <mesh position={tip} rotation={[Math.PI / 2, 0, 0]}>
        <coneGeometry args={[len * 0.12, len * 0.3, 8]} />
        <meshBasicMaterial color={colors.text} />
      </mesh>
      <Html position={[tip[0], tip[1], tip[2] + len * 0.15]} zIndexRange={[10, 0]} style={{ pointerEvents: "none" }}>
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
      <Line points={[[x, 0, zPos], [x, -maxDepthM * SCALE * vertExag, zPos]]} color={colors.text2} lineWidth={1.5} />
      {ticks.filter((d) => d > 0).map((d) => (
        <group key={d}>
          <Line points={[[x, -d * SCALE * vertExag, zPos], [x + 0.06, -d * SCALE * vertExag, zPos]]} color={colors.text2} lineWidth={1.5} />
          <Html position={[x, -d * SCALE * vertExag, zPos]} zIndexRange={[10, 0]} style={{ pointerEvents: "none" }}>
            <div style={tickStyle}>{d.toLocaleString("en-IN")} m</div>
          </Html>
        </group>
      ))}
    </group>
  );
}

function pointAtMd(tr: SceneWell["trajectory"], md: number): { x: number; y: number; z: number } | null {
  if (!tr.length) return null;
  if (md <= tr[0].md) return tr[0];
  for (let i = 1; i < tr.length; i++) {
    if (tr[i].md >= md) {
      const a = tr[i - 1], b = tr[i];
      const f = b.md > a.md ? (md - a.md) / (b.md - a.md) : 0;
      return { x: a.x + (b.x - a.x) * f, y: a.y + (b.y - a.y) * f, z: a.z + (b.z - a.z) * f };
    }
  }
  return tr[tr.length - 1];
}

/** The part of the trajectory between two measured depths, as scene points (for the drilled hole and the look-ahead window). */
function segment(tr: SceneWell["trajectory"], from: number, to: number, vertExag: number): THREE.Vector3[] {
  const pts: { x: number; y: number; z: number }[] = [];
  const a = pointAtMd(tr, from), b = pointAtMd(tr, to);
  if (!a || !b || to <= from) return [];
  pts.push(a);
  for (const p of tr) if (p.md > from && p.md < to) pts.push(p);
  pts.push(b);
  return pts.map((p) => new THREE.Vector3(...toScene(p.x, p.y, p.z, vertExag)));
}

function Tube({ pts, radius, color, opacity = 1, emissive = 0.6 }: { pts: THREE.Vector3[]; radius: number; color: string; opacity?: number; emissive?: number }) {
  const geometry = useMemo(() => {
    if (pts.length < 2) return null;
    if (pts.length === 2) pts = [pts[0], pts[0].clone().lerp(pts[1], 0.5), pts[1]];
    return new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), Math.max(12, pts.length * 6), radius, 10, false);
  }, [pts, radius]);
  if (!geometry) return null;
  return (
    // drawn over the translucent rock block (depthTest off, late render order): the hole is the point of the view
    <mesh geometry={geometry} renderOrder={20}>
      <meshStandardMaterial color={color} emissive={color} emissiveIntensity={emissive} transparent opacity={opacity} depthTest={false} depthWrite={false} fog={false} />
    </mesh>
  );
}

/** Drilling progress during a replay: the hole already drilled (surface to the bit) as a solid tube that grows each
 *  tick, the look-ahead window below the bit in amber, and a rotating bit. Only real values are used: the bit depth
 *  comes from the recorded sensor data, the path from the well's survey (or "assumed vertical"). */
export function DrillingProgress({ well, bitMd, lookaheadM, vertExag, label, size }: { well: SceneWell; bitMd: number; lookaheadM: number; vertExag: number; label: string; size: number }) {
  const tr = well.trajectory;
  // drawn relative to the block size (size = half-width in scene units), so the hole and bit stay visible at a 10 km radius
  const r = Math.max(0.08, size * 0.035);
  const drilled = useMemo(() => segment(tr, tr.length ? tr[0].md : 0, bitMd, vertExag), [tr, bitMd, vertExag]);
  const ahead = useMemo(() => segment(tr, bitMd, bitMd + lookaheadM, vertExag), [tr, bitMd, lookaheadM, vertExag]);
  const bit = useMemo(() => { const p = pointAtMd(tr, bitMd); return p ? toScene(p.x, p.y, p.z, vertExag) : null; }, [tr, bitMd, vertExag]);
  const spin = useRef<THREE.Group>(null);
  useFrame((_, dt) => { if (spin.current) spin.current.rotation.y += dt * 4; });
  if (!bit) return null;
  return (
    <group>
      <Tube pts={drilled} radius={r} color="#7A4A2A" emissive={0.35} />
      <Tube pts={ahead} radius={r * 1.15} color="#C98A12" opacity={0.6} emissive={0.8} />
      <group position={bit}>
        <group ref={spin}>
          {/* tri-cone style bit: point down */}
          <mesh rotation={[Math.PI, 0, 0]} position={[0, -r * 0.8, 0]} renderOrder={22}>
            <coneGeometry args={[r * 2.2, r * 3.4, 3]} />
            <meshStandardMaterial color="#B23A1E" emissive="#B23A1E" emissiveIntensity={0.7} metalness={0.4} roughness={0.35} transparent depthTest={false} fog={false} />
          </mesh>
        </group>
        <mesh scale={2.4} renderOrder={21}>
          <sphereGeometry args={[r * 1.6, 16, 16]} />
          <meshBasicMaterial color="#B23A1E" transparent opacity={0.18} depthWrite={false} depthTest={false} fog={false} />
        </mesh>
        <Html center zIndexRange={[10, 0]} style={{ pointerEvents: "none" }}>
          <div style={{ transform: "translate(40px, 0)", background: "var(--surface, #fff)", border: "1px solid #B23A1E", color: "#B23A1E",
                        fontFamily: "var(--font-plex-mono)", fontSize: 11, padding: "1px 6px", borderRadius: 3, whiteSpace: "nowrap" }}>{label}</div>
        </Html>
      </group>
    </group>
  );
}
