export const m = (x?: number | null, d = 0) => (x === null || x === undefined ? "unknown" : `${x.toLocaleString("en-IN", { maximumFractionDigits: d, minimumFractionDigits: d })} m`);
export const num = (x?: number | null, d = 0) => (x === null || x === undefined ? "unknown" : x.toLocaleString("en-IN", { maximumFractionDigits: d, minimumFractionDigits: d }));
export const pct = (x?: number | null) => {
  if (x === null || x === undefined) return "unknown";
  const v = x * 100;
  if (v > 0 && v < 1) return "<1%";
  return `${Math.round(v)}%`;
};
export const ppg = (x?: number | null) => (x === null || x === undefined ? "—" : `${x.toFixed(2)}`);
export const pretty = (f?: string | null) =>
  !f ? "unknown" : f.split(/\s+/).map((w) => (/^[IVX]+$/.test(w) ? w : w.charAt(0) + w.slice(1).toLowerCase())).join(" ");
export const hazardLabel: Record<string, string> = {
  lost_circulation: "Lost circulation", kick: "Kick / influx", stuck_pipe: "Stuck pipe", torque_spike: "Torque spike",
  overpressure: "Overpressure / gas", cementing_issue: "Cementing issue", fishing: "Fishing / junk", wellbore_instability: "Wellbore instability",
};
export const glyph: Record<string, string> = {
  lost_circulation: "▲", kick: "◆", stuck_pipe: "■", cementing_issue: "○", overpressure: "△", fishing: "✕", torque_spike: "≋", wellbore_instability: "▽",
};
export const actionLabel: Record<string, string> = {
  lcm_pill: "LCM / pill", reduce_mw: "Reduce mud weight", increase_mw: "Increase mud weight", reduce_flow: "Reduce flow rate",
  circulate_condition: "Circulate & condition", ream_backream: "Ream / back-ream", jar: "Jar", spot_pill: "Spot pill (pipe-lax, diesel)",
  pump_out: "Pump out of hole", cement_plug: "Cement plug", squeeze: "Cement squeeze", shut_in_kill: "Shut in & kill",
  pooh: "Pull out of hole", sidetrack: "Sidetrack", change_bha: "Change BHA / bit", fishing_run: "Fishing run", cut_and_abandon: "Cut / back off string",
};
