"use client";
import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { useApp } from "@/lib/state";
import { t } from "@/lib/i18n";
import { EmptyState } from "@/components/kk/EmptyState";
import { get } from "@/lib/api";
const Subsurface3D = dynamic(() => import("@/components/v2/Subsurface3D").then((m) => m.Subsurface3D), { ssr: false, loading: () => <div className="kk-card" style={{ minHeight: 240, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-2)" }}>Loading…</div> });

const RADII = [5000, 10000, 20000, 50000];
const DEFAULT_REPLAY_WELL_NAME = "16B(78)-32";
const tr = (lang: string, en: string, hi: string) => (lang === "hi" ? hi : en);

/** Open the Ctrl+K command palette so the person can change the active well without a second picker on this page. */
function openCommandPalette() {
  window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", ctrlKey: true }));
}

export default function SubsurfacePage() {
  const { wellId, ready, lang } = useApp();
  const [radius, setRadius] = useState(10000);
  const [offsets, setOffsets] = useState<any[] | null>(null);
  const [fallback, setFallback] = useState<{ id: number; name: string } | null>(null);

  // No globally active well yet: default to the replay demo well so the screen never opens empty.
  useEffect(() => {
    if (wellId) return;
    get("/api/replay/wells").then((rows: any[]) => {
      const hit = rows.find((r) => r.name === DEFAULT_REPLAY_WELL_NAME) ?? rows[0];
      if (hit) setFallback({ id: hit.id, name: hit.name });
    }).catch(() => {});
  }, [wellId]);

  const effectiveId = wellId ?? fallback?.id ?? null;
  const [activeName, setActiveName] = useState<string | null>(null);
  useEffect(() => {
    if (!wellId) { setActiveName(fallback?.name ?? null); return; }
    let live = true;
    get(`/api/wells/${wellId}`).then((w: any) => { if (live) setActiveName(w?.name ?? null); }).catch(() => {});
    return () => { live = false; };
  }, [wellId, fallback]);

  useEffect(() => {
    if (!effectiveId) { setOffsets(null); return; }
    get(`/api/wells/${effectiveId}/offsets`, { radius_m: radius }).then((o) => setOffsets(o.offsets ?? o)).catch(() => setOffsets([]));
  }, [effectiveId, radius]);

  return (
    <div className="space-y-4">
      {/* Zone A: title + one-line question + active well (global) + radius picker */}
      <div className="kk-card">
        <h1 className="h-title">{t("subsurfaceTitle", lang)}</h1>
        <p className="label">{t("subsurfaceQuestion", lang)}</p>
        <div className="flex items-center gap-3 flex-wrap mt-3">
          <div className="flex items-center gap-2">
            <span className="label">{t("activeWell", lang)}</span>
            <span className="font-medium">{activeName ?? "—"}</span>
            {!wellId && fallback && <span className="label">({tr(lang, "default replay well", "डिफ़ॉल्ट पुनःचलन कूप")})</span>}
            <button type="button" className="btn" onClick={openCommandPalette}>{tr(lang, "Change (Ctrl+K)", "बदलें (Ctrl+K)")}</button>
          </div>
          <label className="label" htmlFor="radius">{t("offsetRadius", lang)}</label>
          <select id="radius" className="input" value={radius} onChange={(e) => setRadius(Number(e.target.value))}>
            {RADII.map((r) => <option key={r} value={r}>{(r / 1000).toLocaleString("en-IN")} km</option>)}
          </select>
        </div>
      </div>

      {!ready ? null : !effectiveId ? (
        // Zone B (empty state, no well available at all)
        <EmptyState title={t("subsurfaceNoWell", lang)} why={t("subsurfaceProjectionNote", lang)} />
      ) : (
        <div className="grid gap-4" style={{ gridTemplateColumns: "minmax(0,1fr) 320px" }}>
          {/* Zone B: the 3D canvas (tall — ~70vh; Subsurface3D's height prop is typed as px but plugs straight
              into a CSS `height`, so a viewport-relative string works fine at runtime). */}
          <Subsurface3D wellId={effectiveId} radius={radius} height={"70vh" as unknown as number} />

          {/* Zone C: offset wells list — distance, events */}
          <aside className="kk-card" style={{ maxHeight: "70vh", overflowY: "auto" }}>
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
