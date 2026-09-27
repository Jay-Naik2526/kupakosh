"use client";
import { useEffect, useState } from "react";
import { useApp } from "@/lib/state";
import { t } from "@/lib/i18n";
import { WellPicker } from "@/components/kk/WellPicker";
import { EmptyState } from "@/components/kk/EmptyState";
import { Subsurface3D } from "@/components/v2/Subsurface3D";
import { get } from "@/lib/api";

const RADII = [5000, 10000, 20000, 50000];

export default function SubsurfacePage() {
  const { wellId, ready, lang } = useApp();
  const [radius, setRadius] = useState(10000);
  const [offsets, setOffsets] = useState<any[] | null>(null);

  useEffect(() => {
    if (!wellId) { setOffsets(null); return; }
    get(`/api/wells/${wellId}/offsets`, { radius_m: radius }).then((o) => setOffsets(o.offsets ?? o)).catch(() => setOffsets([]));
  }, [wellId, radius]);

  return (
    <div className="space-y-4">
      {/* Zone A: title + one-line question + well/radius picker */}
      <div className="kk-card">
        <h1 className="h-title">{t("subsurfaceTitle", lang)}</h1>
        <p className="label">{t("subsurfaceQuestion", lang)}</p>
        <div className="flex items-center gap-3 flex-wrap mt-3">
          <WellPicker />
          <label className="label" htmlFor="radius">{t("offsetRadius", lang)}</label>
          <select id="radius" className="input" value={radius} onChange={(e) => setRadius(Number(e.target.value))}>
            {RADII.map((r) => <option key={r} value={r}>{(r / 1000).toLocaleString("en-IN")} km</option>)}
          </select>
        </div>
      </div>

      {!ready ? null : !wellId ? (
        // Zone B (empty state, no well picked yet)
        <EmptyState title={t("subsurfaceNoWell", lang)} why={t("subsurfaceProjectionNote", lang)} />
      ) : (
        <div className="grid gap-4" style={{ gridTemplateColumns: "minmax(0,1fr) 320px" }}>
          {/* Zone B: the 3D canvas (tall) */}
          <Subsurface3D wellId={wellId} radius={radius} height={640} />

          {/* Zone C: offset wells list — distance, events */}
          <aside className="kk-card" style={{ maxHeight: 640, overflowY: "auto" }}>
            <div className="font-semibold mb-2">{t("subsurfaceOffsetWells", lang)}</div>
            {offsets === null && <div className="label">{t("subsurfaceLoading", lang)}</div>}
            {offsets !== null && offsets.length === 0 && <EmptyState title={t("insufficient", lang)} why={t("subsurfaceProjectionNote", lang)} />}
            <ul className="space-y-2">
              {offsets?.map((o: any) => (
                <li key={o.well_id} className="rule-b pb-2">
                  <div className="font-medium">{o.name}</div>
                  <div className="label">{t("subsurfaceDistance", lang)}: <span className="mono">{Math.round(o.raw?.distance_m ?? 0).toLocaleString("en-IN")} m</span></div>
                  <div className="label">{t("subsurfaceEvents", lang)}: {o.n_events ?? 0}</div>
                </li>
              ))}
            </ul>
          </aside>
        </div>
      )}
    </div>
  );
}
