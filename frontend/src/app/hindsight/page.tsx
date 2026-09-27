"use client";
import { useEffect, useState } from "react";
import { get } from "@/lib/api";
import { useApp } from "@/lib/state";
import { PageHeader } from "@/components/v2/ui";
import { EmptyState } from "@/components/kk/EmptyState";
import { HindsightTiles, type HindsightSummary } from "@/components/v2/hindsight/HindsightTiles";
import { HindsightTimeline, type WellRow, type WellDetail } from "@/components/v2/hindsight/HindsightTimeline";
import { HindsightStrataTable } from "@/components/v2/hindsight/HindsightStrataTable";
import { tr } from "@/components/v2/hindsight/trLocal";

/**
 * /hindsight — USP1: "Would Kupakosh have warned in time?" (docs/PLAN_V2.md).
 * Blind replay proof: GET /api/hindsight/summary (headline lift + fair baseline + forewarned share),
 * /api/hindsight/wells (picker) and /api/hindsight/{well_id} (per-well timeline).
 */
export default function Hindsight() {
  const { lang } = useApp();
  const t = (en: string, hi: string) => tr(lang, en, hi);
  const [summary, setSummary] = useState<HindsightSummary | null>(null);
  const [summaryState, setSummaryState] = useState<"loading" | "ok" | "none">("loading");
  const [wells, setWells] = useState<WellRow[]>([]);
  const [wellId, setWellId] = useState<number | null>(null);
  const [detail, setDetail] = useState<WellDetail | null>(null);

  useEffect(() => {
    get("/api/hindsight/summary").then((d) => { setSummary(d); setSummaryState("ok"); }).catch(() => setSummaryState("none"));
    get("/api/hindsight/wells").then((rows: WellRow[]) => {
      setWells(rows);
      const preferred = rows.find((r) => r.name.includes("16B(78)-32")) ?? rows.filter((r) => r.events > 0).sort((a, b) => b.events - a.events)[0];
      if (preferred) setWellId(preferred.well_id);
    }).catch(() => setWells([]));
  }, []);

  useEffect(() => {
    if (wellId === null) return;
    setDetail(null);
    get(`/api/hindsight/${wellId}`).then(setDetail).catch(() => setDetail(null));
  }, [wellId]);

  return (
    <div>
      <PageHeader
        title={t("Hindsight — would Kupakosh have warned in time?", "पूर्वाभास — क्या कूपकोश समय पर चेतावनी देता?")}
        subtitle={t(
          "Every documented well, replayed blind: its own reports hidden, alerts computed only from other wells, then checked against what actually happened.",
          "प्रत्येक प्रलेखित कूप का अंध पुनःचलन: इसकी अपनी रिपोर्टें छुपाकर, केवल अन्य कूपों से चेतावनियाँ बनाकर, फिर वास्तव में हुई घटनाओं से मिलान किया गया।"
        )}
      />

      <section aria-label="headline" className="mb-8">
        {summaryState === "loading" && <div className="label">{t("Loading…", "लोड हो रहा है…")}</div>}
        {summaryState === "none" && (
          <EmptyState
            title={t("Hindsight test not computed yet", "पूर्वाभास परीक्षण अभी संगणित नहीं हुआ")}
            why={t("This measurement has not been run in this build.", "इस बिल्ड में यह मापन अभी नहीं चलाया गया है।")}
          />
        )}
        {summaryState === "ok" && summary && <HindsightTiles s={summary} lang={lang} />}
      </section>

      <section aria-label="blind replay viewer" className="mb-8">
        <PageHeader title={t("Blind replay, well by well", "अंध पुनःचलन, कूप-दर-कूप")} />
        {wells.length === 0 ? (
          <EmptyState title={t("No testable wells", "कोई परीक्षण-योग्य कूप नहीं")} why={t("Not evaluated in this build.", "इस बिल्ड में मूल्यांकन नहीं हुआ।")} />
        ) : (
          <HindsightTimeline wells={wells} wellId={wellId} onPick={setWellId} detail={detail} lang={lang} />
        )}
      </section>

      {summaryState === "ok" && summary && (
        <section aria-label="by source and country" className="mb-4">
          <PageHeader title={t("Lift by source and country", "स्रोत व देश अनुसार लिफ्ट")} />
          <HindsightStrataTable bySource={(summary as any).by_source} byCountry={(summary as any).by_country} method={summary.method} lang={lang} />
        </section>
      )}
    </div>
  );
}
