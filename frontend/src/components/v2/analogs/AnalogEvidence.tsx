"use client";
import type { Lang } from "@/lib/i18n";
import { Register, type Col } from "@/components/kk/Register";
import { SourceFootnote } from "@/components/kk/SourceFootnote";
import { Badge } from "@/components/v2/ui";
import { hazardText } from "@/lib/format";
import { RangeBar } from "./RangeBar";
import { tr } from "./trLocal";

export type HazardRow = {
  hazard: string; label: string; status: string; mean: number; ci: [number, number]; ci_level: number;
  n_eff: number; n_wells: number; n_with_event: number; examples: string[];
};
export type CountryRow = { country: string; n_intervals: number; n_wells: number; n_wells_documented: number };
export type AnalogResult = {
  query: { lithology: string; canonical_class: string | null; top_m: number; base_m: number; basin: string | null; basin_name?: string | null };
  n_intervals: number; n_wells: number; by_country: CountryRow[]; hazards: HazardRow[]; fixes: any[]; caveat: string;
};

export function AnalogEvidence({ result, lang }: { result: AnalogResult; lang: Lang }) {
  const t = (en: string, hi: string) => tr(lang, en, hi);
  const maxCountry = Math.max(1, ...result.by_country.map((c) => c.n_wells));
  const ciLevel = result.hazards[0]?.ci_level ?? 0.8;

  const cols: Col<HazardRow>[] = [
    { key: "h", head: t("Hazard", "खतरा"), cell: (r) => hazardText(r.hazard, lang) },
    { key: "s", head: t("Status", "स्थिति"), cell: (r) => (r.status === "ok" ? "" : <Badge kind="caution">{t("insufficient evidence", "अपर्याप्त साक्ष्य")}</Badge>) },
    { key: "m", head: t("Mean", "औसत"), num: true, cell: (r) => (r.status === "ok" ? `${Math.round(r.mean * 100)}%` : "—") },
    { key: "r", head: `${Math.round(ciLevel * 100)}% range`, cell: (r) => (r.status === "ok" ? <RangeBar mean={r.mean} ci={r.ci} /> : <span className="label">—</span>) },
    { key: "n", head: t("n wells", "n कूप"), num: true, cell: (r) => r.n_wells },
    { key: "e", head: t("with event", "घटना सहित"), num: true, cell: (r) => r.n_with_event },
    {
      key: "ex", head: t("examples", "उदाहरण"), cell: (r) => (
        <span>{r.examples.slice(0, 3).map((ref, i) => <SourceFootnote key={ref} refId={ref} n={i + 1} />)}</span>
      ),
    },
  ];

  return (
    <div>
      <div className="flex items-start gap-2 flex-wrap">
        <Badge kind="caution">{t("Analogue evidence from public wells outside India", "भारत से बाहर सार्वजनिक कूपों से अनुरूप साक्ष्य")}</Badge>
        <span className="label max-w-prose">{result.caveat}</span>
      </div>
      <p className="label mt-2">
        {t(
          `${result.n_intervals.toLocaleString()} matched intervals across ${result.n_wells.toLocaleString()} wells worldwide, at this lithology and depth band.`,
          `इस लिथोलॉजी व गहराई परास हेतु विश्व भर में ${result.n_wells.toLocaleString()} कूपों में ${result.n_intervals.toLocaleString()} मेल खाते अंतराल।`
        )}
      </p>

      <div className="mt-4">
        <Register rows={result.hazards} cols={cols} caption={t("Per-hazard analog evidence", "प्रति-खतरा अनुरूप साक्ष्य")} empty={t("No hazard rows.", "कोई पंक्ति नहीं।")} />
      </div>

      {result.by_country.length > 0 && (
        <div className="mt-4">
          <div className="label mb-1">{t("Evidence by country", "देश अनुसार साक्ष्य")}</div>
          <div className="space-y-1">
            {result.by_country.map((c) => (
              <div key={c.country} className="flex items-center gap-2 small">
                <span style={{ width: 90 }}>{c.country}</span>
                <div style={{ background: "var(--surface-2, var(--card))", height: 10, flex: 1, maxWidth: 220, position: "relative" }}>
                  <div style={{ background: "var(--accent)", height: 10, width: `${(c.n_wells / maxCountry) * 100}%` }} />
                </div>
                <span className="num label">{c.n_wells} {t("wells", "कूप")} ({c.n_wells_documented} {t("documented", "प्रलेखित")})</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
