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
export const hazardLabelHi: Record<string, string> = {
  lost_circulation: "मड लॉस (lost circulation)", kick: "किक / इनफ्लक्स (kick)", stuck_pipe: "स्टक पाइप (stuck pipe)", torque_spike: "टॉर्क स्पाइक (torque spike)",
  overpressure: "ओवरप्रेशर / गैस (overpressure)", cementing_issue: "सीमेंटिंग समस्या (cementing issue)", fishing: "फिशिंग / जंक (fishing)", wellbore_instability: "कूप-भित्ति अस्थिरता (wellbore instability)",
};
/** Bilingual hazard label: Hindi (with the English term kept in brackets) when lang is "hi", else English. */
export const hazardText = (key: string, lang: "en" | "hi") => (lang === "hi" ? hazardLabelHi[key] ?? hazardLabel[key] ?? key : hazardLabel[key] ?? key);
export const glyph: Record<string, string> = {
  lost_circulation: "▲", kick: "◆", stuck_pipe: "■", cementing_issue: "○", overpressure: "△", fishing: "✕", torque_spike: "≋", wellbore_instability: "▽",
};
export const actionLabel: Record<string, string> = {
  lcm_pill: "LCM / pill", reduce_mw: "Reduce mud weight", increase_mw: "Increase mud weight", reduce_flow: "Reduce flow rate",
  circulate_condition: "Circulate & condition", ream_backream: "Ream / back-ream", jar: "Jar", spot_pill: "Spot pill (pipe-lax, diesel)",
  pump_out: "Pump out of hole", cement_plug: "Cement plug", squeeze: "Cement squeeze", shut_in_kill: "Shut in & kill",
  pooh: "Pull out of hole", sidetrack: "Sidetrack", change_bha: "Change BHA / bit", fishing_run: "Fishing run", cut_and_abandon: "Cut / back off string",
};
export const actionLabelHi: Record<string, string> = {
  lcm_pill: "एलसीएम / पिल (LCM / pill)", reduce_mw: "मड भार घटाएँ (reduce mud weight)", increase_mw: "मड भार बढ़ाएँ (increase mud weight)", reduce_flow: "प्रवाह दर घटाएँ (reduce flow rate)",
  circulate_condition: "परिसंचरण व कंडीशनिंग (circulate & condition)", ream_backream: "रीम / बैक-रीम (ream / back-ream)", jar: "जार (jar)", spot_pill: "स्पॉट पिल (spot pill)",
  pump_out: "होल से पंप आउट (pump out of hole)", cement_plug: "सीमेंट प्लग (cement plug)", squeeze: "सीमेंट स्क्वीज़ (cement squeeze)", shut_in_kill: "शट-इन व किल (shut in & kill)",
  pooh: "होल से बाहर निकालें (pull out of hole)", sidetrack: "साइडट्रैक (sidetrack)", change_bha: "बीएचए / बिट बदलें (change BHA / bit)", fishing_run: "फिशिंग रन (fishing run)", cut_and_abandon: "स्ट्रिंग काटें (cut / back off string)",
};
/** Bilingual action label: Hindi (with the English term kept in brackets) when lang is "hi", else English. */
export const actionText = (key: string, lang: "en" | "hi") => (lang === "hi" ? actionLabelHi[key] ?? actionLabel[key] ?? key : actionLabel[key] ?? key);
