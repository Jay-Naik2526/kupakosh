type Kind = "approved" | "replay" | "returned" | "draft" | "review";
const GLYPH: Record<Kind, string> = { approved: "✓", replay: "▶", returned: "↩", draft: "✎", review: "◔" };
const TEXT_COLOR: Record<Kind, string> = {
  approved: "var(--ok)", replay: "var(--caution-ink)", returned: "var(--hazard)", draft: "var(--text-2)", review: "var(--text-2)",
};
const TINT: Record<Kind, string> = {
  approved: "color-mix(in srgb, var(--ok) 12%, var(--surface))",
  replay: "color-mix(in srgb, var(--caution) 16%, var(--surface))",
  returned: "color-mix(in srgb, var(--hazard) 12%, var(--surface))",
  draft: "var(--surface-2)",
  review: "var(--surface-2)",
};
const BORDER: Record<Kind, string> = {
  approved: "color-mix(in srgb, var(--ok) 40%, transparent)",
  replay: "color-mix(in srgb, var(--caution) 45%, transparent)",
  returned: "color-mix(in srgb, var(--hazard) 40%, transparent)",
  draft: "var(--border)",
  review: "var(--border)",
};
/** Clean status badge (Approved / Replay / Returned / Draft / In review). Text is always spelled out, never colour alone. */
export function Stamp({ kind, text, sub, round = false }: { kind: Kind; text: string; sub?: string; round?: boolean }) {
  return (
    <span
      className="inline-flex items-center gap-2 px-3 py-1.5 font-semibold select-none"
      style={{ color: TEXT_COLOR[kind], background: TINT[kind], border: `1px solid ${BORDER[kind]}`, borderRadius: round ? 999 : "var(--radius-lg)" }}
      aria-label={`${text}${sub ? " " + sub : ""}`}
    >
      <span aria-hidden="true" className="text-[0.9rem] leading-none">{GLYPH[kind]}</span>
      <span className="flex flex-col leading-tight">
        <span className="text-[0.82rem] tracking-wide">{text}</span>
        {sub && <span className="text-[0.7rem] font-normal text-[var(--text-2)]">{sub}</span>}
      </span>
    </span>
  );
}
