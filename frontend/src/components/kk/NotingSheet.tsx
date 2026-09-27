import { useApp } from "@/lib/state";

export type Note = { para_no: number; author: string; role: string; note: string; action: string; created_at: string | null; git_commit?: string | null };
/** Numbered noting entries (government-file "noting" paras) shown as a clean vertical timeline. */
export function NotingSheet({ notes }: { notes: Note[] }) {
  const { lang } = useApp();
  if (notes.length === 0) return <p className="label">{lang === "hi" ? "अभी तक कोई टिप्पणी नहीं।" : "No noting yet."}</p>;
  return (
    <ol className="relative">
      {notes.map((n, i) => (
        <li key={n.para_no} className="relative pl-8 pb-4 last:pb-0">
          {i < notes.length - 1 && <span className="absolute left-[10px] top-6 bottom-0 w-px bg-[var(--border)]" aria-hidden="true" />}
          <span className="absolute left-0 top-0 flex h-5 w-5 items-center justify-center rounded-full bg-[var(--surface-2)] border border-[var(--border)] num text-[0.68rem] font-bold text-[var(--text-2)]">
            {n.para_no}
          </span>
          <div className="small">{n.note}</div>
          <div className="label mt-0.5">
            {n.author} · {n.role}
            {n.created_at ? ` · ${n.created_at.slice(0, 16).replace("T", " ")}` : ""}
            {n.git_commit ? <> · <span className="mono">{n.git_commit.slice(0, 8)}</span></> : null}
          </div>
        </li>
      ))}
    </ol>
  );
}
