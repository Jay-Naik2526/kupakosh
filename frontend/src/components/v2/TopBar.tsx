"use client";
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { Menu, Sun, Moon, ChevronDown } from "lucide-react";
import { useApp } from "@/lib/state";
import { t } from "@/lib/i18n";
import { get } from "@/lib/api";
import { WellPicker } from "@/components/kk/WellPicker";
import { CountryFilter } from "@/components/kk/CountryFilter";
import { findNavItem } from "./Sidebar";

/** Top bar: route title, active-well combobox, country popover, Ctrl+K hint, EN/हिं, theme, text size, contrast, demo user. */
export function TopBar({ onOpenMobileNav }: { onOpenMobileNav: () => void }) {
  const path = usePathname();
  const item = findNavItem(path);
  const { lang, setLang, scale, setScale, contrast, setContrast, theme, setTheme, user, setUser } = useApp();
  const [users, setUsers] = useState<{ name: string; role: string }[]>([]);
  const [showCountry, setShowCountry] = useState(false);
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
          <button className="chip inline-flex items-center gap-1" aria-expanded={showCountry} onClick={() => setShowCountry((s) => !s)}>
            {t("countryLabel", lang)} <ChevronDown size={13} />
          </button>
          {showCountry && (
            <div className="kk-popover">
              <CountryFilter />
            </div>
          )}
        </div>
        <span className="label kk-hide-mobile" title="Open the command palette">
          Ctrl+K
        </span>
        <button className="chip" aria-pressed={lang === "hi"} onClick={() => setLang(lang === "en" ? "hi" : "en")} aria-label="Toggle language">
          EN / हिं
        </button>
        <button className="chip" onClick={() => setTheme(theme === "dark" ? "light" : "dark")} aria-label="Toggle theme" aria-pressed={theme === "dark"}>
          {theme === "dark" ? <Sun size={14} /> : <Moon size={14} />}
        </button>
        <span className="inline-flex kk-hide-mobile" role="group" aria-label="Text size">
          <button className="chip" onClick={() => setScale(Math.max(13, scale - 1))} aria-label="Smaller text">
            A-
          </button>
          <button className="chip" onClick={() => setScale(15)} aria-label="Default text size">
            A
          </button>
          <button className="chip" onClick={() => setScale(Math.min(19, scale + 1))} aria-label="Larger text">
            A+
          </button>
        </span>
        <button className="chip kk-hide-mobile" aria-pressed={contrast} onClick={() => setContrast(!contrast)}>
          {t("contrastBtn", lang)}
        </button>
        <select
          className="chip kk-hide-mobile"
          aria-label="Demo user"
          value={user?.name ?? ""}
          onChange={(e) => setUser(users.find((u) => u.name === e.target.value) ?? null)}
        >
          <option value="">{t("guestReadOnly", lang)}</option>
          {users.map((u) => (
            <option key={u.name} value={u.name}>
              {u.name} — {u.role} ({t("demoUserSuffix", lang)})
            </option>
          ))}
        </select>
      </div>
    </header>
  );
}
