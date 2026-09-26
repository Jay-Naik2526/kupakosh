"use client";
import { ReactNode, useEffect } from "react";
import { useApp } from "@/lib/state";
import { t } from "@/lib/i18n";
/** Right-side slide-over for details (keeps screens to ≤3 zones). */
export function Drawer({ open, onClose, title, children, width = 480 }: { open: boolean; onClose: () => void; title: ReactNode; children: ReactNode; width?: number }) {
  const { lang } = useApp();
  useEffect(() => {
    const k = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", k); return () => window.removeEventListener("keydown", k);
  }, [onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-40" role="dialog" aria-modal="true" aria-label={typeof title === "string" ? title : "details"}>
      <div className="absolute inset-0" style={{ background: "rgba(27,26,23,.25)" }} onClick={onClose} />
      <aside className="absolute right-0 top-0 h-full bg-paper border-l border-ink overflow-y-auto p-6" style={{ width: `min(${width}px, 100vw)` }}>
        <div className="flex items-start justify-between gap-4 rule-b pb-2 mb-4">
          <div className="font-semibold">{title}</div>
          <button className="btn" onClick={onClose} aria-label="Close">{t("close", lang)}</button>
        </div>
        {children}
      </aside>
    </div>
  );
}
