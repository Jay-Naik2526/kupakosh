export function EmptyState({ title, why, children }: { title: string; why: string; children?: React.ReactNode }) {
  return (
    <div className="border border-dashed border-rule rounded-kk p-6 bg-card" role="status">
      <div className="font-semibold">{title}</div>
      <p className="text-ink2 mt-1 max-w-prose">{why}</p>
      {children}
    </div>
  );
}
