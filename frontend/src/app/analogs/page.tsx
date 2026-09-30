"use client";
import { useEffect, useState } from "react";
import { get } from "@/lib/api";
import { useApp } from "@/lib/state";
import { PageHeader } from "@/components/v2/ui";
import { EmptyState } from "@/components/kk/EmptyState";
import { Register, type Col } from "@/components/kk/Register";
import { IntervalBar } from "@/components/kk/IntervalBar";
import { actionText } from "@/lib/format";
import { BasinPicker, type Basin, type Suggestion } from "@/components/v2/analogs/BasinPicker";
import { AnalogEvidence, type AnalogResult } from "@/components/v2/analogs/AnalogEvidence";
import { tr } from "@/components/v2/analogs/trLocal";
import { AssamColumn } from "@/components/v2/analogs/AssamColumn";

/**
 * /analogs — "What happened in rock like this, anywhere in the world?" (docs/PLAN_V2.md USP).
 * India has almost no public well-level data; this looks worldwide for the same lithology class
 * at an overlapping depth. GET /api/analogs/basins, /api/analogs/classes, /api/analogs.
 */
export default function Analogs() {
  const { lang } = useApp();
  const t = (en: string, hi: string) => tr(lang, en, hi);

  const [basins, setBasins] = useState<Basin[]>([]);
  const [classes, setClasses] = useState<string[]>([]);
  const [basinSlug, setBasinSlug] = useState<string | null>(null);
  const [lithology, setLithology] = useState("sandstone");
  const [top, setTop] = useState(500);
  const [base, setBase] = useState(2000);
  const [hazards, setHazards] = useState<Set<string>>(new Set());
  const [result, setResult] = useState<AnalogResult | null>(null);
  const [state, setState] = useState<"loading" | "ok" | "error">("loading");

  useEffect(() => {
    get("/api/analogs/basins").then((d) => {
      setBasins(d.basins);
      const pref = d.basins.find((b: Basin) => b.slug === "assam-arakan") ?? d.basins[0];
      if (pref) setBasinSlug(pref.slug);
    }).catch(() => setBasins([]));
    get("/api/analogs/classes").then((d) => setClasses(d.classes)).catch(() => setClasses(["sandstone", "shale", "claystone", "limestone", "chalk", "marl", "coal", "salt", "basement", "mixed"]));
  }, []);

  useEffect(() => {
    if (base <= top) return;
    setState("loading");
    get("/api/analogs", { lithology, top, base, hazard: hazards.size ? Array.from(hazards).join(",") : undefined, basin: basinSlug ?? undefined })
      .then((d) => { setResult(d); setState("ok"); })
      .catch(() => { setResult(null); setState("error"); });
  }, [lithology, top, base, hazards, basinSlug]);

  const onPickSuggestion = (s: Suggestion) => {
    setLithology(s.value);
    const nums = s.depth_hints_m.map(Number).filter((n) => Number.isFinite(n)).sort((a, b) => a - b);
    if (nums.length >= 2) { setTop(nums[0]); setBase(nums[nums.length - 1]); }
    else if (nums.length === 1) { setTop(Math.max(0, nums[0] - 500)); setBase(nums[0] + 500); }
  };

  const fixCols: Col<any>[] = [
    { key: "fix", head: t("Fix", "उपाय"), cell: (r) => <span>{actionText(r.action, lang)}{r.anecdotal && <span className="label"> · {t("anecdotal (n<3)", "किस्सागत (n<3)")}</span>}</span> },
    { key: "n", head: t("Cases", "मामले"), num: true, cell: (r) => r.n },
    { key: "rate", head: t("Success", "सफलता"), num: true, cell: (r) => (r.rate === null ? "—" : `${Math.round(r.rate * 100)}%`) },
    { key: "bar", head: "", cell: (r) => <IntervalBar rate={r.rate} lb={r.lb} anecdotal={r.anecdotal} /> },
    { key: "med", head: t("Median time", "माध्यिका समय"), num: true, cell: (r) => (r.median_hours === null ? "unknown" : `${r.median_hours} h`) },
    { key: "worse", head: t("Made worse", "और बिगड़ा"), num: true, cell: (r) => (r.worsened > 0 ? <span style={{ color: "var(--hazard)", fontWeight: 600 }}>▲ {r.worsened}</span> : "0") },
  ];

  return (
    <div>
      <PageHeader
        title={t("India Analogs — rock like this, anywhere in the world", "भारत अनुरूप कूप — विश्व भर में ऐसी ही चट्टान")}
        subtitle={t(
          "India has almost no public well-level records. This searches worldwide for the same lithology at an overlapping depth and reports what actually happened there.",
          "भारत के पास लगभग कोई सार्वजनिक कूप-स्तरीय अभिलेख नहीं है। यह उसी लिथोलॉजी व अतिव्यापी गहराई हेतु विश्व भर में खोजता है और वहाँ वास्तव में क्या हुआ, बताता है।"
        )}
      />

      <section aria-label="Upper Assam column" className="mb-6">
        <AssamColumn lang={lang} onPick={(l) => {
          setLithology(l); setTop(0); setBase(6000);
          document.getElementById("analog-query")?.scrollIntoView({ behavior: "smooth", block: "start" });
        }} />
      </section>

      {/* Zone B: the analog query tool — picker, evidence and fixes are one zone */}
      <section id="analog-query" aria-label="analog query">
      <section aria-label="basin and lithology" className="mb-6">
        {basins.length === 0 ? (
          <div className="label">{t("Loading…", "लोड हो रहा है…")}</div>
        ) : (
          <BasinPicker
            basins={basins} basinSlug={basinSlug} setBasinSlug={setBasinSlug} classes={classes}
            lithology={lithology} setLithology={setLithology} top={top} setTop={setTop} base={base} setBase={setBase}
            hazards={hazards} setHazards={setHazards} onPickSuggestion={onPickSuggestion} lang={lang}
          />
        )}
      </section>

      <section aria-label="analog evidence" className="mb-6">
        {state === "loading" && <div className="label">{t("Loading…", "लोड हो रहा है…")}</div>}
        {state === "error" && <EmptyState title={t("Could not run this query", "यह प्रश्न नहीं चल सका")} why={t("Check the depth band (base must be greater than top).", "गहराई परास जाँचें (base, top से अधिक होना चाहिए)।")} />}
        {state === "ok" && result && result.n_wells === 0 && (
          <EmptyState title={t("No analog intervals found", "कोई अनुरूप अंतराल नहीं मिला")} why={t("No worldwide well matched this lithology and depth band. Try a wider band or a different class.", "इस लिथोलॉजी व गहराई परास से कोई विश्व कूप मेल नहीं खाया। व्यापक परास या भिन्न वर्ग आज़माएँ।")} />
        )}
        {state === "ok" && result && result.n_wells > 0 && <AnalogEvidence result={result} lang={lang} />}
      </section>

      {state === "ok" && result && result.fixes.length > 0 && (
        <section aria-label="top fixes" className="mb-4">
          <PageHeader title={t("What worked in these analog wells", "इन अनुरूप कूपों में क्या कारगर रहा")} subtitle={t("Fixes are scoped to the matched wells above — not a claim about Indian formations.", "उपाय ऊपर मेल खाते कूपों तक सीमित हैं — भारतीय संरचनाओं का दावा नहीं।")} />
          <Register rows={result.fixes} cols={fixCols} empty={t("No fixes recorded.", "कोई उपाय दर्ज नहीं।")} />
        </section>
      )}
      </section>
    </div>
  );
}
