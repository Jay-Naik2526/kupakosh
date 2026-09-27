"use client";
import { useEffect, useState } from "react";

export type ThemeColors = {
  bg: string; surface: string; border: string; text: string; text2: string;
  accent: string; hazard: string; caution: string; ok: string; info: string;
  lith: Record<string, string>;
};

const FALLBACK: ThemeColors = {
  bg: "#F5F7FA", surface: "#FFFFFF", border: "#E4E7EC", text: "#101828", text2: "#5D6673",
  accent: "#0F766E", hazard: "#DC2626", caution: "#D97706", ok: "#16A34A", info: "#2563EB",
  lith: { sand: "#E9D8A6", shale: "#A7B0A0", lime: "#B9C6CF", clay: "#B89B7A", chalk: "#EDEBE4", granite: "#D9CFC7" },
};

function readVar(name: string, fallback: string): string {
  if (typeof window === "undefined") return fallback;
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

function read(): ThemeColors {
  return {
    bg: readVar("--bg", FALLBACK.bg), surface: readVar("--surface", FALLBACK.surface),
    border: readVar("--border", FALLBACK.border), text: readVar("--text", FALLBACK.text),
    text2: readVar("--text-2", FALLBACK.text2), accent: readVar("--accent", FALLBACK.accent),
    hazard: readVar("--hazard", FALLBACK.hazard), caution: readVar("--caution", FALLBACK.caution),
    ok: readVar("--ok", FALLBACK.ok), info: readVar("--info", FALLBACK.info),
    lith: {
      sand: readVar("--lith-sand", FALLBACK.lith.sand), shale: readVar("--lith-shale", FALLBACK.lith.shale),
      lime: readVar("--lith-lime", FALLBACK.lith.lime), clay: readVar("--lith-clay", FALLBACK.lith.clay),
      chalk: readVar("--lith-chalk", FALLBACK.lith.chalk), granite: readVar("--lith-granite", FALLBACK.lith.granite),
    },
  };
}

/** CSS custom properties, re-read whenever the light/dark theme or contrast mode flips (Subsurface3D needs raw
 * colour values for three.js materials — WebGL cannot consume `var(--x)` directly). */
export function useThemeColors(): ThemeColors {
  const [colors, setColors] = useState<ThemeColors>(FALLBACK);
  useEffect(() => {
    setColors(read());
    const el = document.documentElement;
    const obs = new MutationObserver(() => setColors(read()));
    obs.observe(el, { attributes: true, attributeFilter: ["data-theme", "data-contrast"] });
    return () => obs.disconnect();
  }, []);
  return colors;
}

export function lithColor(lith: string | null | undefined, colors: ThemeColors): string {
  if (!lith) return colors.text2;
  const key = lith.toLowerCase();
  for (const k of Object.keys(colors.lith)) if (key.includes(k)) return colors.lith[k];
  return colors.text2;
}
