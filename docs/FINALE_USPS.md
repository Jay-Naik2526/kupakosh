# Grand-finale USPs: what is really different (30 Sept 2026)

Based on a second competitor scan (details in `docs/COMPETITORS.md`, section "Second scan"). This file lists
only differences we can show live and defend under questioning. Nothing here is a claim we have not measured.

## What the field looks like now
- About **150 public repos** now target PS 26121: the 29 from the first scan plus **123 new ones** since 27 Sept,
  about 49 of them with a deployed site.
- The strong ones have **converged on the same feature list**:
  - look-ahead alerts "50–300 m ahead" and offset similarity scores;
  - RAG chat with citations and "why this alert" panels;
  - approval gates, JWT roles and a telemetry simulator;
  - XGBoost + SHAP, and knowledge graphs.
- **None of those is a USP any more.** Judges will see them in every second demo.
- **Data:**
  - Most repos run on generated data. Several give it Upper Assam formation names (Tipam, Barail, Kopili), which
    makes invented numbers look like Oil India data.
  - The largest (lakshmanan72) claims "15,108 Indian wells" with historical drilling events. No public source
    publishes drilling-event logs for Indian wells, and its hazard labels are generated from its own event table.
- **Evaluation:** none of the 13 strongest repos contains a held-out-well or blind back-test evaluation. We
  searched their code for AUC, backtest, leave-one-well-out, GroupKFold and held-out.

## Our USPs, in the order to pitch them

0. **It had happened before (new, 1 Oct).** 332 of 661 real recorded problems (50 %, range 47–54 %) had already been written down in the same rock layer, same hazard, in an older well's report. Within the well's own offset radius: 41 of 661 overall, 13 of 59 (22 %) for 2020s wells with full daily reports. Checked against all 141 competitor repos: none computes it. Line: *"Half of these problems had happened before, and the answer was already in a report."*
1. **The Hindsight test: proven blind on real history, including real daily drilling reports.**
   - Results on 306 public wells and 565 real recorded problems, where the model never saw the well it was tested on (nested cross-validation: even the model choice is made on training wells only):
     - AUC 0.86 (0.84–0.88), against a field average of 0.68;
     - 82.5 % of problem layers flagged before the bit arrived, at 15 alerts per well (86.6 % at 20);
     - right hazard in the layer's top 3 in 74.9 % of cases (field average 62.3 %);
     - exact hazard forewarned for 276 of 565 (49 %), a median 384 m ahead (field average 113).
   - **Rig hours at stake** (same page): logged rig-hours of the real Volve problems, and how many of them were in problems it had warned about blind.
   - **Why it wins:** among competitors, only PLANNS reports a real-data early warning, and that is one stuck pipe on one well (15/9-F-9A).
   - **Demo:** Hindsight page. Pick 15/9-19 S (176 daily reports): 32 of its 53 problems were forewarned. Press "Reveal what really happened".
2. **What actually worked, from real day-by-day reports.**
   - 1,759 real Volve daily drilling reports (23,447 timed activities) are linked problem → action → outcome over the following days.
   - Example: jarring freed stuck pipe in 9 of 13 cases, median 0.5 h; pulling out of hole in 97 of 133.
   - **Why it wins:** PLANNS and anshu2k24 hold the same public reports but use them only for summaries and regex; nobody tracks outcomes.
   - Events from these reports are measured on a fresh random sample never used for tuning: precision 0.90–0.92 on the last two fresh samples (55/60, 37/41).
3. **Compiled, cited, approved memory.**
   - 951 wiki pages, every sentence cited; the compiler rejects uncited sentences and unsupported numbers.
   - Government-file noting approval, with git history.
4. **Honest uncertainty.** Every probability has an 80 % range and an evidence count, and says "insufficient evidence" below 3 wells.
5. **Deployed and running**: https://kupakosh.duckdns.org (HTTPS).
6. **Made for the rig crew**: a one-page shift-handover note in English or हिंदी (Well Room ▸ "Shift handover note"), and alerts that learn from the engineer's "problem happened / no problem" verdict without ever inflating the measured accuracy.
7. **Honest about what failed**: episode outcomes are measured blind (0.55), and a sensor "déjà vu" idea that tested below chance is shown as a negative result, not hidden.

The Upper Assam column (India Analogs page) is useful context for Oil India judges, but it is **not** a USP: it rearranges public geology text. Show it only if asked about Assam.

## Where competitors still lead (be ready)
- **Logins and roles (JWT/RBAC):** several have them; we show a read-only guest.
- **Voice input** (DaddyYoda7, others) and polished "mission control" UIs. Our line is "calm by design (ISA-101)".
- **Claims of Assam wells:** answer with "theirs are generated; ours is cited public DGH/NDR geology, and we say
  where Indian well data will come from (DGH NDR, Oil India's own DDR/WCR)".

## Next (if time allows before 5 Oct)
- An Assam formation picker in the Well Room brief, so a planned Assam well gets its column and analogs in the PDF.
- Re-run the Hindsight test per country and show it stays above the baseline outside Norway.
