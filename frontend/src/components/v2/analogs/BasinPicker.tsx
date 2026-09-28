"use client";
import type { Lang } from "@/lib/i18n";
import { SourceFootnote } from "@/components/kk/SourceFootnote";
import { hazardLabel, hazardText } from "@/lib/format";
import { tr } from "./trLocal";
import { hazardColor, lithColor } from "@/lib/palette";

export type Basin = { slug: string; name: string; url: string; category: string | null; suggestions: Suggestion[] };
export type Suggestion = { type: "lithology" | "formation"; value: string; text: string; source_ref: string; depth_hints_m: string[] };

const HAZ = Object.keys(hazardLabel);

export function BasinPicker({
  basins, basinSlug, setBasinSlug, classes, lithology, setLithology, top, setTop, base, setBase,
  hazards, setHazards, onPickSuggestion, lang,
}: {
  basins: Basin[]; basinSlug: string | null; setBasinSlug: (s: string) => void;
  classes: string[]; lithology: string; setLithology: (s: string) => void;
  top: number; setTop: (n: number) => void; base: number; setBase: (n: number) => void;
  hazards: Set<string>; setHazards: (s: Set<string>) => void;
  onPickSuggestion: (s: Suggestion) => void; lang: Lang;
}) {
  const t = (en: string, hi: string) => tr(lang, en, hi);
  const basin = basins.find((b) => b.slug === basinSlug) ?? null;

  const toggleHazard = (h: string) => {
    const n = new Set(hazards);
    if (n.has(h)) n.delete(h); else n.add(h);
    setHazards(n);
  };

  return (
    <div>
      <div className="flex flex-wrap items-center gap-3">
        <label className="label" htmlFor="basin">{t("Indian basin", "भारतीय द्रोणी")}</label>
        <select id="basin" className="input min-w-[14rem]" value={basinSlug ?? ""} onChange={(e) => setBasinSlug(e.target.value)}>
          {basins.map((b) => <option key={b.slug} value={b.slug}>{b.name}</option>)}
        </select>
        {basin?.url && <a className="link small" href={basin.url} target="_blank" rel="noreferrer">NDR ↗</a>}
      </div>

      {basin && basin.suggestions.length > 0 && (
        <div className="mt-3">
          <div className="label mb-1">{t("Cited suggestions for this basin (click a lithology to search it)", "इस द्रोणी हेतु उद्धृत सुझाव (लिथोलॉजी पर क्लिक कर खोजें)")}</div>
          <div className="flex flex-wrap gap-1.5" role="group" aria-label="basin suggestions">
            {basin.suggestions.map((s, i) => {
              const c = s.type === "lithology" ? lithColor(s.value) : "#8B5CF6";
              return (
                <span key={i} className="chip" style={{ cursor: s.type === "lithology" ? "pointer" : "default", opacity: s.type === "lithology" ? 1 : 0.85 }}
                  onClick={s.type === "lithology" ? () => onPickSuggestion(s) : undefined}
                  title={s.text}>
                  <span aria-hidden="true" className="inline-block mr-1.5" style={{ width: 7, height: 7, borderRadius: 2, background: c }} />
                  {s.type === "lithology" ? t("lithology:", "लिथोलॉजी:") : t("formation:", "संरचना:")} {s.value}
                  <SourceFootnote refId={s.source_ref} n={i + 1} />
                </span>
              );
            })}
          </div>
        </div>
      )}

      <div className="mt-4 flex flex-wrap items-end gap-3 rule-t pt-3">
        <div>
          <label className="label block" htmlFor="lith">{t("Lithology class", "लिथोलॉजी वर्ग")}</label>
          <select id="lith" className="input" value={lithology} onChange={(e) => setLithology(e.target.value)}>
            {classes.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div>
          <label className="label block" htmlFor="top">{t("Depth top (m MD)", "गहराई ऊपर (मी MD)")}</label>
          <input id="top" type="number" className="input w-28" value={top} onChange={(e) => setTop(Number(e.target.value))} />
        </div>
        <div>
          <label className="label block" htmlFor="base">{t("Depth base (m MD)", "गहराई नीचे (मी MD)")}</label>
          <input id="base" type="number" className="input w-28" value={base} onChange={(e) => setBase(Number(e.target.value))} />
        </div>
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5" role="group" aria-label="hazard filter">
        <span className="label mr-1">{t("Hazards", "खतरे")}</span>
        <button className="chip" aria-pressed={hazards.size === 0} onClick={() => setHazards(new Set())}>{t("All", "सभी")}</button>
        {HAZ.map((h) => {
          const c = hazardColor(h);
          const active = hazards.has(h);
          return (
            <button key={h} className="chip" aria-pressed={active} onClick={() => toggleHazard(h)}>
              <span aria-hidden="true" className="inline-block mr-1.5" style={{ width: 7, height: 7, borderRadius: 2, background: c }} />
              {hazardText(h, lang)}
            </button>
          );
        })}
      </div>
    </div>
  );
}
