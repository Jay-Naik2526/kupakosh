"use client";
import { useEffect, useState } from "react";
import { get } from "@/lib/api";
import { actionText, hazardLabel, hazardText, m, pretty } from "@/lib/format";
import { Register } from "@/components/kk/Register";
import { IntervalBar } from "@/components/kk/IntervalBar";
import { SourceFootnote } from "@/components/kk/SourceFootnote";
import { EmptyState } from "@/components/kk/EmptyState";
import { useApp } from "@/lib/state";
import { CountryFilter } from "@/components/kk/CountryFilter";
import { t } from "@/lib/i18n";

const OUT_GLYPH: Record<string, string> = { resolved: "✓ resolved", partial: "◐ partial", unresolved: "✕ unresolved", worsened: "▲ worsened", unknown: "? unknown" };
const OUT_GLYPH_HI: Record<string, string> = { resolved: "✓ समाधान", partial: "◐ आंशिक", unresolved: "✕ अनसुलझा", worsened: "▲ बिगड़ा", unknown: "? अज्ञात" };

export default function Fixes() {
  const { wellId, country, lang } = useApp();
  const [hazard, setHazard] = useState("stuck_pipe");
  const [formation, setFormation] = useState("");
  const [scope, setScope] = useState<"all" | "offsets">("all");
  const [forms, setForms] = useState<any[]>([]);
  const [L, setL] = useState<any>(null);
  const [open, setOpen] = useState<number | null>(null);
  const [eps, setEps] = useState<any[]>([]);

  useEffect(() => { get("/api/formations", { hazard, min_wells: 3, country: country ?? undefined }).then((f) => setForms(f.filter((x: any) => x.n_well_events > 0))); }, [hazard, country]);
  useEffect(() => {
    setOpen(null);
    get("/api/ledger", { hazard, formation: formation || undefined, well: scope === "offsets" && wellId ? wellId : undefined, country: country ?? undefined }).then(setL);
  }, [hazard, formation, scope, wellId, country]);
  const expand = (r: any, i: number) => {
    if (open === i) { setOpen(null); return; }
    setOpen(i); setEps([]);
    get("/api/episodes", { ids: r.episode_ids.slice(0, 40).join(","), limit: 40 }).then((e) => setEps(e.filter((x: any) => x.outcome !== "unknown").concat(e.filter((x: any) => x.outcome === "unknown"))));
  };
  const rows = (L?.rows ?? []).filter((r: any) => r.n > 0 || r.unknown_outcome > 0);

  return (
    <div>
      {/* Zone A — selectors, in a toolbar card */}
      <section className="kk-card flex flex-wrap items-center gap-3" aria-label="selectors">
        <label className="label" htmlFor="hz">{t("fixHazard", lang)}</label>
        <select id="hz" className="input" value={hazard} onChange={(e) => { setHazard(e.target.value); setFormation(""); }}>
          {Object.keys(hazardLabel).map((k) => <option key={k} value={k}>{hazardText(k, lang)}</option>)}
        </select>
        <label className="label" htmlFor="fm">{t("fixFormation", lang)}</label>
        <select id="fm" className="input" value={formation} onChange={(e) => setFormation(e.target.value)}>
          <option value="">{t("fixAllFormations", lang)}</option>
          {forms.map((f) => <option key={f.formation} value={f.formation}>{f.label} ({f.n_well_events} wells)</option>)}
        </select>
        <span className="label">{t("fixScope", lang)}</span>
        <button className="chip" aria-pressed={scope === "all"} onClick={() => setScope("all")}>{t("fixAllRecords", lang)}</button>
        <button className="chip" aria-pressed={scope === "offsets"} onClick={() => setScope("offsets")} disabled={!wellId} title={wellId ? "" : t("fixPickWellFirst", lang)}>{t("fixActiveOffsets", lang)}</button>
        <CountryFilter metric="episodes" label={t("countryLabel", lang)} />
        {L && <span className="ml-auto small text-[var(--text-2)]">{L.n_episodes} episodes · {L.n_known_outcome} with a stated outcome</span>}
      </section>

      {/* Zone B — the ledger, a clean table with the outcome bar */}
      <section className="mt-6" aria-label="what worked">
        {L && rows.length === 0 && <EmptyState title={t("fixNoEpisodesTitle", lang)} why={t("fixNoEpisodesWhy", lang)} />}
        {L && rows.length > 0 && (
          <Register rows={rows} onRow={expand} selected={open}
            caption={t("fixCaption", lang)}
            cols={[
              { key: "fix", head: t("fixCol_fix", lang), cell: (r: any) => <span>{actionText(r.action, lang)}{r.anecdotal && <span className="label"> · {t("fixAnecdotalN", lang)}</span>}</span> },
              { key: "n", head: t("fixCol_cases", lang), num: true, cell: (r: any) => r.n },
              { key: "k", head: t("fixCol_worked", lang), num: true, cell: (r: any) => (Number.isInteger(r.k) ? r.k : r.k.toFixed(1)) },
              { key: "rate", head: t("fixCol_success", lang), num: true, cell: (r: any) => (r.rate === null ? "—" : `${Math.round(r.rate * 100)}%`) },
              { key: "lb", head: t("fixCol_lb", lang), num: true, cell: (r: any) => (r.lb === null ? "—" : `${Math.round(r.lb * 100)}%`) },
              { key: "bar", head: "", cell: (r: any) => <IntervalBar rate={r.rate} lb={r.lb} anecdotal={r.anecdotal} /> },
              { key: "med", head: t("fixCol_med", lang), num: true, cell: (r: any) => (r.median_hours === null ? t("offsUnknown", lang) : `${r.median_hours} h`) },
              { key: "worse", head: t("fixCol_worse", lang), num: true, cell: (r: any) => (r.worsened > 0 ? <span className="inline-flex items-center gap-1 font-semibold" style={{ color: "var(--hazard)" }}>▲ {r.worsened}</span> : "0") },
              { key: "unk", head: t("fixCol_unk", lang), num: true, cell: (r: any) => <span className="text-[var(--text-2)]">{r.unknown_outcome}</span> },
            ]} />
        )}
      </section>

      {/* Zone C — problem → action → outcome timeline for the expanded row */}
      {open !== null && rows[open] && (
        <section className="mt-6" aria-label="episodes">
          <h3 className="font-semibold">{t("fixEpisodesFor", lang)} “{actionText(rows[open].action, lang)}” — {hazardText(hazard, lang)}{formation ? ` in ${pretty(formation)}` : ""}</h3>
          {eps.length === 0 && <p className="label mt-2">{t("fixLoadingEllipsis", lang)}</p>}
          <div className="mt-3 space-y-4">
            {eps.map((e) => (
              <div key={e.id} className="grid gap-0 sm:grid-cols-[1fr_auto_1fr_auto_1fr]" style={{ alignItems: "stretch" }}>
                <Step n={1} title={`${t("fixProblem", lang)} · ${e.well}`} sub={`${m(e.md_m)}${e.formation ? " · " + pretty(e.formation) : ""}${e.event.t ? " · " + e.event.t.slice(0, 10) : ""}`} text={e.event.text} refId={e.event.source_ref} />
                <Arrow />
                <Step n={2} title={t("fixAction", lang)} sub={e.actions.map((a: any) => actionText(a.type, lang)).filter((v: any, i: number, s: any[]) => s.indexOf(v) === i).join(", ") || t("fixNoneRecorded", lang)}
                  text={e.actions[0]?.detail ? `…${e.actions[0].detail}…` : ""} refId={e.actions[0]?.source_ref} />
                <Arrow />
                <Step n={3} title={`${t("fixOutcome", lang)} · ${lang === "hi" ? OUT_GLYPH_HI[e.outcome] : OUT_GLYPH[e.outcome]}`} sub={e.hours_to_resolve ? `${e.hours_to_resolve} ${t("fixHoursLater", lang)}` : e.npt_hours ? `${e.npt_hours} ${t("fixHoursLostStated", lang)}` : ""}
                  text={e.outcome_text ?? t("fixNothingSaysEither", lang)} refId={e.outcome_ref} danger={e.outcome === "worsened"} />
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function Arrow() {
  return <div className="hidden sm:flex items-center justify-center px-2 text-[var(--text-2)]" aria-hidden="true">→</div>;
}

function Step({ n, title, sub, text, refId, danger }: { n: number; title: string; sub?: string; text?: string; refId?: string | null; danger?: boolean }) {
  return (
    <div className="border rounded-[var(--radius-lg)] p-3 small bg-[var(--surface)] mb-2 sm:mb-0"
         style={{ borderColor: danger ? "var(--hazard)" : "var(--border)", borderLeftWidth: danger ? 3 : 1 }}>
      <div className="flex items-center gap-2">
        <span className="num flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[var(--surface-2)] border border-[var(--border)] text-[0.68rem] font-bold text-[var(--text-2)]">{n}</span>
        <div className="font-semibold">{title}</div>
      </div>
      {sub && <div className="label mt-1">{sub}</div>}
      {text && <p className="mt-1">“{text.length > 260 ? text.slice(0, 260) + "…" : text}”{refId && <SourceFootnote refId={refId} n="src" />}</p>}
    </div>
  );
}
