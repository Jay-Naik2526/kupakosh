// Shapes returned by GET /api/wells/{id}/scene (backend/app/api/routes_3d.py).
// x = east (m), y = north (m) relative to the active well's surface location; z = -TVD (m, down is negative).

export type ScenePoint = { md: number; x: number; y: number; z: number };

export type SceneFormationTop = {
  formation: string; label: string | null; md: number; x: number; y: number; z: number;
  z_is_approx_md: boolean; lithology: string | null; source_ref: string;
};

export type SceneEvent = {
  id: number; hazard: string; md: number; x: number; y: number; z: number;
  formation: string | null; source_ref: string; evidence: string | null; confidence: number;
};

export type SceneWell = {
  well_id: number; name: string; country: string | null; field: string | null;
  lat: number; lon: number; x: number; y: number;
  is_active: boolean; assumed_vertical: boolean;
  td_md_m: number | null; td_tvd_m: number | null;
  trajectory: ScenePoint[];
  formation_tops: SceneFormationTop[];
  events: SceneEvent[];
  distance_m?: number; similarity?: number; documented?: boolean;
};

export type Scene = {
  active_well_id: number; radius_m: number; projection: string; z_convention: string;
  n_wells: number; n_offsets: number; wells: SceneWell[];
  lookahead?: { bit_md_m: number; alerts: any[]; notices: any[] } | null;
};

// Hazards recorded as red ("hazard" state colour); everything else is amber ("caution").
// Kept in sync with backend/config/taxonomy.yaml hazard keys.
export const SEVERE_HAZARDS = new Set(["kick", "lost_circulation"]);
