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

1. **The Hindsight test: proven blind on real history.**
   - On 304 public wells and 449 real recorded problems, the model never saw the well it was tested on.
   - Results:
     - AUC 0.86, against a field average of 0.69;
     - 79.5 % of problem layers flagged before the bit arrived, at 15 alerts per well;
     - right hazard in the layer's top 3 in 74.4 % of cases;
     - 193/449 exact hazards forewarned, a median 348 m ahead.
   - **Why it wins:** nobody else measures prediction on held-out wells. Their accuracy numbers, where they show
     any, come from generated data or are not reported at all.
   - **Demo:** Hindsight page, then one well's replay.
2. **The Upper Assam column (new, built 30 Sept).**
   - Oil India's own formations, from Dhekiajuli down to Disang. Rock type, age, role (reservoir, source rock or
     cap rock) and depth mentions are all quoted from public DGH/NDR sentences, with a citation on each fact.
   - Beside each formation, the measured problem rates in the same rock type abroad, with range and evidence
     count, and what worked there.
   - **Why it wins:** competitors show Assam names on invented numbers; we show real Assam geology plus real
     measured analog evidence, and say plainly which is which.
   - **Demo:** India Analogs page, top section.
3. **What actually worked.**
   - Fixes ranked by real outcomes with a Wilson lower bound, median time to resolve, and a "made worse" count.
   - Others list "recommended actions"; we show outcome evidence.
4. **Compiled, cited, approved memory.**
   - 951 wiki pages, every sentence cited; the compiler rejects uncited sentences and unsupported numbers.
   - Government-file noting approval, with git history.
5. **Honest uncertainty.** Every probability has an 80 % range and an evidence count, and says "insufficient
   evidence" below 3 wells. Nobody else shows ranges.
6. **Deployed and running**: https://kupakosh.duckdns.org (HTTPS). The live replay, copilot, maps, 3D and PDF
   brief all work there.

## Where competitors still lead (be ready)
- **Logins and roles (JWT/RBAC):** several have them; we show a read-only guest.
- **Voice input** (DaddyYoda7, others) and polished "mission control" UIs. Our line is "calm by design (ISA-101)".
- **Claims of Assam wells:** answer with "theirs are generated; ours is cited public DGH/NDR geology, and we say
  where Indian well data will come from (DGH NDR, Oil India's own DDR/WCR)".

## Next (if time allows before 5 Oct)
- An Assam formation picker in the Well Room brief, so a planned Assam well gets its column and analogs in the PDF.
- Re-run the Hindsight test per country and show it stays above the baseline outside Norway.
