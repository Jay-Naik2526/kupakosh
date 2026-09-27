# Kupakosh v2: plan to reach the SIH top 5 (started 27 Sept 2026)

The user asked for a much more user-friendly UI, 3D, proper maps, and USPs that stand out. This **replaces the visual rules of SPEC.md §11** (no sidebar, file-board look) at the user's request.

**Kept from SPEC.md:**
- the honesty rules (§0.4–0.7, §11.7): real data only, REPLAY labelled, "insufficient evidence", sources on every number, "Prototype for Oil India Limited · SIH 2026", no Oil India logo or State Emblem, "Decision support only – the engineer decides";
- no copying of competitor code (ideas only);
- EN/हिं.

## New outstanding USPs
1. **Hindsight Test: Kupakosh proves itself on real history.**
   - Take a real well and hide it, so the model uses only other wells.
   - Replay the well's depth, and at every depth ask "would Kupakosh have warned?".
   - Then reveal what really happened in its reports.
   - Report the lead distance (m) before each real problem, missed problems and false alarms.
   - Aggregate over all testable wells into one headline: "X of Y real problems were forewarned, median Z m ahead", with n and method.
   - No competitor shows measured, blind, well-level proof.
2. **Global Analog Memory for Indian basins.**
   - India has almost no public well-level data.
   - For an Indian basin, formation or lithology and depth band, find analogue intervals worldwide by lithology, depth and setting, using the 8 countries' records.
   - Show hazard rates with ranges and n, the best fixes, and the source wells, clearly labelled "analogue evidence, not Indian wells".
   - This turns our biggest weakness (no Indian well data) into a feature Oil India can use on day one.
3. **3D subsurface room.**
   - Offset wells as real 3D trajectories: survey where it exists, otherwise vertical and labelled "assumed vertical".
   - Formation tops as coloured markers, drilling events as glyphs at their depth, the active well's bit, and the look-ahead window.
   - Orbit, zoom and click → source.
4. **"Why this number" on every probability.**
   - Evidence wells with distance and similarity, prior and base rate, n_eff, the 80 % range, and the source lines.
   - This answers the explainability that competitors show with SHAP.
5. Existing: Well Wiki with approval, outcome-ranked fixes, mud window, report auditor, review queue, OCR, 8-country cited data.

## Design system v2 (every agent follows this)
**Shell:**
- A left **sidebar**: 248 px, collapsible to 64 px icons, lucide-react icons plus labels. Groups:
  - Operate: Home, Well Room (live replay), Hindsight
  - Explore: Map, 3D Subsurface, India Analogs, Offsets
  - Knowledge: Wiki, Fixes, Mud Window, Checker
  - Ask: Copilot
  - Deliver: Brief
  - Trust: Accuracy
- A **top bar**: well search combobox, country selector, Ctrl+K, EN/हिं, theme (light/dark), demo user.
- A slim tricolour hairline under the top bar (decorative).
- Footer line: "Prototype for Oil India Limited · SIH 2026 · Decision support only – the engineer decides".

**Look:**
- Light by default: page `#F5F7FA`, cards white with a 1 px `#E4E7EC` border, radius 12 px, soft shadow (`0 1px 2px rgba(16,24,40,.06)`), 24 px gutters.
- Dark ("Rig / control room"): page `#0B1220`, cards `#111A2E`, text `#E6EAF2`.
- Primary accent teal `#0F766E` (buttons, links, focus).
- **State colours only for state:** hazard `#DC2626`, caution `#D97706`, ok `#16A34A`, info `#2563EB`. Always paired with a text label or glyph.
- Type: IBM Plex Sans (UI), IBM Plex Mono with tabular numbers (numbers), Noto Sans Devanagari (Hindi). Body 14–15 px, page title 22–24 px, key numbers 28–40 px.
- Components: Card, StatTile (big number + label + source link), Badge (REPLAY amber, APPROVED green, SYNTHETIC never used), Tabs, Drawer, EmptyState ("Insufficient evidence" with the reason), WhyPanel. Keep Register-style tables with thin rules and mono numbers.

**UX rules:**
- Every screen opens with a one-line question and one primary action.
- Progressive disclosure: details in drawers or tabs.
- Hover shows the source; click opens the source slip.
- Empty and loading states are always explicit.
- Keyboard navigable, visible focus, WCAG AA contrast.
- Mobile width works (sidebar becomes a drawer).

**Maps:**
- MapLibre GL with OpenFreeMap vector tiles (no key).
- Terrain from the public AWS Terrain Tiles for 3D hillshade, with an optional 3D pitch.
- Satellite imagery only if `NEXT_PUBLIC_MAPTILER_KEY` is set. Google Maps needs a billing account, which is the user's choice; the map layer is swappable.
- Cluster ~97k wells; colour by "has recorded events"; radius circle; click → well card.

## Phases
| Phase | What | Owner | State |
|---|---|---|---|
| V1 | Hindsight engine + API + tests + eval metric | agent A | done |
| V2 | Global Analog engine + API + tests | agent B | done |
| V3 | 3D subsurface API + component + page | agent C | done |
| V4 | Well map API (compact geo) + component + page | agent D | done |
| V5 | App shell v2 (sidebar, top bar, tokens, Home "Start here" with a guided tour); Command moves to /command | agent E | done |
| V6 | Hindsight and India Analogs pages; WhyPanel | agents (round 2) | done |
| V7 | Restyle the 9 existing screens to v2 | agents (round 2) | done |
| V8 | Integration, router registration, tests (backend + Playwright), screenshots, deck and docs update, commit | main | done |

## Result (27 Sept 2026)
All V phases are done.
- **Backend:** 81 tests.
- **Frontend:** 18/18 Playwright checks on 12 screens (no console errors, ≤ 3 zones, WCAG AA contrast, Hindi toggle), plus vitest 5/5.

**Hindsight (absolute alert mode, all 299 testable wells, 30,920 formation×hazard cells):**
- Blind alerts were right 11/14 times (79 %). Where Kupakosh stayed silent, only 1 % of layers had a recorded problem: 81× lift (approx. 95 % interval 49–107×).
- A fair baseline that alerts on the field base rate alone gets 74×.
- Only 15/438 problems (3.4 %) were forewarned, with a median lead of 786 m.
- The stricter "elevated" mode flags nothing on this data yet.
- All of this is shown on the Hindsight page and the Accuracy page.
