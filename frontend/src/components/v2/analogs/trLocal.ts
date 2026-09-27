import type { Lang } from "@/lib/i18n";

/** Local bilingual helper (v2_common.md ROUND 2 ADDENDUM: do not edit lib/i18n.ts). */
export const tr = (lang: Lang, en: string, hi: string) => (lang === "hi" ? hi : en);
