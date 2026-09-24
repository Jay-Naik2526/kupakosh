# Kupakosh (कूपकोश) — "Oil India's memory of every well"

Prototype for Oil India Limited · SIH 2026 · PS 26121 · Team The RAGnarok.
**Decision support only — the engineer decides.** Data: public Sodir (Norway) and Utah FORGE (USA)
records used as stand-ins; no Oil India data is used or claimed.

Kupakosh compiles historical drilling reports once into (a) an engineer-approved, versioned
**Well Wiki** with a citation on every sentence and (b) a **problem → action → outcome ledger** that
ranks fixes by how often they actually worked. On top: an honest Bayesian hazard rate with range and
evidence count, an offset mud-weight window, a report auditor, a pre-drill brief, and a REPLAY
look-ahead on real rig-sensor data.

## Run it (macOS, no Docker needed)

```bash
make setup        # python 3.11 venv (uv) + npm install; brew install pango for PDF output
make data         # downloads Sodir tables + Utah FORGE 16A/16B (~2.5 GB with sensor zips)
make bootstrap    # builds data/kupakosh.db, wiki/ (git), and runs evals (~30 s)
make api          # http://localhost:8010  (8000 was taken on the build machine)
make web          # http://localhost:3000
make test
```

## Screens (right-edge binder tabs; Ctrl+K to jump)
01 Command (REPLAY + look-ahead) · 02 Offsets (correlation panel / map) · 03 Wiki (noting + approval) ·
04 Fixes (ledger) · 05 Mud Window · 06 Checker (report conflicts) · 07 Copilot · 08 Brief (A4 + PDF) ·
09 Accuracy (counts, sources, measured accuracy, limitations).

## Where to read more
- `docs/DATA_REPORT.md` — what real data is loaded and what was not reachable
- `docs/ARCHITECTURE.md` — modules and data flow
- `docs/LIMITATIONS.md` — what the numbers do and do not mean
- `docs/WIKI_FORMAT.md` — wiki bundle format
- `docs/PROGRESS.md` — phase status, test and eval results
