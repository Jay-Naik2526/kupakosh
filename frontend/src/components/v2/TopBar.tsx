"use client";
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { Menu, Sun, Moon, ChevronDown, Settings2, User } from "lucide-react";
import { useApp } from "@/lib/state";
import { t } from "@/lib/i18n";
import { get } from "@/lib/api";
import { WellPicker } from "@/components/kk/WellPicker";
import { CountryFilter } from "@/components/kk/CountryFilter";
import { findNavItem } from "./Sidebar";

const tr = (lang: string, en: string, hi: string) => (lang === "hi" ? hi : en);

/** Top bar: route title, active-well combobox, country popover, Ctrl+K, EN/हिं, theme, Display settings, demo user. */
export function TopBar({ onOpenMobileNav }: { onOpenMobileNav: () => void }) {
  const path = usePathname();
  const item = findNavItem(path);
  const { lang, setLang, scale, setScale, contrast, setContrast, theme, setTheme, user, setUser } = useApp();
  const [users, setUsers] = useState<{ name: string; role: string }[]>([]);
  const [showCountry, setShowCountry] = useState(false);
  const [showDisplay, setShowDisplay] = useState(false);
  const [showUser, setShowUser] = useState(false);
  useEffect(() => {
    get("/api/config").then((c) => setUsers(c.demo_users)).catch(() => {});
  }, []);

  return (
    <header className="kk-topbar">
      <button className="kk-hamburger" onClick={onOpenMobileNav} aria-label="Open navigation">
        <Menu size={20} />
      </button>
      <div className="kk-topbar-title">
        <h1 className="h-title leading-tight">
          {t(item.key, lang)} <span className="deva label">{lang === "hi" ? t(item.key, "en") : t(item.key, "hi")}</span>
        </h1>
      </div>
      <div className="kk-topbar-tools">
        <WellPicker label={t("activeWell", lang)} />

        <div className="kk-country-pop">
          <button className="chip inline-flex items-center gap-1" aria-expanded={showCountry} onClick={() => { setShowCountry((s) => !s); setShowDisplay(false); setShowUser(false); }}>
            {t("countryLabel", lang)} <ChevronDown size={13} />
          </button>
          {showCountry && (
            <div className="kk-popover">
              <CountryFilter />
            </div>
          )}
        </div>

        <button className="chip kk-hide-mobile" title="Open the command palette (Ctrl+K)" onClick={() => window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", ctrlKey: true }))}>
          <span className="mono">Ctrl+K</span>
        </button>

        <button className="chip" aria-pressed={lang === "hi"} onClick={() => setLang(lang === "en" ? "hi" : "en")} aria-label="Toggle language">
          EN / हिं
        </button>

        <button className="chip" onClick={() => setTheme(theme === "dark" ? "light" : "dark")} aria-label="Toggle theme" aria-pressed={theme === "dark"}>
          {theme === "dark" ? <Sun size={14} /> : <Moon size={14} />}
        </button>

        <div className="kk-display-pop">
          <button className="chip inline-flex items-center gap-1" aria-expanded={showDisplay} aria-label="Display settings"
            onClick={() => { setShowDisplay((s) => !s); setShowCountry(false); setShowUser(false); }}>
            <Settings2 size={14} />
          </button>
          {showDisplay && (
            <div className="kk-popover kk-display-pop-panel">
              <div className="kk-display-pop-row">
                <span className="label">{tr(lang, "Text size", "पाठ आकार")}</span>
                <span className="inline-flex" role="group" aria-label="Text size">
                  <button className="chip" onClick={() => setScale(Math.max(13, scale - 1))} aria-label="Smaller text">A-</button>
                  <button className="chip" onClick={() => setScale(15)} aria-label="Default text size">A</button>
                  <button className="chip" onClick={() => setScale(Math.min(19, scale + 1))} aria-label="Larger text">A+</button>
                </span>
              </div>
              <div className="kk-display-pop-row">
                <span className="label">{t("contrastBtn", lang)}</span>
                <button className="chip" aria-pressed={contrast} onClick={() => setContrast(!contrast)}>
                  {contrast ? "On" : "Off"}
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="kk-country-pop">
          <button className="chip inline-flex items-center gap-1" aria-expanded={showUser} aria-label="Demo user menu"
            onClick={() => { setShowUser((s) => !s); setShowCountry(false); setShowDisplay(false); }}>
            <User size={14} />
            <span className="kk-hide-mobile">{user ? user.name : t("guestReadOnly", lang)}</span>
            <ChevronDown size={12} />
          </button>
          {showUser && (
            <div className="kk-popover" style={{ minWidth: 240 }}>
              <div className="flex flex-col gap-1">
                <button className="kk-nav-item" style={{ justifyContent: "flex-start" }} onClick={() => { setUser(null); setShowUser(false); }}>
                  {t("guestReadOnly", lang)}
                </button>
                {users.map((u) => (
                  <button key={u.name} className="kk-nav-item" style={{ justifyContent: "flex-start" }}
                    onClick={() => { setUser(u); setShowUser(false); }} aria-pressed={user?.name === u.name}>
                    <span>{u.name}</span>
                    <span className="label ml-2">— {u.role} ({t("demoUserSuffix", lang)})</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
