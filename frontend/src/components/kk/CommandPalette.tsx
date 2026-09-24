"use client";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { TABS } from "@/lib/i18n";
import { get } from "@/lib/api";
import { useApp } from "@/lib/state";

/** Ctrl+K: jump to a screen, a well, or a wiki page. */
export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [wells, setWells] = useState<any[]>([]);
  const [pages, setPages] = useState<any[]>([]);
  const [i, setI] = useState(0);
  const router = useRouter();
  const { setWellId } = useApp();
  useEffect(() => {
    const k = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setOpen((o) => !o); setQ(""); }
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", k); return () => window.removeEventListener("keydown", k);
  }, []);
  useEffect(() => {
    if (!open || q.length < 2) { setWells([]); setPages([]); return; }
    const h = setTimeout(() => {
      get("/api/wells", { q, limit: 6 }).then(setWells).catch(() => {});
      get("/api/wiki", { q }).then((p) => setPages(p.slice(0, 6))).catch(() => {});
    }, 150);
    return () => clearTimeout(h);
  }, [q, open]);
  const items = useMemo(() => [
    ...TABS.filter((t) => !q || (t.en + t.hi).toLowerCase().includes(q.toLowerCase())).map((t) => ({ label: `${t.no} ${t.en} / ${t.hi}`, hint: t.q, go: () => router.push(t.href) })),
    ...wells.map((w) => ({ label: `Well ${w.name}`, hint: `${w.field ?? ""} · ${w.documented ? "has reports" : "no reports"}`, go: () => { setWellId(w.id); router.push("/offsets"); } })),
    ...pages.map((p) => ({ label: `Wiki: ${p.title}`, hint: `${p.ref_no} · ${p.status}`, go: () => router.push(`/wiki?page=${encodeURIComponent(p.slug)}`) })),
  ], [q, wells, pages, router, setWellId]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-24" style={{ background: "rgba(27,26,23,.3)" }} onClick={() => setOpen(false)}>
      <div className="bg-paper border border-ink rounded-kk w-[min(560px,92vw)]" onClick={(e) => e.stopPropagation()} role="dialog" aria-label="Command palette">
        <input autoFocus className="w-full bg-transparent px-4 py-3 rule-b outline-none" placeholder="Jump to screen, well or wiki page…"
          value={q} onChange={(e) => { setQ(e.target.value); setI(0); }}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") setI((x) => Math.min(x + 1, items.length - 1));
            if (e.key === "ArrowUp") setI((x) => Math.max(x - 1, 0));
            if (e.key === "Enter" && items[i]) { items[i].go(); setOpen(false); }
          }} />
        <ul className="max-h-80 overflow-y-auto">
          {items.map((it, k) => (
            <li key={k}><button className="w-full text-left px-4 py-2 rule-b" style={k === i ? { background: "var(--card)" } : undefined} onClick={() => { it.go(); setOpen(false); }}>
              <div>{it.label}</div><div className="label">{it.hint}</div></button></li>
          ))}
        </ul>
      </div>
    </div>
  );
}
