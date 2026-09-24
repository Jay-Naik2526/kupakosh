# Progress — Kupakosh prototype

Status as of **24 Sept 2026** (first autonomous build). Phases refer to SPEC.md §15.

| Phase | Status | Notes |
|---|---|---|
| P0 Data spike | ✅ done | `docs/DATA_REPORT.md`. Volve DDRs not reachable → Sodir + Utah FORGE used. USP3 & USP4 = GO. |
| P1 Infra | ◐ partial | SQLite instead of Postgres/PostGIS/pgvector (no Docker on build machine). Config loader, Makefile, health endpoint done. Alembic migrations **not** written (`create_all`). docker-compose written but **not verified**. |
| P2 Ingestion | ◐ mostly | Sodir → wells/tops/casing/LOT/mud/history; FORGE DDR PDFs (2 vendor formats) → documents/activities/passages; surveys; sensor data. **Missing:** Volve DDR XML, FORCE 2020, OCR for scanned PDFs, `POST /api/ingest` upload. |
| P3 Extraction | ◐ rules only | Regex + taxonomy, confidence, review flags, verbatim evidence. **LLM pass not built** (no API key); `app/llm/` empty. Precision 0.90 / recall 0.92 on 50 labelled lines. |
| P4 Episodes + Ledger | ✅ done | Sentence-window (narratives) and 72 h time-window (DDRs) linkers; Wilson-ranked ledger. Outcome precision 0.79 (n=19). |
| P5 Offsets + Hazard | ✅ done (weak result) | Similarity with component breakdown; Beta posterior, 80 % CI, n_eff; LOO Brier stored. **Model does not beat base rate** (skill ≈ 0) — reported, not hidden. |
| P6 Wiki | ✅ done | 479 pages compiled; citation + number post-check (0 rejected); git store; Approve / Edit / Return with noting paras + commits; diff. |
| P7 USP3 / USP4 | ✅ done | Mud window from LOT/FIT + loss/kick mud weights; auditor rules R1, R2, R3, R4, R6 (R5 WCR-vs-DDR not built — no WCRs parsed). 26 open conflicts. |
| P8 Live | ✅ done | WS replay of real FORGE sensor data (REPLAY stamp), robust-z + CUSUM anomalies with persistence gating, look-ahead with cooldown and escalation. |
| P9 Copilot | ◐ extractive | Tools: search_evidence (BM25), well_events, get_wiki, nearby_wells, hazard_profile, ledger, mud_window; scope check; refusal. No LLM. Eval questions are templated (citation 1.0 / refusal 1.0 — optimistic). |
| P10a UI foundation | ◐ mostly | Tokens, fonts, FileFrame, IndexTabs, CommandPalette, Stamp, NoticeSlip, LithologyColumn(+patterns), CurveTrack, SourceFootnote, IntervalBar, Register, Drawer, NotingSheet, EmptyState, MiniMap, EN/HI toggle, text size, contrast. **Missing:** `/dev/components` page, formal contrast check. |
| P10b Screens | ◐ mostly | All 9 screens + Rig mode. **Missing:** Playwright smoke test; full Hindi translation of body text (only chrome/labels). |
| P11 Brief | ✅ done | A4 preview + WeasyPrint PDF (ref no., sections, sources, signature blocks, disclaimer). "Send for review" not built. |
| P12 Polish | ◐ partial | README, ARCHITECTURE, LIMITATIONS, WIKI_FORMAT, DATA_REPORT written; no screenshots yet. |

## Test status
`make test` → 16 backend tests pass (rules on real sentences, Wilson bound, minimum curvature vs vendor TVD,
wiki citation rejection, review → commit + noting, API smoke incl. every event resolving to its verbatim line);
frontend type-check clean.

## Measured (see Accuracy screen for n and notes)
- Extraction precision 0.897 (n=39), recall 0.921 (n=38), depth within ±30 m 0.923 (n=13)
- Episode outcome precision 0.789 (n=19); 13 % of sampled "episodes" were extraction errors
- Hazard LOO Brier: model 0.002377 vs base rate 0.002378 (n=41,848) → no measurable skill
- Copilot citation 1.00 (n=25), refusal 1.00 (n=30) — templated questions, optimistic
- All gold labels were made by the AI assistant on real report lines and **must be verified by a person**.
