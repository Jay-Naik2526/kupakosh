"use client";
// The "geological block": one translucent, coloured slab per formation that appears in >=1
// well of the current scene. Each slab's top surface is inverse-distance-weighted across the
// wells that recorded that formation (flat plane when only one well has it, per SPEC.md's
// "no invented numbers" rule — we only ever interpolate real tops, never guess a shape).
import { useMemo } from "react";
import * as THREE from "three";
import { Html } from "@react-three/drei";
import type { Scene } from "./types";
import { toScene, tipStyle } from "./SceneObjects";
import { formationColor } from "@/lib/palette";

type Corner = { x: number; y: number };
type Corner4 = [number, number, number, number];

export type FormationLayer = {
  formation: string; label: string; lithology: string | null;
  topZ: Corner4; color: string; nTops: number; nWells: number;
};

// Corners walk the block's footprint perimeter (used both for the IDW query points and the
// slab's side walls): [-x-y, +x-y, +x+y, -x+y].
function cornerSet(half: number): Corner[] {
  return [{ x: -half, y: -half }, { x: half, y: -half }, { x: half, y: half }, { x: -half, y: half }];
}

/** Inverse-distance-weighted top height at a corner, from real formation-top instances only. */
function idw(corner: Corner, pts: { x: number; y: number; z: number }[]): number {
  if (pts.length === 1) return pts[0].z;
  let num = 0, den = 0;
  for (const p of pts) {
    const d2 = (corner.x - p.x) ** 2 + (corner.y - p.y) ** 2;
    if (d2 < 4) return p.z; // within 2 m of the well: use its own top exactly
    const w = 1 / d2;
    num += w * p.z; den += w;
  }
  return den > 0 ? num / den : pts[0].z;
}

export function buildFormationLayers(scene: Scene, half: number): FormationLayer[] {
  const corners = cornerSet(half);
  const byFormation = new Map<string, { label: string; lithology: string | null; pts: { x: number; y: number; z: number }[]; wells: Set<number> }>();
  for (const w of scene.wells) {
    for (const f of w.formation_tops) {
      let rec = byFormation.get(f.formation);
      if (!rec) { rec = { label: f.label ?? f.formation, lithology: f.lithology, pts: [], wells: new Set() }; byFormation.set(f.formation, rec); }
      rec.pts.push({ x: w.x, y: w.y, z: f.z });
      rec.wells.add(w.well_id);
      if (f.lithology && !rec.lithology) rec.lithology = f.lithology;
    }
  }
  const layers: FormationLayer[] = [];
  Array.from(byFormation.entries()).forEach(([formation, rec]) => {
    const topZ = corners.map((c) => idw(c, rec.pts)) as Corner4;
    layers.push({ formation, label: rec.label, lithology: rec.lithology, topZ, color: formationColor(formation, rec.lithology), nTops: rec.pts.length, nWells: rec.wells.size });
  });
  // Shallowest (z nearest 0) first, so the block reads top-to-bottom like a real column.
  layers.sort((a, b) => (b.topZ.reduce((s, z) => s + z, 0) - a.topZ.reduce((s, z) => s + z, 0)));
  return layers;
}

function buildSlabGeometry(half: number, topZ: Corner4, bottomZ: Corner4, vertExag: number): THREE.BufferGeometry {
  const corners = cornerSet(half);
  const top = corners.map((c, i) => toScene(c.x, c.y, topZ[i], vertExag));
  const bot = corners.map((c, i) => toScene(c.x, c.y, bottomZ[i], vertExag));
  const positions = new Float32Array([...top.flat(), ...bot.flat()]);
  const idx: number[] = [0, 1, 2, 0, 2, 3, 4, 6, 5, 4, 7, 6];
  for (let e = 0; e < 4; e++) { const a = e, b = (e + 1) % 4; idx.push(a, b, b + 4, a, b + 4, a + 4); }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geo.setIndex(idx);
  geo.computeVertexNormals();
  return geo;
}

function FormationSlab({ layer, bottomZ, half, vertExag, opacity, showLabel, clip, onSelect }: {
  layer: FormationLayer; bottomZ: Corner4; half: number; vertExag: number; opacity: number; showLabel: boolean;
  clip: THREE.Plane[]; onSelect?: (l: FormationLayer) => void;
}) {
  const geometry = useMemo(() => buildSlabGeometry(half, layer.topZ, bottomZ, vertExag), [half, layer.topZ, bottomZ, vertExag]);
  const midZ = (layer.topZ[1] + bottomZ[1]) / 2;
  const labelPos = toScene(half * 1.06, -half * 1.06, midZ, vertExag);
  return (
    <group>
      <mesh geometry={geometry} onClick={(e) => { e.stopPropagation(); onSelect?.(layer); }}>
        <meshStandardMaterial
          color={layer.color} transparent opacity={opacity} side={THREE.DoubleSide}
          roughness={0.85} metalness={0} depthWrite={false} clippingPlanes={clip}
          emissive={layer.color} emissiveIntensity={0.28}
        />
      </mesh>
      <lineSegments>
        <edgesGeometry args={[geometry]} />
        <lineBasicMaterial color={layer.color} clippingPlanes={clip} />
      </lineSegments>
      {showLabel && (
        <Html position={labelPos} style={{ pointerEvents: "none" }}>
          <div style={{ ...tipStyle, display: "flex", alignItems: "center", gap: 6, whiteSpace: "nowrap" }}>
            <span style={{ width: 10, height: 10, borderRadius: 2, background: layer.color, flex: "0 0 auto", border: "1px solid rgba(0,0,0,.2)" }} />
            <strong>{layer.label}</strong>
            {layer.lithology && <span style={{ color: "var(--text-2, #667)" }}>· {layer.lithology}</span>}
          </div>
        </Html>
      )}
    </group>
  );
}

export function GeoBlock({ scene, half, floorZ, vertExag, opacity, showLabels, clip, onSelect }: {
  scene: Scene; half: number; floorZ: number; vertExag: number; opacity: number; showLabels: boolean;
  clip: THREE.Plane[]; onSelect?: (l: FormationLayer) => void;
}) {
  const layers = useMemo(() => buildFormationLayers(scene, half), [scene, half]);
  if (!layers.length) return null;
  // With many real formations (Volve: 40+), slab labels would pile up; the legend names every layer and a click opens its card.
  const thick = layers.map((l, i) => {
    const next = i < layers.length - 1 ? layers[i + 1].topZ[1] : floorZ;
    return { f: l.formation, t: l.topZ[1] - next };
  }).sort((a, b) => b.t - a.t).slice(0, 8).map((x) => x.f);
  const labelled = new Set(layers.length <= 8 ? thick : []);
  return (
    <group>
      {layers.map((layer, i) => {
        const nextTop = i < layers.length - 1 ? layers[i + 1].topZ : ([floorZ, floorZ, floorZ, floorZ] as Corner4);
        const bottomZ = nextTop.map((z, k) => Math.min(z, layer.topZ[k] - 0.5)) as Corner4;
        return (
          <FormationSlab
            key={layer.formation} layer={layer} bottomZ={bottomZ} half={half} vertExag={vertExag}
            opacity={opacity} showLabel={showLabels && labelled.has(layer.formation)} clip={clip} onSelect={onSelect}
          />
        );
      })}
    </group>
  );
}
