# Architecture

```
data/raw ──► ingest/ (sodir.py, forge.py, well_ids.py, units.py, survey.py)
                │   wells, formation_top, casing_string, pressure_test, mud_check,
                │   document → passage (one per sentence / DDR activity row), activity, survey_station,
                │   realtime_sample
                ▼
         extract/ (rules.py, pipeline.py)            config/taxonomy.yaml
                │   event (hazard, depth, formation, qty, MW, confidence, needs_review, verbatim evidence)
                │   action (typed mitigation mentions)
                ▼
         engines/
           episodes.py   event → actions → outcome  (sentence window | 72 h activity window)
           ledger.py     action success rate, Wilson lower bound, worsened count      (USP2)
           offsets.py    radius + similarity (geo, strat Jaccard, TD overlap)
           hazard.py     Beta posterior per formation × hazard, 80 % CI, n_eff         (USP5)
           mudwindow.py  LOT/FIT + loss/kick mud weights → window per formation         (USP3)
           auditor.py    text vs tables, DDR vs DDR, DDR vs sensors → audit_flag         (USP4)
           anomaly.py    robust z + CUSUM on the replay stream
           lookahead.py  formations within 150 m below the bit → alerts / notices + fixes
                ▼
         wiki/ compiler.py (cited Markdown, post-check) · gitstore.py · review.py        (USP1)
         copilot/ agent.py (tool routing, BM25 evidence, refusal)
         brief/ prespud.py (data + HTML + WeasyPrint PDF)
         eval/ run.py (gold-set precision, LOO Brier, copilot)
                ▼
         api/ routes*.py (REST, §10) · ws.py (/ws/replay/{well_id})  — FastAPI :8010
                ▼
         frontend/ Next.js 14 · components/kk design system · 9 screens
```

Every stored fact keeps a `source_ref`: `doc:<id>#<locator>` (verbatim report line),
`sodir:<table>:<npdid>#<row>` (official table row), `realtime:<well>@<time>` (sensor record) or
`query:<kind>?…` (a reproducible query). `GET /api/source?ref=` resolves any of them.

Storage is SQLite via SQLAlchemy in this prototype (portable models); the PostGIS/pgvector target
is described in `docker-compose.yml` but not migrated.
