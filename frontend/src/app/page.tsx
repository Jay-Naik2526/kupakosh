"use client";
import { useEffect, useState } from "react";
import { ArrowRight } from "lucide-react";
import { get } from "@/lib/api";
import { useApp } from "@/lib/state";
import { Lang } from "@/lib/i18n";
import { Button } from "@/components/v2/ui";
import { EmptyState } from "@/components/kk/EmptyState";
import { openGuidedTour } from "@/components/v2/GuidedTour";
import Link from "next/link";
import { StrataBanner } from "@/components/v2/StrataBanner";

/**
 * Home (v2) — docs/PLAN_V2.md "Design system v2 / Home". Bilingual copy lives locally (a plain
 * {en, hi} dictionary, below) rather than in the shared lib/i18n.ts table, which this task's
 * scope keeps to nav keys only so several agents editing that file in parallel don't collide.
 */
function tr(lang: Lang, en: string, hi: string) {
  return lang === "hi" ? hi : en;
}

type Status = {
  counts: { wells: number; report_entries: number; events: number; events_trusted?: number; wiki_approved: number; documented_wells: number };
  by_country: { country: string }[];
};

type HindsightSummary = {
  n_testable: number;
  n_candidates: number;
  lift: { model: { n_flagged: number; k_flagged: number; rate_flagged: number | null; headline: string } };
  forewarned: { events: number; forewarned: number; forewarned_share: number | null; median_lead_m?: number | null };
  learned?: {
    learned_live?: { baseline_forewarned: number; alerts_per_well: number | null };
    auc?: Record<string, { auc: number | null }>;
    budget_curve?: { budget_per_well: number; layer_flagged: number; layer_flagged_share: number | null }[];
  } | null;
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

  const pctx = (x: number | null | undefined, d = 0) => (x == null ? "—" : `${(x * 100).toFixed(d)}%`);
  const figures: [string, string | undefined][] = status ? [
    [t("wells located", "स्थित कूप"), status.counts.wells.toLocaleString()],
    [t("report sentences indexed", "अनुक्रमित रिपोर्ट वाक्य"), status.counts.report_entries.toLocaleString()],
    [t("drilling problems on record", "दर्ज ड्रिलिंग समस्याएँ"), (status.counts.events_trusted ?? status.counts.events).toLocaleString()],
    [t("countries", "देश"), status.by_country.length.toLocaleString()],
    [t("wiki pages approved", "अनुमोदित ज्ञानकोश पृष्ठ"), status.counts.wiki_approved.toLocaleString()],
  ] : [];
  const steps: { href: string; title: string; body: string; c: string }[] = [
    { c: "var(--sec-operate)", href: "/command", title: t("Watch a real alert", "एक वास्तविक चेतावनी देखें"), body: t("Replay recorded rig data; a look-ahead notice fires before the bit reaches a problem layer.", "अभिलिखित रिग डेटा का पुनःचलन; समस्या परत से पहले आगे-दृष्टि सूचना।") },
    { c: "var(--sec-trust)", href: "/hindsight", title: t("Check the proof", "प्रमाण जाँचें"), body: t("Every documented well replayed as if new, then compared with what really happened.", "हर प्रलेखित कूप नए जैसा पुनःचलाया गया, फिर वास्तविक घटनाओं से तुलना।") },
    { c: "var(--sec-knowledge)", href: "/fixes", title: t("See what actually worked", "देखें क्या वास्तव में कारगर रहा"), body: t("Fixes ranked by how often they resolved the problem, with the cases behind each number.", "उपाय इस आधार पर क्रमबद्ध कि कितनी बार समस्या सुलझी।") },
    { c: "var(--sec-ask)", href: "/copilot", title: t("Ask the records", "अभिलेखों से पूछें"), body: t("A cited answer from the reports, or a plain refusal when there is no evidence.", "रिपोर्टों से उद्धृत उत्तर, या साक्ष्य न होने पर स्पष्ट अस्वीकृति।") },
  ];
  const more: { href: string; title: string; body: string; c: string }[] = [
    { c: "var(--teal)", href: "/map", title: t("Map", "मानचित्र"), body: t("All located wells, eight countries, satellite and terrain.", "सभी स्थित कूप, आठ देश, उपग्रह और भू-आकृति।") },
    { c: "var(--slate)", href: "/subsurface", title: t("3D subsurface", "3D उपसतह"), body: t("Offset wells and formation layers in depth.", "गहराई में निकट कूप और संरचना परतें।") },
    { c: "var(--ochre)", href: "/analogs", title: t("India analogs", "भारत अनुरूप"), body: t("Same rock, same depth, elsewhere — for Indian basins.", "वही चट्टान, वही गहराई, अन्यत्र — भारतीय द्रोणियों हेतु।") },
    { c: "var(--sage)", href: "/wiki", title: t("Well wiki", "ज्ञानकोश"), body: t("Compiled pages, every sentence cited, approved by an engineer.", "संकलित पृष्ठ, हर वाक्य उद्धृत, अभियंता-अनुमोदित।") },
  ];

  return (
    <div style={{ maxWidth: 1180 }}>
      <section aria-label="introduction" className="kk-hero kk-contours" style={{ margin: "-24px calc(-1 * clamp(16px, 3vw, 32px)) 0", padding: "40px clamp(16px, 3vw, 32px) 26px" }}>
        <div className="grid gap-10" style={{ gridTemplateColumns: "minmax(0, 1.5fr) minmax(260px, 1fr)", alignItems: "end" }}>
          <div>
            <div className="eyebrow">{t("Offset-well memory for drilling engineers", "ड्रिलिंग अभियंताओं हेतु निकट-कूप स्मृति")}</div>
            <h1 className="mt-3">
              Kupakosh <span className="deva" style={{ fontWeight: 400, color: "var(--text-2)" }}>कूपकोश</span>
            </h1>
            <p className="mt-3" style={{ fontSize: 18, lineHeight: 1.5, maxWidth: "36rem" }}>
              {t(
                "What went wrong in the wells around you, which fix actually worked, and a warning before the bit gets there — compiled from the drilling reports, with the source behind every number.",
                "आपके आसपास के कूपों में क्या गलत हुआ, कौन-सा उपाय वास्तव में कारगर रहा, और बिट के पहुँचने से पहले चेतावनी — ड्रिलिंग रिपोर्टों से संकलित, हर संख्या के पीछे स्रोत सहित।"
              )}
            </p>
            <div className="mt-6 flex flex-wrap gap-2">
              <Button variant="primary" onClick={openGuidedTour}>{t("Start guided tour", "मार्गदर्शित दौरा प्रारंभ करें")}</Button>
              <Button href="/accuracy">{t("See what's real", "वास्तविक क्या है, देखें")}</Button>
            </div>
          </div>
          <dl aria-label={t("records right now", "अभिलेख, अभी")} style={{ borderTop: "3px solid var(--text)", background: "var(--surface)", padding: "0 14px 10px", border: "1px solid var(--border)", borderTopWidth: 3, borderTopColor: "var(--text)" }}>
            {!status && <div className="label py-2">{t("Loading…", "लोड हो रहा है…")}</div>}
            {figures.map(([k, v]) => (
              <div key={k} className="flex items-baseline justify-between gap-4 py-2" style={{ borderBottom: "1px solid var(--border)" }}>
                <dt className="label">{k}</dt>
                <dd className="num" style={{ fontSize: 18, fontWeight: 600 }}>{v}</dd>
              </div>
            ))}
            <div className="pt-2"><Link href="/accuracy" className="small link">{t("Sources and licences", "स्रोत और अनुज्ञप्तियाँ")}</Link></div>
          </dl>
        </div>
        <div className="mt-8">
          <StrataBanner caption={(w, td) => t(
            `Formation column of well ${w.name}${w.field ? ` (${w.field})` : ""}, ${w.country ?? ""} — recorded tops from the public ${w.source === "sodir" ? "Sodir FactPages" : "well records"}, drawn to scale to ${Math.round(td).toLocaleString()} m MD. Colour = formation, hatch = rock type.`,
            `कूप ${w.name} का संरचना स्तंभ — सार्वजनिक अभिलेखों से दर्ज शीर्ष, ${Math.round(td).toLocaleString()} मी MD तक पैमाने पर। रंग = संरचना, रेखांकन = चट्टान प्रकार।`
          )} />
        </div>
      </section>

      <section aria-label="start here" className="mt-10">
        <div className="eyebrow">{t("Start here", "यहाँ से शुरू करें")}</div>
        <ol className="mt-3" style={{ borderTop: "1px solid var(--border)" }}>
          {steps.map((s, i) => (
            <li key={s.href} style={{ borderBottom: "1px solid var(--border)" }}>
              <Link href={s.href} className="kk-row-link grid items-baseline gap-4 py-4" style={{ gridTemplateColumns: "3rem minmax(0, 16rem) minmax(0, 1fr) auto" }}>
                <span className="num inline-flex items-center gap-2" style={{ color: "var(--text-2)" }}><span className="swatch" style={{ background: s.c }} />{String(i + 1).padStart(2, "0")}</span>
                <span className="serif" style={{ fontWeight: 600, fontSize: 18 }}>{s.title}</span>
                <span className="label">{s.body}</span>
                <ArrowRight size={16} aria-hidden="true" style={{ color: "var(--text-2)" }} />
              </Link>
            </li>
          ))}
        </ol>
      </section>

      <section aria-label="proof and more" className="mt-12">
        <div className="grid gap-12" style={{ gridTemplateColumns: "minmax(0, 1.5fr) minmax(0, 1fr)" }}>
          <div>
            <div className="eyebrow">{t("Does it work?", "क्या यह काम करता है?")}</div>
            <h2 className="mt-2 serif" style={{ fontSize: 26, fontWeight: 600, letterSpacing: "-.01em" }}>{t("Measured on real history, blind", "वास्तविक इतिहास पर, अंध रूप से मापा गया")}</h2>
            <p className="label mt-2" style={{ maxWidth: "38rem" }}>
              {t(
                "Each documented well is replayed as if it were being drilled today: the model never trained on it and sees nothing below the bit. The alerts are then compared with what the reports say happened.",
                "हर प्रलेखित कूप को ऐसे पुनःचलाया जाता है मानो आज ड्रिल हो रहा हो: मॉडल ने इस पर कभी प्रशिक्षण नहीं लिया और बिट के नीचे कुछ नहीं देखता।"
              )}
            </p>
            {hindsightState === "loading" && <div className="label mt-4">{t("Loading…", "लोड हो रहा है…")}</div>}
            {hindsightState === "none" && (
              <div className="mt-4">
                <EmptyState
                  title={t("Hindsight test not computed yet", "पूर्वाभास परीक्षण अभी संगणित नहीं हुआ")}
                  why={t("This measurement has not been run in this build. Not evaluated is shown rather than a made-up score.", "इस बिल्ड में यह मापन अभी नहीं चलाया गया है। बनावटी अंक के स्थान पर \"मूल्यांकन नहीं हुआ\" दिखाया गया है।")}
                />
              </div>
            )}
            {hindsightState === "ok" && hindsight && (() => {
              const f = hindsight.forewarned, live = hindsight.learned?.learned_live;
              const auc = hindsight.learned?.auc?.learned_live?.auc;
              const aucBase = hindsight.learned?.auc?.field_average?.auc;
              const b15 = hindsight.learned?.budget_curve?.find((r) => r.budget_per_well === 15);
              const bars = ["var(--rust)", "var(--ochre)", "var(--sage)", "var(--slate)"];
              const cells: [string, string, string][] = [
                [pctx(auc), t("ranking accuracy (AUC)", "क्रम सटीकता (AUC)"), aucBase != null ? t(`field average ${pctx(aucBase)}`, `क्षेत्र औसत ${pctx(aucBase)}`) : ""],
                [b15 ? pctx(b15.layer_flagged_share, 1) : "—", t("problem layers flagged ahead", "समस्या परतें पहले चिह्नित"), b15 ? t(`${b15.budget_per_well} alerts per well`, `${b15.budget_per_well} चेतावनी प्रति कूप`) : ""],
                [`${f.forewarned}/${f.events}`, t("exact hazard named ahead", "सटीक खतरा पहले बताया"), live ? t(`field average ${live.baseline_forewarned}`, `क्षेत्र औसत ${live.baseline_forewarned}`) : ""],
                [f.median_lead_m ? `${Math.round(f.median_lead_m)} m` : "—", t("median warning ahead", "माध्यिका अग्रिम चेतावनी"), ""],
              ];
              return (
                <div className="mt-5 grid gap-5" style={{ gridTemplateColumns: "repeat(4, minmax(0, 1fr))" }}>
                  {cells.map(([v, l, b], i) => (
                    <div key={l} className="pt-3" style={{ borderTop: `5px solid ${bars[i]}` }}>
                      <div className="num" style={{ fontSize: 28, fontWeight: 600, letterSpacing: "-.01em" }}>{v}</div>
                      <div className="small mt-1">{l}</div>
                      {b && <div className="label">{b}</div>}
                    </div>
                  ))}
                </div>
              );
            })()}
            <div className="mt-5"><Link href="/hindsight" className="small link inline-flex items-center gap-1">{t("Method, trade-offs and every well", "विधि, संतुलन और हर कूप")} <ArrowRight size={14} aria-hidden="true" /></Link></div>
          </div>
          <div>
            <div className="eyebrow">{t("Also in Kupakosh", "कूपकोश में और भी")}</div>
            <ul className="mt-3" style={{ borderTop: "1px solid var(--border)" }}>
              {more.map((m) => (
                <li key={m.href} style={{ borderBottom: "1px solid var(--border)" }}>
                  <Link href={m.href} className="kk-row-link block py-3">
                    <div className="flex items-center gap-2" style={{ fontWeight: 600 }}><span className="swatch" style={{ background: m.c }} />{m.title}</div>
                    <div className="label">{m.body}</div>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>
    </div>
  );
}
