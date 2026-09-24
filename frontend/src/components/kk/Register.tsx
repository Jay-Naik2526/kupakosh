import { ReactNode } from "react";
export type Col<T> = { key: string; head: ReactNode; cell: (r: T) => ReactNode; num?: boolean; width?: string };
/** Plain ruled government register: thin rules, mono numbers, no zebra stripes. */
export function Register<T>({ cols, rows, onRow, selected, empty, caption }: {
  cols: Col<T>[]; rows: T[]; onRow?: (r: T, i: number) => void; selected?: number | null; empty?: ReactNode; caption?: string;
}) {
  return (
    <table className="w-full border-collapse small">
      {caption && <caption className="text-left label pb-1">{caption}</caption>}
      <thead>
        <tr className="border-b-2 border-ink">
          {cols.map((c) => <th key={c.key} scope="col" style={{ width: c.width }} className={`py-1.5 px-2 font-semibold text-left ${c.num ? "text-right" : ""}`}>{c.head}</th>)}
        </tr>
      </thead>
      <tbody>
        {rows.length === 0 && <tr><td colSpan={cols.length} className="py-3 px-2 text-ink2">{empty ?? "No rows."}</td></tr>}
        {rows.map((r, i) => (
          <tr key={i} className={`rule-b align-top ${onRow ? "cursor-pointer hover:bg-card" : ""}`} style={selected === i ? { background: "var(--card)", outline: "1px solid var(--ink)" } : undefined}
              onClick={onRow ? () => onRow(r, i) : undefined} tabIndex={onRow ? 0 : undefined}
              onKeyDown={onRow ? (e) => { if (e.key === "Enter") onRow(r, i); } : undefined}>
            {cols.map((c) => <td key={c.key} className={`py-1.5 px-2 ${c.num ? "text-right num" : ""}`}>{c.cell(r)}</td>)}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
