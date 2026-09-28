"use client";
import { useEffect, useState } from "react";
import { get } from "@/lib/api";
import { useApp } from "@/lib/state";
import { t } from "@/lib/i18n";
import { countryColor } from "@/lib/palette";

type Row = { country: string; wells: number; located_wells: number; documents_linked: number; events: number; episodes: number };

let cache: Promise<Row[]> | null = null;
export const loadCountries = () => (cache ??= get("/api/countries").catch(() => { cache = null; return []; }));

/** Country chips (shared across screens). Counts come from /api/countries; `metric` picks which count is shown. */
export function CountryFilter({ metric = "wells", label }: { metric?: keyof Omit<Row, "country">; label?: string }) {
  const { country, setCountry, lang } = useApp();
  const [rows, setRows] = useState<Row[]>([]);
  useEffect(() => { loadCountries().then(setRows); }, []);
  if (!rows.length) return null;
  const unit = metric === "events" ? "events" : metric === "episodes" ? "episodes" : "wells";
  return (
    <div className="flex items-center gap-2 flex-wrap" role="group" aria-label="country filter">
      <span className="label">{label ?? t("countryLabel", lang)}</span>
      <button className="chip" aria-pressed={country === null} onClick={() => setCountry(null)}>{t("allOpt", lang)}</button>
      {rows.map((r) => {
        const c = countryColor(r.country);
        const active = country === r.country;
        return (
          <button key={r.country} className="chip" aria-pressed={active} onClick={() => setCountry(r.country)}
            title={`${r.wells.toLocaleString()} wells (${r.located_wells.toLocaleString()} located) · ${r.documents_linked.toLocaleString()} documents · ${r.events.toLocaleString()} events`}>
            <span aria-hidden="true" className="inline-block mr-1.5" style={{ width: 8, height: 8, borderRadius: 2, background: c }} />
            {r.country} <span className="mono text-ink2">{Number(r[metric]).toLocaleString()}</span><span className="sr-only"> {unit}</span>
          </button>
        );
      })}
    </div>
  );
}
