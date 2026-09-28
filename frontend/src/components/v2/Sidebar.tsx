"use client";
import type React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Home, Radio, History, Map as MapIcon, Box, Globe2, GitCompare, BookOpen, Wrench, Gauge, ShieldCheck, MessageSquare, FileText,
  PanelLeftClose, PanelLeftOpen, X,
} from "lucide-react";
import { useApp } from "@/lib/state";
import { t } from "@/lib/i18n";
import { Wordmark } from "@/components/kk/Wordmark";

/** Sidebar nav model (docs/PLAN_V2.md "Design system v2" shell groups). Shared with TopBar for the route title. */
/** Each nav group gets its earth colour as a small legend square (tokens.css --sec-*), like a survey-map key. */
const GROUP_COLOR: Record<string, string> = {
  navGroupOperate: "var(--sec-operate)", navGroupExplore: "var(--sec-explore)", navGroupKnowledge: "var(--sec-knowledge)",
  navGroupAsk: "var(--sec-ask)", navGroupDeliver: "var(--sec-deliver)", navGroupTrust: "var(--sec-trust)",
};

export const NAV_GROUPS = [
  {
    groupKey: "navGroupOperate" as const,
    items: [
      { href: "/", key: "navHome" as const, icon: Home },
      { href: "/command", key: "navWellRoom" as const, icon: Radio },
      { href: "/hindsight", key: "navHindsight" as const, icon: History },
    ],
  },
  {
    groupKey: "navGroupExplore" as const,
    items: [
      { href: "/map", key: "navMap" as const, icon: MapIcon },
      { href: "/subsurface", key: "navSubsurface" as const, icon: Box },
      { href: "/analogs", key: "navAnalogs" as const, icon: Globe2 },
      { href: "/offsets", key: "navOffsets" as const, icon: GitCompare },
    ],
  },
  {
    groupKey: "navGroupKnowledge" as const,
    items: [
      { href: "/wiki", key: "navWiki" as const, icon: BookOpen },
      { href: "/fixes", key: "navFixes" as const, icon: Wrench },
      { href: "/mudwindow", key: "navMudWindow" as const, icon: Gauge },
      { href: "/checker", key: "navChecker" as const, icon: ShieldCheck },
    ],
  },
  { groupKey: "navGroupAsk" as const, items: [{ href: "/copilot", key: "navCopilot" as const, icon: MessageSquare }] },
  { groupKey: "navGroupDeliver" as const, items: [{ href: "/brief", key: "navBrief" as const, icon: FileText }] },
  { groupKey: "navGroupTrust" as const, items: [{ href: "/accuracy", key: "navAccuracy" as const, icon: ShieldCheck }] },
];

export type NavItem = (typeof NAV_GROUPS)[number]["items"][number];

function isActive(href: string, path: string) {
  return href === "/" ? path === "/" : path.startsWith(href);
}

/** The route the TopBar should title itself after (falls back to Home). */
export function findNavItem(path: string): NavItem {
  for (const g of NAV_GROUPS) for (const it of g.items) if (isActive(it.href, path)) return it;
  return NAV_GROUPS[0].items[0];
}

export function Sidebar({
  collapsed,
  onToggleCollapsed,
  mobileOpen,
  onCloseMobile,
}: {
  collapsed: boolean;
  onToggleCollapsed: () => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
}) {
  const path = usePathname();
  const { lang } = useApp();
  return (
    <nav
      className="kk-sidebar"
      data-collapsed={collapsed ? "1" : "0"}
      data-mobile-open={mobileOpen ? "1" : "0"}
      aria-label="Main navigation"
    >
      <div className="kk-sidebar-head">
        <Link href="/" className="kk-sidebar-brand" onClick={onCloseMobile}>
          <Wordmark size={24} />
          {!collapsed && (
            <span className="kk-sidebar-brand-text">
              <span>Kupakosh</span>
              <span className="deva label">कूपकोश</span>
            </span>
          )}
        </Link>
        <button className="kk-sidebar-close" onClick={onCloseMobile} aria-label="Close navigation">
          <X size={18} />
        </button>
      </div>
      <div className="kk-sidebar-scroll">
        {NAV_GROUPS.map((g) => {
          return (
            <div className="kk-nav-group" key={g.groupKey} style={{ ["--nav-color" as string]: GROUP_COLOR[g.groupKey] } as React.CSSProperties}>
              {!collapsed && <div className="kk-nav-group-label">{t(g.groupKey, lang)}</div>}
              {g.items.map((it) => {
                const active = isActive(it.href, path);
                const Icon = it.icon;
                return (
                  <Link
                    key={it.href}
                    href={it.href}
                    onClick={onCloseMobile}
                    aria-current={active ? "page" : undefined}
                    className="kk-nav-item"
                    data-active={active ? "1" : "0"}
                    title={t(it.key, lang)}
                  >
                    <span className="kk-nav-icon-chip">
                      <Icon size={15} aria-hidden="true" />
                    </span>
                    {!collapsed && <span>{t(it.key, lang)}</span>}
                  </Link>
                );
              })}
            </div>
          );
        })}
      </div>
      <button
        className="kk-sidebar-collapse-btn"
        onClick={onToggleCollapsed}
        aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        aria-pressed={collapsed}
      >
        {collapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
        {!collapsed && <span className="label">Collapse</span>}
      </button>
    </nav>
  );
}
