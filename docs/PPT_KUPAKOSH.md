# Kupakosh: SIH 2026 idea-submission deck (PS 26121)

This follows the NiyamKosh deck: same 6 slides, same layout and same template. It has two parts:
- **Part A** is the content of every slide, text ready to paste.
- **Part B** is copy-paste prompts for ChatGPT or Gemini to make each infographic panel in the same visual style.

> **Values below were filled from the live database on 27 Sept 2026** (final all-country rebuild with OCR). If the data changes,
> re-copy them from the **09 Accuracy** page.
>
> **Numbers rule (same as the product):** every number in this deck is measured from our database or
> taken from a cited public document. Figures marked ⟦live⟧ must be copied from the app's
> **09 Accuracy** page on the day you export the deck. Never round a figure up. Never add a number
> that is not on the Accuracy page or in a reference.

---

## v2 update (27 Sept 2026): use these where they differ from Part A

**New headline USPs (put them on slide 2, "The idea", and the comparison table):**
1. **Hindsight Test: it proves itself on real history.**
   - Each real well is replayed *blind*: its own reports are hidden and alerts come from other wells only. Then the page reveals what really happened.
   - **Headline trio (all blind, cross-validated, on 438 real recorded problems in 299 wells):**
     - **86 % ranking accuracy (AUC 0.86, 95 % range 0.84–0.88):** a layer that really had a problem is ranked above one that did not 86 times in 100. The field average alone manages 70 %; random is 50 %.
     - **83 % of problems happened in a layer Kupakosh had put on alert before the bit arrived** (15 alerts per well; 13 % of layer×hazard cells).
     - **74 % right hazard in the layer's top 3** of 8 (random 38 %, field average 61 %).
   - Stricter: with about 6 alerts per well, the exact hazard was forewarned for 193 of 438 (44 %), a median 356 m ahead. The field average with the same alerts gets 87; blind pre-drill 186.
   - How: a ranker trained on other wells only (grouped 5-fold cross-validation, sidetracks kept together); live mode also reads the well's own reports for depths already drilled; the alert threshold is set on the training wells for a fixed budget of 6 alerts per well.
   - Strict alerts (posterior ≥ 40 %) remain available: 11 of 14 right (79 %), 73× lift, but they forewarn only 15.
   - **Blind watch-list:** each well's own top-5 layer risks (about 4 % of its layer×hazard cells) already held **137 of 438 real problems (31 %)**, against 31 by chance (**4.4×**). The top 10 held 44 % against 14 %.
   - Honest lines: strict alerts (≥ 40 %) forewarned only 15 of 438. Ranking layers by their field-wide rate alone catches about the same as the watch-list (133/438); the value is Kupakosh's compiled memory of every layer.
   - No public PS 26121 project shows blind, measured proof (`docs/COMPETITORS.md`).
2. **India Analogs.**
   - For an Indian basin, the rock types are taken from its NDR summary (cited). Kupakosh then finds the same rock at the same depth in **thousands of public wells worldwide** and shows what went wrong and what fixed it.
   - It is labelled "analogue evidence, not Indian wells", and it is usable on day one, before Oil India loads its own data.
3. **3D subsurface and world map.**
   - All **97,078** located wells on the map.
   - Offset wells in 3D with formation tops and problem markers; click a marker to open its source.
4. **"Why this number?"** on every probability: the evidence wells, the field average, n_eff and the range. This answers the explainability that competitors show with SHAP.

**Comparison table: add these rows**
| Feature | eRTMAC | PDF search / RAG | Manual review | KUPAKOSH |
|---|---|---|---|---|
| Blind proof on real history (Hindsight) | ✗ | ✗ | ✗ | ✓ |
| Indian basins answered from global analogues | ✗ | ✗ | ✗ | ✓ |
| 3D subsurface + world map of wells | ✗ | ✗ | ✗ | ✓ |
| "Why this number?" on every risk | ✗ | ✗ | ✗ | ✓ |

**Screenshots for v2** (`docs/screenshots/`):
- 00-home.png
- 13-hindsight.png: slide 2, "One alert" alternative, or slide 3, "Technical validation"
- 10-map.png
- 11-subsurface.png
- 12-analogs.png
- 01-command-replay.png

**Image prompt: Hindsight panel (add to Part B)**
```
[Style block]
Title in bold navy: "HINDSIGHT TEST". Subtitle in grey: "Each real well replayed blind — its own reports hidden".
Left: a tall vertical depth strip (0 m at the top, down to 3,000 m) with two lanes labelled "ALERTS (blind)" and "WHAT REALLY HAPPENED".
The alerts lane has red dots with small labels. The real lane has markers joined to the alerts by dashed brackets labelled "lead".
Right: two stat cards. The first, with a teal top border: big gradient "193 / 438 · 44%" and a chip "14.8× vs silent layers", three small tiles "356 m median warning ahead", "6.1 alerts per well", "1 in 10 alerts matched a record", then four coloured bars: Kupakosh live 193, Kupakosh blind pre-drill 186, field average same alerts 87 (grey), strict alerts 15 (amber). Above both cards: three big tiles "86% ranking accuracy (AUC)" (blue), "83% problem layers flagged ahead" (green), "74% right hazard in top 3" (violet).
The second, with a teal border: big gradient "137 / 438 · 31%" and a chip "4.4× chance", "real problems on the blind top-5 watch-list", then three coloured bars (top 3 / 5 / 10 vs a black "random" tick) and small chips "≥40%: 15/438, 79% right".
```

## Part A: slide content

### Slide 1: Title (same template as NiyamKosh slide 1)

- **Problem Statement ID:** 26121
- **Problem Statement Title:** ⟦copy the exact title from the SIH 2026 portal⟧. It is Oil India Limited's problem statement on offset-well data, drilling-event knowledge and real-time risk alerts.
- **Theme:** ⟦copy from portal⟧
- **PS Category:** Software
- **Team ID:** ⟦fill⟧
- **Team Name:** The RAGnarok

The right-hand graphic stays the same as in NiyamKosh (SIH bulb). Keep the RAGnarok logo top-left and the SIH 2026 logo top-right, as on every slide.

---

### Slide 2: "Kupakosh: Oil India's Memory of Every Well"

Four blocks, same positions as NiyamKosh slide 2.

**THE PROBLEM** (top-left, 3 orange-rule cards and a flow strip)
1. **Lessons are locked in PDFs.** Offset-well history sits in daily drilling reports and completion reports, not in any searchable system.
   - Sub-line: "eRTMAC shows the live well, not what happened in the wells around it."
2. **Rigs lose a fifth of their time.** Rig non-productive time was **19–23 %** in 2010–14. The bulk of the idle time, worth **₹6,418 crore**, was within the company's control.
   - Source: CAG Report 39 of 2015, on ONGC rigs.
3. **The same problem repeats in the same layer.** Losses, kicks and stuck pipe come back at the same formation in nearby wells.
   - Sub-line: "Baghjan-5, 2020: blowout, then fire on 9 June; two OIL firemen died." (Source: PIB)
- **Flow strip (icons):** OLD REPORT → NOT FOUND → SAME PROBLEM → LOST RIG DAYS

**THE IDEA: KUPAKOSH** (top-right, 3 green-rule cards and a flow strip)
1. **Warns before the bit reaches the danger layer.** A replay of real rig data triggers an alert about 150 m ahead, with probability, range and number of wells.
2. **Shows what actually worked, and how often.** Problem → action → outcome, ranked by success rate. Fixes that made things worse are shown in red.
3. **An engineer-approved Well Wiki.** Every sentence cites the exact report line. Reviewers approve pages in a government file-noting style, and every version is kept.
- **Flow strip (icons):** READ REPORTS → REMEMBER → WARN AHEAD → SAFER WELL

**WHY KUPAKOSH** (bottom-left, comparison table, same look as NiyamKosh)

| Feature | eRTMAC (live view) | PDF search / RAG chatbot | Manual offset review | **KUPAKOSH** |
|---|---|---|---|---|
| Live rig data on screen | ✓ | ✗ | ✗ | ✓ (replay) |
| History of nearby wells | ✗ | ✓ | ✓ | ✓ |
| Which fix worked, and how often | ✗ | ✗ | ✗ | ✓ |
| Risk with a range, or "insufficient evidence" | ✗ | ✗ | ✗ | ✓ |
| Engineer-approved knowledge with version history | ✗ | ✗ | ✗ | ✓ |
| Flags when reports disagree | ✗ | ✗ | ✗ | ✓ |
| Every answer cites the exact report line | ✗ | ✓ | ✗ | ✓ |

(Only write ✓ or ✗ where the column truly does or does not do it. Do not name commercial products we have not tested.)

**ONE ALERT, AS KUPAKOSH SHOWS IT** (bottom-right, an annotated screenshot with 6 numbered callouts)
- Use a real screenshot of **01 Command** during the replay of well **16B(78)-32** (Utah FORGE, a stand-in for an Oil India well).
- Callouts:
  1. **REPLAY OF REAL RIG DATA.** Bit depth and current formation. Source: Pason sensor log.
  2. **HAZARD AHEAD.** Stuck pipe in basin fill, **55 %** (range 29–80 %), evidence **4.8** wells. Source: offset wells.
  3. **WHAT WORKED BEFORE.** The top 3 fixes with "worked k of n". Source: mitigation ledger.
  4. **EXACT REPORT LINE.** Click to see the daily-report sentence. Source: DDR page and line.
  5. **APPROVED WIKI PAGE.** The formation page carries a noting sheet. Source: reviewer and date.
  6. **SAYS WHEN IT DOESN'T KNOW.** "Insufficient evidence" instead of a guess. Source: the hazard model.

---

### Slide 3: Technical Approach (same 3 columns as NiyamKosh slide 3)

**Left: MEASURED, NOT CLAIMED** (dark panel, 5 orange number rows)

| Big number | Text |
|---|---|
| **92.1 %** | of extracted drilling events were correct (n = 38 labelled report lines) |
| **92.1 %** | of labelled drilling problems were found (n = 38) |
| **78.9 %** | of problem → fix → outcome chains were linked correctly (n = 19) |
| 0 | answers without a source: every copilot sentence cites a report line |
| **30 of 30** | out-of-scope and test questions answered or refused correctly ("No evidence found in the records") |

- Footer line: *"Every figure recomputed from the database on load. Labels are pending engineer verification."*
- **Say it honestly:** the hazard model is **not yet better than the base rate** (the Brier score is the same). That's why it always shows a range and n_eff. Put this on the Accuracy slide or in the speaker notes. Never hide it.

**Middle: KUPAKOSH SYSTEM ARCHITECTURE** (two lanes, like NiyamKosh)
- **Ingestion pipeline** (runs once, and again on each upload):
  1. **Harvest:** 8 countries of public well data, plus report upload.
  2. **Read:** PDF text, sentence by sentence, each with page and line.
  3. **Extract:** rules and, when enabled, an LLM with verbatim-evidence checks. Produces events, actions and LOT/FIT.
  4. **Link episodes:** problem → action → outcome within 72 h.
  5. **Compile wiki:** only cited sentences, with a git version for every change.
  - Footer: *"Writes only what it can cite. A new report sends affected pages back for review."*
- **Runtime path** (per well, live):
  - **Replay / eRTMAC stream** → **Look-ahead** (next 150 m of formations) → **Intelligence**, which has three boxes:
    - Offset wells (radius + similarity)
    - Bayesian hazard (probability, 80 % range, n_eff)
    - Live anomaly (torque, pit volume)
  - Sub-line: *"The model gives a probability; the engineer decides."*
- **Knowledge core** (dark pill): WELL WIKI | MITIGATION LEDGER | EVIDENCE INDEX (keyword + meaning search)
- **Outputs** (3 boxes):
  - LOOK-AHEAD ALERT: hazard, range, best fix
  - PRE-DRILL BRIEF: official-style PDF
  - REPORT CHECKER: where the reports disagree

**Right: TECHNICAL VALIDATION: Offset-Well Map** (like the co-citation graph)
- Use a real screenshot of **02 Offsets** (map view or correlation panel). It shows wells within the radius, formation tops joined by tie-lines, and hazard glyphs by depth.
- Three icon labels: **Offset Wells** (radius + similarity) · **Evidence Search** (keyword + meaning) · **Bayesian Hazard** (+ ledger)
- Line: *"Wells, layers and past problems correlated by depth and formation, the way a drilling engineer reads a mud log."*
- Pill: **REAL DATA • REAL WELLS • WORKING PIPELINE**

**Bottom strip, tech logos (only what we use):** Python · FastAPI · SQLite (PostgreSQL + PostGIS target) · Next.js · MapLibre · Hugging Face (bge-small embeddings) · pdfplumber · Git · Docker (target) · GitHub

---

### Slide 4: Feasibility and Viability

**CURRENT SCALE** (4 numbers; measured from the live database, not estimated)

| Number | Label |
|---|---|
| **96,418** | WELLS INDEXED (8 countries) |
| **2,24,016** (224,016) | REPORT SENTENCES, EACH CITABLE |
| **1,54,058** (154,058) | FORMATION TOPS |
| **2,623** | DRILLING EVENTS EXTRACTED (772 trusted, the rest in the review queue) |

**DEPLOYMENT MODEL: "Runs beside eRTMAC, inside Oil India"** (replaces NiyamKosh's business model)
- **Value proposition (dark bar):** "Fewer lost rig days: know the next layer before the bit does."
- **Users (left):**
  - Drilling engineers: pre-drill planning
  - Rig-site supervisors: live look-ahead
  - Geologists: formation correlation
  - HSE and management: lessons, audits
- **Learning loop (centre):** DRILL → REPORT → EXTRACT → APPROVE → WARN → (back to DRILL). Every new well makes the next one safer.
- **Cost structure (bottom):**
  - Local models: no per-query fee
  - Runs on an ordinary laptop or server
  - Only recurring cost: hosting and support
- **Go-to-market timeline:**
  - YEAR ZERO: pilot on one Oil India field (NDR data)
  - YEAR ONE: eRTMAC stream integration
  - YEAR TWO: all fields, own DDR archive

**RISKS AND MITIGATION** (right, 4 rows: risk card → mitigation card)

| Risk | Mitigation |
|---|---|
| **Well data is restricted.** Oil India and NDR well files need authorisation. | **Same schema, swap the data.** Built on public stand-ins from 8 countries. Oil India data loads with no code change (upload or bulk). |
| **Scanned old reports.** Many old DDRs are images. | **Read with OCR, confidence kept.** Tesseract reads scanned pages and stores a confidence for each page. Events from low-quality scans get lower confidence and go to the review queue. |
| **AI might invent facts.** | **Cite or stay silent.** Evidence must be a verbatim quote. Uncited sentences are rejected. The copilot refuses when there's no record. |
| **Engineers must trust it.** | **Engineer approves.** A noting-sheet review, a git history for every change, and a probability with its range and "insufficient evidence". |

---

### Slide 5: Impacts and Benefits (same two-column arrow cards)

**IMPACTS (by user)**
- **Drilling Engineers:** Plan the next well from what happened in the wells around it, layer by layer, in minutes instead of days of reading reports.
- **Rig-site Supervisors:** Warned about 150 m before a known danger formation, with the fix that worked most often nearby.
- **Oil India & PSUs:** Knowledge stays when experts retire. The PM asked that the Baghjan lessons "be studied and documented so that learnings become useful in future" (PIB, 2020).
- **HSE & Regulators:** Report conflicts are flagged, and every alert traces to its source line, which makes audits and inquiries faster.

**BENEFITS**
- **Transparency:** Every sentence, alert and number names its source (report, page, line), so it can be checked.
- **Operational:** Runs beside eRTMAC without changing it. Works offline on an ordinary laptop, and upload a new report to update it.
- **Honest risk:** A probability with its range and evidence count, or "insufficient evidence", never a false certainty.
- **What actually worked:** Fixes are ranked by success rate with a lower bound. Fixes that made things worse are shown.

**Bottom line (bold):** "96,418 wells, 2,24,016 report sentences, 8 countries. The challenge isn't data, it's remembering it at the right depth. Kupakosh turns old drilling reports into a warning before the bit reaches the danger layer."

---

### Slide 6: Research and References (4 coloured boxes, 2 references each, as in NiyamKosh)

**POLICY & SAFETY FOUNDATION** (blue)
- **01 · Press Information Bureau: Baghjan-5 well fire (June 2020).** Well caught fire on 9 June 2020 and two OIL firemen died; the PM directed that the lessons be documented.
  - pib.gov.in/PressReleasePage.aspx?PRID=1632427 · pib.gov.in/PressReleasePage.aspx?PRID=1630694
- **02 · Comptroller & Auditor General: Utilisation of Rigs, Report 39 of 2015.** Rig non-productive time of 19–23 % (2010–14), the bulk of it controllable.
  - cag.gov.in/webroot/uploads/download_audit_report/2015/Union_Commercial_Performance_Utilisation_Rigs_39_2015.pdf

**INDIAN E&P DATA** (orange)
- **03 · DGH National Data Repository (NDR): sedimentary basins of India and data policy.** 23 basin summaries used for Indian geology and exploration facts.
  - ndrdgh.gov.in/NDR/
- **04 · Oil Industry Safety Directorate (OISD): safety alerts.** Incident root causes and recommendations across Indian oil & gas.
  - oisd.gov.in

**STAND-IN WELL DATA** (green)
- **05 · Norwegian Offshore Directorate (Sodir): FactPages.** Wellbores, formation tops, casing, LOT/FIT and well histories (NLOD 2.0).
  - factpages.sodir.no
- **06 · Utah FORGE (US DOE GDR): daily drilling reports and rig sensor data (CC-BY 4.0).** Wells 16A/16B(78)-32, the source of the replay.
  - gdr.openei.org/submissions/1516

**METHODS** (purple)
- **07 · Wilson, E. B. (1927). Probable inference, the law of succession, and statistical inference. JASA 22(158).** The lower bound used to rank fixes.
- **08 · Gelman et al., *Bayesian Data Analysis* (3rd ed.), Beta-Binomial model.** Hazard probability with a credible range.
  - Optional swap: add **BSEE (US) offshore incident data** (data.bsee.gov) or **NLOG (Netherlands)** if you'd rather show more data sources.

---

### Ready-made screenshots (real app, 26 Sept 2026)
All in `docs/screenshots/`, regenerated with `cd frontend && node scripts/screenshots.mjs` (API and web must be running):
- `01-command-replay.png`: Slide 2, "One alert" panel (stuck pipe, basin fill, 55 %, range 29–80 %, 4.8 wells)
- `02-offsets.png` and `02-offsets-map.png`: Slide 3, "Technical validation"
- `07-copilot.png`: one cited answer and one refusal
- `03-wiki.png`, `04-fixes.png`, `05-mudwindow.png`, `06-checker.png`, `08-brief.png`, `09-accuracy.png`: backups or appendix

## Part B: prompts for ChatGPT or Gemini (to make the panels look like NiyamKosh)

### How to use (read once)
1. **Generate panels, not whole slides.** Make one infographic per prompt (for example "The Problem" block). Then place the panels on the slide template in PowerPoint or Google Slides. Add the logos and the slide title yourself.
2. **ChatGPT (GPT-4o image or newer) renders text most reliably.** Gemini also works well; ask it to "keep the text exactly as written".
3. **Always check every word and number after generating.** Image models misspell and change digits. If a number is wrong, regenerate or cover it with a PPT text box. The numbers come from Part A, never from the image model.
4. For screenshots (Slide 2 bottom-right, Slide 3 right), use **real screenshots of our app**. Only the callouts and frame come from the prompt.

### Style block (paste at the start of every prompt)
```
Style: clean flat infographic panel for a government hackathon presentation, 16:9, white background, 
thin-line vector icons (1.5px stroke), rounded rectangle cards with a soft pastel fill and a thick left 
accent rule, generous spacing, modern sans-serif (like Inter or Poppins), headings in dark navy #1F3A5F, 
accents burnt orange #C0561B and deep green #2E7D5B, soft peach #FBE9DF and mint #E6F2EC card fills, 
no gradients, no 3D, no photos, no people's faces, no company logos, no watermark. 
Render ALL text exactly as written below, spelled exactly, nothing added.
```

### Prompt 1: Slide 2 "THE PROBLEM" panel
```
[Style block]
Panel title at top-left in wide-spaced orange capitals: "THE PROBLEM".
Three stacked cards, each with a peach fill, a thick burnt-orange left rule and a round peach icon on the left:
Card 1 icon: a stack of PDF files with a padlock. Bold: "Lessons are locked in PDFs". Small grey: "eRTMAC shows the live well, not the wells around it".
Card 2 icon: a drilling rig with a pause symbol. Bold: "Rigs lose a fifth of their time". Small grey: "Rig non-productive time 19–23% (CAG, 2015)".
Card 3 icon: rock layers with a repeating warning triangle. Bold: "The same problem repeats in the same layer". Small grey: "Losses, kicks and stuck pipe return in nearby wells".
Below the cards, a light peach strip with four small line icons joined by orange arrows, captions in small capitals:
"OLD REPORT" (document) -> "NOT FOUND" (magnifier with an X) -> "SAME PROBLEM" (warning triangle) -> "LOST RIG DAYS" (calendar with a clock).
```

### Prompt 2: Slide 2 "THE IDEA: KUPAKOSH" panel
```
[Style block]
Title in wide-spaced dark-teal capitals "THE IDEA" followed by a dark rounded pill containing white text "KUPAKOSH".
Three stacked cards with a mint fill, a thick deep-green left rule and a round mint icon on the left:
Card 1 icon: a drill bit above layered rock with a bell. Bold: "Warns before the bit reaches the danger layer". Small grey: "About 150 m ahead, with probability, range and number of wells".
Card 2 icon: a checklist with a trophy. Bold: "Shows what actually worked, and how often". Small grey: "Problem → action → outcome, ranked; fixes that made it worse in red".
Card 3 icon: an open book with an approval stamp. Bold: "An engineer-approved Well Wiki". Small grey: "Every sentence cites the exact report line; every change is kept".
Below, a light mint strip with four icons joined by green arrows, captions in small capitals:
"READ REPORTS" (document) -> "REMEMBER" (database) -> "WARN AHEAD" (bell) -> "SAFER WELL" (shield with a check).
```

### Prompt 3: Slide 2 "WHY KUPAKOSH" comparison table
```
[Style block]
Title in wide-spaced navy capitals: "WHY KUPAKOSH".
A clean comparison table on a white card. The header row is light grey, except the last column, which is a dark teal-navy
block with white bold text "KUPAKOSH" that extends slightly above and below the table (highlighted column).
Columns: "Feature" | "eRTMAC (LIVE VIEW)" | "PDF SEARCH / RAG CHATBOT" | "MANUAL OFFSET REVIEW" | "KUPAKOSH".
Rows (use a pink circle with a red X for no, a pale-green circle with a green tick for yes; the Kupakosh column uses white ticks in green circles):
"Live rig data on screen": yes, no, no, yes
"History of nearby wells": no, yes, yes, yes
"Which fix worked, how often": no, no, no, yes
"Risk with a range or 'insufficient evidence'": no, no, no, yes
"Engineer-approved, versioned knowledge": no, no, no, yes
"Flags when reports disagree": no, no, no, yes
"Cites the exact report line": no, yes, no, yes
Thin grey row dividers, no zebra stripes.
```

### Prompt 4: Slide 2 "ONE ALERT, AS KUPAKOSH SHOWS IT" (callout frame around our screenshot)
```
[Style block]
Title in bold navy capitals: "ONE ALERT, AS KUPAKOSH SHOWS IT". Subtitle in grey: "A real replay. Every number is marked, and every number names its source".
Left 45%: a light-grey rounded placeholder rectangle labelled "SCREENSHOT" (I will paste the real screenshot here).
Six small numbered circles (1–6) sit on the placeholder's right edge, joined by thin coloured elbow lines to six
stacked callout cards on the right. Each card has a coloured left rule, a numbered circle, a bold capital title, a grey line, and a small italic source at the top-right:
1 navy: "REPLAY OF REAL RIG DATA" / "Bit depth and current formation" / source: "rig sensor log"
2 orange: "HAZARD AHEAD" / "Probability, range and evidence wells" / source: "offset wells"
3 green: "WHAT WORKED BEFORE" / "Top fixes: worked k of n" / source: "mitigation ledger"
4 purple: "EXACT REPORT LINE" / "The daily-report sentence, one click away" / source: "DDR page and line"
5 green: "APPROVED WIKI PAGE" / "Formation page with noting sheet" / source: "reviewer and date"
6 teal: "SAYS WHEN IT DOESN'T KNOW" / "'Insufficient evidence', not a guess" / source: "hazard model"
```

### Prompt 5: Slide 3 "MEASURED, NOT CLAIMED" dark panel
```
[Style block]
A tall dark navy rounded panel containing a white rounded card. At the top, a small orange clipboard-with-tick line icon.
Bold heading: "MEASURED, NOT CLAIMED". Grey text: "Tested on real drilling-report lines labelled for the task".
Five rows. Each row has a big bold burnt-orange number on a pale peach block at the left and dark text on the right:
"[N1]" — "of extracted drilling events were correct"
"[N2]" — "of labelled drilling problems were found"
"[N3]" — "of problem-fix-outcome chains linked correctly"
"0" — "answers without a source: every sentence is cited"
"[N5]" — "out-of-scope questions correctly refused"
At the bottom, a pale grey pill with italic text: "Every figure recomputed from the database on load".
```
(Use [N1] = "92.1%", [N2] = "92.1%", [N3] = "78.9%", [N5] = "30 of 30".)

### Prompt 6: Slide 3 "KUPAKOSH SYSTEM ARCHITECTURE"
```
[Style block] on a very faint engineering grid background.
Title: "KUPAKOSH" in bold navy followed by "SYSTEM ARCHITECTURE" in light grey, with a thin orange underline.
Left column box with a dark header "INGESTION PIPELINE" and a small italic label "RUNS ON UPLOAD". Five stacked white
boxes with line icons, joined by down arrows: "HARVEST" (download), "READ" (document with magnifier),
"EXTRACT" (tag), "LINK EPISODES" (chain links), "COMPILE WIKI" (book with a check).
Footer in small italics: "WRITES ONLY WHAT IT CAN CITE".
Right column box with a dark header "RUNTIME PATH" and the italic label "PER WELL, LIVE": box "REPLAY / eRTMAC STREAM" (signal icon)
-> box "LOOK-AHEAD, NEXT 150 m" (layers icon) -> an orange-bordered box "INTELLIGENCE" containing three small boxes
"OFFSET WELLS", "BAYESIAN HAZARD", "LIVE ANOMALY" and one italic line "THE MODEL GIVES A PROBABILITY, THE ENGINEER DECIDES".
An orange curved arrow from the left column labelled "FEEDS THE SHARED CORE" goes into a large dark rounded pill
"KNOWLEDGE CORE" with three white labels separated by bars: "WELL WIKI" | "MITIGATION LEDGER" | "EVIDENCE INDEX".
Under it, three output boxes with orange top rules: "LOOK-AHEAD ALERT / HAZARD, RANGE, BEST FIX",
"PRE-DRILL BRIEF / OFFICIAL PDF", "REPORT CHECKER / WHERE REPORTS DISAGREE".
```

### Prompt 7: Slide 3 "TECHNICAL VALIDATION" frame (around our Offsets screenshot)
```
[Style block]
A round green icon with a network symbol, then the bold navy title "TECHNICAL VALIDATION" and subtitle "Offset-Well Correlation".
A large light-grey rounded placeholder labelled "SCREENSHOT" (I will paste the real app screenshot).
Below it, three icon + label pairs separated by thin vertical lines: "Offset Wells (radius + similarity)",
"Evidence Search (keyword + meaning)", "Bayesian Hazard (+ ledger)".
A centred navy line: "Wells, layers and past problems correlated by depth and formation."
A pale blue pill at the bottom in bold navy capitals: "REAL DATA • REAL WELLS • WORKING PIPELINE".
```

### Prompt 8: Slide 4 "CURRENT SCALE" and "DEPLOYMENT MODEL"
```
[Style block]
Top: a white card with an orange top rule. Left cell: "CURRENT SCALE" in bold spaced capitals, with grey text "Measured from the
live database, not estimated". Four cells, each with a line icon above a big burnt-orange number and grey caps caption:
(oil-well icon) "96,418" "WELLS INDEXED"; (document stack) "2,24,016" "REPORT SENTENCES"; (rock layers) "1,54,058" "FORMATION TOPS";
(warning triangle) "2,623" "DRILLING EVENTS".
Below: title "DEPLOYMENT MODEL" with the grey subtitle "RUNS BESIDE eRTMAC, INSIDE OIL INDIA". A dark navy rounded bar with a small orange
label "VALUE PROPOSITION" and white bold text "FEWER LOST RIG DAYS" and small text "KNOW THE NEXT LAYER BEFORE THE BIT DOES".
Left list "USERS" with small icons: "DRILLING ENGINEERS / PRE-DRILL PLANNING", "RIG-SITE SUPERVISORS / LIVE LOOK-AHEAD",
"GEOLOGISTS / FORMATION CORRELATION", "HSE AND MANAGEMENT / LESSONS AND AUDITS".
Centre: a circular loop of 5 arrows (navy and orange) with the labels "DRILL", "REPORT", "EXTRACT", "APPROVE", "WARN", and
centre text "LEARNING LOOP / EVERY WELL MAKES THE NEXT SAFER".
Bottom grey bar "COST STRUCTURE": "LOCAL MODELS / NO PER-QUERY FEE", "ORDINARY LAPTOP OR SERVER",
"HOSTING AND SUPPORT / THE ONLY RECURRING COST".
A timeline with 3 dots: "YEAR ZERO / PILOT ON ONE FIELD", "YEAR ONE / eRTMAC INTEGRATION", "YEAR TWO / ALL FIELDS".
```

### Prompt 9: Slide 4 "RISKS AND MITIGATION"
```
[Style block] on a faint grid.
Title "RISKS AND MITIGATION" in bold dark grey. Two small pills: peach "⚠ RISK" and mint "✦ MITIGATION".
Four rows. Each row has a peach risk card, then an orange arrow, then a mint mitigation card. Each card has a small round line icon on top:
1 Risk "WELL DATA IS RESTRICTED" — "Oil India and NDR well files need authorisation"
  → Mitigation "SAME SCHEMA, SWAP THE DATA" — "Built on public data from 8 countries; Oil India data loads with no code change"
2 Risk "SCANNED OLD REPORTS" — "Many old daily reports are images with no text"
  → Mitigation "READ WITH OCR, CONFIDENCE KEPT" — "Scanned pages read by OCR; low-confidence text goes to review"
3 Risk "AI MIGHT INVENT FACTS" — "A wrong depth or hazard is dangerous"
  → Mitigation "CITE OR STAY SILENT" — "Evidence must be a verbatim quote; uncited sentences are rejected"
4 Risk "ENGINEERS MUST TRUST IT" — "An alert nobody believes is ignored"
  → Mitigation "THE ENGINEER APPROVES" — "Noting-sheet review, full version history, and a probability with its range"
```

### Prompt 10: Slide 5 "IMPACTS / BENEFITS"
```
[Style block]
Top: a black target icon with the big bold navy word "IMPACTS" on the left half; an icon of a hand holding coins and a heart with the big
bold navy word "BENEFITS" on the right half.
Left column: four wide pastel rounded banners (peach, rose, sand, sage). Each ends on the right with an arrow-shaped tab holding a
flat colour icon:
"Drilling Engineers:" — "Plan the next well from what happened in the wells around it, layer by layer, in minutes." (icon: engineer with a blueprint)
"Oil India & PSUs:" — "Knowledge stays when experts retire. Baghjan lessons, documented as the PM asked." (icon: government building)
"Rig-site Supervisors:" — "Warned about 150 m before a known danger formation, with the fix that worked most often." (icon: rig with a bell)
"HSE & Regulators:" — "Report conflicts flagged; every alert traces to its source line." (icon: clipboard with a shield)
Right column: four matching banners, arrow tabs on the left:
"Transparency:" — "Every sentence, alert and number names its report, page and line."
"Operational:" — "Runs beside eRTMAC, offline on an ordinary laptop; upload a new report to update."
"Honest Risk:" — "A probability with its range, or 'insufficient evidence', never false certainty."
"What Actually Worked:" — "Fixes ranked by success rate; those that made it worse are shown."
Alternate the banners slightly (zig-zag) like a two-column infographic.
```
(Put the bold bottom line from Part A under this panel as a PPT text box, not inside the image.)

### Prompt 11: Slide 6 "RESEARCH AND REFERENCES"
Tip: don't generate this slide as an image. Build it in PPT (text must be exact and the links clickable). If you want the look, generate only the empty frame:
```
[Style block]
Four large rounded cards in a 2x2 grid on a white background. Each card has a thick left colour rule and a big round coloured icon at the top-left:
blue card (document icon) header "POLICY & SAFETY FOUNDATION",
orange card (drilling-rig icon) header "INDIAN E&P DATA",
green card (map-pin-on-layers icon) header "STAND-IN WELL DATA",
purple card (chart icon) header "METHODS".
Under each header, a thin grey divider and two empty numbered circles (01–08 in order) with blank space to the right for text.
```

---

## Checklist before submitting
- Every ⟦live⟧ value has been copied from the **09 Accuracy** page on the day of export.
- No slide says "Oil India data". Our wells are public stand-ins, and Indian data is public (NDR, PIB, CAG, OISD, courts).
- No Oil India logo and no State Emblem. Keep only the RAGnarok and SIH logos.
- The hazard model's "no skill vs base rate yet" is stated honestly (Accuracy slide or speaker notes).
- Every image has been proof-read for spelling and digits.
