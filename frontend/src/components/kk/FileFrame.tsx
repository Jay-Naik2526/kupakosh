"use client";
import { ReactNode, useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { useApp } from "@/lib/state";
import { t, TABS } from "@/lib/i18n";
import Link from "next/link";
import { get } from "@/lib/api";
import { IndexTabs, activeTab } from "./IndexTabs";
import { CommandPalette } from "./CommandPalette";
import { SourceSlip } from "./SourceFootnote";
import { LithologyPatterns } from "./LithologyPatterns";
import { Wordmark } from "./Wordmark";

const FILE_NO: Record<string, string> = { "01": "DRL", "02": "OFS", "03": "WIKI", "04": "FIX", "05": "MUD", "06": "CHK", "07": "CPL", "08": "PDB", "09": "ACC" };

/** Desk + khaki file board + file number + paper sheet + tricolour hairline + footer (§11.4). */
export function FileFrame({ children }: { children: ReactNode }) {
  const path = usePathname();
  const tab = activeTab(path);
  const { lang, setLang, scale, setScale, contrast, setContrast, user, setUser } = useApp();
  const [users, setUsers] = useState<{ name: string; role: string }[]>([]);
  useEffect(() => { get("/api/config").then((c) => setUsers(c.demo_users)).catch(() => {}); }, []);
  const fileNo = `KPK/${FILE_NO[tab.no]}/2026/${tab.no.padStart(4, "0")}`;
  if (path.startsWith("/dev")) return <>{children}<LithologyPatterns /><SourceSlip /></>;
  return (
    <div className="min-h-screen p-3 md:p-6" style={{ background: "var(--desk)" }}>
      <LithologyPatterns />
      <div className="rounded-kk p-3 md:p-6" style={{ background: "var(--file-board)" }}>
        <div className="typewriter text-[13px] md:text-[14px] mb-3 text-ink flex flex-wrap gap-x-3">
          <span>FILE No. {fileNo}</span><span>·</span><span>{t("board", lang)}</span>
          <span className="ml-auto label hidden md:inline" style={{ color: "var(--ink)" }}>{lang === "hi" ? "Ctrl+K — खोजें / जाएँ" : "Ctrl+K — search / jump"}</span>
        </div>
        <div className="flex items-start">
          <main className="flex-1 min-w-0 bg-paper rounded-kk relative" style={{ minHeight: "calc(100vh - 120px)" }}>
            <div style={{ height: 2, background: "linear-gradient(90deg,#FF9933 33.3%,#FFFFFF 33.3% 66.6%,#138808 66.6%)" }} aria-hidden="true" />
            <header className="flex flex-wrap items-center gap-3 px-4 md:px-8 py-3 rule-b">
              <Wordmark />
              <div>
                <h1 className="h-title leading-tight">{lang === "hi" ? tab.hi : tab.en} <span className="text-ink2 text-base font-normal deva">{lang === "hi" ? tab.en : tab.hi}</span></h1>
                <div className={lang === "hi" ? "label deva" : "label"}>{lang === "hi" ? tab.qhi : tab.q}</div>
              </div>
              <div className="ml-auto flex items-center gap-2 flex-wrap small">
                <button className="chip" aria-pressed={lang === "hi"} onClick={() => setLang(lang === "en" ? "hi" : "en")} aria-label="Toggle language">EN / हिं</button>
                <span className="inline-flex" role="group" aria-label="Text size">
                  <button className="chip" onClick={() => setScale(Math.max(13, scale - 1))} aria-label="Smaller text">A-</button>
                  <button className="chip" onClick={() => setScale(15)} aria-label="Default text size">A</button>
                  <button className="chip" onClick={() => setScale(Math.min(19, scale + 1))} aria-label="Larger text">A+</button>
                </span>
                <button className="chip" aria-pressed={contrast} onClick={() => setContrast(!contrast)}>{t("contrastBtn", lang)}</button>
                <select className="chip" aria-label="Demo user" value={user?.name ?? ""} onChange={(e) => setUser(users.find((u) => u.name === e.target.value) ?? null)}>
                  <option value="">{t("guestReadOnly", lang)}</option>
                  {users.map((u) => <option key={u.name} value={u.name}>{u.name} — {u.role} ({t("demoUserSuffix", lang)})</option>)}
                </select>
              </div>
            </header>
            <div className="px-4 md:px-8 py-6 overflow-x-auto">{children}</div>
            <footer className="px-4 md:px-8 py-3 rule-t label">{t("footer", lang)}</footer>
          </main>
          <IndexTabs />
        </div>
      </div>
      <nav className="md:hidden mt-3 flex flex-wrap gap-1" aria-label="Sections (mobile)">
        {TABS.map((x) => <Link key={x.href} href={x.href} className="chip" aria-current={x.href === tab.href ? "page" : undefined}
          style={{ background: x.href === tab.href ? "var(--paper)" : "var(--file-board)" }}>{x.no} {lang === "hi" ? x.hi : x.en}</Link>)}
      </nav>
      <CommandPalette />
      <SourceSlip />
    </div>
  );
}
