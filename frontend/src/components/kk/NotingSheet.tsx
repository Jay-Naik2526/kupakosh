import { useApp } from "@/lib/state";

export type Note = { para_no: number; author: string; role: string; note: string; action: string; created_at: string | null; git_commit?: string | null };
/** Ruled paper with numbered noting paras (government file style). */
export function NotingSheet({ notes }: { notes: Note[] }) {
  const { lang } = useApp();
  return (
    <ol className="bg-card border border-rule rounded-kk" style={{ backgroundImage: "repeating-linear-gradient(transparent 0 27px, var(--grid) 27px 28px)" }}>
      {notes.length === 0 && <li className="p-3 text-ink2">{lang === "hi" ? "अभी तक कोई टिप्पणी नहीं।" : "No noting yet."}</li>}
      {notes.map((n) => (
        <li key={n.para_no} className="px-3 py-2 flex gap-3" style={{ minHeight: 56 }}>
          <span className="num font-semibold w-6 shrink-0">{n.para_no}.</span>
          <div className="flex-1">
            <div>{n.note}</div>
            <div className="label mt-0.5">— {n.author}, {n.role}{n.created_at ? ` · ${n.created_at.slice(0, 16).replace("T", " ")}` : ""}{n.git_commit ? <> · <span className="mono">{n.git_commit.slice(0, 8)}</span></> : null}</div>
          </div>
        </li>
      ))}
    </ol>
  );
}
