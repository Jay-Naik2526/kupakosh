"use client";
import { useEffect, useState } from "react";
import { get } from "@/lib/api";
import type { Lang } from "@/lib/i18n";
import { actionText, hazardText } from "@/lib/format";
import { formationColor } from "@/lib/palette";
import { hatchUrl, LithologyPatterns } from "@/components/kk/LithologyPatterns";
import { SourceFootnote } from "@/components/kk/SourceFootnote";
import { tr } from "./trLocal";

type Fact = { source_ref: string; text: string };
type Formation = {
  key: string; label: string; n_sentences: number; n_documents: number; in_records: boolean;
  lithology: (Fact & { class: string; counts: Record<string, number> }) | null;
  age: (Fact & { value: string }) | null;
  roles: (Fact & { role: string })[];
  depth_mentions: (Fact & { depth_m: number })[];
  quotes: (Fact & { document: string })[];
  analogs: {
    lithology: string; n_wells: number; n_wells_documented: number; countries: string[];
    hazards: { hazard: string; label: string; mean: number; ci: [number, number]; n_eff: number; n_wells: number; n_with_event: number }[];
    insufficient: string[];
    fixes: { action: string; n: number; k: number; worsened: number; anecdotal: boolean }[];
  } | null;
};
type Column = { formations: Formation[]; caveat: string; n_sentences_searched: number };

const ROLE: Record<string, [string, string]> = {
  reservoir: ["reservoir", "भंडार शैल"],
  source_rock: ["source rock", "स्रोत शैल"],
  cap_rock: ["cap rock", "आवरण शैल"],
};
const pct = (x: number) => (x < 0.1 ? (x * 100).toFixed(1) : Math.round(x * 100).toString());

/** Upper Assam column (GET /api/analogs/assam): Oil India's home formations, youngest at the top, each described
 *  only by quoted public DGH/NDR sentences, beside measured drilling-problem evidence from the same rock type abroad. */
export function AssamColumn({ lang, onPick }: { lang: Lang; onPick?: (lithology: string) => void }) {
  const t = (en: string, hi: string) => tr(lang, en, hi);
  const [col, setCol] = useState<Column | null>(null);
  const [err, setErr] = useState(false);
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    get<Column>("/api/analogs/assam").then(setCol).catch(() => setErr(true));
  }, []);

  if (err) return <div className="label">{t("Could not load the Upper Assam column.", "ऊपरी असम स्तंभ लोड नहीं हो सका।")}</div>;
  if (!col) return <div className="label">{t("Reading the DGH/NDR records…", "DGH/NDR अभिलेख पढ़े जा रहे हैं…")}</div>;

  let n = 0;
  const cite = (ref: string) => <SourceFootnote refId={ref} n={++n} />;

  return (
    <div className="kk-card" style={{ padding: 0, overflow: "hidden" }}>
      <LithologyPatterns />
      <div style={{ padding: "16px 20px 10px", borderBottom: "1px solid var(--border)" }}>
        <div className="eyebrow">{t("Oil India's home geology", "ऑयल इंडिया का गृह भूविज्ञान")}</div>
        <h2 className="serif" style={{ fontSize: 22, margin: "2px 0 4px" }}>{t("The Upper Assam column", "ऊपरी असम स्तंभ")}</h2>
        <p className="label" style={{ maxWidth: 860 }}>
          {t(
            `Every rock type, age and role below is quoted from public DGH/NDR records (${col.n_sentences_searched.toLocaleString("en-IN")} sentences searched). The problem rates on the right are measured in public wells abroad drilled through the same rock type.`,
            `नीचे हर शैल प्रकार, आयु और भूमिका सार्वजनिक DGH/NDR अभिलेखों से उद्धृत है (${col.n_sentences_searched.toLocaleString("en-IN")} वाक्य खोजे गए)। दाईं ओर की समस्या-दरें विदेश के उन सार्वजनिक कूपों में मापी गई हैं जो उसी शैल प्रकार से होकर खोदे गए।`
          )}
        </p>
      </div>

      <div role="table" aria-label={t("Upper Assam formations", "ऊपरी असम संरचनाएँ")}>
        <div role="row" className="assam-row assam-head">
          <span role="columnheader" />
          <span role="columnheader" className="eyebrow">{t("Formation · youngest first", "संरचना · नवीनतम पहले")}</span>
          <span role="columnheader" className="eyebrow">{t("What the Indian records say", "भारतीय अभिलेख क्या कहते हैं")}</span>
          <span role="columnheader" className="eyebrow">{t("Recorded problems in the same rock abroad", "विदेश में उसी शैल में दर्ज समस्याएँ")}</span>
        </div>

        {col.formations.map((f) => {
          const cls = f.lithology?.class ?? null;
          const others = f.lithology ? Object.entries(f.lithology.counts).filter(([k, v]) => k !== cls && v >= 2).sort((a, b) => b[1] - a[1]) : [];
          const isOpen = open === f.key;
          return (
            <div key={f.key} role="row" className="assam-row" style={{ opacity: f.in_records ? 1 : 0.6 }}>
              <span aria-hidden="true" style={{ position: "relative", alignSelf: "stretch", minHeight: 64, borderRight: "1px solid var(--border)" }}>
                <svg width="100%" height="100%" style={{ position: "absolute", inset: 0 }} preserveAspectRatio="none">
                  <rect width="100%" height="100%" fill={cls ? formationColor(f.label, cls) : "var(--surface-2)"} />
                  {cls && <rect width="100%" height="100%" fill={hatchUrl(cls)} />}
                </svg>
              </span>

              <div role="cell">
                <div className="serif" style={{ fontSize: 16, fontWeight: 600 }}>{f.label}</div>
                <div className="label" style={{ marginTop: 2 }}>
                  {f.age ? <>{f.age.value}{cite(f.age.source_ref)}</> : t("age not stated in the records", "आयु अभिलेखों में नहीं")}
                </div>
                <div style={{ marginTop: 4, fontSize: 13 }}>
                  {cls ? (
                    <>
                      <span style={{ fontWeight: 600 }}>{cls}</span>{cite(f.lithology!.source_ref)}
                      {others.length > 0 && <span className="label"> · {t("also named", "भी उल्लेख")}: {others.map(([k, v]) => `${k} ×${v}`).join(", ")}</span>}
                    </>
                  ) : <span className="label">{t("rock type not stated in the records", "शैल प्रकार अभिलेखों में नहीं")}</span>}
                </div>
              </div>

              <div role="cell" style={{ fontSize: 13 }}>
                {!f.in_records ? (
                  <span className="label">{t("Not found in the loaded public records.", "लोड किए गए सार्वजनिक अभिलेखों में नहीं मिला।")}</span>
                ) : (
                  <>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 4 }}>
                      {f.roles.map((r) => (
                        <span key={r.role} className="chip" style={{ fontSize: 12 }}>{t(ROLE[r.role][0], ROLE[r.role][1])}{cite(r.source_ref)}</span>
                      ))}
                      {f.depth_mentions.map((d) => (
                        <span key={d.depth_m} className="chip mono" style={{ fontSize: 12 }}>{d.depth_m.toLocaleString("en-IN")} m{cite(d.source_ref)}</span>
                      ))}
                    </div>
                    {f.quotes[0] && (
                      <div style={{ color: "var(--text-2)" }}>
                        &ldquo;{f.quotes[0].text.length > 220 ? f.quotes[0].text.slice(0, 217) + "…" : f.quotes[0].text}&rdquo;{cite(f.quotes[0].source_ref)}
                      </div>
                    )}
                    {f.quotes.length > 1 && (
                      <button type="button" className="kk-row-link" style={{ marginTop: 4, fontSize: 12 }} onClick={() => setOpen(isOpen ? null : f.key)} aria-expanded={isOpen}>
                        {isOpen ? t("Hide", "छिपाएँ") : t(`${f.n_sentences} sentences in ${f.n_documents} records ▸`, `${f.n_documents} अभिलेखों में ${f.n_sentences} वाक्य ▸`)}
                      </button>
                    )}
                    {isOpen && f.quotes.slice(1).map((q) => (
                      <div key={q.source_ref} style={{ color: "var(--text-2)", marginTop: 4 }}>
                        &ldquo;{q.text.length > 260 ? q.text.slice(0, 257) + "…" : q.text}&rdquo;{cite(q.source_ref)}
                      </div>
                    ))}
                  </>
                )}
              </div>

              <div role="cell" style={{ fontSize: 13 }}>
                {!f.analogs ? (
                  <span className="label">{t("No rock type in the records, so no analogue is claimed.", "अभिलेखों में शैल प्रकार नहीं, अतः कोई अनुरूप दावा नहीं।")}</span>
                ) : (
                  <>
                    {f.analogs.hazards.length === 0 && <span className="label">{t("No recorded problems in matched wells.", "मेल खाते कूपों में कोई समस्या दर्ज नहीं।")}</span>}
                    {f.analogs.hazards.map((h) => (
                      <div key={h.hazard} style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                        <span>{hazardText(h.hazard, lang)}</span>
                        <span className="mono">
                          <strong>{pct(h.mean)}%</strong> <span className="label">({pct(h.ci[0])}–{pct(h.ci[1])}%)</span>
                        </span>
                      </div>
                    ))}
                    <div className="label" style={{ marginTop: 2 }}>
                      {t(`${f.analogs.lithology} · ${f.analogs.n_wells_documented.toLocaleString("en-IN")} documented wells`, `${f.analogs.lithology} · ${f.analogs.n_wells_documented.toLocaleString("en-IN")} प्रलेखित कूप`)}
                      {f.analogs.countries.length > 0 && ` · ${f.analogs.countries.slice(0, 3).join(", ")}`}
                    </div>
                    {f.analogs.fixes[0] && (
                      <div style={{ marginTop: 4 }}>
                        {t("Worked there", "वहाँ कारगर")}: <strong>{actionText(f.analogs.fixes[0].action, lang)}</strong>{" "}
                        <span className="mono">{Number.isInteger(f.analogs.fixes[0].k) ? f.analogs.fixes[0].k : f.analogs.fixes[0].k.toFixed(1)} {t("of", "में से")} {f.analogs.fixes[0].n}</span>
                        {f.analogs.fixes[0].anecdotal && <span className="label"> · {t("anecdotal", "किस्सागत")}</span>}
                      </div>
                    )}
                    {onPick && (
                      <button type="button" className="kk-row-link" style={{ marginTop: 4, fontSize: 12 }} onClick={() => onPick(f.analogs!.lithology)}>
                        {t("Open these analogues ▾", "ये अनुरूप खोलें ▾")}
                      </button>
                    )}
                  </>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="label" style={{ padding: "10px 20px", borderTop: "1px solid var(--border)", background: "var(--surface-2)" }}>
        {col.caveat}
      </div>
    </div>
  );
}
