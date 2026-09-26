# Kupakosh — end-to-end build plan (started 26 Sept 2026)

Every phase uses real public data only. The state column is updated as work lands.

| Phase | What | Who | State |
|---|---|---|---|
| E0 | Foundations: `well.country`, plug-in ingesters (`backend/app/ingest/ext/`), bootstrap discovery | main | done |
| E1 | Maximum data, gathered in parallel by background agents. Each agent writes only `ext/<name>.py` + `data/raw/<country>/<source>/` + a MANIFEST | agents | done |
| E1a | India: more public DGH / PIB / Parliament Q&A / OISD / ONGC / OIL / open papers, plus named wells with coordinates where published | agent (sonnet) | done: 32 docs, 5,834 sentences (Lok Sabha report unreachable) |
| E1b | UK: NSTA open data (wells, tops) | agent (sonnet) | done: 13,382 wells, 80 reports |
| E1c | Netherlands: NLOG wells, lithostratigraphy, reports | agent (sonnet) | done: 6,737 wells, 109,042 tops, 102 reports |
| E1d | Australia: Geoscience Australia / state portals, open WCRs | agent (sonnet) | done: 4,082 wells, 93 completion reports |
| E1e | USA: BSEE Gulf of Mexico boreholes and well-control incidents | agent (sonnet) | done: 55,567 wells, 42,502 incident sentences (not yet linked to single wells) |
| E1f | New Zealand and Canada: open well headers and reports | agent (sonnet) | done: 1,267 NZ + 5,472 Canada wells (headers only; reports need login) |
| E1g | Norway: FORCE 2020 logs and lithology | agent (sonnet) | done: 111 wells matched, 3,459 lithology intervals |
| E2 | Country-wise filter: `?country=` on API and country chips in the UI | main | done |
| E3 | Integrate the ingesters, rebuild, extract, compile wiki, run evals, update docs, commit | main | done: 96,422 wells, 215,830 sentences; all tests green |
| E4 | Upload endpoint `POST /api/ingest` with jobs and incremental wiki recompile | main | done (Accuracy → "Add a report") |
| E5 | LLM pass 2 (Gemini/Groq), only when a key is set; Pydantic-validated | main | done (off: no key here; tested with fake model) |
| E6 | Local embeddings (bge-small) + hybrid search in the copilot | main | done |
| E7 | `/dev/components`, Playwright smoke test, contrast check, vitest | main | done (11/11 e2e, 5/5 unit) |
| E8 | Hindi body text, polish, screenshots, docs | main | done (≈150 Hindi strings, screenshots, docs) |
| E9 | Postgres/PostGIS docker scripts (target stack; not runnable here) | main | compose + Dockerfiles exist; unverified (no Docker) |

## Rules for data agents
- Use public sources only: no login, no registration, no CAPTCHA. Record the licence of every source.
- Never invent a value. A missing value stays NULL.
- Every Well gets `country`, `source`, and `position_source` (when lat/lon are set).
- Every Document gets a `url` and a `licence`. Text is split into Passages so events can be extracted and cited.
- Test against a scratch SQLite DB, never `data/kupakosh.db`.

## Follow-up round (27 Sept 2026)
All done:
- USA incidents linked to wells.
- Event review queue; decisions are replayed after every rebuild.
- OCR (Tesseract), including the 1956–1990 BSEE volume.
- Auditor R5, and R2/R3 widened to more report types.
- `download_world.sh`.
- An independent eval-label second pass.
- Hindi UI.
- Final rebuild: 96,418 wells, 224,016 sentences, 2,623 events. All tests green.

Left for people:
- Approve the demo wiki pages.
- Verify the gold labels.
- Add an LLM key (optional).
- Fill the portal fields in the deck.
