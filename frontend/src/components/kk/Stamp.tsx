type Kind = "approved" | "replay" | "returned" | "draft" | "review";
const GLYPH: Record<Kind, string> = { approved: "✓", replay: "▶", returned: "↩", draft: "✎", review: "◔" };
// Slate for draft/review keeps them visibly distinct from the approve/replay/return hues without implying a hazard state.
const SLATE = "#475569";
// var(--ok) itself is only ~3.3:1 on white (fine for a solid fill, not for small text) — this darker green keeps the same hue family but clears AA as text.
const OK_TEXT = "#166534";
const TEXT_COLOR: Record<Kind, string> = {
  approved: OK_TEXT, replay: "var(--caution-ink)", returned: "var(--hazard)", draft: SLATE, review: SLATE,
};
const TINT: Record<Kind, string> = {
  approved: "color-mix(in srgb, var(--ok) 16%, var(--surface))",
  replay: "color-mix(in srgb, var(--caution) 20%, var(--surface))",
  returned: "color-mix(in srgb, var(--hazard) 16%, var(--surface))",
  draft: `color-mix(in srgb, ${SLATE} 12%, var(--surface))`,
  review: `color-mix(in srgb, ${SLATE} 12%, var(--surface))`,
};
const BORDER: Record<Kind, string> = {
  approved: "color-mix(in srgb, var(--ok) 45%, transparent)",
  replay: "color-mix(in srgb, var(--caution) 50%, transparent)",
  returned: "color-mix(in srgb, var(--hazard) 45%, transparent)",
  draft: `color-mix(in srgb, ${SLATE} 40%, transparent)`,
  review: `color-mix(in srgb, ${SLATE} 40%, transparent)`,
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
