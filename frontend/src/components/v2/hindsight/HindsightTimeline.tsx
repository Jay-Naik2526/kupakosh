"use client";
import { useMemo, useState } from "react";
import { scaleLinear } from "d3-scale";
import type { Lang } from "@/lib/i18n";
import { useApp } from "@/lib/state";
import { Badge, Button } from "@/components/v2/ui";
import { LithologyColumn } from "@/components/kk/LithologyColumn";
import { DepthAxis } from "@/components/kk/CurveTrack";
import { hazardLabel, hazardText, m as fmtM } from "@/lib/format";
import { tr } from "./trLocal";

export type WellRow = {
  well_id: number; name: string; field: string | null; country: string; source: string;
  n_offsets: number; events: number; forewarned: number; missed: number; median_lead_m: number | null;
  alerts: number; alerts_with_event: number; alerts_without_record: number;
};

type Formation = { formation: string; label: string; top_md_m: number; base_md_m: number; lithology: string | null; source_ref: string };
type Alert = {
  formation: string; formation_label: string; hazard: string; label: string; top_md_m: number; alert_md_m: number;
  mean: number; ci: [number, number]; n_eff: number; n_wells: number; status: string; base: number; rr: number | null;
};
type EventRow = {
  event_id: number; hazard: string; label: string; md_m: number; formation: string | null; formation_label: string;
  source_ref: string; evidence: string; forewarned: boolean; lead_m: number | null;
  alert_ref: { formation: string; hazard: string; alert_md_m: number; mean: number; base: number; rr: number | null; n_eff: number } | null;
};
export type WellDetail = {
  well: { id: number; name: string; field: string | null; country: string; source: string; td_md_m: number | null };
  alert_mode: string; testable: boolean; n_offsets: number; n_offsets_documented: number;
  formations: Formation[]; alerts: Alert[]; events: EventRow[];
  summary: { events: number; forewarned: number; missed: number; alerts: number; alerts_with_event: number; alerts_without_record: number; median_lead_m: number | null };
};

const H = 620, LITH_W = 150, LANE_W = 230, MIN_LABEL_GAP = 15;

/** Push overlapping labels apart vertically (min gap) while keeping each item's true depth for its marker/tick. */
function layoutLabels<T extends { yTrue: number }>(items: T[]): (T & { yLabel: number })[] {
  const withIdx = items.map((it, i) => ({ ...it, i }));
  const sortedIdx = [...withIdx].sort((a, b) => a.yTrue - b.yTrue);
  let prev = -Infinity;
  const laid = sortedIdx.map((it) => {
    const yLabel = Math.max(it.yTrue, prev + MIN_LABEL_GAP);
    prev = yLabel;
    return { ...it, yLabel };
  });
  const byIdx = new Map(laid.map((o) => [o.i, o]));
  return withIdx.map((it) => byIdx.get(it.i)!);
}

/** Zone B: pick a testable well, blind-replay it as a vertical depth timeline, then reveal what really happened. */
export function HindsightTimeline({
  wells, wellId, onPick, detail, lang,
}: { wells: WellRow[]; wellId: number | null; onPick: (id: number) => void; detail: WellDetail | null; lang: Lang }) {
  const { openSource } = useApp();
  const [revealed, setRevealed] = useState(false);
  const [picked, setPicked] = useState<{ kind: "alert" | "event"; i: number } | null>(null);
  const t = (en: string, hi: string) => tr(lang, en, hi);

  const sorted = useMemo(() => [...wells].sort((a, b) => b.events - a.events), [wells]);
  const td = detail?.well.td_md_m ?? 3000;
  const y = scaleLinear().domain([0, td]).range([10, H]);

  const matchedAlertKeys = useMemo(() => {
    const s = new Set<string>();
    (detail?.events ?? []).forEach((e) => { if (e.forewarned && e.alert_ref) s.add(`${e.alert_ref.formation}|${e.alert_ref.hazard}`); });
    return s;
  }, [detail]);

  const alertLaid = useMemo(() => layoutLabels((detail?.alerts ?? []).map((a) => ({ a, yTrue: y(a.alert_md_m) }))), [detail, y]);
  const eventLaid = useMemo(() => layoutLabels((detail?.events ?? []).map((ev) => ({ ev, yTrue: y(ev.md_m) }))), [detail, y]);

  return (
    <div>
      <div className="flex flex-wrap items-center gap-3">
        <label className="label" htmlFor="hswell">{t("Testable well", "परीक्षण-योग्य कूप")}</label>
        <select id="hswell" className="input min-w-[16rem]" value={wellId ?? ""} onChange={(e) => e.target.value && onPick(Number(e.target.value))}>
          {sorted.map((w) => (
            <option key={w.well_id} value={w.well_id}>
              {w.name} · {w.field ?? w.country} · {w.events} {t("events", "घटनाएँ")} · {w.forewarned}/{w.events} {t("forewarned", "पूर्व-चेतावनी")}
            </option>
          ))}
        </select>
        <Button onClick={() => setRevealed((r) => !r)} variant={revealed ? "primary" : "default"}>
          {revealed ? t("Hide real events (blind view)", "वास्तविक घटनाएँ छुपाएँ (अंध दृश्य)") : t("Reveal what really happened", "वास्तव में क्या हुआ, प्रकट करें")}
        </Button>
      </div>

      {!detail && <div className="label mt-4">{t("Loading…", "लोड हो रहा है…")}</div>}

      {detail && (
        <div className="mt-4">
          <div className="flex flex-wrap items-center gap-2 mb-2">
            <span className="font-semibold">{detail.well.name}</span>
            <span className="label">{detail.well.field ?? detail.well.country} · {detail.well.source}</span>
            {!detail.testable && <Badge kind="caution">{t("not testable", "परीक्षण-योग्य नहीं")}</Badge>}
            <span className="label ml-auto">
              {t(
                `${detail.summary.alerts} alerts · ${detail.summary.alerts_with_event} matched a record · ${detail.summary.forewarned}/${detail.summary.events} problems forewarned`,
                `${detail.summary.alerts} चेतावनियाँ · ${detail.summary.alerts_with_event} अभिलेख से मेल · ${detail.summary.forewarned}/${detail.summary.events} समस्याएँ पूर्व-चेतावनी दी गईं`
              )}
            </span>
          </div>

          <div className="flex gap-0 overflow-x-auto">
            <div>
              <div className="small label mono mb-1" style={{ height: 16 }}>&nbsp;</div>
              <DepthAxis y={y} height={H} width={44} />
            </div>
            <div>
              <div className="small label mono mb-1" style={{ height: 16 }}>{t("FORMATION", "संरचना")}</div>
              <LithologyColumn intervals={detail.formations} y={y} width={LITH_W} height={H} labels />
            </div>
            {/* alerts lane */}
            <div>
              <div className="small label mono mb-1" style={{ height: 16 }}>{t("ALERTS (blind)", "चेतावनियाँ (अंध)")}</div>
              <svg width={LANE_W} height={H} role="img" aria-label="blind alerts by depth">
                <line x1={0} x2={0} y1={0} y2={H} stroke="var(--rule)" />
                {detail.alerts.length === 0 && <text x={10} y={16} fontSize={11} fill="var(--ink-2)">{t("no alerts would have fired", "कोई चेतावनी नहीं दी जाती")}</text>}
                {alertLaid.map(({ a, yTrue, yLabel }, i) => {
                  const matched = matchedAlertKeys.has(`${a.formation}|${a.hazard}`);
                  const isSel = picked?.kind === "alert" && picked.i === i;
                  return (
                    <g key={i} style={{ cursor: "pointer" }} onClick={() => setPicked({ kind: "alert", i })}>
                      {Math.abs(yLabel - yTrue) > 1 && <line x1={0} x2={16} y1={yTrue} y2={yLabel} stroke={matched ? "var(--hazard)" : "var(--ink-2)"} strokeWidth={0.8} opacity={0.6} />}
                      <line x1={0} x2={16} y1={yTrue} y2={yTrue} stroke={matched ? "var(--hazard)" : "var(--ink-2)"} strokeDasharray={matched ? undefined : "2 2"} strokeWidth={isSel ? 2.2 : 1.1} opacity={matched ? 0.9 : 0.6} />
                      <circle cx={10} cy={yTrue} r={4} fill={matched ? "var(--hazard)" : "var(--surface, var(--card))"} stroke={matched ? "var(--hazard)" : "var(--ink-2)"} strokeWidth={1.3} />
                      <text x={20} y={yLabel + 4} fontSize={11} fill="var(--ink)">{hazardLabel[a.hazard] ?? a.hazard} <tspan className="num" fill="var(--ink-2)">{Math.round(a.mean * 100)}%</tspan></text>
                    </g>
                  );
                })}
              </svg>
            </div>
            {/* events lane (revealed) */}
            <div>
              <div className="small label mono mb-1" style={{ height: 16 }}>{revealed ? t("REAL EVENTS", "वास्तविक घटनाएँ") : t("hidden — click Reveal", "छुपा — प्रकट करें दबाएँ")}</div>
              <svg width={LANE_W} height={H} role="img" aria-label="real recorded events by depth">
                <line x1={0} x2={0} y1={0} y2={H} stroke="var(--rule)" />
                {revealed && eventLaid.map(({ ev, yTrue, yLabel }, i) => {
                  const isSel = picked?.kind === "event" && picked.i === i;
                  const color = ev.forewarned ? "var(--ok)" : "var(--hazard)";
                  return (
                    <g key={ev.event_id}>
                      {ev.forewarned && ev.alert_ref && (
                        <line x1={-LANE_W} x2={0} y1={y(ev.alert_ref.alert_md_m)} y2={yTrue} stroke="var(--ok)" strokeWidth={1} strokeDasharray="2 3" opacity={0.7} />
                      )}
                      {Math.abs(yLabel - yTrue) > 1 && <line x1={0} x2={16} y1={yTrue} y2={yLabel} stroke={color} strokeWidth={0.8} opacity={0.6} />}
                      <g style={{ cursor: "pointer" }} onClick={(e) => { e.stopPropagation(); setPicked({ kind: "event", i }); openSource(ev.source_ref); }}>
                        <circle cx={10} cy={yTrue} r={4.5} fill={color} stroke="var(--ink)" strokeWidth={isSel ? 1.6 : 0.8} />
                        <text x={20} y={yLabel + 4} fontSize={11} fill="var(--ink)">
                          {hazardLabel[ev.hazard] ?? ev.hazard}
                          {ev.forewarned ? <tspan fill="var(--ok)" className="num"> · +{Math.round(ev.lead_m ?? 0)} m {t("lead", "अग्रता")}</tspan> : <tspan fill="var(--hazard)"> · {t("missed", "छूट गई")}</tspan>}
                        </text>
                      </g>
                    </g>
                  );
                })}
              </svg>
            </div>
          </div>

          {picked && (
            <DetailPanel detail={detail} picked={picked} lang={lang} onOpenSource={openSource} />
          )}
          <p className="label mt-3">
            {t(
              "Grey dashed lines: alerts with no matching record here — reports under-record problems, so this is not proof of a false alarm.",
              "धूसर टूटी रेखाएँ: यहाँ कोई मेल खाता अभिलेख नहीं — रिपोर्टें समस्याओं को कम दर्ज करती हैं, इसलिए यह झूठी चेतावनी का प्रमाण नहीं है।"
            )}
          </p>
        </div>
      )}
    </div>
  );
}

function DetailPanel({ detail, picked, lang, onOpenSource }: { detail: WellDetail; picked: { kind: "alert" | "event"; i: number }; lang: Lang; onOpenSource: (r: string) => void }) {
  const t = (en: string, hi: string) => tr(lang, en, hi);
  if (picked.kind === "alert") {
    const a = detail.alerts[picked.i];
    if (!a) return null;
    return (
      <div className="mt-3 kk-card">
        <div className="font-semibold">{hazardText(a.hazard, lang)} · {a.formation_label}</div>
        <p className="label mt-1">
          {t(
            `Blind posterior ${Math.round(a.mean * 100)}% (80% range ${Math.round(a.ci[0] * 100)}–${Math.round(a.ci[1] * 100)}%), n_eff ${a.n_eff} from ${a.n_wells} offset wells. Field base rate ${Math.round(a.base * 100)}%${a.rr !== null ? ` (${a.rr}× base)` : ""}. Would alert at ${fmtM(a.alert_md_m)}.`,
            `अंध पश्च संभावना ${Math.round(a.mean * 100)}% (80% परास ${Math.round(a.ci[0] * 100)}–${Math.round(a.ci[1] * 100)}%), n_eff ${a.n_eff}, ${a.n_wells} निकट कूपों से। क्षेत्र औसत दर ${Math.round(a.base * 100)}%${a.rr !== null ? ` (आधार का ${a.rr}×)` : ""}। ${fmtM(a.alert_md_m)} पर चेतावनी देती।`
          )}
        </p>
      </div>
    );
  }
  const e = detail.events[picked.i];
  if (!e) return null;
  return (
    <div className="mt-3 kk-card">
      <div className="flex items-center justify-between gap-3">
        <div className="font-semibold">{hazardText(e.hazard, lang)} · {e.formation_label} · {fmtM(e.md_m)}</div>
        <Button onClick={() => onOpenSource(e.source_ref)}>{t("View source", "स्रोत देखें")}</Button>
      </div>
      <p className="mt-1 small">{e.evidence}</p>
      <p className="label mt-1">
        {e.forewarned
          ? t(`Forewarned ${Math.round(e.lead_m ?? 0)} m ahead by the ${hazardText(e.hazard, lang)} alert in ${e.alert_ref?.formation}.`, `${hazardText(e.hazard, lang)} चेतावनी ने ${e.alert_ref?.formation} में ${Math.round(e.lead_m ?? 0)} मी पहले सूचित किया।`)
          : t("No blind alert covered this depth/formation — a missed problem.", "इस गहराई/संरचना के लिए कोई अंध चेतावनी नहीं थी — एक छूटी हुई समस्या।")}
      </p>
    </div>
  );
}
