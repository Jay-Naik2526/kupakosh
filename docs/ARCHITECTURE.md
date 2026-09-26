# Architecture

```
data/raw/<country>/<source>/  (download_world.sh; MANIFEST.csv per source)
        │
        ▼
ingest/
  built-in:    sodir.py, forge.py, india.py, india_docs.py, survey.py, units.py, well_ids.py
  plug-ins:    ext/<name>.py  (india_more, uk_nsta, nl_nlog, au_wells, us_bsee, no_force2020, nz_wells, ca_wells)
               contract: SOURCE {name, country, url, licence, raw_dir} + ingest(db) -> counts
  pdftext.py:  pdfplumber text; OCR (Tesseract, 300 dpi) for pages with no text layer; confidence per page;
               cached in data/processed/pdf_text/
  upload.py:   POST /api/ingest → background job (one new report, end to end)
        │   wells (country, source, position_source), formation_top, casing_string, pressure_test, mud_check,
        │   document (kind, url, licence, country, ocr_mean_conf) → passage (one per sentence / DDR row),
        │   activity, survey_station, realtime_sample
        ▼
search/embeddings.py   bge-small-en-v1.5 vectors per sentence (reused across rebuilds by text fingerprint)
        ▼
extract/  rules.py + pipeline.py (config/taxonomy.yaml; incident reports need drilling context;
          confidence × OCR confidence), llm_extract.py (pass 2, only with GEMINI/GROQ key; Pydantic +
          verbatim-evidence check; disagreement → needs_review)
        │   event (hazard, depth, formation, qty, MW, confidence, needs_review, verbatim evidence), action
        ▼
engines/
  episodes.py       event → actions → outcome (sentence window | 72 h activity window)          USP2
  ledger.py         success rate per fix, Wilson lower bound, "made worse" count               USP2
  offsets.py        radius + similarity (geo, formation Jaccard, TD overlap)
  hazard.py         Beta posterior per formation × hazard, 80 % range, n_eff                    USP5
  mudwindow.py      LOT/FIT + loss/kick mud weights → window per formation                      USP3
  auditor.py        R1–R6: report text vs tables vs other reports vs rig sensors → audit_flag   USP4
  anomaly.py        robust z + CUSUM on the replay stream
  lookahead.py      formations within 150 m below the bit → alerts + best fixes
  review_replay.py  human review decisions re-applied after every rebuild
  post.py           country per document, data-source register
        ▼
wiki/     compiler.py (cited Markdown, uncited sentence / unsupported number rejected) · gitstore.py · review.py  USP1
copilot/  agent.py (tools; hybrid retrieval = BM25 + embeddings, reciprocal-rank fusion; refusal)
brief/    prespud.py (HTML + WeasyPrint PDF)
eval/     run.py (gold precision/recall, episode precision, LOO Brier, copilot)
        ▼
api/  routes.py (+ ?country=), routes_wiki, routes_copilot, routes_brief, routes_ingest, routes_review, ws.py
      FastAPI :8010 — also serves the built site (frontend/out) for a one-link share
        ▼
frontend/  Next.js 14 · components/kk design system · 9 screens · EN/हिं · /dev/components
           tests: vitest (format), Playwright (all screens: no console errors, ≤ 3 zones, WCAG AA contrast, Hindi toggle)
```

**Traceability.** Every stored fact keeps a `source_ref`:
- `doc:<id>#<locator>`: a verbatim report sentence (page, paragraph, sentence);
- `sodir:<table>:<npdid>#<row>`: an official table row;
- `realtime:<well>@<time>`: a sensor record;
- `query:<kind>?…`: a reproducible query.

`GET /api/source?ref=` resolves any of them.

**Countries.**
- `well.country` is set by each ingester.
- `document.country` is set by `post.assign_countries`: from the document's well, otherwise from the raw-data folder of its plug-in.

**Storage.**
- The prototype uses SQLite through SQLAlchemy, with portable models. Vectors are in `data/processed/embeddings*.npy`.
- The PostGIS/pgvector target stack is described in `docker-compose.yml` and `docker/`. It has not been migrated or verified on the build machine.
