"use client";
import { useState } from "react";
import type { Lang } from "@/lib/i18n";
import { Register, type Col } from "@/components/kk/Register";
import { Tabs } from "@/components/v2/ui";
import { tr } from "./trLocal";

type StratRow = {
  n_wells: number; n_cells: number;
  lift: { n_flagged: number; rate_flagged: number | null; rate_unflagged: number | null; headline: string; no_measured_lift_yet: boolean };
  forewarned: { events: number; forewarned: number; forewarned_share: number | null };
};

export function HindsightStrataTable({ bySource, byCountry, method, lang }: { bySource: Record<string, StratRow>; byCountry: Record<string, StratRow>; method: string; lang: Lang }) {
  const t = (en: string, hi: string) => tr(lang, en, hi);
  const [group, setGroup] = useState<"source" | "country">("source");
  const [showMethod, setShowMethod] = useState(false);
  const data = group === "source" ? bySource : byCountry;
  const rows = Object.entries(data).map(([k, v]) => ({ key: k, ...v }));

  const cols: Col<(typeof rows)[number]>[] = [
    { key: "g", head: group === "source" ? t("Source", "स्रोत") : t("Country", "देश"), cell: (r) => r.key },
    { key: "w", head: t("Wells", "कूप"), num: true, cell: (r) => r.n_wells },
    { key: "c", head: t("Cells", "कोशिकाएँ"), num: true, cell: (r) => r.n_cells.toLocaleString() },
    { key: "f", head: t("Flagged", "चिह्नित"), num: true, cell: (r) => r.lift.n_flagged },
    { key: "rf", head: t("Rate flagged", "दर (चिह्नित)"), num: true, cell: (r) => (r.lift.rate_flagged === null ? "—" : `${Math.round(r.lift.rate_flagged * 100)}%`) },
    { key: "ru", head: t("Rate unflagged", "दर (अचिह्नित)"), num: true, cell: (r) => (r.lift.rate_unflagged === null ? "—" : `${Math.round(r.lift.rate_unflagged * 100)}%`) },
    { key: "lift", head: t("Lift", "लिफ्ट"), cell: (r) => r.lift.headline },
    { key: "fw", head: t("Forewarned", "पूर्व-चेतावनी"), num: true, cell: (r) => `${r.forewarned.forewarned}/${r.forewarned.events}` },
  ];

  return (
    <div>
      <div className="flex items-center justify-between flex-wrap gap-2">
        <Tabs items={[{ key: "source", label: t("By source", "स्रोत अनुसार") }, { key: "country", label: t("By country", "देश अनुसार") }]} active={group} onChange={(k) => setGroup(k as any)} />
        <button className="btn" onClick={() => setShowMethod((s) => !s)} aria-expanded={showMethod}>
          {showMethod ? t("Hide method & limits", "विधि व सीमाएँ छुपाएँ") : t("Method & limits", "विधि व सीमाएँ")}
        </button>
      </div>
      {showMethod && <p className="label mt-2 max-w-prose">{method}</p>}
      <div className="mt-3">
        <Register rows={rows} cols={cols} empty={t("No cells in this group.", "इस समूह में कोई कोशिका नहीं।")} />
      </div>
    </div>
  );
}
