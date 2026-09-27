import { ReactNode } from "react";
export type Col<T> = { key: string; head: ReactNode; cell: (r: T) => ReactNode; num?: boolean; width?: string };
/** Clean table in a bordered, rounded card: subtle header shading, hover rows, mono numbers, no zebra stripes. */
export function Register<T>({ cols, rows, onRow, selected, empty, caption }: {
  cols: Col<T>[]; rows: T[]; onRow?: (r: T, i: number) => void; selected?: number | null; empty?: ReactNode; caption?: string;
}) {
  return (
    <div className="border border-[var(--border)] rounded-[var(--radius-lg)] overflow-hidden bg-[var(--surface)] shadow-[var(--shadow-sm)]">
      {caption && (
        <div className="label px-3.5 py-2 border-b border-[var(--border)]"
             style={{ background: "color-mix(in srgb, var(--brand-via, var(--accent)) 10%, var(--surface))" }}>{caption}</div>
      )}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse small">
          <thead>
            <tr>
              {cols.map((c) => (
                <th key={c.key} scope="col" style={{ width: c.width, background: "color-mix(in srgb, var(--brand-via, var(--accent)) 7%, var(--surface-2))" }}
                    className={`py-2.5 px-3.5 font-semibold text-[0.76rem] uppercase tracking-wide text-[var(--text-2)] border-b-2 border-[var(--border)] whitespace-nowrap ${c.num ? "text-right" : "text-left"}`}>
                  {c.head}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr><td colSpan={cols.length} className="py-5 px-3.5 text-[var(--text-2)]">{empty ?? "No rows."}</td></tr>
            )}
            {rows.map((r, i) => (
              <tr key={i}
                  className={`border-b border-[var(--border)] last:border-b-0 align-top transition-colors ${onRow ? "cursor-pointer hover:bg-[var(--surface-2)]" : ""}`}
                  style={selected === i ? { background: "color-mix(in srgb, var(--accent) 10%, var(--surface))" } : undefined}
                  onClick={onRow ? () => onRow(r, i) : undefined} tabIndex={onRow ? 0 : undefined}
                  onKeyDown={onRow ? (e) => { if (e.key === "Enter") onRow(r, i); } : undefined}>
                {cols.map((c) => <td key={c.key} className={`py-2.5 px-3.5 ${c.num ? "text-right num" : ""}`}>{c.cell(r)}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
