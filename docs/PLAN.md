# Kupakosh — end-to-end build plan (started 26 Sept 2026)

Every phase uses real public data only. The state column is updated as work lands.

| Phase | What | Who | State |
|---|---|---|---|
| E0 | Foundations: `well.country`, plug-in ingesters (`backend/app/ingest/ext/`), bootstrap discovery | main | done |
| E1 | Maximum data, gathered in parallel by background agents. Each agent writes only `ext/<name>.py` + `data/raw/<country>/<source>/` + a MANIFEST | agents | running |
| E1a | India: more public DGH / PIB / Parliament Q&A / OISD / ONGC / OIL / open papers, plus named wells with coordinates where published | agent (sonnet) | |
| E1b | UK: NSTA open data (wells, tops) | agent (sonnet) | |
| E1c | Netherlands: NLOG wells, lithostratigraphy, reports | agent (sonnet) | |
| E1d | Australia: Geoscience Australia / state portals, open WCRs | agent (sonnet) | |
| E1e | USA: BSEE Gulf of Mexico boreholes and well-control incidents | agent (sonnet) | |
| E1f | New Zealand and Canada: open well headers and reports | agent (sonnet) | |
| E1g | Norway: FORCE 2020 logs and lithology | agent (sonnet) | |
| E2 | Country-wise filter: `?country=` on API and country chips in the UI | main | done |
| E3 | Integrate the ingesters, rebuild, extract, compile wiki, run evals, update docs, commit | main | |
| E4 | Upload endpoint `POST /api/ingest` with jobs and incremental wiki recompile | main | done (Accuracy → "Add a report") |
| E5 | LLM pass 2 (Gemini/Groq), only when a key is set; Pydantic-validated | main | |
| E6 | Local embeddings (bge-small) + hybrid search in the copilot | main | |
| E7 | `/dev/components`, Playwright smoke test, contrast check, vitest | main | |
| E8 | Hindi body text, polish, screenshots, docs | main | |
| E9 | Postgres/PostGIS docker scripts (target stack; not runnable here) | main | |

## Rules for data agents
- Use public sources only: no login, no registration, no CAPTCHA. Record the licence of every source.
- Never invent a value. A missing value stays NULL.
- Every Well gets `country`, `source`, and `position_source` (when lat/lon are set).
- Every Document gets a `url` and a `licence`. Text is split into Passages so events can be extracted and cited.
- Test against a scratch SQLite DB, never `data/kupakosh.db`.
