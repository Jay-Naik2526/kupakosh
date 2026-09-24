type Kind = "approved" | "replay" | "returned" | "draft" | "review";
const C: Record<Kind, string> = { approved: "var(--ok)", replay: "var(--caution)", returned: "var(--hazard)", draft: "var(--ink-2)", review: "var(--ink-2)" };
/** Flat rubber-stamp mark. Text always spelled out (never colour alone). */
export function Stamp({ kind, text, sub, round = false }: { kind: Kind; text: string; sub?: string; round?: boolean }) {
  return (
    <span className="typewriter inline-flex flex-col items-center justify-center select-none"
      style={{ color: C[kind], border: `2px solid ${C[kind]}`, borderRadius: round ? "50%" : "var(--radius)", padding: round ? "10px 8px" : "2px 8px",
               transform: "rotate(-4deg)", letterSpacing: "0.08em", fontWeight: 700, lineHeight: 1.1, minWidth: round ? 84 : undefined }}
      aria-label={`${text}${sub ? " " + sub : ""}`}>
      <span style={{ fontSize: "0.95rem" }}>{text}</span>
      {sub && <span style={{ fontSize: "0.72rem", fontWeight: 400 }}>{sub}</span>}
    </span>
  );
}
