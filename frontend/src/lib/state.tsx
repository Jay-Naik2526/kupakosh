"use client";
import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import type { Lang } from "./i18n";

type User = { name: string; role: string };
type St = {
  lang: Lang; setLang: (l: Lang) => void;
  scale: number; setScale: (n: number) => void;
  contrast: boolean; setContrast: (b: boolean) => void;
  user: User | null; setUser: (u: User | null) => void;
  wellId: number | null; setWellId: (n: number | null) => void;
  country: string | null; setCountry: (c: string | null) => void;
  source: string | null; openSource: (ref: string | null) => void;
  ready: boolean;
};
const Ctx = createContext<St | null>(null);

function load<T>(k: string, d: T): T {
  try { const v = localStorage.getItem("kk." + k); return v === null ? d : JSON.parse(v); } catch { return d; }
}
function save(k: string, v: unknown) { try { localStorage.setItem("kk." + k, JSON.stringify(v)); } catch { /* private mode */ } }

export function AppState({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>("en");
  const [scale, setScale] = useState(15);
  const [contrast, setContrast] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [wellId, setWellId] = useState<number | null>(null);
  const [country, setCountry] = useState<string | null>(null);
  const [source, openSource] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    setLang(load("lang", "en")); setScale(load("scale", 15)); setContrast(load("contrast", false));
    setUser(load("user", null)); setWellId(load("wellId", null)); setCountry(load("country", null)); setReady(true);
  }, []);
  useEffect(() => { if (!ready) return; save("lang", lang); save("scale", scale); save("contrast", contrast); save("user", user); save("wellId", wellId); save("country", country);
    document.documentElement.style.setProperty("--fs", `${scale}px`);
    document.documentElement.dataset.contrast = contrast ? "high" : "normal";
    document.documentElement.lang = lang === "hi" ? "hi" : "en";
  }, [ready, lang, scale, contrast, user, wellId, country]);
  return <Ctx.Provider value={{ lang, setLang, scale, setScale, contrast, setContrast, user, setUser, wellId, setWellId, country, setCountry, source, openSource, ready }}>{children}</Ctx.Provider>;
}
export const useApp = () => { const c = useContext(Ctx); if (!c) throw new Error("AppState missing"); return c; };
