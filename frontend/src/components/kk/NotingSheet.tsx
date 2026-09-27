import { useApp } from "@/lib/state";

export type Note = { para_no: number; author: string; role: string; note: string; action: string; created_at: string | null; git_commit?: string | null };

// One colour per noting action, so the timeline reads at a glance (compile = slate, approve = green, edit = blue, return = rose).
// Two variants: a vivid one for decoration (the dot's ring/fill) and a darker one that clears AA (4.5:1) as small text on a light tint.
const ACTION_COLOR: Record<string, string> = { compile: "#64748B", approve: "#10B981", edit: "#2563EB", return: "#E11D48" };
const ACTION_TEXT: Record<string, string> = { compile: "#475569", approve: "#166534", edit: "var(--info)", return: "var(--hazard)" };
const actionColor = (a: string) => ACTION_COLOR[a] ?? "#64748B";
const actionText = (a: string) => ACTION_TEXT[a] ?? "#475569";

/** Numbered noting entries (government-file "noting" paras) shown as a clean vertical timeline. */
export function NotingSheet({ notes }: { notes: Note[] }) {
  const { lang } = useApp();
  if (notes.length === 0) return <p className="label">{lang === "hi" ? "अभी तक कोई टिप्पणी नहीं।" : "No noting yet."}</p>;
  return (
    <ol className="relative">
      {notes.map((n, i) => {
        const c = actionColor(n.action);
        const tc = actionText(n.action);
        return (
          <li key={n.para_no} className="relative pl-8 pb-4 last:pb-0">
            {i < notes.length - 1 && <span className="absolute left-[10px] top-6 bottom-0 w-px bg-[var(--border)]" aria-hidden="true" />}
            <span className="absolute left-0 top-0 flex h-5 w-5 items-center justify-center rounded-full num text-[0.68rem] font-bold"
                  style={{ background: `color-mix(in srgb, ${c} 18%, var(--surface))`, border: `1.5px solid ${c}`, color: tc }}
                  title={n.action}>
              {n.para_no}
            </span>
            <div className="small">{n.note}</div>
            <div className="label mt-0.5">
              <span style={{ color: tc, fontWeight: 600 }}>{n.action}</span> · {n.author} · {n.role}
              {n.created_at ? ` · ${n.created_at.slice(0, 16).replace("T", " ")}` : ""}
              {n.git_commit ? <> · <span className="mono">{n.git_commit.slice(0, 8)}</span></> : null}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
