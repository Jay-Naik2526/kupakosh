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

1. **The Hindsight test: proven blind on real history, including real daily drilling reports.**
   - Results on 306 public wells and 578 real recorded problems, where the model never saw the well it was tested on:
     - AUC 0.84 (0.81–0.86), against a field average of 0.68;
     - 78.4 % of problem layers flagged before the bit arrived, at 15 alerts per well;
     - right hazard in the layer's top 3 in 68.2 % of cases;
     - exact hazard forewarned for 222 of 578, a median 394 m ahead (field average 113).
   - **Why it wins:** among competitors, only PLANNS reports a real-data early warning, and that is one stuck pipe on one well (15/9-F-9A).
   - **Demo:** Hindsight page. Pick 15/9-19 S (176 daily reports): 32 of its 58 problems were forewarned, the baseline caught 0. Press "Reveal what really happened".
2. **What actually worked, from real day-by-day reports.**
   - 1,759 real Volve daily drilling reports (23,447 timed activities) are linked problem → action → outcome over the following days.
   - Example: jarring freed stuck pipe in 5 of 10 cases, median 0.5 h; pulling out of hole in 36 of 78.
   - **Why it wins:** PLANNS and anshu2k24 hold the same public reports but use them only for summaries and regex; nobody tracks outcomes.
   - Events from these reports are measured: precision 0.75 on 40 random trusted events.
3. **Compiled, cited, approved memory.**
   - 951 wiki pages, every sentence cited; the compiler rejects uncited sentences and unsupported numbers.
   - Government-file noting approval, with git history.
4. **Honest uncertainty.** Every probability has an 80 % range and an evidence count, and says "insufficient evidence" below 3 wells.
5. **Deployed and running**: https://kupakosh.duckdns.org (HTTPS).

The Upper Assam column (India Analogs page) is useful context for Oil India judges, but it is **not** a USP: it rearranges public geology text. Show it only if asked about Assam.

## Where competitors still lead (be ready)
- **Logins and roles (JWT/RBAC):** several have them; we show a read-only guest.
- **Voice input** (DaddyYoda7, others) and polished "mission control" UIs. Our line is "calm by design (ISA-101)".
- **Claims of Assam wells:** answer with "theirs are generated; ours is cited public DGH/NDR geology, and we say
  where Indian well data will come from (DGH NDR, Oil India's own DDR/WCR)".

## Next (if time allows before 5 Oct)
- An Assam formation picker in the Well Room brief, so a planned Assam well gets its column and analogs in the PDF.
- Re-run the Hindsight test per country and show it stays above the baseline outside Norway.
