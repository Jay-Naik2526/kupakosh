# Kupakosh: SIH 2026 idea-submission deck (PS 26121). Updated guide, 28 Sept 2026

The deck keeps the NiyamKosh layout: same 6 slides, same order, same SIH template. This version replaces all earlier ones.

- **Part A:** the content of every slide, ready to paste.
- **Part B:** image prompts for ChatGPT or Gemini, restyled to match the website's new "geological survey map" look, so the deck and the product feel like one piece of work.
- **Part C:** screenshots to use, a 5-minute demo script, hard judge questions with honest answers, and the checklist.

> **Numbers rule, same as the product.**
> - Every number below was read from the live system on **28 Sept 2026**: `/api/status`, `/api/hindsight/summary` and the Accuracy page.
> - If the data changes, re-copy from the **Accuracy** and **Hindsight** pages on the day you export.
> - Never round a figure up. For example, 79.5 % stays 79.5 %, not "80 %".
> - Never add a number that is not on those pages or in a cited reference.

---

## The numbers at a glance (copy from here)

| What | Value | Where it comes from |
|---|---|---|
| Wells located | **96,418** (8 countries) | Accuracy, figures |
| Report sentences, each citable | **2,24,016** (224,016) | Accuracy |
| Formation tops | **1,54,058** (154,058) | Accuracy |
| Drilling problems on record | **1,851** (1,079 of them AI-reviewed; see "Honesty lines") | Accuracy |
| Problem → action → outcome episodes | **1,851** (537 with a stated outcome) | Fixes |
| Rig sensor samples (replay) | **3,50,172** | Accuracy |
| **Ranking accuracy (AUC), blind** | **86 %** (95 % range 84–88 %); field average alone 69 %; random 50 % | Hindsight |
| **Problem layers flagged before the bit arrived** | **79.5 %** (357 of 449) at 15 alerts per well; **84.2 %** at 20 | Hindsight |
| **Right hazard in the layer's top 3 (of 8)** | **74.4 %**; random 37.5 %; field average 59.2 % | Hindsight |
| Exact hazard named ahead, about 6 alerts per well | **193 of 449 (43 %)**, median **348 m** ahead; field average with the same alerts gets 86 | Hindsight |
| Hindsight test size | **304** wells, **449** real problems, **36,776** layer × hazard cells | Hindsight |
| Extraction precision | **91.7 %** (n = 36) | Accuracy |
| Extraction recall | **86.8 %** (n = 38) | Accuracy |
| Problem → fix → outcome linked correctly | **77.8 %** (n = 18) | Accuracy |
| Copilot answers with a source | **25 of 25**; correct refusals **30 of 30** | Accuracy |

**Honesty lines (keep them in the speaker notes and never hide them):**
- **Blind replay.** The Hindsight test replays each real well as if it were new. The model never trained on it (grouped cross-validation), and it sees nothing below the bit. The alert threshold is set on the *training* wells only.
- **What 86 % means.** It is a *ranking* score. It is not "86 % of alerts are right": about 1 in 10 alerts matches a recorded problem, and reports under-record problems.
- **The per-layer Bayesian risk model.** On its own it is no better than the field average (the Brier scores match). That is why the product shows a range and the evidence count, and says "insufficient evidence" when evidence is thin. The skill comes from the learned ranker.
- **AI review.** 1,079 of the 1,851 problems were checked by an AI review pass at the team lead's request, and are labelled that way. They are **not engineer-verified**. The gold labels used for precision and recall were also AI-made.
- **No Oil India data.** Well-level data is public stand-in data from Norway, the USA, the UK, the Netherlands, Australia, New Zealand and Canada. Indian facts come from public NDR, PIB, CAG and OISD documents.

---

## Part A: slide content

### Slide 1: Title (same template as NiyamKosh slide 1)
- **Problem Statement ID:** 26121
- **Problem Statement Title:** ⟦copy the exact title from the SIH 2026 portal⟧. It is Oil India Limited's problem statement on offset-well data, drilling-event knowledge and real-time risk alerts.
- **Theme:** ⟦copy from portal⟧
- **PS Category:** Software
- **Team ID:** ⟦fill⟧
- **Team Name:** The RAGnarok
- **Visual:** keep the SIH bulb graphic and both logos (RAGnarok top-left, SIH 2026 top-right) on every slide.
- **Optional:** a thin strip of the formation-column banner from `00-home.png` along the bottom edge.

---

### Slide 2: "Kupakosh: Oil India's Memory of Every Well"
Four blocks, in the same positions as NiyamKosh slide 2.

**THE PROBLEM** (top-left: 3 cards and a flow strip)
1. **Lessons are locked in PDFs.** Offset-well history sits in daily drilling reports and completion reports, not in any searchable system.
   - Sub-line: "eRTMAC shows the live well, not what happened in the wells around it."
2. **Rigs lose a fifth of their time.** Rig non-productive time was **19–23 %** in 2010–14. The bulk of the idle time, worth **₹6,418 crore**, was within the company's control.
   - Source: CAG Report 39 of 2015, on ONGC rigs.
3. **The same problem repeats in the same layer.** Losses, kicks and stuck pipe come back at the same formation in nearby wells.
   - Sub-line: "Baghjan-5, 2020: blowout, then fire on 9 June; two OIL firemen died." (Source: PIB)
- **Flow strip:** OLD REPORT → NOT FOUND → SAME PROBLEM → LOST RIG DAYS

**THE IDEA: KUPAKOSH** (top-right: 3 cards and a flow strip)
1. **Warns before the bit reaches the danger layer.** Look-ahead alerts with probability, range and evidence wells.
   - Proven blind on real history: 79.5 % of real problems fell in a layer that was on alert before the bit arrived.
2. **Shows what actually worked, and how often.** Problem → action → outcome, ranked by success rate. Fixes that made things worse are shown.
3. **An engineer-approved Well Wiki.** Every sentence cites the exact report line. Reviewers approve pages in a government file-noting style, and every version is kept.
- **Flow strip:** READ REPORTS → REMEMBER → WARN AHEAD → SAFER WELL

**WHY KUPAKOSH** (bottom-left: comparison table)

| Feature | eRTMAC (live view) | PDF search / RAG chatbot | Manual offset review | **KUPAKOSH** |
|---|---|---|---|---|
| Live rig data on screen | ✓ | ✗ | ✗ | ✓ (replay) |
| History of nearby wells | ✗ | ✓ | ✓ | ✓ |
| Blind proof on real history (Hindsight test) | ✗ | ✗ | ✗ | ✓ |
| Which fix worked, and how often | ✗ | ✗ | ✗ | ✓ |
| Risk with a range, or "insufficient evidence" | ✗ | ✗ | ✗ | ✓ |
| Indian basins answered from global analogues | ✗ | ✗ | ✗ | ✓ |
| Engineer-approved knowledge with version history | ✗ | ✗ | ✗ | ✓ |
| Every answer cites the exact report line | ✗ | ✓ | ✗ | ✓ |

(Write ✓ or ✗ only where the column truly does or does not do it. Do not name commercial products we have not tested.)

**ONE ALERT, AS KUPAKOSH SHOWS IT** (bottom-right: annotated screenshot `01-command-replay.png`)
Replay of well **16B(78)-32** (Utah FORGE, a public stand-in). Callouts:
1. **REPLAY OF REAL RIG DATA.** Bit depth, formation, "recorded data, not live". Source: Pason sensor log.
2. **HAZARD AHEAD.** Stuck pipe in basin fill, **55 %** (range 29–80 %), evidence **4.8 wells** (2 of 5 with a record). Source: offset wells.
3. **WHAT WORKED BEFORE.** "Pull out of hole, 1/1, anecdotal". It says "anecdotal" when evidence is thin. Source: mitigation ledger.
4. **WHY THIS NUMBER?** One click shows the evidence wells, the field average and the range. Source: hazard model.
5. **EXACT REPORT LINE.** "View sources" opens the daily-report sentence. Source: DDR page and line.
6. **SAYS WHEN IT DOESN'T KNOW.** "Insufficient evidence" instead of a guess.

---

### Slide 3: Technical Approach (same 3 columns as NiyamKosh slide 3)

**Left: MEASURED, NOT CLAIMED** (5 big-number rows)

| Big number | Text |
|---|---|
| **86 %** | ranking accuracy, blind (AUC; field average 69 %, random 50 %) |
| **79.5 %** | of 449 real problems fell in a layer on alert before the bit arrived (15 alerts per well) |
| **74.4 %** | right hazard in the layer's top 3 of 8 (random 37.5 %) |
| **91.7 %** | of extracted drilling events were correct (n = 36) |
| **30 of 30** | out-of-scope questions refused correctly: "No evidence found in the records" |

- **Footer:** *"Blind test: each well replayed as if new, the model never trained on it, nothing below the bit visible."*
- **Speaker note, say it:** "About 1 in 10 alerts matches a recorded problem. Reports under-record, so the rest are 'no record', not proven false alarms. The per-layer Bayesian model alone is no better than the field average, which is why we show ranges and 'insufficient evidence'."

**Middle: KUPAKOSH SYSTEM ARCHITECTURE** (two lanes)
- **Ingestion pipeline** (runs once, and again on each upload):
  1. **Harvest:** 8 countries of public well data, plus report upload.
  2. **Read:** PDF text and OCR, sentence by sentence, each with page and line.
  3. **Extract:** rules plus an optional LLM pass; evidence must be a verbatim quote.
  4. **Review:** a low-confidence queue; human or labelled AI review, and every decision is logged and replayed on rebuild.
  5. **Link and compile:** problem → action → outcome episodes, and a cited wiki with a git version for every change.
  - Footer: *"Writes only what it can cite."*
- **Runtime path** (per well, live): Replay / eRTMAC stream → Look-ahead (next 150 m) → **Intelligence**, which has three boxes:
  - Offset wells (radius + similarity)
  - Risk ranker (trained on other wells) + Bayesian range
  - Live anomaly (torque, pit volume)
  - Sub-line: *"The model ranks and warns; the engineer decides."*
- **Knowledge core:** WELL WIKI | MITIGATION LEDGER | EVIDENCE INDEX (keyword + meaning search)
- **Outputs:** LOOK-AHEAD ALERT · PRE-DRILL BRIEF (official-style PDF) · REPORT CHECKER · HINDSIGHT PROOF

**Right: TECHNICAL VALIDATION: Hindsight test** (use `13-hindsight.png`, top half)
- Three labels: **Blind replay** (grouped cross-validation) · **Real outcomes** (449 recorded problems) · **Fair baseline** (field average, same alerts)
- Line: *"Every documented well replayed as if new, then compared with what the reports say happened."*
- Pill: **REAL DATA • BLIND TEST • MEASURED**

**Bottom strip, tech logos (only what we use):** Python · FastAPI · scikit-learn · SQLite (PostgreSQL + PostGIS target) · Next.js · MapLibre · three.js · bge-small embeddings · Tesseract OCR · Git

---

### Slide 4: Feasibility and Viability

**CURRENT SCALE** (measured, not estimated)

| Number | Label |
|---|---|
| **96,418** | WELLS LOCATED (8 countries) |
| **2,24,016** | REPORT SENTENCES, EACH CITABLE |
| **1,54,058** | FORMATION TOPS |
| **1,851** | DRILLING PROBLEMS ON RECORD |

**DEPLOYMENT MODEL: "Runs beside eRTMAC, inside Oil India"**
- **Value proposition:** "Fewer lost rig days: know the next layer before the bit does."
- **Users:**
  - Drilling engineers: pre-drill planning
  - Rig-site supervisors: live look-ahead
  - Geologists: formation correlation
  - HSE and management: lessons, audits
- **Learning loop:** DRILL → REPORT → EXTRACT → APPROVE → WARN → back to DRILL. "Every new well makes the next one safer."
- **Cost structure:**
  - local models: no per-query fee;
  - runs on one ordinary 2 GB server;
  - only recurring cost: hosting and support.
- **Timeline:**
  - YEAR ZERO: pilot on one Oil India field (NDR data)
  - YEAR ONE: eRTMAC stream integration
  - YEAR TWO: all fields, own DDR archive

**RISKS AND MITIGATION** (4 rows)

| Risk | Mitigation |
|---|---|
| **Well data is restricted.** Oil India and NDR files need authorisation. | **Same schema, swap the data.** Built on public stand-ins from 8 countries; Oil India data loads with no code change. |
| **Scanned old reports.** | **OCR with confidence kept.** Low-quality scans lower an event's confidence and send it to the review queue. |
| **AI might invent facts.** | **Cite or stay silent.** Evidence must be a verbatim quote, uncited sentences are rejected, and the copilot refuses when there's no record. |
| **Engineers must trust it.** | **Proof and approval.** A blind Hindsight test on real history, a noting-sheet review, a version history for every change, and "insufficient evidence" instead of a guess. |

---

### Slide 5: Impacts and Benefits (two-column arrow cards)

**IMPACTS (by user)**
- **Drilling engineers:** plan the next well from what happened in the wells around it, layer by layer, in minutes instead of days of reading reports.
- **Rig-site supervisors:** warned before a known problem layer. In the blind test, 79.5 % of real problems fell in a layer already on alert.
- **Oil India & PSUs:** knowledge stays when experts retire. The PM asked that the Baghjan lessons "be studied and documented" (PIB, 2020).
- **HSE & regulators:** report conflicts are flagged, and every alert traces to its source line, which makes audits faster.

**BENEFITS**
- **Transparency:** every sentence, alert and number names its source (report, page, line).
- **Operational:** runs beside eRTMAC without changing it, on one ordinary server. Upload a new report to update it.
- **Honest risk:** a probability with its range and evidence count, or "insufficient evidence", never false certainty.
- **What actually worked:** fixes ranked by success rate with a lower bound; fixes that made things worse are shown.

**Bottom line (bold):** "96,418 wells, 2,24,016 report sentences, 8 countries. Replayed blind, Kupakosh ranked the real problem layer higher 86 times in 100. It turns old drilling reports into a warning before the bit reaches the danger layer."

---

### Slide 6: Research and References (4 boxes, 2 references each)

**POLICY & SAFETY FOUNDATION**
- **01 · Press Information Bureau: Baghjan-5 well fire (June 2020).** The well caught fire on 9 June 2020 and two OIL firemen died; the PM directed that the lessons be documented.
  - pib.gov.in/PressReleasePage.aspx?PRID=1632427
- **02 · Comptroller & Auditor General: Utilisation of Rigs, Report 39 of 2015.** Rig non-productive time of 19–23 % (2010–14), the bulk of it controllable.
  - cag.gov.in (Report 39 of 2015)

**INDIAN E&P DATA**
- **03 · DGH National Data Repository (NDR):** sedimentary basins of India. ndrdgh.gov.in/NDR/
- **04 · Oil Industry Safety Directorate (OISD):** safety alerts. oisd.gov.in

**STAND-IN WELL DATA**
- **05 · Norwegian Offshore Directorate (Sodir) FactPages:** wellbores, formation tops, casing, LOT/FIT, well histories (NLOD 2.0). factpages.sodir.no
- **06 · Utah FORGE (US DOE GDR):** daily drilling reports and rig sensor data (CC-BY 4.0), the source of the replay. gdr.openei.org/submissions/1516

**METHODS**
- **07 · Wilson, E. B. (1927). Probable inference, the law of succession, and statistical inference. JASA 22(158).** The lower bound used to rank fixes.
- **08 · Friedman, J. H. (2001). Greedy function approximation: a gradient boosting machine. Annals of Statistics 29(5).** The risk ranker used in the Hindsight test.
  - Optional swap: Gelman et al., *Bayesian Data Analysis*, the Beta-Binomial model for the per-layer range.

---

## Part B: image prompts (ChatGPT / Gemini) in the new website style

### How to use
1. **Generate panels, not whole slides.** Place them on the SIH template in PowerPoint or Google Slides; add titles and logos yourself.
2. **Proof-read every word and digit afterwards.** Image models misspell and change numbers. The numbers come from Part A, never from the image model. If one is wrong, cover it with a PPT text box.
3. **Screenshots are always real** (`docs/screenshots/`). A prompt only makes the frame and callouts around them.

### Style block (paste at the start of every prompt)
```
Style: a printed geological-survey-map infographic, flat and hand-designed, 16:9.
Background warm paper cream #F3EEE3 with very faint topographic contour lines. Ink text #1F1B16.
Flat earth colours only, used as solid fields, thin rules and small square legend keys:
deep teal #1F5F66, rust #A8472A, ochre #C8902E, sage #6E8B5A, slate blue #3D5A73, plum #6B4A6E, sand #E3C98F.
Headings in a serif typeface (like IBM Plex Serif or Georgia), body in a clean sans (like IBM Plex Sans), numbers in a monospaced figure style.
Hairline 1px rules, square-ish corners (4-6px), small 9px colour squares before labels like a map legend.
Geological hatch patterns (dots for sand, short dashes for shale, brick for limestone) are welcome as texture.
NO gradients, NO glow, NO drop shadows, NO glassmorphism, NO neon, NO 3D icons, NO stock photos, NO faces, NO logos, NO watermark.
Render ALL text exactly as written below, spelled exactly, nothing added.
```

### Prompt 1: Slide 2 "THE PROBLEM"
```
[Style block]
Eyebrow label with a rust square: "THE PROBLEM".
Three stacked rows separated by hairline rules. Each row has a thin line icon in rust, a bold serif line and a small grey line:
1 icon: stack of PDF pages with a padlock. "Lessons are locked in PDFs" / "eRTMAC shows the live well, not the wells around it"
2 icon: drilling rig with a pause symbol. "Rigs lose a fifth of their time" / "Rig non-productive time 19–23% (CAG, 2015)"
3 icon: rock layers with a repeating warning triangle. "The same problem repeats in the same layer" / "Losses, kicks and stuck pipe return in nearby wells"
Below, a flow strip of four small line icons joined by thin rust arrows, captions in small capitals:
"OLD REPORT" -> "NOT FOUND" -> "SAME PROBLEM" -> "LOST RIG DAYS".
```

### Prompt 2: Slide 2 "THE IDEA: KUPAKOSH"
```
[Style block]
Eyebrow with a teal square: "THE IDEA", then the serif word "Kupakosh" in ink.
Three stacked rows with hairline rules, teal line icons:
1 icon: drill bit above layered rock with a bell. "Warns before the bit reaches the danger layer" / "Blind test on real history: 79.5% of problems were in a layer already on alert"
2 icon: checklist with a small trophy. "Shows what actually worked, and how often" / "Problem → action → outcome, ranked; fixes that made it worse shown"
3 icon: open book with an approval stamp. "An engineer-approved Well Wiki" / "Every sentence cites the exact report line; every change is kept"
Flow strip with teal arrows: "READ REPORTS" -> "REMEMBER" -> "WARN AHEAD" -> "SAFER WELL".
```

### Prompt 3: Slide 2 "WHY KUPAKOSH" comparison table
```
[Style block]
Serif title "Why Kupakosh". A ruled table with a 2px ink top rule and hairline row dividers, no zebra stripes, no box shadow.
The last column header "KUPAKOSH" sits on a solid deep-teal field with cream text.
Columns: "Feature" | "eRTMAC (LIVE VIEW)" | "PDF SEARCH / RAG CHATBOT" | "MANUAL OFFSET REVIEW" | "KUPAKOSH".
Use a small ink tick for yes and a small grey dash for no:
"Live rig data on screen": yes, no, no, yes (replay)
"History of nearby wells": no, yes, yes, yes
"Blind proof on real history": no, no, no, yes
"Which fix worked, how often": no, no, no, yes
"Risk with a range or 'insufficient evidence'": no, no, no, yes
"Indian basins from global analogues": no, no, no, yes
"Engineer-approved, versioned knowledge": no, no, no, yes
"Cites the exact report line": no, yes, no, yes
```

### Prompt 4: Slide 2 "ONE ALERT, AS KUPAKOSH SHOWS IT" (frame around the real screenshot)
```
[Style block]
Serif title "One alert, as Kupakosh shows it". Grey subtitle "A real replay; every number names its source".
Left 50%: a plain rectangle with a 1px ink border labelled "SCREENSHOT" (the real screenshot goes here).
Six small numbered squares (1–6) on its right edge, joined by thin ink elbow lines to six stacked callouts,
each with a 4px coloured left rule, bold small-caps title, grey line and small italic source:
1 slate: "REPLAY OF REAL RIG DATA" / "Bit depth, formation, recorded not live" / "rig sensor log"
2 ochre: "HAZARD AHEAD" / "Probability, range and evidence wells" / "offset wells"
3 sage: "WHAT WORKED BEFORE" / "Top fixes: worked k of n, 'anecdotal' when thin" / "mitigation ledger"
4 plum: "WHY THIS NUMBER?" / "Evidence wells, field average, range" / "hazard model"
5 teal: "EXACT REPORT LINE" / "The daily-report sentence, one click away" / "DDR page and line"
6 rust: "SAYS WHEN IT DOESN'T KNOW" / "'Insufficient evidence', not a guess" / "hazard model"
```

### Prompt 5: Slide 3 "MEASURED, NOT CLAIMED"
```
[Style block]
A tall panel on a flat deep-teal field with a cream paper card inside. Eyebrow with an ochre square "MEASURED, NOT CLAIMED".
Grey line: "Blind test on real history, and task-labelled report lines".
Five rows separated by hairline rules. Left: a big monospaced number in ink with a 5px solid underline bar in a different earth colour per row
(rust, ochre, sage, slate, plum). Right: the text.
"86%" — "ranking accuracy, blind (field average 69%)"
"79.5%" — "of 449 real problems in a layer on alert before the bit arrived"
"74.4%" — "right hazard in the layer's top 3 of 8 (random 37.5%)"
"91.7%" — "of extracted drilling events correct (n = 36)"
"30 of 30" — "out-of-scope questions refused correctly"
Bottom, small italic: "Each well replayed as if new; the model never trained on it".
```

### Prompt 6: Slide 3 "SYSTEM ARCHITECTURE"
```
[Style block] with faint engineering graph-paper grid.
Serif title "Kupakosh" + grey "system architecture", thin ochre underline.
Left column, header on a solid slate field "INGESTION PIPELINE" (small italic "runs on upload"):
five stacked paper boxes with line icons joined by down arrows: "HARVEST", "READ (OCR)", "EXTRACT", "REVIEW", "LINK & COMPILE".
Footer italic: "Writes only what it can cite".
Right column, header on a solid rust field "RUNTIME PATH" (italic "per well, live"):
"REPLAY / eRTMAC STREAM" -> "LOOK-AHEAD, NEXT 150 m" -> a box with an ochre border "INTELLIGENCE" containing
"OFFSET WELLS", "RISK RANKER + RANGE", "LIVE ANOMALY" and the italic line "The model ranks and warns; the engineer decides".
Both columns feed a wide solid deep-teal band "KNOWLEDGE CORE": "WELL WIKI | MITIGATION LEDGER | EVIDENCE INDEX".
Below it four output boxes with coloured top rules (rust, ochre, sage, plum):
"LOOK-AHEAD ALERT", "PRE-DRILL BRIEF (PDF)", "REPORT CHECKER", "HINDSIGHT PROOF".
```

### Prompt 7: Slide 3 "TECHNICAL VALIDATION" (frame around `13-hindsight.png`)
```
[Style block]
Eyebrow with a slate square "TECHNICAL VALIDATION", serif subtitle "The Hindsight test".
A plain 1px-ink-bordered rectangle labelled "SCREENSHOT".
Below: three labels separated by hairline vertical rules, each with a small colour square:
"Blind replay (grouped cross-validation)", "Real outcomes (449 recorded problems)", "Fair baseline (field average, same alerts)".
Centred line: "Every documented well replayed as if new, then compared with what the reports say happened."
Bottom pill with square corners on a solid slate field, cream text: "REAL DATA • BLIND TEST • MEASURED".
```

### Prompt 8: Slide 4 "CURRENT SCALE" and "DEPLOYMENT MODEL"
```
[Style block]
Top band, ruled: eyebrow "CURRENT SCALE" with grey "measured from the live database". Four figures separated by hairline vertical rules,
each a big monospaced ink number with a 5px coloured underline bar and a small-caps caption:
"96,418" WELLS LOCATED (teal); "2,24,016" REPORT SENTENCES (ochre); "1,54,058" FORMATION TOPS (sage); "1,851" DRILLING PROBLEMS (rust).
Below: serif title "Deployment model", grey "runs beside eRTMAC, inside Oil India".
A solid ink band with cream text: "FEWER LOST RIG DAYS — know the next layer before the bit does".
Left list "USERS" with small line icons: "DRILLING ENGINEERS / pre-drill planning", "RIG-SITE SUPERVISORS / live look-ahead",
"GEOLOGISTS / formation correlation", "HSE AND MANAGEMENT / lessons and audits".
Centre: a loop of five arrows in earth colours: "DRILL", "REPORT", "EXTRACT", "APPROVE", "WARN"; centre text "Every well makes the next safer".
Bottom ruled row "COST": "Local models / no per-query fee", "One ordinary 2 GB server", "Hosting and support / the only recurring cost".
Timeline, three dots on a hairline: "YEAR ZERO / pilot on one field", "YEAR ONE / eRTMAC integration", "YEAR TWO / all fields".
```

### Prompt 9: Slide 4 "RISKS AND MITIGATION"
```
[Style block]
Serif title "Risks and mitigation". Two legend keys: rust square "RISK", sage square "MITIGATION".
Four rows. Each has a paper card with a 4px rust left rule, then a thin ink arrow, then a paper card with a 4px sage left rule:
1 "WELL DATA IS RESTRICTED" — "Oil India and NDR files need authorisation"
  → "SAME SCHEMA, SWAP THE DATA" — "Built on public data from 8 countries; Oil India data loads with no code change"
2 "SCANNED OLD REPORTS" — "Many old daily reports are images"
  → "OCR WITH CONFIDENCE KEPT" — "Low-quality scans go to the review queue"
3 "AI MIGHT INVENT FACTS" — "A wrong depth or hazard is dangerous"
  → "CITE OR STAY SILENT" — "Evidence must be a verbatim quote; uncited sentences rejected"
4 "ENGINEERS MUST TRUST IT" — "An alert nobody believes is ignored"
  → "PROOF AND APPROVAL" — "Blind test on real history, noting-sheet review, full version history"
```

### Prompt 10: Slide 5 "IMPACTS / BENEFITS"
```
[Style block]
Two columns under serif headings "Impacts" (left) and "Benefits" (right).
Each column has four rows separated by hairline rules, each with a 9px colour square and a small line icon:
Impacts: "Drilling engineers" — "Plan the next well from the wells around it, layer by layer, in minutes."
"Rig-site supervisors" — "Warned before a known problem layer; 79.5% of real problems were in a layer already on alert."
"Oil India & PSUs" — "Knowledge stays when experts retire; Baghjan lessons documented as the PM asked."
"HSE & regulators" — "Report conflicts flagged; every alert traces to its source line."
Benefits: "Transparency" — "Every sentence, alert and number names its report, page and line."
"Operational" — "Runs beside eRTMAC on one ordinary server; upload a report to update."
"Honest risk" — "A probability with its range, or 'insufficient evidence'."
"What actually worked" — "Fixes ranked by success rate; those that made it worse are shown."
```
(Put the bold bottom line from Part A under this panel as a PPT text box, not inside the image.)

### Prompt 11: Slide 6 "RESEARCH AND REFERENCES"
Don't generate this slide as an image: build it in PowerPoint so the text is exact and the links are clickable. For the look only:
```
[Style block]
A 2x2 grid of paper cards with 1px ink borders and a 6px solid left rule: slate "POLICY & SAFETY FOUNDATION",
ochre "INDIAN E&P DATA", sage "STAND-IN WELL DATA", plum "METHODS". Under each header a hairline and two empty numbered squares (01–08).
```

---

## Part C: screenshots, demo, judge questions, checklist

### Screenshots (real app, new design, in `docs/screenshots/`)
Regenerate on the day with `cd frontend && node scripts/screenshots.mjs` (the API and web server must be running).

| File | Use it for |
|---|---|
| `00-home.png` | Title or closing slide; the formation-column banner is a real well (15/9-19 S, Sodir tops) |
| `01-command-replay.png` | Slide 2, "One alert" |
| `13-hindsight.png` | Slide 3, "Technical validation" (crop the top half: 86 % / 79.5 % / 74.4 %) |
| `02-offsets.png`, `02-offsets-map.png` | Appendix: correlation by formation |
| `10-map.png`, `10b-map-satellite.png` | Appendix: 96,418 wells, 8 countries |
| `11b-subsurface-norway.png` | Appendix: 3D formation block from real tops, 41 wells |
| `12-analogs.png` | Appendix: India Analogs |
| `04-fixes.png`, `03-wiki.png`, `07-copilot.png`, `09-accuracy.png`, `08-brief.png`, `06-checker.png`, `05-mudwindow.png` | Backups |
| `14-home-dark.png` | Only if the template is dark |

### 5-minute demo script
1. **Accuracy (30 s):** "Real public data: 96,418 wells, 2,24,016 report sentences, 1,851 recorded problems. Every number on this page is measured, including the ones that don't flatter us."
2. **Well Room (60 s):**
   - Start the replay of 16B(78)-32.
   - The alert appears: stuck pipe, 55 %, range 29–80 %, 4.8 wells.
   - Open **Why this number?**, then **View sources**, which shows the exact daily-report line.
3. **Hindsight (60 s):**
   - "We replayed every documented well blind. The model ranked the real problem layer higher 86 times in 100."
   - "79.5 % of real problems were in a layer already on alert."
   - "Here's the trade-off table: we don't hide that only 1 in 10 alerts matches a record."
4. **Fixes (40 s):** "Not just what happened, but what actually worked, and the fix that made it worse."
5. **Map → 3D (40 s):** the world map with satellite view, then the 3D formation block for a Norwegian well.
6. **Copilot (30 s):** one cited answer and one correct refusal.
7. **Brief (20 s):** download the official-style PDF.
8. **Close:** "Oil India can swap in its own reports and eRTMAC stream with no schema change."

### Hard questions, and honest answers
- **"Is 86 % your accuracy?"**
  - "It's ranking accuracy (AUC): how often a real problem layer is ranked above a quiet one, blind."
  - "Per alert, about 1 in 10 matches a recorded problem. Reports under-record problems, so the rest are 'no record', not proven false alarms."
- **"Did the model see the well it's tested on?"**
  - "No. Grouped cross-validation: a well and its sidetracks are never in training."
  - "Live mode reads only the well's own reports above the alert point, and the threshold is set on training wells."
  - "We even found and fixed a subtle leak in our own baseline, and we disclose it."
- **"Is this Oil India data?"**
  - "No. It's public stand-ins from 8 countries, plus public Indian documents."
  - "The same schema takes Oil India's DDRs and WCRs."
- **"Who verified the labels?"**
  - "The evaluation labels and 1,079 queued events were checked by an AI review pass, labelled as such; they're not engineer-verified yet. The review queue is built for engineers."
- **"Why not a chatbot like everyone else?"**
  - "Others search PDFs every time. Kupakosh compiles the reports once into an approved wiki and a problem → fix → outcome ledger, and proves itself blind."

### Checklist before submitting
- Every number was re-copied from the **Accuracy** and **Hindsight** pages on the day of export, with none rounded up (79.5 % stays 79.5 %).
- No slide says "Oil India data", and no slide says "80 % of alerts are correct".
- No Oil India logo and no State Emblem. Keep only the RAGnarok and SIH logos. The app says "Prototype for Oil India Limited · SIH 2026".
- The honesty lines appear in the speaker notes: alert precision, no Oil India data, and AI-reviewed and AI-labelled data.
- Every generated image has been proof-read for spelling and digits.
- Live link: ⟦fill once hosted⟧, with the Cloudflare Tunnel backup ready (`make share`, then `cloudflared tunnel --url http://localhost:8010`).
