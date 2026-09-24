import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        desk: "var(--desk)", board: "var(--file-board)", paper: "var(--paper)", card: "var(--card)", grid: "var(--grid)",
        rule: "var(--rule)", ink: "var(--ink)", ink2: "var(--ink-2)", hazard: "var(--hazard)", caution: "var(--caution)", ok: "var(--ok)",
      },
      borderRadius: { kk: "var(--radius)" },
    },
  },
  plugins: [],
};
export default config;
