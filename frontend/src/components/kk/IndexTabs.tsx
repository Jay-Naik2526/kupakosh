"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { TABS } from "@/lib/i18n";
import { useApp } from "@/lib/state";

const TINT = ["var(--tab-1)", "var(--tab-2)", "var(--tab-3)", "var(--tab-4)"];

export function activeTab(path: string) {
  return TABS.find((t) => (t.href === "/" ? path === "/" : path.startsWith(t.href))) ?? TABS[0];
}

/** Binder index tabs sticking out of the right edge of the sheet (keyboard accessible). */
export function IndexTabs() {
  const path = usePathname();
  const { lang } = useApp();
  const cur = activeTab(path);
  return (
    <nav aria-label="Sections" className="hidden md:flex flex-col gap-1 pt-6">
      {TABS.map((t, i) => {
        const active = t.href === cur.href;
        return (
          <Link key={t.href} href={t.href} aria-current={active ? "page" : undefined}
            className="flex flex-col justify-center px-2 border border-l-0 border-ink/40"
            style={{ width: 56 + (active ? 8 : 0), height: 92, marginLeft: active ? -1 : 0, background: active ? "var(--paper)" : TINT[i % 4],
                     borderRadius: "0 var(--radius) var(--radius) 0", transform: active ? "none" : "translateX(0)", opacity: active ? 1 : 0.92 }}>
            <span className="num text-[12px] font-semibold">{t.no}</span>
            <span className="text-[11px] leading-tight font-medium" style={{ writingMode: "horizontal-tb" }}>{lang === "hi" ? t.hi : t.en}</span>
            <span className="text-[10px] leading-tight text-ink2 deva">{lang === "hi" ? t.en : t.hi}</span>
          </Link>
        );
      })}
    </nav>
  );
}
