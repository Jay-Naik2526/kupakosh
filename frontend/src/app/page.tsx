"use client";
import { useEffect, useState } from "react";
import { Radar, Map as MapIcon, MessageSquare, History, Globe2, BookOpen, Wrench, Box, ArrowRight } from "lucide-react";
import { get } from "@/lib/api";
import { useApp } from "@/lib/state";
import { Lang } from "@/lib/i18n";
import { Card, LinkCard, StatTile, Button, PageHeader } from "@/components/v2/ui";
import { EmptyState } from "@/components/kk/EmptyState";
import { openGuidedTour } from "@/components/v2/GuidedTour";

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
  n_wells: number;
  n_problems: number;
  n_forewarned: number;
  median_lead_m: number | null;
  n_false_alarms: number;
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
      {/* Hero */}
      <section aria-label="hero" className="mb-8">
        <div className="kk-card" style={{ background: "linear-gradient(135deg, color-mix(in srgb, var(--accent) 8%, var(--surface)), var(--surface))" }}>
          <div className="label">{t("Well memory for Oil India's engineers", "ऑयल इंडिया के अभियंताओं हेतु कूप-स्मृति")}</div>
          <h1 className="mt-1" style={{ fontSize: 32, fontWeight: 700, lineHeight: 1.15 }}>
            Kupakosh <span className="deva" style={{ fontWeight: 500 }}>कूपकोश</span>
          </h1>
          <p className="mt-2 max-w-prose" style={{ fontSize: 17, color: "var(--text-2)" }}>
            {t("Oil India's memory of every well.", "ऑयल इंडिया की हर कूप की स्मृति।")}
          </p>
          <div className="mt-5 flex flex-wrap gap-2">
            <Button variant="primary" onClick={openGuidedTour}>
              {t("Start guided tour", "मार्गदर्शित दौरा प्रारंभ करें")}
            </Button>
            <Button href="/accuracy">{t("See what's real", "वास्तविक क्या है, देखें")}</Button>
          </div>
        </div>
      </section>

      {/* Zone B: three primary actions + the live KPI strip */}
      <section aria-label="explore and status" className="mb-8">
        <div className="grid gap-4" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))" }}>
          <LinkCard href="/command">
            <Radar size={22} style={{ color: "var(--accent)" }} aria-hidden="true" />
            <div className="font-semibold mt-2">{t("Watch a real alert", "एक वास्तविक चेतावनी देखें")}</div>
            <p className="label mt-1">{t("Replay recorded rig data and see a look-ahead hazard notice fire.", "अभिलिखित रिग डेटा का पुनःचलन करें और आगे-दृष्टि खतरा सूचना देखें।")}</p>
            <div className="mt-3 small link inline-flex items-center gap-1">
              {t("Open Well Room", "कूप कक्ष खोलें")} <ArrowRight size={14} />
            </div>
          </LinkCard>
          <LinkCard href="/map">
            <MapIcon size={22} style={{ color: "var(--accent)" }} aria-hidden="true" />
            <div className="font-semibold mt-2">{t("Explore wells on the map", "मानचित्र पर कूप देखें")}</div>
            <p className="label mt-1">{t("Every well we hold, from eight countries, with its record status.", "आठ देशों के सभी कूप, उनकी अभिलेख स्थिति सहित।")}</p>
            <div className="mt-3 small link inline-flex items-center gap-1">
              {t("Open Map", "मानचित्र खोलें")} <ArrowRight size={14} />
            </div>
          </LinkCard>
          <LinkCard href="/copilot">
            <MessageSquare size={22} style={{ color: "var(--accent)" }} aria-hidden="true" />
            <div className="font-semibold mt-2">{t("Ask the records", "अभिलेखों से पूछें")}</div>
            <p className="label mt-1">{t("A cited, extractive answer — or a plain refusal when there is no evidence.", "एक उद्धृत, निष्कर्षणात्मक उत्तर — या साक्ष्य न होने पर स्पष्ट अस्वीकृति।")}</p>
            <div className="mt-3 small link inline-flex items-center gap-1">
              {t("Open Copilot", "सहायक खोलें")} <ArrowRight size={14} />
            </div>
          </LinkCard>
        </div>
        <div className="mt-8">
          <PageHeader title={t("The records, right now", "अभिलेख, अभी की स्थिति")} />
          {!status ? (
            <div className="label">{t("Loading…", "लोड हो रहा है…")}</div>
          ) : (
            <div className="grid gap-4" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))" }}>
              <StatTile label={t("wells", "कूप")} value={status.counts.wells.toLocaleString()} href="/accuracy" />
              <StatTile label={t("report entries", "रिपोर्ट प्रविष्टियाँ")} value={status.counts.report_entries.toLocaleString()} href="/accuracy" />
              <StatTile label={t("extracted events", "निष्कर्षित घटनाएँ")} value={status.counts.events.toLocaleString()} href="/accuracy" />
              <StatTile label={t("countries", "देश")} value={status.by_country.length.toLocaleString()} href="/accuracy" />
              <StatTile label={t("approved wiki pages", "अनुमोदित ज्ञानकोश पृष्ठ")} value={status.counts.wiki_approved.toLocaleString()} href="/wiki" />
            </div>
          )}
        </div>
      </section>

      {/* Zone C: the Hindsight proof + "what makes it different" */}
      <section aria-label="proof and differentiators" className="mb-4">
        <Card>
          <div className="flex items-center gap-2">
            <History size={18} style={{ color: "var(--accent)" }} aria-hidden="true" />
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
          {hindsightState === "ok" && hindsight && (
            <div className="grid gap-4 mt-3" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))" }}>
              <StatTile label={t("problems forewarned", "पूर्व-चेतावनी दी गई समस्याएँ")} value={`${hindsight.n_forewarned} / ${hindsight.n_problems}`} href="/hindsight" />
              <StatTile
                label={t("median lead distance", "माध्यिका अग्रता दूरी")}
                value={hindsight.median_lead_m !== null ? `${Math.round(hindsight.median_lead_m)} m` : t("unknown", "अज्ञात")}
                href="/hindsight"
              />
              <StatTile label={t("false alarms", "झूठी चेतावनियाँ")} value={hindsight.n_false_alarms} href="/hindsight" />
              <StatTile label={t("wells tested", "परीक्षित कूप")} value={hindsight.n_wells} href="/hindsight" />
            </div>
          )}
          <div className="mt-3">
            <Button href="/hindsight">{t("Open Hindsight", "पूर्वाभास परीक्षण खोलें")}</Button>
          </div>
        </Card>
        <div className="mt-8">
          <PageHeader title={t("What makes it different", "यह अलग कैसे है")} />
          <div className="grid gap-4" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))" }}>
          <LinkCard href="/hindsight">
            <History size={18} style={{ color: "var(--accent)" }} aria-hidden="true" />
            <div className="font-semibold mt-2 small">{t("Hindsight proof", "पूर्वाभास प्रमाण")}</div>
            <p className="label mt-1">{t("Measured, blind, well-level.", "मापित, अंध, कूप-स्तरीय।")}</p>
          </LinkCard>
          <LinkCard href="/analogs">
            <Globe2 size={18} style={{ color: "var(--accent)" }} aria-hidden="true" />
            <div className="font-semibold mt-2 small">{t("India Analogs", "भारत अनुरूप कूप")}</div>
            <p className="label mt-1">{t("Global analogue evidence for Indian basins.", "भारतीय द्रोणियों हेतु वैश्विक अनुरूप साक्ष्य।")}</p>
          </LinkCard>
          <LinkCard href="/wiki">
            <BookOpen size={18} style={{ color: "var(--accent)" }} aria-hidden="true" />
            <div className="font-semibold mt-2 small">{t("Well Wiki", "ज्ञानकोश")}</div>
            <p className="label mt-1">{t("Compiled, cited, engineer-approved.", "संकलित, उद्धृत, अभियंता-अनुमोदित।")}</p>
          </LinkCard>
          <LinkCard href="/fixes">
            <Wrench size={18} style={{ color: "var(--accent)" }} aria-hidden="true" />
            <div className="font-semibold mt-2 small">{t("What actually worked", "वास्तव में क्या कारगर रहा")}</div>
            <p className="label mt-1">{t("Fixes ranked by measured success.", "मापित सफलता से क्रमबद्ध उपाय।")}</p>
          </LinkCard>
          <LinkCard href="/subsurface">
            <Box size={18} style={{ color: "var(--accent)" }} aria-hidden="true" />
            <div className="font-semibold mt-2 small">{t("3D subsurface", "3D उपसतह")}</div>
            <p className="label mt-1">{t("Offset wells as real trajectories.", "निकट कूप वास्तविक पथ के रूप में।")}</p>
          </LinkCard>
        </div>
        </div>
      </section>
    </div>
  );
}
