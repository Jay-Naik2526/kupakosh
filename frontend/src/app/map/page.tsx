"use client";
import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft, ChevronRight, Search, X } from "lucide-react";
import { get } from "@/lib/api";
import { useApp } from "@/lib/state";
import { t } from "@/lib/i18n";
import { Card, PageHeader, Button, Badge } from "@/components/v2/ui";
import { CountryFilter } from "@/components/kk/CountryFilter";
import { EmptyState } from "@/components/kk/EmptyState";
import type { SelectedWell, SelectedBasin, FlyTarget } from "@/components/v2/WellMap";
const WellMap = dynamic(() => import("@/components/v2/WellMap").then((m) => m.WellMap), { ssr: false, loading: () => <div className="kk-card" style={{ minHeight: 240, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-2)" }}>Loading…</div> });

type WellDetail = {
  id: number; name: string; country: string | null; lat: number | null; lon: number | null;
  operator: string | null; td_md_m: number | null; n_events: number; documented: boolean;
};

type OffsetRow = {
  well_id: number; name: string; lat: number; lon: number; documented: boolean; n_events: number;
  sim: number; raw: { distance_m: number };
};

/**
 * 02 Map (docs/PLAN_V2.md V4). Zone A: title + question + search + country filter. Zone B: the map
 * (WellMap.tsx). Zone C: a collapsible right panel — the selected well's card, or the radius controls
 * and the list of wells inside the active well's radius.
 */
export default function MapPage() {
  const router = useRouter();
  const { wellId, setWellId, country, lang, theme } = useApp();

  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selected, setSelected] = useState<WellDetail | null>(null);
  const [selectedBasin, setSelectedBasin] = useState<SelectedBasin | null>(null);
  const [flyTarget, setFlyTarget] = useState<FlyTarget>(null);
  const [panelOpen, setPanelOpen] = useState(true);

  const [activeWellDetail, setActiveWellDetail] = useState<WellDetail | null>(null);
  const [radiusKm, setRadiusKm] = useState(10);
  const [radiusList, setRadiusList] = useState<OffsetRow[]>([]);
  const [radiusLoading, setRadiusLoading] = useState(false);

  const [q, setQ] = useState("");
  const [searchResults, setSearchResults] = useState<WellDetail[]>([]);

  // Selected well's card details (id-only from a map click carries just the geo-payload's minimal props).
  useEffect(() => {
    if (!selectedId) { setSelected(null); return; }
    let live = true;
    get<WellDetail>(`/api/wells/${selectedId}`).then((w) => { if (live) setSelected(w); }).catch(() => { if (live) setSelected(null); });
    return () => { live = false; };
  }, [selectedId]);

  // The globally active well (useApp().wellId) — drives the radius circle drawn on the map.
  useEffect(() => {
    if (!wellId) { setActiveWellDetail(null); return; }
    let live = true;
    get<WellDetail>(`/api/wells/${wellId}`).then((w) => { if (live) setActiveWellDetail(w); }).catch(() => { if (live) setActiveWellDetail(null); });
    return () => { live = false; };
  }, [wellId]);

  // Wells inside the active well's radius.
  useEffect(() => {
    if (!wellId) { setRadiusList([]); return; }
    setRadiusLoading(true);
    get(`/api/wells/${wellId}/offsets`, { radius_m: radiusKm * 1000, country: country ?? undefined })
      .then((r) => setRadiusList(r.offsets ?? []))
      .catch(() => setRadiusList([]))
      .finally(() => setRadiusLoading(false));
  }, [wellId, radiusKm, country]);

  // Jump-to-well search.
  useEffect(() => {
    const h = setTimeout(() => {
      if (!q.trim()) { setSearchResults([]); return; }
      get("/api/wells", { q, limit: 8, country: country ?? undefined }).then(setSearchResults).catch(() => setSearchResults([]));
    }, 200);
    return () => clearTimeout(h);
  }, [q, country]);

  const pick = (id: number, coords?: { lat: number; lon: number }) => {
    setSelectedId(id);
    setSelectedBasin(null);
    setPanelOpen(true);
    if (coords) setFlyTarget({ id, lat: coords.lat, lon: coords.lon });
  };

  const onMapSelectWell = (w: SelectedWell) => pick(w.id); // already on screen — no flyTo needed
  const goSubsurface = (id: number) => { setWellId(id); router.push("/subsurface"); };
  const goOffsets = (id: number) => { setWellId(id); router.push("/offsets"); };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 230px)", minHeight: 480 }}>
      {/* Zone A — title, one-line question, search, country filter */}
      <PageHeader
        title={t("mapTitle", lang)}
        subtitle={t("mapQuestion", lang)}
        actions={
          <>
            <div style={{ position: "relative" }}>
              <Search size={14} style={{ position: "absolute", left: 9, top: 9, color: "var(--text-2)" }} aria-hidden="true" />
              <input className="input" style={{ paddingLeft: 28, width: 220 }} placeholder={t("mapSearchPlaceholder", lang)}
                     value={q} onChange={(e) => setQ(e.target.value)} aria-label={t("mapSearchPlaceholder", lang)} />
              {q && (
                <button type="button" className="btn" style={{ position: "absolute", right: 2, top: 2, padding: "3px 6px" }}
                        onClick={() => { setQ(""); setSearchResults([]); }} aria-label="clear search"><X size={12} /></button>
              )}
              {searchResults.length > 0 && (
                <div className="kk-popover" style={{ minWidth: 260, maxHeight: 260, overflowY: "auto", padding: 4 }}>
                  {searchResults.map((w: any) => (
                    <button key={w.id} type="button" className="kk-nav-item" style={{ width: "100%", textAlign: "left" }}
                            onClick={() => { pick(w.id, { lat: w.lat, lon: w.lon }); setQ(""); setSearchResults([]); }}>
                      {w.name} <span className="label">· {w.field ?? w.country ?? ""} · {w.n_events} ev</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
            <CountryFilter metric="located_wells" />
          </>
        }
      />

      {/* Zone B (map) + Zone C (collapsible panel) */}
      <div style={{ display: "flex", gap: 12, flex: "1 1 auto", minHeight: 0, marginTop: 12 }}>
        <WellMap
          className="flex-1"
          theme={theme}
          country={country}
          activeWell={activeWellDetail?.lat != null && activeWellDetail?.lon != null ? { lat: activeWellDetail.lat, lon: activeWellDetail.lon } : null}
          radiusKm={radiusKm}
          flyTo={flyTarget}
          onSelectWell={onMapSelectWell}
          onSelectBasin={(b) => { setSelectedBasin(b); setSelectedId(null); setPanelOpen(true); }}
        />

        <div style={{ width: panelOpen ? 340 : 40, flex: "0 0 auto", transition: "width .15s ease", overflow: "hidden" }}>
          <Card className="h-full flex flex-col" style={{ height: "100%", overflowY: panelOpen ? "auto" : "hidden", padding: panelOpen ? 16 : 8 }}>
            <button type="button" className="btn" style={{ alignSelf: panelOpen ? "flex-end" : "center", padding: 6 }}
                    onClick={() => setPanelOpen((v) => !v)} aria-label={panelOpen ? t("mapPanelCollapse", lang) : t("mapPanelExpand", lang)}>
              {panelOpen ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
            </button>

            {panelOpen && (
              <div className="flex flex-col gap-4 mt-2">
                {/* Selected well / basin card */}
                {selectedBasin ? (
                  <div>
                    <div className="h-title" style={{ fontSize: 16 }}>{selectedBasin.name}</div>
                    {selectedBasin.category && <div className="label mt-1">{selectedBasin.category}</div>}
                    <div className="flex flex-col gap-2 mt-3">
                      <Button href={`/analogs?basin=${encodeURIComponent(selectedBasin.slug)}`}>{t("mapBasinOpenAnalogs", lang)}</Button>
                      <a className="link" href={selectedBasin.url} target="_blank" rel="noreferrer">{t("mapBasinSource", lang)}</a>
                    </div>
                  </div>
                ) : selected ? (
                  <div>
                    <div className="h-title" style={{ fontSize: 16 }}>{selected.name}</div>
                    <div className="label mt-1">{selected.country ?? "unknown"}</div>
                    <div className="flex flex-col gap-1 mt-3 small">
                      <Row label={t("mapOperator", lang)} value={selected.operator ?? t("insufficient", lang)} />
                      <Row label={t("mapTD", lang)} value={selected.td_md_m != null ? `${Math.round(selected.td_md_m).toLocaleString()} m` : "unknown"} />
                      <Row label={t("mapEventsRecorded", lang)} value={
                        selected.n_events > 0 ? <Badge kind="hazard">{selected.n_events}</Badge> : "0"
                      } />
                      <Row label="" value={selected.documented ? <Badge kind="ok">{t("mapDocumented", lang)}</Badge> : <span className="label">{t("mapNotDocumented", lang)}</span>} />
                    </div>
                    <div className="flex flex-col gap-2 mt-3">
                      <Button variant="primary" onClick={() => setWellId(selected.id)}>{t("mapSetActive", lang)}</Button>
                      <Button onClick={() => goSubsurface(selected.id)}>{t("map3DView", lang)}</Button>
                      <Button onClick={() => goOffsets(selected.id)}>{t("mapOpenOffsets", lang)}</Button>
                    </div>
                  </div>
                ) : (
                  <EmptyState title={t("mapNoSelection", lang)} why="" />
                )}

                <hr className="rule-b" style={{ border: "none", borderTop: "1px solid var(--border)" }} />

                {/* Radius controls + list, around the globally active well */}
                {wellId && activeWellDetail ? (
                  <div>
                    <div className="label">{t("activeWell", lang)}</div>
                    <div className="font-medium">{activeWellDetail.name}</div>
                    <label className="label mt-2 block" htmlFor="radiusKm">{t("mapRadiusKm", lang)}: <span className="mono">{radiusKm}</span></label>
                    <input id="radiusKm" type="range" min={1} max={50} step={1} value={radiusKm}
                           onChange={(e) => setRadiusKm(Number(e.target.value))} style={{ width: "100%" }} />
                    <div className="label mt-2">{t("mapWellsInRadius", lang)}{radiusLoading ? "…" : ` (${radiusList.length})`}</div>
                    <div className="flex flex-col mt-1" style={{ maxHeight: 260, overflowY: "auto" }}>
                      {radiusList.map((o) => (
                        <button key={o.well_id} type="button" className="kk-nav-item" style={{ justifyContent: "space-between", textAlign: "left" }}
                                onClick={() => pick(o.well_id, { lat: o.lat, lon: o.lon })}>
                          <span>{o.name}</span>
                          <span className="mono label">{(o.raw.distance_m / 1000).toFixed(1)} km{o.n_events > 0 ? ` · ${o.n_events} ev` : ""}</span>
                        </button>
                      ))}
                      {!radiusLoading && radiusList.length === 0 && <EmptyState title={t("insufficient", lang)} why="" />}
                    </div>
                  </div>
                ) : (
                  <div className="label">{t("mapNoActiveWell", lang)}</div>
                )}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-2">
      {label && <span className="label">{label}</span>}
      <span className="mono">{value}</span>
    </div>
  );
}
