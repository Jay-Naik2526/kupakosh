"use client";
import { useEffect, useState } from "react";
import { Radar, Map as MapIcon, MessageSquare, History, Globe2, BookOpen, Wrench, Box, ArrowRight, Database, Activity } from "lucide-react";
import { get } from "@/lib/api";
import { useApp } from "@/lib/state";
import { Lang } from "@/lib/i18n";
import { Card, LinkCard, StatTile, Button, PageHeader, IconChip } from "@/components/v2/ui";
import { EmptyState } from "@/components/kk/EmptyState";
import { openGuidedTour } from "@/components/v2/GuidedTour";
import { SECTION_COLOR, LITH_COLOR } from "@/lib/palette";

/**
 * Home (v2) — docs/PLAN_V2.md "Design system v2 / Home". Bilingual copy lives locally (a plain
 * {en, hi} dictionary, below) rather than in the shared lib/i18n.ts table, which this task's
 * scope keeps to nav keys only so several agents editing that file in parallel don't collide.
 */
function tr(lang: Lang, en: string, hi: string) {
  return lang === "hi" ? hi : en;
}

type Status = {
  counts: { wells: number; report_entries: number; events: number; wiki_approved: number; documented_wells: number };
  by_country: { country: string }[];
};

type HindsightSummary = {
  n_testable: number;
  n_candidates: number;
  lift: { model: { n_flagged: number; k_flagged: number; rate_flagged: number | null; headline: string } };
  forewarned: { events: number; forewarned: number; forewarned_share: number | null };
  watchlist?: { rows: { k: number; hits: number; events: number; share: number | null; x_random: number | null }[] };
  method?: string;
} | null;

export default function Home() {
  const { lang } = useApp();
  const [status, setStatus] = useState<Status | null>(null);
  const [hindsight, setHindsight] = useState<HindsightSummary>(null);
  const [hindsightState, setHindsightState] = useState<"loading" | "ok" | "none">("loading");

  useEffect(() => {
    get("/api/status").then(setStatus).catch(() => setStatus(null));
    get("/api/hindsight/summary")
      .then((d) => { setHindsight(d); setHindsightState("ok"); })
      .catch(() => setHindsightState("none"));
  }, []);

  const t = (en: string, hi: string) => tr(lang, en, hi);

  return (
    <div>
      {/* Hero: brand gradient + a decorative geological-layer illustration (no numbers — colour only) */}
      <section aria-label="hero" className="mb-8">
        <div className="kk-hero">
          <div className="label">{t("Well memory for Oil India's engineers", "ऑयल इंडिया के अभियंताओं हेतु कूप-स्मृति")}</div>
          <h1 className="mt-1" style={{ fontSize: 32, fontWeight: 700, lineHeight: 1.15 }}>
            Kupakosh <span className="deva" style={{ fontWeight: 500 }}>कूपकोश</span>
          </h1>
          <p className="mt-2 max-w-prose" style={{ fontSize: 17, opacity: 0.92 }}>
            {t("Oil India's memory of every well.", "ऑयल इंडिया की हर कूप की स्मृति।")}
          </p>
          <div className="mt-5 flex flex-wrap gap-2">
            <Button variant="primary" onClick={openGuidedTour} style={{ background: "#fff", color: "var(--brand-to)" }}>
              {t("Start guided tour", "मार्गदर्शित दौरा प्रारंभ करें")}
            </Button>
            <Button href="/accuracy" style={{ background: "rgba(255,255,255,.16)", color: "#fff", borderColor: "rgba(255,255,255,.5)" }}>
              {t("See what's real", "वास्तविक क्या है, देखें")}
            </Button>
          </div>
          <svg className="kk-hero-strata" viewBox="0 0 100 20" preserveAspectRatio="none" aria-hidden="true">
            {[LITH_COLOR.sand, LITH_COLOR.shale, LITH_COLOR.lime, LITH_COLOR.clay, LITH_COLOR.chalk].map((c, i, arr) => (
              <rect key={c + i} x={0} y={(i * 20) / arr.length} width={100} height={20 / arr.length} fill={c} opacity={0.9} />
            ))}
          </svg>
        </div>
      </section>

      {/* Zone B: three primary actions + the live KPI strip */}
      <section aria-label="explore and status" className="mb-8">
        <div className="grid gap-4" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))" }}>
          <LinkCard href="/command" accent={SECTION_COLOR.operate}>
            <IconChip icon={Radar} color={SECTION_COLOR.operate} />
            <div className="font-semibold mt-2">{t("Watch a real alert", "एक वास्तविक चेतावनी देखें")}</div>
            <p className="label mt-1">{t("Replay recorded rig data and see a look-ahead hazard notice fire.", "अभिलिखित रिग डेटा का पुनःचलन करें और आगे-दृष्टि खतरा सूचना देखें।")}</p>
            <div className="mt-3 small link inline-flex items-center gap-1">
              {t("Open Well Room", "कूप कक्ष खोलें")} <ArrowRight size={14} />
            </div>
          </LinkCard>
          <LinkCard href="/map" accent={SECTION_COLOR.explore}>
            <IconChip icon={MapIcon} color={SECTION_COLOR.explore} />
            <div className="font-semibold mt-2">{t("Explore wells on the map", "मानचित्र पर कूप देखें")}</div>
            <p className="label mt-1">{t("Every well we hold, from eight countries, with its record status.", "आठ देशों के सभी कूप, उनकी अभिलेख स्थिति सहित।")}</p>
            <div className="mt-3 small link inline-flex items-center gap-1">
              {t("Open Map", "मानचित्र खोलें")} <ArrowRight size={14} />
            </div>
          </LinkCard>
          <LinkCard href="/copilot" accent={SECTION_COLOR.ask}>
            <IconChip icon={MessageSquare} color={SECTION_COLOR.ask} />
            <div className="font-semibold mt-2">{t("Ask the records", "अभिलेखों से पूछें")}</div>
            <p className="label mt-1">{t("A cited, extractive answer — or a plain refusal when there is no evidence.", "एक उद्धृत, निष्कर्षणात्मक उत्तर — या साक्ष्य न होने पर स्पष्ट अस्वीकृति।")}</p>
            <div className="mt-3 small link inline-flex items-center gap-1">
              {t("Open Copilot", "सहायक खोलें")} <ArrowRight size={14} />
            </div>
          </LinkCard>
        </div>
        <div className="mt-8">
          <PageHeader title={t("The records, right now", "अभिलेख, अभी की स्थिति")} icon={Database} color={SECTION_COLOR.trust} />
          {!status ? (
            <div className="label">{t("Loading…", "लोड हो रहा है…")}</div>
          ) : (
            <div className="grid gap-4" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))" }}>
              <StatTile label={t("wells", "कूप")} value={status.counts.wells.toLocaleString()} href="/accuracy" color={SECTION_COLOR.operate} />
              <StatTile label={t("report entries", "रिपोर्ट प्रविष्टियाँ")} value={status.counts.report_entries.toLocaleString()} href="/accuracy" color={SECTION_COLOR.explore} />
              <StatTile label={t("extracted events", "निष्कर्षित घटनाएँ")} value={status.counts.events.toLocaleString()} href="/accuracy" color={SECTION_COLOR.knowledge} />
              <StatTile label={t("countries", "देश")} value={status.by_country.length.toLocaleString()} href="/accuracy" color={SECTION_COLOR.ask} />
              <StatTile label={t("approved wiki pages", "अनुमोदित ज्ञानकोश पृष्ठ")} value={status.counts.wiki_approved.toLocaleString()} href="/wiki" color={SECTION_COLOR.deliver} />
            </div>
          )}
        </div>
      </section>

      {/* Zone C: the Hindsight proof + "what makes it different" */}
      <section aria-label="proof and differentiators" className="mb-4">
        <Card accent={SECTION_COLOR.trust}>
          <div className="flex items-center gap-2">
            <IconChip icon={History} color={SECTION_COLOR.trust} />
            <div className="font-semibold">{t("How Kupakosh proves itself", "कूपकोश स्वयं को कैसे सिद्ध करता है")}</div>
          </div>
          <p className="label mt-1 max-w-prose">
            {t(
              "The Hindsight test hides a real well, replays it depth by depth using only the other wells, and checks afterwards whether Kupakosh would have warned in time.",
              "पूर्वाभास परीक्षण एक वास्तविक कूप को छुपाकर, केवल अन्य कूपों का उपयोग कर गहराई-दर-गहराई पुनःचलन करता है, और बाद में जाँचता है कि क्या कूपकोश समय पर चेतावनी देता।"
            )}
          </p>
          {hindsightState === "loading" && <div className="label mt-3">{t("Loading…", "लोड हो रहा है…")}</div>}
          {hindsightState === "none" && (
            <div className="mt-3">
              <EmptyState
                title={t("Hindsight test not computed yet", "पूर्वाभास परीक्षण अभी संगणित नहीं हुआ")}
                why={t("This measurement has not been run in this build. Not evaluated is shown rather than a made-up score.", "इस बिल्ड में यह मापन अभी नहीं चलाया गया है। बनावटी अंक के स्थान पर \"मूल्यांकन नहीं हुआ\" दिखाया गया है।")}
              />
            </div>
          )}
          {hindsightState === "ok" && hindsight && (() => { const wl5 = hindsight.watchlist?.rows.find((r) => r.k === 5) ?? hindsight.watchlist?.rows[0]; return (
            <div className="mt-3">
              <p>
                {t(
                  `Alerts right ${hindsight.lift.model.k_flagged}/${hindsight.lift.model.n_flagged} times a blind alert fired (${hindsight.lift.model.rate_flagged !== null ? Math.round(hindsight.lift.model.rate_flagged * 100) : "?"}%)${wl5 ? ` · ${wl5.hits}/${wl5.events} real problems were on the well's blind top-${wl5.k} watch-list` : ""} · strict alerts forewarned ${hindsight.forewarned.forewarned}/${hindsight.forewarned.events}.`,
                  `जब भी अंध चेतावनी दी गई, ${hindsight.lift.model.n_flagged} में से ${hindsight.lift.model.k_flagged} बार सही रही (${hindsight.lift.model.rate_flagged !== null ? Math.round(hindsight.lift.model.rate_flagged * 100) : "?"}%) · ${hindsight.forewarned.events} में से ${hindsight.forewarned.forewarned} समस्याएँ पूर्व-चेतावनी दी गईं।`
                )}
              </p>
              <div className="grid gap-4 mt-3" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))" }}>
                <StatTile label={t("measured lift", "मापित लिफ्ट")} value={hindsight.lift.model.headline} href="/hindsight" color={SECTION_COLOR.trust} />
                {wl5 ? (
                  <>
                    <StatTile label={t(`caught on blind top-${wl5.k} watch-list`, `अंध शीर्ष-${wl5.k} सूची में पकड़ी गईं`)} value={`${wl5.hits} / ${wl5.events}`} href="/hindsight" color={SECTION_COLOR.operate} />
                    <StatTile label={t("vs picking at random", "यादृच्छिक चयन की तुलना में")} value={wl5.x_random !== null ? `${wl5.x_random}×` : t("unknown", "अज्ञात")} href="/hindsight" color={SECTION_COLOR.knowledge} />
                  </>
                ) : (
                  <StatTile label={t("problems forewarned", "पूर्व-चेतावनी दी गई समस्याएँ")} value={`${hindsight.forewarned.forewarned} / ${hindsight.forewarned.events}`} href="/hindsight" color={SECTION_COLOR.operate} />
                )}
                <StatTile label={t("wells tested", "परीक्षित कूप")} value={`${hindsight.n_testable} / ${hindsight.n_candidates}`} href="/hindsight" color={SECTION_COLOR.explore} />
              </div>
            </div>
          ); })()}
          <div className="mt-3">
            <Button href="/hindsight">{t("Open Hindsight", "पूर्वाभास परीक्षण खोलें")}</Button>
          </div>
        </Card>
        <div className="mt-8">
          <PageHeader title={t("What makes it different", "यह अलग कैसे है")} icon={Activity} color={SECTION_COLOR.deliver} />
          <div className="grid gap-4" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))" }}>
          <LinkCard href="/hindsight" accent={SECTION_COLOR.trust}>
            <IconChip icon={History} color={SECTION_COLOR.trust} />
            <div className="font-semibold mt-2 small">{t("Hindsight proof", "पूर्वाभास प्रमाण")}</div>
            <p className="label mt-1">{t("Measured, blind, well-level.", "मापित, अंध, कूप-स्तरीय।")}</p>
          </LinkCard>
          <LinkCard href="/analogs" accent={SECTION_COLOR.explore}>
            <IconChip icon={Globe2} color={SECTION_COLOR.explore} />
            <div className="font-semibold mt-2 small">{t("India Analogs", "भारत अनुरूप कूप")}</div>
            <p className="label mt-1">{t("Global analogue evidence for Indian basins.", "भारतीय द्रोणियों हेतु वैश्विक अनुरूप साक्ष्य।")}</p>
          </LinkCard>
          <LinkCard href="/wiki" accent={SECTION_COLOR.knowledge}>
            <IconChip icon={BookOpen} color={SECTION_COLOR.knowledge} />
            <div className="font-semibold mt-2 small">{t("Well Wiki", "ज्ञानकोश")}</div>
            <p className="label mt-1">{t("Compiled, cited, engineer-approved.", "संकलित, उद्धृत, अभियंता-अनुमोदित।")}</p>
          </LinkCard>
          <LinkCard href="/fixes" accent={SECTION_COLOR.knowledge}>
            <IconChip icon={Wrench} color={SECTION_COLOR.knowledge} />
            <div className="font-semibold mt-2 small">{t("What actually worked", "वास्तव में क्या कारगर रहा")}</div>
            <p className="label mt-1">{t("Fixes ranked by measured success.", "मापित सफलता से क्रमबद्ध उपाय।")}</p>
          </LinkCard>
          <LinkCard href="/subsurface" accent={SECTION_COLOR.explore}>
            <IconChip icon={Box} color={SECTION_COLOR.explore} />
            <div className="font-semibold mt-2 small">{t("3D subsurface", "3D उपसतह")}</div>
            <p className="label mt-1">{t("Offset wells as real trajectories.", "निकट कूप वास्तविक पथ के रूप में।")}</p>
          </LinkCard>
        </div>
        </div>
      </section>
    </div>
  );
}
