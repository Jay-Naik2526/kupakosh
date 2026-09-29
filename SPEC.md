# SPEC.md — KUPAKOSH (SIH 2026 · PS 26121 · Oil India Limited)

> Team: **The RAGnarok** · Lead: Jay Naik · National portal submission deadline: **30 Sept 2026**.

---

## 0. HOW TO WORK WITH ME (read first, follow always)

1. **Plan first.** Before writing code for any part, show a short plan: files, functions, data flow, acceptance test. Wait for my "go".
2. **Part by part.** Build one phase (section 15) at a time. At the end of each phase, run the tests, show the results, stop, and wait for confirmation.
3. **Full files, not diffs.** When you change a file, give or write the complete file.
4. **No fake data in the product.**
   - Every number on screen must come from the database, a fitted model, or `config/*.yaml`.
   - The live feed is a *replay of real recorded data* and must be labelled "REPLAY" in the UI.
   - Unknown values are shown as "unknown" or "insufficient evidence", never 0 and never invented.
5. **Every claim is traceable.** Every extracted fact, wiki sentence, alert, and copilot answer carries source references (`doc_id + page/line` or `xml file + activity index`).
6. **No magic numbers.** Thresholds, windows, weights, and radii live in `config/default.yaml`.
7. **Be honest about limits.**
   - Our data is public Norwegian, US, and Australian data used as stand-ins for Oil India data.
   - Never claim Oil India data, and never claim accuracy we have not measured.
8. **Do not copy code from competitor repos** (list in section 3).
9. **Commit after each phase** with a clear message. Keep a running `docs/PROGRESS.md`.
10. When unsure about domain meaning, ask me. Do not guess silently.
11. **UI must follow section 11 exactly.** Uncluttered, at most 3 zones per screen, no impersonation of Oil India.

---

## 1. THE PROBLEM (plain words)

Oil India drills deep wells (2–4 km). Wells pass through underground rock layers called **formations**. Problems repeat in the same layers across nearby wells:
- **mud loss** (drilling fluid leaks into cracks)
- **kick** (gas or fluid enters the well; dangerous, can become a blowout)
- **stuck pipe**
- **torque spikes**
- **overpressure**
- **cementing failures**
- **fishing** (retrieving broken tools)

Knowledge of what happened in older nearby wells (**offset wells**) is buried in thousands of PDFs:
- **DDRs**: Daily Drilling Reports, the rig's diary
- **WCRs**: Well Completion Reports, the final summary
- engineers' memories

Oil India's live system **eRTMAC** shows real-time data from the active well but no history.

Oil India wants a standalone system beside eRTMAC that:
1. extracts and structures information from historical drilling reports (AI + NLP + OCR);
2. shows nearby wells on a map within a user-defined radius;
3. provides a searchable repository of drilling events, lessons learned, and mitigations;
4. correlates geological, drilling, and reservoir data across wells by depth and formation;
5. predicts risks: mud loss, stuck pipe, overpressure, torque spikes, cementing issues;
6. gives real-time alerts and recommendations as drilling approaches known danger depths or formations;
7. presents everything on a user-friendly dashboard for field and office staff.

The official PS also lists these as relevant data:
- WCRs, DDRs, mud logging
- historical parameters, reservoir and geology data
- eRTMAC streams
- **trajectory/survey**
- **casing, cementing, and mud programs**
- events: losses, kicks, stuck pipe, fishing, NPT

---

## 2. OUR PRODUCT: KUPAKOSH (कूपकोश)

*Kupa* = well, *Kosh* = treasury. Tagline: **"Oil India's memory of every well."**

**Core idea (the main difference):** competitors *search* raw PDFs every time (a RAG chatbot). We **compile** the reports once, into two things:
- **(a)** an engineer-approved, versioned **Well Wiki**;
- **(b)** a **problem → action → outcome ledger**, which tells us *which fix actually worked* and how often.

On top of these we add an honest probabilistic hazard model, a mud-weight window, a report auditor, and a live look-ahead.

### Our 5 USPs (none of them appear in the 9 public competitor repos checked on 24 Sept 2026)

| # | USP | One line |
|---|---|---|
| 1 | **Well Wiki (compiled memory, OKF-style)** | An LLM compiles Markdown pages per well, formation, and hazard, with a citation on every sentence. An engineer approves them, and every change is kept in git history. |
| 2 | **Outcome-ranked mitigation ledger** | Links DDR days into problem → action → outcome episodes. Ranks fixes by success rate, showing n and a Wilson lower bound. |
| 3 | **Offset mud-weight window + casing/cement lessons** *(gated on data, see P0)* | Safe mud-weight range per formation, built from LOT/FIT tests, kicks, and losses. Plus casing-seat and cement-job lessons. |
| 4 | **Report auditor** *(gated on data)* | Cross-checks DDR vs WITSML sensors vs WCR vs formation tops. Flags conflicts and gives each fact a trust badge. |
| 5 | **Honest Bayesian hazard model** | Probability with an 80% credible interval and effective n. Says "insufficient evidence" when n is small. Fused with live anomaly signals. |

**Cut order if time runs out:** USP4 first, then USP3. USPs 1, 2, and 5 are mandatory.

---

## 3. COMPETITION (so we stay different)

Public repos on PS 26121, checked 24 Sept 2026:
- Physics0070/nwis (strongest)
- n3ssdub3y/SIH_2026_PLANNS (knowledge graph + GraphRAG; now private)
- SurveAnil/geodrill-ai (formation correlation, WITSML/LAS)
- CB-acc-tech/Hackathon2026 "RigMind" (PostGIS, dip correction, RAG with citations)
- IqraS-gif/DrillSight (PINO, playbooks, voice notes)
- bishopcommander/OffsetEye
- tarumishra22/eRTMAC-NWIS
- SujalPatil21/Drill-Insight
- shaurya212121/BoreX

**Common in all of them** (our baseline, not a USP): map + radius, RAG chatbot, depth-window alerts, risk heatmap, telemetry simulator, OCR.

**Never make these our headline:** knowledge graph/GraphRAG, formation correlation alone, WITSML adapter alone, "physics-informed" claims, voice notes, dark neon "command center" UIs.

---

## 4. TECH STACK (fixed unless I approve a change)

| Layer | Choice |
|---|---|
| Backend | Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2 (psycopg 3), Alembic |
| Database | PostgreSQL 16 + PostGIS 3.4 + pgvector (single DB) |
| Embeddings | `BAAI/bge-small-en-v1.5` via sentence-transformers (384-dim, local/offline) |
| LLM | Abstraction in `app/llm/client.py`. Primary: Gemini (`google-genai`) with JSON-schema output. Fallback: Groq. **All LLM output is validated by Pydantic. If invalid, retry once; if still invalid, mark `needs_review`.** |
| PDF text | pdfplumber (digital PDFs) |
| OCR | Tesseract via pytesseract + pdf2image (scanned PDFs); OCR confidence stored per page |
| XML | lxml (WITSML 1.4 drillReport, log, and trajectory objects) |
| Stats | numpy, scipy, pandas |
| Wiki versioning | GitPython on `wiki/` (a git repo of Markdown + YAML frontmatter) |
| Realtime | FastAPI WebSocket `/ws/replay/{well_id}` |
| PDF output | WeasyPrint (HTML → PDF) for the pre-drill brief |
| Frontend | Next.js 14 (App Router) + TypeScript + Tailwind + Radix primitives (shadcn/ui only as base, fully restyled to section 11) + MapLibre GL (OSM tiles, custom muted paper style) + visx or D3 for mud-log tracks (Recharts only for simple charts) |
| Fonts | `next/font`: IBM Plex Sans, IBM Plex Mono, Noto Sans Devanagari, Courier Prime (file numbers and stamps only) |
| Infra | Docker Compose (db, api, web); Makefile |
| Tests | pytest (backend), vitest + Playwright smoke test (frontend) |

**DB image** — `docker/db.Dockerfile`:
```
FROM postgis/postgis:16-3.4
RUN apt-get update && apt-get install -y postgresql-16-pgvector && rm -rf /var/lib/apt/lists/*
```

---

## 5. REPO STRUCTURE

```
kupakosh/
├── SPEC.md
├── README.md
├── Makefile
├── docker-compose.yml
├── .env.example
├── config/
│   ├── default.yaml            # all thresholds/weights
│   └── taxonomy.yaml           # hazards, actions, outcomes, synonyms
├── design/
│   └── stitch/                 # exported Stitch mockups (reference only)
├── docker/ (db.Dockerfile, api.Dockerfile, web.Dockerfile)
├── data/                       # gitignored; raw + processed
│   ├── raw/{volve,sodir,force2020,forge,nopims}/
│   ├── processed/
│   └── eval/                   # hand-labelled eval sets
├── wiki/                       # separate git repo; OKF-style bundle
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── db/ (models.py, session.py, migrations/)
│   │   ├── llm/ (client.py, prompts/, schemas.py)
│   │   ├── ingest/ (sodir.py, force2020.py, volve_ddr.py, volve_realtime.py, forge.py, pdf_docs.py, units.py, well_ids.py)
│   │   ├── extract/ (rules.py, llm_extract.py, confidence.py)
│   │   ├── engines/
│   │   │   ├── episodes.py     # USP2 linker
│   │   │   ├── ledger.py       # USP2 ranking
│   │   │   ├── hazard.py       # USP5 Bayesian
│   │   │   ├── anomaly.py      # live signals
│   │   │   ├── mudwindow.py    # USP3
│   │   │   ├── auditor.py      # USP4
│   │   │   ├── offsets.py      # radius + similarity selection
│   │   │   └── lookahead.py    # live alerts
│   │   ├── wiki/ (compiler.py, review.py, gitstore.py)
│   │   ├── copilot/ (agent.py, tools.py)
│   │   ├── brief/ (prespud.py, templates/)
│   │   ├── api/ (routes_*.py, ws.py)
│   │   └── eval/ (extraction_eval.py, episode_eval.py, copilot_eval.py, hazard_loo.py)
│   ├── scripts/ (download_*.py, inspect_data.py, bootstrap.py, rebuild.py)
│   └── tests/
└── frontend/
    └── src/
        ├── app/
        │   ├── layout.tsx              # desk + file board + sheet + index tabs
        │   ├── page.tsx                # 01 Command
        │   ├── offsets/                # 02 Offsets
        │   ├── wiki/                   # 03 Wiki
        │   ├── fixes/                  # 04 Fixes (ledger)
        │   ├── mudwindow/              # 05 Mud Window
        │   ├── checker/                # 06 Checker (auditor)
        │   ├── copilot/                # 07 Copilot
        │   ├── brief/                  # 08 Brief
        │   └── accuracy/               # 09 Accuracy (status/eval)
        ├── components/kk/              # design-system components (section 11.5)
        ├── styles/tokens.css           # CSS variables (section 11.2)
        └── lib/ (api.ts, ws.ts, format.ts, i18n.ts)
```

---

## 6. DATA SOURCES (all public; stand-ins for Oil India data)

| Source | Use | Access | Notes |
|---|---|---|---|
| **Equinor Volve** | DDRs as WITSML drillReport XML (~1,759 files per the literature), real-time WITSML logs, trajectories, formation tops, some PDF reports | Free academic licence. Download via Databricks Marketplace (Equinor ASA); user-guide PDF on equinor.com/energy/volve-data-sharing | **Main dataset.** Trap: the GitHub mirror f0nzie/volve-drilling is completion/workover data with ROP = 0. Use the full dataset. |
| **Volve real-time CSV (Univ. of Stavanger, Tunkiel)** | Parsed real-time drilling data (2.7 GB compressed) | ux.uis.no/~atunkiel/file_list.html · CC BY-NC-SA | Replay source. **Verify ROP ≠ 0 and pit-volume columns exist.** |
| **Sodir FactPages** (Norway) | Wellbore coordinates, formation tops (lithostratigraphy), well history, casing/LOT tables if present | factpages.sodir.no (CSV export) | Map, formation tops, canonical well IDs |
| **FORCE 2020** | 98 wells of logs with lithology/formation labels + coordinates | github.com/bolgebrygg/Force-2020-Machine-Learning-competition | Formation similarity, section view |
| **Utah FORGE** | DDR PDFs, Pason drilling data, mud logs, end-of-well reports for close wells (16A, 16B, 56-32, 78B-32, 58-32) | gdr.openei.org (CC-BY) | Second field, to prove the method generalises |
| **NOPIMS** (Australia) | Scanned WCR PDFs with casing, cement, and LOT/FIT tables | NOPIMS (registration) | OCR stress test; data for USP3 |
| **India NDR (DGH)** | Real Indian data | Academic registration: student ID + HOD authority letter to indr@dghindia.gov.in | Unlikely before the deadline. Mention it as the deployment path. |

**Canonical well ID:** Volve spells well names several ways (`15/9-F-5`, `NO 15/9-F-5`, `15_9-F-5`, `15$47$9-F-5`). Implement `ingest/well_ids.py` with `canonical(name) -> "15/9-F-5"`, plus unit tests.

**Units:**
- Store depth in **metres** (MD and TVD), mud weight in **ppg**, volume in **bbl**.
- Conversions: ft → m ×0.3048; sg → ppg ×8.345; m³ → bbl ×6.2898.
- Keep the original value and unit in `raw_value` / `raw_unit`.

---

## 7. DATABASE SCHEMA (PostGIS + pgvector)

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE field (id SERIAL PRIMARY KEY, name TEXT UNIQUE, country TEXT, source TEXT);

CREATE TABLE well (
  id SERIAL PRIMARY KEY,
  canonical_name TEXT UNIQUE NOT NULL,
  aliases TEXT[] DEFAULT '{}',
  field_id INT REFERENCES field(id),
  geom GEOGRAPHY(POINT, 4326),
  kb_elev_m REAL, water_depth_m REAL,
  spud_date DATE, td_md_m REAL, td_tvd_m REAL,
  status TEXT, source TEXT, position_source TEXT
);
CREATE INDEX ON well USING GIST (geom);

CREATE TABLE survey_station (well_id INT REFERENCES well(id), md_m REAL, inc_deg REAL, azi_deg REAL, tvd_m REAL, north_m REAL, east_m REAL);

CREATE TABLE formation_top (
  id SERIAL PRIMARY KEY, well_id INT REFERENCES well(id),
  formation TEXT NOT NULL, grp TEXT, lithology TEXT,
  top_md_m REAL, top_tvd_m REAL, base_md_m REAL,
  source TEXT, source_ref TEXT
);

CREATE TABLE document (
  id SERIAL PRIMARY KEY, well_id INT REFERENCES well(id),
  kind TEXT CHECK (kind IN ('DDR_XML','DDR_PDF','WCR_PDF','EOWR_PDF','MUDLOG','OTHER')),
  path TEXT, report_date DATE, pages INT, is_scanned BOOL, ocr_mean_conf REAL, sha256 TEXT UNIQUE
);

CREATE TABLE passage (
  id SERIAL PRIMARY KEY, document_id INT REFERENCES document(id),
  locator TEXT, text TEXT, md_m REAL, report_date DATE,
  embedding VECTOR(384)
);
CREATE INDEX ON passage USING hnsw (embedding vector_cosine_ops);

CREATE TABLE activity (
  id SERIAL PRIMARY KEY, well_id INT REFERENCES well(id), document_id INT REFERENCES document(id),
  seq INT, t_start TIMESTAMPTZ, t_end TIMESTAMPTZ, md_m REAL, tvd_m REAL,
  phase TEXT, code TEXT, state TEXT, comment TEXT, formation TEXT
);

CREATE TABLE event (
  id SERIAL PRIMARY KEY, well_id INT REFERENCES well(id), activity_id INT REFERENCES activity(id),
  hazard TEXT, md_m REAL, tvd_m REAL, formation TEXT, t TIMESTAMPTZ,
  severity TEXT, quantity REAL, quantity_unit TEXT, mud_weight_ppg REAL,
  confidence REAL, method TEXT CHECK (method IN ('rule','llm','rule+llm','human')),
  needs_review BOOL DEFAULT false, source_ref TEXT NOT NULL
);

CREATE TABLE action (
  id SERIAL PRIMARY KEY, well_id INT REFERENCES well(id), activity_id INT REFERENCES activity(id),
  action_type TEXT, detail TEXT, t TIMESTAMPTZ, md_m REAL, confidence REAL, source_ref TEXT NOT NULL
);

CREATE TABLE episode (
  id SERIAL PRIMARY KEY, well_id INT REFERENCES well(id), event_id INT REFERENCES event(id),
  hazard TEXT, formation TEXT, md_m REAL, action_ids INT[],
  outcome TEXT CHECK (outcome IN ('resolved','partial','unresolved','worsened','unknown')),
  outcome_ref TEXT, hours_to_resolve REAL, confidence REAL, reviewed_by TEXT
);

CREATE TABLE pressure_test (
  id SERIAL PRIMARY KEY, well_id INT REFERENCES well(id), kind TEXT CHECK (kind IN ('LOT','FIT')),
  md_m REAL, tvd_m REAL, emw_ppg REAL, casing_shoe_md_m REAL, formation TEXT, source_ref TEXT
);

CREATE TABLE casing_string (
  id SERIAL PRIMARY KEY, well_id INT REFERENCES well(id), od_in REAL, shoe_md_m REAL, shoe_tvd_m REAL,
  cement_top_md_m REAL, cement_issue TEXT, source_ref TEXT
);

CREATE TABLE realtime_sample (
  well_id INT, t TIMESTAMPTZ, md_m REAL, bit_md_m REAL, rop REAL, wob REAL, rpm REAL, torque REAL,
  spp REAL, flow_in REAL, pit_vol REAL, hookload REAL, mw_in_ppg REAL
);
CREATE INDEX ON realtime_sample (well_id, t);

CREATE TABLE audit_flag (
  id SERIAL PRIMARY KEY, well_id INT, rule TEXT, severity TEXT,
  claim_a TEXT, ref_a TEXT, claim_b TEXT, ref_b TEXT, delta TEXT, status TEXT DEFAULT 'open', reviewer_note TEXT
);

CREATE TABLE wiki_page (
  id SERIAL PRIMARY KEY, slug TEXT UNIQUE, kind TEXT CHECK (kind IN ('well','formation','hazard','lesson')),
  title TEXT, ref_no TEXT, version INT, status TEXT CHECK (status IN ('draft','in_review','approved','returned')),
  git_commit TEXT, approved_by TEXT, approved_at TIMESTAMPTZ, trust REAL
);

CREATE TABLE wiki_noting (   -- government-file style noting entries per page
  id SERIAL PRIMARY KEY, page_id INT REFERENCES wiki_page(id), para_no INT,
  author TEXT, role TEXT, note TEXT, action TEXT, created_at TIMESTAMPTZ DEFAULT now(), git_commit TEXT
);

CREATE TABLE eval_result (id SERIAL PRIMARY KEY, name TEXT, metric TEXT, value REAL, n INT, run_at TIMESTAMPTZ DEFAULT now(), notes TEXT);
```

---

## 8. TAXONOMY (`config/taxonomy.yaml`)

**Hazards** (keyword seeds; extend them by reading real DDR comments):
- `lost_circulation`: losses, lost circulation, partial returns, total losses, no returns, LCM, seepage losses
- `kick`: kick, influx, gain, pit gain, flow check positive, shut in, well control, kill
- `stuck_pipe`: stuck, overpull, tight hole, pack off, packoff, differential sticking, jarring, jarred
- `torque_spike`: high torque, erratic torque, torque spike, stalling
- `overpressure`: connection gas, trip gas, high background gas, gas peak, pore pressure increase
- `cementing_issue`: cement losses, squeeze, poor bond, no cement returns, WOC problems, remedial cement
- `fishing`: fish, fishing, junk, twisted off, left in hole
- `wellbore_instability`: cavings, hole collapse, washout, ream, backream, tight spot

**Actions:** lcm_pill, reduce_mw, increase_mw, reduce_flow, circulate_condition, ream_backream, jar, spot_pill, pump_out, cement_plug, squeeze, shut_in_kill, pooh, sidetrack, change_bha, other

**Outcomes:**
- `resolved`: losses cured, full returns, pipe free, well static, torque normal
- `partial`: reduced losses, partial returns continuing
- `unresolved`: still losing, still stuck
- `worsened`: losses increased, kick after MW cut, stuck deeper
- `unknown`: nothing in the window says either way

---

## 9. ENGINE SPECS

### 9.1 Extraction (`extract/`)

**Pass 1: rules.** Regex plus the keyword taxonomy on activity comments. Captures:
- hazard
- quantity: `(\d+\.?\d*)\s*(bbl|m3)`
- depth: `@\s*(\d+)\s*m`
- mud weight: `(\d+\.\d+)\s*(ppg|sg)`

**Pass 2: LLM.** Runs only on activities flagged by rules or with ambiguous text. Output schema:
```python
class ExtractedEvent(BaseModel):
    hazard: Literal[...]            # taxonomy keys or "none"
    md_m: float | None
    quantity: float | None; quantity_unit: Literal["bbl","m3",None]
    mud_weight_ppg: float | None
    actions: list[Literal[...]]
    outcome_hint: Literal["resolved","partial","unresolved","worsened","unknown"]
    evidence_span: str              # MUST be a verbatim substring of input
    confidence: float
```

**Validation rules:**
- `evidence_span` must appear verbatim in the source.
- Depth must lie within `[0, td_md_m]`.
- Mud weight must lie within `[7, 20]` ppg.

**Confidence** combines rule/LLM agreement, OCR confidence, and whether validation passed. Anything below `config.extract.review_threshold` is marked `needs_review`.

**Formation** comes from looking up `formation_top` at the event's MD/TVD.

### 9.2 Episode linker (USP2, `engines/episodes.py`)
- For each `event`, collect activities from the same well in `(t_event, t_event + window_h]` (default 72 h).
- Stop early at an unrelated phase change, or at a new event of the same hazard at a new depth.
- **Actions** = the extracted actions inside the window.
- **Outcome** = the first activity in the window that matches outcome phrases (rules first, LLM as fallback). Store `outcome_ref`.
- `hours_to_resolve` = time of outcome − time of event.
- **Eval:** compare against `data/eval/episodes_gold.csv` (30+ episodes, hand-labelled from real reports). Report precision.

### 9.3 Mitigation ledger (USP2, `engines/ledger.py`)
- Group episodes by `(hazard, formation)`, or field-wide.
- For each action type compute:
  - `n` (number of episodes)
  - `k` = resolved (1) + partial (0.5)
  - `rate = k/n`
  - **Wilson lower bound**, z = 1.96: `lb = (p + z²/2n − z·sqrt(p(1−p)/n + z²/4n²)) / (1 + z²/n)`
- Rank by `lb`.
- Also show median hours to resolve and the `worsened` count.
- If `n < 3`, tag the row "anecdotal".
- Every row links to its episodes and their sources.

### 9.4 Offset selection (`engines/offsets.py`)
- Candidate wells: `ST_DWithin` of the active well within the chosen radius.
- Similarity score: `sim = w_geo·exp(−d/D) + w_strat·Jaccard(formation sequences) + w_depth·overlap(TD ranges)`.
- Return the ranked list with the score broken down per component.

### 9.5 Hazard model (USP5, `engines/hazard.py`)
- Each offset well *i* that penetrated formation F gives `y_i ∈ {0,1}` (did the hazard occur there?), with weight `w_i = sim_i`.
- **Prior:** `Beta(a0, b0)` from the field base rate, with strength `prior_strength`.
- **Posterior:** `Beta(a0 + Σw_i y_i, b0 + Σw_i(1−y_i))`.
- **Report:** posterior mean, 80% credible interval, and `n_eff = (Σw)²/Σw²`.
- If `n_eff < min_neff`, return "insufficient evidence".
- **Validation:** leave-one-well-out. Report the Brier score against the base-rate baseline, **even if it is weak**.

### 9.6 Live anomaly (`engines/anomaly.py`)
- Rolling robust z-score (median/MAD) on torque, SPP, hookload, and Δpit_vol.
- CUSUM on Δpit_vol:
  - sustained drop → `possible_losses`
  - sustained gain → `possible_influx`
- Output wording is **"Abnormal behaviour"** plus the channels that triggered it. Never a diagnosis without evidence.

### 9.7 Look-ahead (`engines/lookahead.py`)
- Replay `realtime_sample` at `speed×` over the WebSocket, labelled REPLAY.
- On each tick:
  - find the current formation and the formations in the next `lookahead_m` (150 m);
  - emit an alert for each hazard whose posterior is at or above the threshold. The alert includes probability ± CI, n_eff, the top-3 ledger fixes, and wiki and source links.
- If a live anomaly matches a hazard expected in the current formation, escalate the alert.
- Apply a cooldown between repeated alerts.

### 9.8 Mud-weight window (USP3; gated by P0)
- For each formation, collect evidence from offset wells:
  - **Lower bound:** mud weight at kicks or influx, and the minimum stable mud weight.
  - **Upper bound:** LOT/FIT equivalent mud weight, and mud weight at losses.
- Window = [max of the lower evidence, min of the upper evidence].
- Show every evidence point with its source, and overlay the active well's mud weight.
- Also list casing shoes against formations, and cement issues with their sources.

### 9.9 Report auditor (USP4; gated by P0)
**Rules** (tolerances in config):
1. DDR loss depth/time vs WITSML pit-volume drop.
2. Casing shoe depth: WCR vs DDR vs Sodir.
3. Formation top: Sodir vs report text.
4. The same quantity reported differently on consecutive days.
5. An event in the WCR summary but missing from the DDRs, and the reverse.

**Output:** rows in `audit_flag`, plus a `trust` score per wiki claim.

### 9.10 Well Wiki (USP1)
**Bundle layout:**
- Pages: `wiki/wells/*.md`, `wiki/formations/*.md`, `wiki/hazards/*.md`, `wiki/lessons/*.md`
- Index and log: `wiki/index.md`, `wiki/log.md`
- Format: Markdown + YAML frontmatter.
- **Check Google's Open Knowledge Format v0.1 conventions first.** If they're unreachable, document our own format in `docs/WIKI_FORMAT.md`.

**Frontmatter:**
```yaml
---
id: formation/hugin
kind: formation
ref_no: KPK/WIKI/FRM/0007
version: 4
title: Hugin Formation
status: approved        # draft | in_review | approved | returned
trust: 0.82
sources: [doc:123#activity:17, doc:88#p4:l3-l9]
related: [[hazards/lost_circulation]], [[wells/15-9-F-5]]
approved_by: R. Das
approved_at: 2026-09-26
---
```

**Compiler rules:**
- The compiler writes **only from structured rows plus quoted passages**.
- Every sentence ends with a citation marker `[^sN]`.
- A post-check rejects any sentence without a citation, and any number that isn't present in the sources.

**Review workflow (government "noting" style):**
- Actions: Approve / Edit / Return.
- Each action adds a numbered noting para (author, role, note, timestamp) and a git commit.
- Only `approved` pages count as "approved knowledge"; drafts are shown with a badge.

**Incremental updates:** when a new document arrives, recompile only the affected pages and send them back to review.

### 9.11 Copilot
- **Tools:**
  - `search_evidence` (hybrid: pgvector + keyword)
  - `get_wiki`
  - `nearby_wells`
  - `hazard_profile`
  - `ledger`
  - `mud_window`
- **Rules:** answers must cite sources. When there's no evidence, reply "No evidence found in the records." Never generate SQL. Numbers come only from tool outputs.
- **Eval:** `data/eval/copilot_questions.csv` — 30 questions with expected sources, 5 of which should be refused.

### 9.12 Pre-drill brief
- **Input:** location, target TD, and planned tops (optional; if missing, infer from offsets).
- **Output:** a PDF styled as an official office document (section 11.6, screen 08), containing:
  - formation column
  - hazards per section with probability ± CI
  - best fixes
  - mud window, if available
  - casing lessons
  - open audit conflicts
  - sources
  - signature blocks
  - the line "Decision support only. The engineer decides."

---

## 10. API (FastAPI)

```
GET  /api/status                          counts, sources, eval metrics
GET  /api/wells?bbox=&q=
GET  /api/wells/{id}                      details + tops + casing + tests
GET  /api/wells/{id}/offsets?radius_m=    ranked offsets with similarity breakdown
GET  /api/wells/{id}/section              tops + events by depth (correlation panel)
GET  /api/wells/{id}/hazards              posterior per formation×hazard
GET  /api/events?well=&hazard=&formation=
GET  /api/episodes?hazard=&formation=
GET  /api/ledger?hazard=&formation=
GET  /api/mudwindow?formation=&well=
GET  /api/audit?well=&status=             | POST /api/audit/{id}/resolve
GET  /api/wiki | /api/wiki/{slug} | /api/wiki/{slug}/history | /api/wiki/{slug}/diff?a=&b= | /api/wiki/{slug}/noting
POST /api/wiki/{slug}/review              {action: approve|edit|return, content?, reviewer, note}
POST /api/wiki/compile?scope=
POST /api/copilot                         {question, context_well?}
POST /api/brief                           {lat, lon, target_td_m, planned_tops?} -> PDF
POST /api/ingest                          upload PDF/XML -> job id ; GET /api/jobs/{id}
WS   /ws/replay/{well_id}?speed=          samples + alerts
```

---

## 11. UI DESIGN SYSTEM (MANDATORY)

### 11.1 Concept: "A mud-log sheet inside a government file"
- The app looks like an Indian **government file**: khaki file board, file number, subject line, noting sheet, rubber stamps.
- Inside the file lies a **mud-log sheet**: the off-white grid paper drilling engineers actually read, with rock-pattern columns.
- **Colour follows ISA-101 high-performance HMI rules.** The interface is calm and nearly monochrome, and colour appears **only** to signal state.
- **The number one rule is to stay uncluttered.** Each screen answers one question, has **at most 3 zones**, and puts details behind a click (drawers, expanders, other tabs).
- **Explicitly NOT allowed:**
  - navy + gold palettes
  - dark neon "command center" looks (except Rig mode, 11.4)
  - gradients, drop shadows, glassmorphism, glow
  - rounded "pill everything" styling
  - purple
  - emoji icons

### 11.2 Tokens (`styles/tokens.css`)
```css
:root {
  --desk: #2B2A27;          /* page background around the file */
  --file-board: #D8CBA8;    /* khaki file cover */
  --paper: #F3F0E8;         /* log-paper sheet */
  --card: #FBFAF6;
  --grid: #E2DDD0;          /* 24px engineering grid, very faint */
  --rule: #CFC8B8;          /* borders */
  --ink: #1B1A17;           /* primary text */
  --ink-2: #5E5A50;         /* secondary text */
  --hazard: #B23A1E;        /* oxide red: hazard/critical ONLY */
  --caution: #C98A12;       /* safety amber: caution/REPLAY ONLY */
  --ok: #2F6B5E;            /* verdigris: approved/resolved ONLY */
  --tab-1: #E6DCC3; --tab-2: #D9E2D3; --tab-3: #E0E0DA; --tab-4: #EAD9D3;  /* muted index-tab tints */
  /* lithology fills (+ SVG hatch patterns) */
  --lith-sand: #E9D8A6; --lith-shale: #A7B0A0; --lith-lime: #B9C6CF; --lith-clay: #B89B7A; --lith-chalk: #EDEBE4;
  --radius: 2px;
}
```
- **Lithology hatch patterns:** SVG `<pattern>` defs in `components/kk/LithologyPatterns.tsx`:
  - sandstone = dots
  - shale = short dashes
  - limestone = brick
  - claystone = fine horizontal lines
  - chalk = sparse blocks
- **Tricolour hairline:** 2px at the very top of the sheet (#FF9933 / #FFFFFF / #138808). Decorative only.

### 11.3 Typography
- **UI text:** IBM Plex Sans. **Numbers, depths, units:** IBM Plex Mono with `font-variant-numeric: tabular-nums`. **Hindi:** Noto Sans Devanagari. **File numbers and stamps only:** Courier Prime.
- **Sizes:** body 14–15px; minimum 13px only for secondary footnotes (never below); key numbers 20–40px; screen title 22px.
- **Bilingual headings:** English primary, with Hindi in smaller text below or beside it. Strings live in `lib/i18n.ts` and the EN/हिं toggle switches the primary language.

### 11.4 Layout and navigation
- **Frame:**
  - `--desk` background, with the `--file-board` on top (24px margin).
  - One line of typewriter mono on the file board, e.g. `FILE No. KPK/DRL/2026/0142 · Prototype for Oil India Limited · SIH 2026`. The file number changes per screen.
  - The `--paper` sheet sits inside, holding the content.
- **Navigation:** **no top nav bar, no left sidebar.**
  - **Binder index tabs** stick out of the **right edge** of the sheet, stacked vertically, each 56×120px.
  - Tab tints rotate through `--tab-1..4`.
  - Each tab shows a mono number plus a two-line EN/HI label.
  - The active tab is flush with the sheet and the same colour, so it looks joined. Inactive tabs are recessed 8px.
  - Tab list: `01 Command/कमान`, `02 Offsets/निकट कूप`, `03 Wiki/ज्ञानकोश`, `04 Fixes/उपाय`, `05 Mud Window/मड सीमा`, `06 Checker/मिलान`, `07 Copilot/सहायक`, `08 Brief/सार`, `09 Accuracy/सटीकता`.
  - A **Ctrl+K command palette** handles quick jumps and search.
- **Sheet header** (a single line):
  - left: small wordmark (a drop-shaped mark cut by horizontal strata lines) + screen title
  - right: EN/हिं, A- A A+, contrast toggle, user chip
- **Sheet footer:** `Decision support only – the engineer decides. Data: public Equinor Volve dataset (stand-in).`
- **Spacing:** 32px gutters and plenty of empty paper. **Max 3 zones per screen.**
- **Rig mode (Command screen only):**
  - ISA-101 dark: bg #1E1F21, panels #2A2B2E, text #D9D6CF.
  - Normal values are grey; only abnormal values get colour (red #E0543A, amber #E0A93A).
  - Larger numbers, thicker lines. Keep the REPLAY stamp and the tricolour hairline.
- **Accessibility (GIGW-inspired):**
  - text-size controls
  - high-contrast mode
  - keyboard navigation for the tabs
  - visible focus rings
  - WCAG AA contrast
  - never rely on colour alone (always pair it with a glyph or text)

### 11.5 Components (`components/kk/`)
| Component | Purpose |
|---|---|
| `FileFrame` | desk + file board + file number + sheet + tricolour hairline + footer |
| `IndexTabs` | right-edge binder tabs (keyboard accessible) |
| `CommandPalette` | Ctrl+K |
| `Stamp` | flat circular or rectangular rubber-stamp mark (APPROVED green, REPLAY amber, RETURNED red); Courier Prime text; slight rotation (−4°) allowed |
| `NoticeSlip` | hazard card with a 3px coloured left rule, title, big mono probability, range + n_eff line, and actions |
| `LithologyColumn` | depth-scaled formation column with hatch patterns, bit marker, and target brackets |
| `CurveTrack` | mud-log style parallel curve track sharing the depth or time axis; normal band shaded; abnormal segments in `--hazard` |
| `SourceFootnote` | tiny superscript marker; hover opens a paper slip with the verbatim source text + ref |
| `IntervalBar` | point + lower-bound whisker (used in the ledger); no fat bars |
| `NotingSheet` | ruled paper with numbered paras (author, role, note, date) |
| `Register` | plain ruled table (government register look): mono numbers, no zebra stripes, thin rules |
| `Drawer` | right-side slide-over for details (keeps screens clean) |
| `EmptyState` | "Insufficient evidence" / "Not evaluated" with an explanation, never blank |

### 11.6 Screens (each lists its max-3 zones)

**01 Command** (question: *what's coming next and what should I do?*)
- **Zone A:** a single status line: Well · `Stamp REPLAY` · Bit depth MD/TVD · Current formation.
- **Zone B (60%):** mud-log view: depth scale, `LithologyColumn`, and 3 `CurveTrack`s (Torque, Pit volume, Mud weight). Red bit marker; red bracket at the next hazardous formation top.
- **Zone C (40%):** one `NoticeSlip` for the top look-ahead hazard, e.g. "LOST CIRCULATION · Hugin · in 148 m", big "58%", "range 39–75% · evidence 5 wells". Then "What worked before" (3 ledger rows with `IntervalBar`) and two buttons: View sources, Open wiki.
- **Behind a click:** drawer "Offset wells (7) ▸" (mini map + list), and further alerts.
- **Toggle:** Rig mode.

**02 Offsets** (question: *what happened in nearby wells, by layer?*)
- **Zone A:** toolbar: radius, "Align: MD | TVD | Formation", hazard filter chips.
- **Zone B:** correlation panel with up to 6 `LithologyColumn`s side by side, dashed tie-lines between formation tops, event glyphs (▲ losses, ◆ kick, ■ stuck pipe, ○ cementing), and distance + similarity in each header.
- **Zone C:** `Drawer` showing the selected event's verbatim source excerpt.
- **Map:** a small toggle card, "Map view", swaps Zone B to a muted paper-style map with the radius circle.

**03 Wiki** (government file noting)
- **Zone A (64%):** the document. Ref no. + version, `Stamp APPROVED` (name + date), trust bar, sections (Summary, Known hazards, What worked, Casing & cement notes, Related wells), and `SourceFootnote`s on every sentence.
- **Zone B (36%):** `NotingSheet`, e.g. "1. Draft compiled from 23 sources – System", "2. Corrected loss depth – A. Sharma", "3. Approved – R. Das". Approve / Edit / Return actions.
- **Behind a click:** page index (Ctrl+K or an "Index ▸" drawer), "Pending in tray (n)", version diff (added text underlined green, removed text struck through red).

**04 Fixes** (question: *what actually worked?*)
- **Zone A:** selectors: hazard, formation, scope.
- **Zone B:** a `Register` with columns Fix · Cases · Worked · Success · Lower bound · Median time · Made worse, each row with an `IntervalBar`. Rows with n < 3 are tagged "anecdotal"; "Made worse" > 0 shows in red.
- **Zone C:** the expanded row shows an episode timeline of report cards (Day N event → action → outcome), each with a source.

**05 Mud Window**
- **Zone A:** depth-vs-ppg chart on log paper. Hatched safe band, evidence glyphs (△ LOT/FIT, ▲ losses, ◆ kicks), the active well's MW line, and an amber segment where it runs close to the edge.
- **Zone B:** a thin `LithologyColumn` aligned to depth.
- **Zone C:** a "Casing & cement lessons" `Register`.
- If the data can't support it: an `EmptyState` explaining why.

**06 Checker**
- **Zone A:** summary line (Open / Resolved / Avg trust).
- **Zone B:** a conflicts `Register`.
- **Zone C:** the selected conflict as two source excerpts side by side, with actions Accept A / Accept B / Mark uncertain + reviewer note.

**07 Copilot** (research style, not a bubbly chatbot)
- **Zone A (70%):** Q&A as document text with footnote chips, and a collapsible "Method" block listing the tool steps.
- **Zone B (30%):** "Sources used", plus suggested questions.
- Refusals appear in a plain bordered box: "No evidence found in the records."

**08 Brief**
- **Zone A (35%):** form: map pick, target depth, optional tops, radius.
- **Zone B (65%):** A4 preview formatted as an official office document: ref no. KPK/PDB/2026/NNN, date, subject, distribution list, formation column, hazard table, mini mud window, sources, and signature blocks (Prepared (system) / Reviewed / Approved).
- Buttons: Download PDF, Send for review.

**09 Accuracy** (honesty page, audit-statement look)
- **Zone A:** 4 plain figure blocks (wells, report entries, events, approved wiki pages).
- **Zone B:** `Register` of data sources (licence, records, date loaded).
- **Zone C:** `Register` of measured accuracy (metric, value, n, "how measured"), plus "Known limitations". Missing evals show "Not evaluated".

### 11.7 Hard content rules for UI
- Never show "Oil India Limited" as the issuer, never use "Confidential/गोपनीय", never use the Oil India logo, and never use the State Emblem. Always say "Prototype for Oil India Limited · SIH 2026".
- Never display metrics we don't compute (UCS, friction angle, geomechanics, etc.).
- Never claim Assam or Indian data. Wells shown are Volve/FORGE, with their true locations.
- Demo names such as "R. Das" and "A. Sharma" are **placeholders** configured in `config/default.yaml → demo.users` and labelled "demo user" on the Accuracy page.
- Stitch mockups in `design/stitch/` are **visual reference only**. Their numbers are fake and must never be copied into code.

---

## 12. CONFIG DEFAULTS (`config/default.yaml`)

```yaml
units: {depth: m, mud_weight: ppg, volume: bbl}
extract: {review_threshold: 0.6, mw_range_ppg: [7, 20]}
episodes: {window_h: 72}
ledger: {min_n_display: 3, z: 1.96, partial_credit: 0.5}
offsets: {default_radius_m: 10000, D_m: 5000, w_geo: 0.4, w_strat: 0.4, w_depth: 0.2}
hazard: {prior_strength: 2, min_neff: 3, ci: 0.8, alert_threshold: 0.4}
anomaly: {window_s: 300, z_thresh: 3.5, cusum_k: 0.5, cusum_h: 5}
lookahead: {lookahead_m: 150, cooldown_s: 120}
auditor: {depth_tol_m: 30, time_tol_min: 60}
replay: {default_speed: 60}
llm: {provider: gemini, fallback: groq, max_retries: 1, temperature: 0}
embeddings: {model: BAAI/bge-small-en-v1.5, dim: 384}
ui: {max_zones: 3, file_prefix: "KPK", default_lang: en}
demo: {users: [{name: "R. Das", role: "Senior Reviewer"}, {name: "A. Sharma", role: "Drilling Engineer"}]}
```

---

## 13. DEMO FLOW (5 minutes; everything must work for this)

1. **Tab 09 Accuracy:** "Real public data: N wells, N report entries, N events; measured accuracy X% (n = …)."
2. **Tab 01 Command:** pick the active well; start REPLAY.
3. About 150 m before a risky formation, the `NoticeSlip` appears: hazard, probability ± range, n_eff, best fix with success fraction.
4. Click **View sources**. The exact DDR line appears in a paper slip.
5. **Open wiki** → the formation page: citations, APPROVED stamp, noting sheet, version diff.
6. **Tab 04 Fixes:** a fix that *made things worse* ("what actually worked" moment).
7. **Tab 05 / 06:** mud window + one report conflict (if built).
8. **Tab 07 Copilot:** one cited answer + one correct refusal.
9. **Tab 08 Brief:** download the official-style PDF.
10. **Close:** "Oil India can swap in its own WCR/DDR/eRTMAC streams without changing the schema."

---

## 14. PITCH LINES

- "Others search your PDFs. Kupakosh **remembers**: compiled, engineer-approved, and it gets smarter with every correction."
- "Others tell you what happened. We tell you **what actually worked**, and how often."
- "We don't just read reports. We tell you **when they disagree**."
- "When we don't know, we say so: a probability with its uncertainty, or 'insufficient evidence'."
- "Designed like the files Oil India engineers already use: mud logs and file notings."

---

## 15. BUILD PHASES (each ends with tests + stop for my confirmation)

| Phase | Deliverable | Acceptance |
|---|---|---|
| **P0 Data spike** | Samples: 20 Volve DDR XML, 1 real-time well, Sodir wellbore + tops CSV, 1 FORGE well, 3 NOPIMS WCR PDFs. `scripts/inspect_data.py` reports: activity fields, % comments with depth, LOT/FIT mentions, pit volume/ROP non-zero, DDR ↔ real-time well overlap | `docs/DATA_REPORT.md` + **go/no-go for USP3 & USP4** |
| **P1 Infra** | docker-compose, Alembic schema (section 7), config loader, health endpoint, Makefile (`up`, `migrate`, `bootstrap`, `test`) | `make up && make migrate && make test` green |
| **P2 Ingestion** | Sodir → wells/tops; Volve DDR XML → documents/activities/passages; real-time → samples; trajectories → surveys (+TVD, minimum curvature); FORGE; PDF text/OCR | Counts on `/api/status`; well-ID tests |
| **P3 Extraction** | Rules + LLM → events, actions, pressure tests, casing; confidence; review flags | Precision on `events_gold.csv` reported |
| **P4 Episodes + Ledger** | Linker + ledger API | Precision on `episodes_gold.csv` reported |
| **P5 Offsets + Hazard** | Similarity API, Bayesian posteriors, LOO validation | Brier vs baseline stored |
| **P6 Wiki** | Compiler, citation post-check, git store, noting + review API | Uncited sentences rejected; review creates commits + noting paras |
| **P7 USP3/USP4** *(if P0 = go)* | Mud window + auditor | Visible with sources |
| **P8 Live** | Replay WS, anomaly, look-ahead | Demo steps 2–4 work |
| **P9 Copilot** | Agent + tools + eval | Citation + refusal accuracy reported |
| **P10a UI foundation** | tokens.css, fonts, `FileFrame`, `IndexTabs`, `CommandPalette`, `Stamp`, `NoticeSlip`, `LithologyColumn`, `CurveTrack`, `SourceFootnote`, `Register`, `Drawer`, `EmptyState`; i18n EN/HI | Storybook-like `/dev/components` page renders all components; contrast check passes |
| **P10b Screens** | 01–09 per section 11.6, Rig mode | Demo flow (section 13) runs with no console errors; every screen ≤ 3 zones; Playwright smoke test |
| **P11 Brief** | Official-style pre-drill PDF | PDF with sources + signature blocks |
| **P12 Polish** | README, `docs/ARCHITECTURE.md`, `docs/LIMITATIONS.md`, `docs/WIKI_FORMAT.md`, screenshots | Fresh clone → `make bootstrap` works |

---

## 16. EVAL FILES (hand-labelled from real reports; never fabricated)

- `data/eval/events_gold.csv`: 50 DDR lines with the true hazard, depth, quantity, and MW.
- `data/eval/episodes_gold.csv`: 30 episodes, each with its event ref, actions, outcome, and outcome ref.
- `data/eval/copilot_questions.csv`: 30 questions with expected sources, 5 of which should be refused.
- If a file is missing, the eval reports **"Not evaluated"** and the UI shows that. Never invent a score.

---

## 17. ENVIRONMENT

`.env.example`:
```
DATABASE_URL=postgresql+psycopg://kupa:kupa@localhost:5432/kupakosh
GEMINI_API_KEY=
GROQ_API_KEY=
WIKI_REPO_PATH=./wiki
DATA_DIR=./data
```

---

## 18. FIRST PROMPT TO START

> Read SPEC.md fully. Start Phase P0 (data spike). Show me the plan first and wait for my go.
