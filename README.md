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

## Getting the data

`data/raw/` is gitignored — a fresh clone has to re-download it. Everything below is public,
no-login data used as a stand-in for Oil India's own records (see SPEC.md §6/§0.7). Two entry
points, both idempotent (safe to re-run; already-present files are skipped):

```bash
make data-core   # fast path: Sodir (Norway) + Utah FORGE (USA) + India — enough to bootstrap a demo
make data        # everything above, plus UK, Netherlands, Australia, USA (BSEE), New Zealand, Canada
```

Both run `backend/scripts/download_world.sh`, which also takes explicit sections
(`bash backend/scripts/download_world.sh uk nz canada`) and an alternate destination via
`DATA_DIR=/some/path bash backend/scripts/download_world.sh ...` (useful for verifying the script
without touching the real `data/raw/`). It re-pages the ArcGIS FeatureServer layers behind the
UK/NZ/Canada sources and re-issues the Netherlands (NLOG) bulk POST calls, rather than just
re-fetching a single saved URL, so the record counts match what's already on disk. At the end it
prints a summary of what's present and what's missing.

| Source | Country | Licence | Approx. size |
|---|---|---|---|
| Sodir FactPages (wellbore/tops/casing/mud/history CSVs) | Norway | NLOD 2.0 | ~25 MB |
| Utah FORGE (DDR PDFs, Pason/mud-log data, surveys, 6 wells) | USA | CC-BY | ~1 GB |
| FORCE 2020 lithology competition | Norway (Sodir data) | NLOD 2.0 | ~140 MB |
| NDR/DGH, OISD alerts, Oil India/ONGC annual reports, CAG audits, NGT/court orders, Wikipedia/press | India | Mixed public/government | ~250 MB |
| NSTA Open Data (3 ArcGIS layers + sampled legacy report PDFs) | UK | NSTA Open Data Licence | ~140 MB |
| NLOG (borehole headers/details, stratstelsel CSV, sampled well reports) | Netherlands | Dutch government open data | ~350 MB |
| SARIG (South Australia) + GSQ (Queensland WCR PDF sample) | Australia | CC-BY 4.0 | ~250 MB |
| BSEE Borehole file, incident-narrative PDFs, CY workbooks | USA (Gulf OCS) | US public domain | ~180 MB |
| NZP&M "Petroleum Wells" ArcGIS layer | New Zealand | CC-BY 4.0 | <5 MB |
| CNSOPB, C-NLOPB, Saskatchewan ArcGIS layers | Canada | Open Government Licence / public | ~10 MB |

### What can't be scripted

- **`data/raw/australia/gsq/wcr_meta.json`** — built by querying GSQ's CKAN `package_search` API
  with several filters (report type, commodity, per-company cap) and isn't one stable URL. The
  individual `gsq/wcr/*.pdf` files it describes *are* re-fetched (their per-report URLs are in
  `MANIFEST.csv`), but the portal sits behind a WAF that rate-limits and occasionally challenges
  even a cookie-primed `curl`, so a run may come back with a few of the ~90 PDFs missing — re-run
  the script to pick up stragglers.
- **South Australian well-completion reports** (SARIG catalogue / PEPS-SA) — every scripted or
  headless-browser request gets a 403 from the portal's WAF; never obtained, not just un-scripted.
- **`data/raw/netherlands/nlog/{docs_index_sample,selected_reports}.json`** — a one-off editorial
  sample (which ~280 of 6,737 wells' document lists were inspected, which 117 PDFs were picked).
  There's no stable URL for "the sample"; the report PDFs themselves (`nlog/reports/*.pdf`) are
  re-fetched fine and the ingester falls back to the filename as the document title without them.
- **New Zealand and Canadian well-report/history text** — the narrative sources behind NZP&M's
  PR-numbered reports and CNSOPB's Data Management Centre both require a login (RealMe / a
  requested username+password); only well headers are scripted for these two countries.
- **`data/raw/force2020/lithology_key.csv`** — hand-transcribed from a table in the competition's
  README, not a downloadable file.
- India's `eparlib.sansad.in` committee report and DGH activity reports past 2014-15 were
  unreachable/not published at the expected URL when this was last checked (see
  `data/raw/india_more/REPORT.md`).

`download_data.sh` (Sodir/FORGE) and `download_india*.sh` (India) predate this script and don't
honour `DATA_DIR` — they always write under the repo's own `data/raw/`; `download_world.sh` calls
them as-is for the `core`/`india` sections.

## Where to read more
- `docs/DATA_REPORT.md` — what real data is loaded and what was not reachable
- `docs/ARCHITECTURE.md` — modules and data flow
- `docs/LIMITATIONS.md` — what the numbers do and do not mean
- `docs/WIKI_FORMAT.md` — wiki bundle format
- `docs/PROGRESS.md` — phase status, test and eval results
