"use client";
import { useApp } from "@/lib/state";
import { pct, m as fmtM } from "@/lib/format";
import { hazardColor } from "@/lib/palette";

/** Shape returned by backend engines/hazard.posterior() (see backend/app/engines/hazard.py:posterior),
 *  optionally widened with the extra fields engines/lookahead.py adds (formation_label, label = hazard label). */
export type PosteriorEvidenceEvent = { event_id: number; md_m: number; source_ref: string };
export type PosteriorEvidence = { well_id: number; name: string; weight: number; y: number; distance_m: number; events: PosteriorEvidenceEvent[] };
export type Posterior = {
  formation?: string;
  formation_label?: string;
  hazard?: string;
  label?: string; // hazard label, e.g. "Stuck pipe"
  mean: number;
  ci: [number, number];
  ci_level?: number;
  n_eff: number;
  n_wells: number;
  n_with_event: number;
  status: string; // "ok" | "insufficient_evidence"
  prior: { base_rate: number; base_n: number; scope: string; strength: number; source: string | null };
  evidence: PosteriorEvidence[];
};

const tr = (lang: string, en: string, hi: string) => (lang === "hi" ? hi : en);
const scopeLabel = (lang: string, scope: string) => {
  const words = scope.replace(/_/g, " ");
  return tr(lang, words, words); // scope text stays English (field/source names); kept as-is for both languages
};

/** "Why this number?" explainability panel — plain-language sentence, per-well evidence bars, prior, n_eff, range, clickable sources. */
export function WhyPanel({ posterior }: { posterior: Posterior }) {
  const { lang, openSource } = useApp();
  const p = posterior;
  const ok = p.status === "ok";
  const hazardWord = p.label ?? tr(lang, "this hazard", "इस समस्या");
  const withEvent = p.evidence.filter((e) => e.y > 0);
  const withoutEvent = p.evidence.filter((e) => !(e.y > 0));

  const sentence = ok
    ? tr(
        lang,
        `${pct(p.mean)} because ${p.n_with_event} of ${p.n_wells} nearby well${p.n_wells === 1 ? "" : "s"} that drilled this layer recorded ${hazardWord.toLowerCase()}; field average ${pct(p.prior.base_rate)}.`,
        `${pct(p.mean)} क्योंकि इस परत में ड्रिल करने वाले ${p.n_wells} में से ${p.n_with_event} निकट कूपों में ${hazardWord} दर्ज हुआ; क्षेत्र औसत ${pct(p.prior.base_rate)}।`
      )
    : tr(
        lang,
        `Insufficient evidence: only ${p.n_eff.toFixed(1)} effective well${p.n_eff === 1 ? "" : "s"} of similarity-weighted evidence (${p.n_with_event} of ${p.n_wells} offset wells recorded ${hazardWord.toLowerCase()}) — below the minimum needed to trust a number here.`,
        `अपर्याप्त साक्ष्य: केवल ${p.n_eff.toFixed(1)} प्रभावी कूप (समानता-भारित) — यहाँ भरोसे लायक आँकड़े के लिए न्यूनतम से कम। (${p.n_wells} निकट कूपों में से ${p.n_with_event} में ${hazardWord} दर्ज)।`
      );

  const maxW = Math.max(0.01, ...p.evidence.map((e) => e.weight));
  const hc = hazardColor(p.hazard ?? "");

  return (
    <div className="kk-card" style={{ padding: 14, marginTop: 10, background: "var(--surface-2)", borderLeft: `3px solid ${hc}` }} aria-label="Why this number">
      <p className="small" style={{ marginTop: 0 }}>{sentence}</p>

      <div className="label" style={{ display: "flex", flexWrap: "wrap", gap: "4px 16px", margin: "8px 0" }}>
        <span>{tr(lang, "Prior / field average", "पूर्व / क्षेत्र औसत")}: <span className="num">{pct(p.prior.base_rate)}</span> ({scopeLabel(lang, p.prior.scope)}, n={p.prior.base_n})</span>
        <span>{tr(lang, "Effective evidence", "प्रभावी साक्ष्य")}: <span className="num">{p.n_eff.toFixed(1)}</span> {tr(lang, "wells", "कूप")}</span>
        {ok && <span>{tr(lang, "80% range", "80% परास")}: <span className="num">{pct(p.ci[0])}–{pct(p.ci[1])}</span></span>}
      </div>

      {p.evidence.length === 0 ? (
        <p className="label">{tr(lang, "No offset well in radius penetrated this formation with a recorded outcome.", "त्रिज्या में किसी भी निकट कूप ने इस संरचना को दर्ज परिणाम सहित नहीं भेदा।")}</p>
      ) : (
        <ul style={{ margin: "6px 0 0", padding: 0, listStyle: "none" }}>
          {[...withEvent, ...withoutEvent].map((e) => (
            <li key={e.well_id} style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: "2px 10px", alignItems: "center", padding: "5px 0", borderBottom: "1px solid var(--border)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
                <span aria-hidden="true" style={{ color: e.y > 0 ? hc : "var(--text-2)", fontWeight: 700 }}>{e.y > 0 ? "●" : "○"}</span>
                <span className="small" style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{e.name}</span>
              </div>
              <span className="label num">{fmtM(e.distance_m)}</span>
              <div style={{ gridColumn: "1 / -1", display: "flex", alignItems: "center", gap: 8 }}>
                <div style={{ flex: "1 1 auto", height: 7, background: "var(--border)", borderRadius: 999, overflow: "hidden" }} title={`weight ${e.weight.toFixed(2)}`}>
                  <div style={{ width: `${Math.max(3, (e.weight / maxW) * 100)}%`, height: "100%", background: e.y > 0 ? hc : "var(--text-2)", opacity: e.y > 0 ? 1 : 0.5 }} />
                </div>
                <span className="label num" style={{ flex: "0 0 auto" }}>w={e.weight.toFixed(2)}</span>
                {e.events.length > 0 && (
                  <span className="label" style={{ flex: "0 0 auto", display: "flex", gap: 4, flexWrap: "wrap" }}>
                    {e.events.map((ev) => (
                      <button key={ev.event_id} className="btn" style={{ padding: "0px 7px", fontSize: "0.78rem" }} onClick={() => openSource(ev.source_ref)}>
                        {Math.round(ev.md_m)} m ▸
                      </button>
                    ))}
                  </span>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
      <p className="label" style={{ marginTop: 8, marginBottom: 0 }}>
        {tr(lang, "● = recorded the problem here · ○ = drilled the layer, no record · bar width = similarity weight to the active well.",
                  "● = यहाँ समस्या दर्ज · ○ = परत ड्रिल की, कोई दर्ज नहीं · पट्टी की चौड़ाई = सक्रिय कूप से समानता भार।")}
      </p>
    </div>
  );
}
