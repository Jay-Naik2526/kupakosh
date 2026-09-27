"use client";
import { ReactNode, useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { useApp } from "@/lib/state";
import { t } from "@/lib/i18n";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { GuidedTour } from "./GuidedTour";
import { CommandPalette } from "@/components/kk/CommandPalette";
import { SourceSlip } from "@/components/kk/SourceFootnote";
import { LithologyPatterns } from "@/components/kk/LithologyPatterns";

function loadBool(k: string, d: boolean) {
  try {
    const v = localStorage.getItem(k);
    return v === null ? d : v === "1";
  } catch {
    return d;
  }
}
function saveBool(k: string, v: boolean) {
  try {
    localStorage.setItem(k, v ? "1" : "0");
  } catch {
    /* private mode */
  }
}

/**
 * v2 app shell (docs/PLAN_V2.md "Design system v2"): left sidebar + top bar, replacing the
 * §11 file-board/binder-tabs FileFrame. Every existing screen renders unchanged inside <main>.
 */
export function AppShell({ children }: { children: ReactNode }) {
  const path = usePathname();
  const { lang } = useApp();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setCollapsed(loadBool("kk.sidebarCollapsed", false));
    setReady(true);
  }, []);
  useEffect(() => {
    if (ready) saveBool("kk.sidebarCollapsed", collapsed);
  }, [ready, collapsed]);
  useEffect(() => {
    setMobileOpen(false);
  }, [path]);

  // /dev/components is a bare component gallery, not a product screen — keep it outside the shell.
  if (path.startsWith("/dev")) {
    return (
      <>
        {children}
        <LithologyPatterns />
        <SourceSlip />
      </>
    );
  }

  return (
    <div className="kk-shell" data-collapsed={collapsed ? "1" : "0"}>
      <Sidebar collapsed={collapsed} onToggleCollapsed={() => setCollapsed((c) => !c)} mobileOpen={mobileOpen} onCloseMobile={() => setMobileOpen(false)} />
      {mobileOpen && <div className="kk-scrim" onClick={() => setMobileOpen(false)} aria-hidden="true" />}
      <div className="kk-shell-main">
        <TopBar onOpenMobileNav={() => setMobileOpen(true)} />
        <div
          style={{ height: 3, background: "linear-gradient(90deg,#FF9933 33.3%,#FFFFFF 33.3% 66.6%,#138808 66.6%)" }}
          aria-hidden="true"
        />
        <main className="kk-content">{children}</main>
        <footer className="kk-footer label">
          {t("board", lang)} · {t("footer", lang)}
        </footer>
      </div>
      <CommandPalette />
      <SourceSlip />
      <LithologyPatterns />
      <GuidedTour />
    </div>
  );
}
