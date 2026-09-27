# Progress: Kupakosh prototype

> **v2 (27 Sept 2026, user-requested redesign).** New features:
> - a sidebar UI, light/dark theme and a guided tour;
> - a world map of 97k wells with 3D terrain;
> - a 3D subsurface room;
> - the **Hindsight test** (blind replay proof);
> - **India Analogs**;
> - a "Why this number?" panel.
>
> Tests: 81 backend, 18/18 Playwright. See `docs/PLAN_V2.md`. The visual rules of SPEC.md §11 were superseded at the user's request; the honesty rules still apply.

Status as of **27 Sept 2026** (end-to-end build). Phases are those of SPEC.md §15, plus the extension plan in `docs/PLAN.md`.

| Phase | Status | Notes |
|---|---|---|
| P0 Data spike | done | `docs/DATA_REPORT.md`. Volve DDRs are behind Databricks, so public data from 8 countries is used instead. USP3 and USP4: GO. |
| P1 Infra | partial | SQLite, not Postgres/PostGIS/pgvector, because the build machine has no Docker. Config loader, Makefile (`setup`, `data`, `data-core`, `bootstrap`, `api`, `web`, `test`, `e2e`, `share`) and health endpoint done. Alembic migrations are **not** written (`create_all`). docker-compose is written but **not verified**. |
| P2 Ingestion | done | Built-in: Sodir, Utah FORGE, India (NDR/DGH, OISD, CAG, OIL/ONGC, courts). Plug-ins: India (more), UK, Netherlands, Australia, USA (BSEE), Norway (FORCE 2020), New Zealand, Canada. OCR (Tesseract) with confidence per page. Report upload (`POST /api/ingest`) as a background job. Reproducible downloads (`download_world.sh`). |
| P3 Extraction | done | Rules and taxonomy, confidence (× OCR confidence), review flags, verbatim evidence. LLM pass 2 (Gemini/Groq, Pydantic, verbatim-evidence check) is built and tested with a fake model, but **off**: no API key. |
| P4 Episodes + Ledger | done | Sentence-window and 72 h linkers; Wilson-ranked ledger; country filter. |
| P5 Offsets + Hazard | done (weak result) | Similarity breakdown, Beta posterior, 80 % range, n_eff, LOO Brier. **No measurable skill over the base rate**; this is reported. |
| P6 Wiki | done | 609 pages. Every sentence cited, unsupported numbers rejected, git history, noting review, diff, incremental recompile on upload. **0 pages approved.** Approval must be done by a person. |
| P7 USP3 / USP4 | done | Mud window. Auditor R1–R6: R5 is built and tested but gives 0 flags, because no well has both a summary and daily reports. There is a review queue for low-confidence events, and decisions survive rebuilds. |
| P8 Live | done | WebSocket replay of real FORGE sensor data (labelled REPLAY), anomalies, look-ahead with fixes. |
| P9 Copilot | done (extractive) | Tools plus hybrid retrieval (BM25 + bge-small embeddings) and refusal. Country scope. No LLM wording. |
| P10a UI foundation | done | Design system, `/dev/components` (live records), WCAG AA contrast checked by axe. |
| P10b Screens | done | 9 screens plus Rig mode, EN/हिं (about 150 strings; long methodology notes stay English), country filter. Playwright: 14/14. |
| P11 Brief | done | A4 preview + PDF. "Send for review" is not built. |
| P12 Polish | done | README, ARCHITECTURE, LIMITATIONS, DATA_REPORT, EVAL_REVIEW, WIKI_FORMAT, the deck guide (`PPT_KUPAKOSH.md`) and screenshots (`docs/screenshots/`). |

## Test status (27 Sept 2026)
- Backend: `pytest`, 36 passed. Covers rules, Wilson bound, survey, wiki post-check, review, LLM validation (fake model), OCR, auditor R5, the review queue and replay, and the API.
- Frontend: vitest 5/5, type check clean, Playwright 14/14. Every screen loads with no console errors, has ≤ 3 zones and passes WCAG AA contrast. The country filter and the Hindi toggle are tested too.

## Measured (see the Accuracy screen)
| Measure | Value |
|---|---|
| Extraction precision | 0.921 (n=38) |
| Extraction recall | 0.921 (n=38) |
| Depth within ±30 m | 0.923 (n=13) |
| Episode outcome precision | 0.789 (n=19) |
| Hazard LOO Brier, model vs base rate | same (n=41,848): no skill |
| Copilot citation | 1.00 (n=25), templated questions |
| Copilot refusal | 1.00 (n=30), templated questions |

The gold labels were AI-made. An independent AI second pass agreed on 96 % of events and 100 % of episodes, and found no references broken by the rebuild (`docs/EVAL_REVIEW.md`). They are **not human-verified**.
