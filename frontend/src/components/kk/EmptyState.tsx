export function EmptyState({ title, why, children }: { title: string; why: string; children?: React.ReactNode }) {
  return (
    <div className="border border-dashed border-[var(--border)] rounded-[var(--radius-lg)] p-7 bg-[var(--surface)] text-center" role="status">
      <div aria-hidden="true" className="text-xl text-[var(--text-2)] mb-1">○</div>
      <div className="font-semibold">{title}</div>
      <p className="text-[var(--text-2)] mt-1 max-w-[60ch] mx-auto">{why}</p>
      {children}
    </div>
  );
}
