import { ReactNode } from "react";
import { pct } from "@/lib/format";

/** Hazard card: 3px left rule (colour = state), title, big mono probability, range + n_eff line, actions. */
export function NoticeSlip({ level, title, where, mean, ci, neff, nWells, nWithEvent, status, children, actions }: {
  level: "alert" | "escalated" | "notice"; title: string; where: string; mean: number; ci: [number, number]; neff: number;
  nWells: number; nWithEvent: number; status: string; children?: ReactNode; actions?: ReactNode;
}) {
  const color = level === "escalated" ? "var(--hazard)" : level === "alert" ? "var(--hazard)" : "var(--caution)";
  const tag = level === "escalated" ? "ESCALATED · live signal matches" : level === "alert" ? "ALERT" : "NOTICE";
  const ok = status === "ok";
  return (
    <section className="bg-card border border-rule rounded-kk p-5" style={{ borderLeft: `3px solid ${color}` }} aria-live="polite">
      <div className="label mono" style={{ color }}>{level === "notice" ? "○" : "▲"} {tag}</div>
      <h2 className="font-semibold mt-1 uppercase tracking-wide">{title}</h2>
      <div className="text-ink2">{where}</div>
      {ok ? (
        <>
          <div className="num mt-3" style={{ fontSize: 40, lineHeight: 1 }}>{pct(mean)}</div>
          <div className="small mt-1">range {pct(ci[0])}–{pct(ci[1])} (80%) · evidence {neff.toFixed(1)} wells ({nWithEvent} of {nWells} with a record)</div>
        </>
      ) : (
        <>
          <div className="num mt-3" style={{ fontSize: 22 }}>Insufficient evidence</div>
          <div className="small mt-1">effective evidence {neff.toFixed(1)} well{neff === 1 ? "" : "s"} — below the minimum; {nWithEvent} of {nWells} offset well{nWells === 1 ? "" : "s"} recorded this problem here.</div>
        </>
      )}
      {children && <div className="mt-4">{children}</div>}
      {actions && <div className="mt-4 flex gap-2 flex-wrap">{actions}</div>}
    </section>
  );
}
