"use client";
import * as React from "react";
import { ReactNode } from "react";
import Link from "next/link";

/** Shared v2 primitives (docs/PLAN_V2.md "Design system v2"). Plain CSS classes in globals.css, themed via CSS vars. */

/** `accent`: a hex colour (see lib/palette.ts SECTION_COLOR) — top border + drives --card-color for any icon chip inside. */
export function Card({ children, className = "", as: As = "div", accent, style, ...props }: { children: ReactNode; className?: string; as?: any; accent?: string; style?: React.CSSProperties; [k: string]: any }) {
  return (
    <As className={`kk-card ${className}`} data-accent={accent ? "1" : undefined} style={accent ? { ["--card-color" as any]: accent, ...style } : style} {...props}>
      {children}
    </As>
  );
}

/** A card that is also a link (e.g. Home's three primary actions, "what makes it different" row). `accent` colours the hover border + any icon chip inside. */
export function LinkCard({ href, children, className = "", accent }: { href: string; children: ReactNode; className?: string; accent?: string }) {
  return (
    <Link href={href} className={`kk-card kk-card-link ${className}`} style={accent ? { ["--card-color" as any]: accent } : undefined}>
      {children}
    </Link>
  );
}

/** A small coloured icon badge, e.g. <IconChip icon={Radar} color={SECTION_COLOR.operate} /> — used on cards, tiles and page headers. */
export function IconChip({ icon: Icon, color, size = 18 }: { icon: any; color?: string; size?: number }) {
  return (
    <span className="kk-icon-chip" style={color ? { ["--card-color" as any]: color } : undefined} aria-hidden="true">
      <Icon size={size} />
    </span>
  );
}

/** Big number + label; optional source link (every KPI on Home traces back to /accuracy or a source). `color` gives the tile its own top-border accent. */
export function StatTile({ label, value, href, sub, color }: { label: string; value: ReactNode; href?: string; sub?: string; color?: string }) {
  const body = (
    <div className="kk-stat-tile" style={color ? { ["--card-color" as any]: color } : undefined}>
      <div className="kk-stat-value num">{value}</div>
      <div className="kk-stat-label">{label}</div>
      {sub && <div className="label mt-1">{sub}</div>}
    </div>
  );
  return href ? (
    <Link href={href} className="kk-stat-tile-link block">
      {body}
    </Link>
  ) : (
    body
  );
}

type BadgeKind = "replay" | "approved" | "hazard" | "caution" | "ok" | "info";
export function Badge({ kind = "info", children }: { kind?: BadgeKind; children: ReactNode }) {
  return <span className={`kk-badge kk-badge-${kind}`}>{children}</span>;
}

export function Button({
  variant = "default",
  className = "",
  as: As,
  href,
  children,
  ...props
}: {
  variant?: "default" | "primary";
  className?: string;
  as?: any;
  href?: string;
  children: ReactNode;
  [k: string]: any;
}) {
  const cls = `btn ${variant === "primary" ? "btn-primary" : ""} ${className}`;
  if (href) {
    return (
      <Link href={href} className={cls} {...props}>
        {children}
      </Link>
    );
  }
  const Comp = As ?? "button";
  return (
    <Comp className={cls} {...props}>
      {children}
    </Comp>
  );
}

export function Tabs({ items, active, onChange }: { items: { key: string; label: string }[]; active: string; onChange: (k: string) => void }) {
  return (
    <div className="kk-tabs" role="tablist">
      {items.map((it) => (
        <button
          key={it.key}
          role="tab"
          aria-selected={it.key === active}
          data-active={it.key === active ? "1" : "0"}
          className="kk-tab"
          onClick={() => onChange(it.key)}
        >
          {it.label}
        </button>
      ))}
    </div>
  );
}

export function PageHeader({ title, subtitle, actions, icon, color }: { title: ReactNode; subtitle?: ReactNode; actions?: ReactNode; icon?: any; color?: string }) {
  return (
    <div className="kk-page-header">
      {icon && <IconChip icon={icon} color={color} size={20} />}
      <div>
        <h1>{title}</h1>
        {subtitle && <div className="label mt-1">{subtitle}</div>}
      </div>
      {actions && <div className="ml-auto flex items-center gap-2 flex-wrap">{actions}</div>}
    </div>
  );
}
