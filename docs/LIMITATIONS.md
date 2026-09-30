# Limitations (read before quoting any number)

1. **Stand-in data.** Well-level data is public data from Norway, the USA, the UK, the Netherlands, Australia, New Zealand and Canada. Indian data is public too: NDR/DGH summaries, OISD alerts, CAG audits, PIB releases and court records. **No Oil India well data** is used or claimed.
2. **Summaries, not diaries.** Most report text is a well history, a completion report or an incident summary. These under-record problems. A Kupakosh rate is a rate of *recorded* problems; "no record" does not mean "no problem".
3. **The hazard model has no measured skill.** In leave-one-well-out testing, the model's Brier score equals the base rate's (n = 41,848). The UI therefore shows ranges and evidence counts, says "insufficient evidence" when n_eff < 3, and never claims to predict.
4. **Extraction is rule-based.**
   - Precision and recall are both 0.92 (n = 38).
   - 1,851 of 2,623 events fall below the confidence threshold and wait in the review queue.
   - The LLM pass is built but off (no key).
5. **Gold labels are AI-made.** An independent AI second pass agreed 96–100 %, but a person must verify them before any external claim.
6. **The copilot is extractive,** and its eval questions are templated, so 1.00 is optimistic.
7. **Headers only for UK, NZ and Canada.** Their report archives need a login, so no events come from them.
8. **OCR quality varies.** Clean scans read at about 91–95 % confidence, degraded ones at 30–58 %. Event confidence is scaled by OCR confidence, but garbled text can still produce a wrong event, which then waits in the review queue.
9. **US incident records.**
   - They are linked to a single well only by API number or a unique lease + block. Otherwise they go to a block aggregate, or stay unlinked (2,897 records).
   - Block aggregates are locations, not wells, and are never counted as wells.
   - Some BSEE borehole columns were inferred, because the official layout page is not machine-readable.
10. **Depths are MD.** Most exploration wells have no public trajectory here, so the mud window and correlation are approximate for deviated wells. FORGE wells have full surveys.
11. **The live look-ahead is a replay** of recorded FORGE sensor data. There is no WITSML/eRTMAC adapter.
12. **Target stack not verified.** It runs on SQLite. PostGIS, pgvector, Alembic and Docker are described but not verified on the build machine.
13. **Reviewer names are demo placeholders** (R. Das, A. Sharma) from `config/default.yaml`. Wiki approvals so far are AI approvals (item 19), not engineer approvals.
14. **Not built:**
    - Volve DDR XML ingest (licence access);
    - "Send for review" on the brief;
    - Dutch-language text rules (English patterns only);
    - Tesseract refuses a few extremely long log-strip pages, so their own text is kept.
15. **Hindsight: what the forewarned number means.**
    - Headline measures (live, 29 Sept 2026, after the leak fix and the AI review in item 18; 304 wells, 449 real problems, 36,776 layer cells): ranking accuracy AUC 0.86 (field average 0.69); problem layer flagged before the bit arrived 61.7 / 70.2 / 79.5 / 84.2 % at 6 / 10 / 15 / 20 alerts per well; right hazard in the layer's top 3: 74.4 % (random 37.5 %). Exact hazard at about 6 alerts per well: 193/449 (43 %), median 348 m ahead; the field average with the same alerts gets 86/449. The older figures below (438 problems) are kept as history.
    - AUC is flattered by the many easy layers with no problem at all; "79.5 % of problem layers flagged" costs 15 alerts per well. Both are shown with their trade-off.
    - **Fixed 28 Sept 2026:** the field base rate (the prior) used to include the tested well itself, a small leak in every earlier Hindsight number and in the leave-one-well-out Brier. The tested well and its sidetracks are now excluded; the numbers above are after the fix.
    - The ranker is trained on other wells only (grouped cross-validation); live mode uses the well's own reports only above the alert point. It assumes the planned formation column equals the recorded one, which flatters pre-drill results slightly.
    - Precision per alert is low (about 10 %), and FORGE (4 wells) shows no measured lift on its own.
    - Strict alerts (posterior ≥ 40 %) forewarn only 15 of 438 real problems (3.4 %). Their 73× lift comes from just 14 alerts, mostly in the small FORGE set, and a field-average baseline already reaches 66×.
    - The blind top-5 watch-list per well holds 137/438 (31 %, 4.4× chance), but ranking by the field-wide layer rate alone does about as well (133/438): nearby-well weighting adds little on this data.
    - 44 problems sit in layers missing from their well's formation column and can never be listed.
    - The stricter "elevated" rule flags nothing yet. Testable wells are Norway and USA only.
16. **India Analogs** use lithology and depth analogues from outside India. They are not Indian well records, and the fixes shown are scoped per well, not per interval.
17. **3D view assumptions.** Wells without a survey are drawn vertical (labelled "assumed vertical"). Positions are projected locally, which is valid within about 50 km.
18. **AI-reviewed events (28 Sept 2026).** The 1,851 low-confidence events in the review queue were reviewed by an AI pass (8 AI reviewers reading each verbatim sentence; brief in `docs/AI_REVIEW.md`), at the project lead's explicit request because no engineer was available. Result: 993 confirmed, 86 relabelled, 772 rejected; 20 depths added only when quoted verbatim from the sentence, 36 unverifiable auto-depths cleared. These events carry `method = ai_review` (reviewer "AI review, authorised by Jay Naik") and are **not** engineer-verified. Afterwards: 1,851 trusted events (1,079 AI-reviewed); Hindsight AUC 0.86, problem layer flagged ahead 79.5 % at 15 alerts per well and 84.2 % at 20; extraction recall on the AI-made gold set fell from 0.92 to 0.87 because some rule events the gold set counts were rejected.
19. **AI-approved wiki pages (29 Sept 2026).** At the project lead's explicit request (no engineer available), all 951 wiki pages were approved by `backend/scripts/approve_wiki_ai.py`. It re-ran the compiler's citation check on every page (every sentence must carry a citation; the compiler had already rejected unsupported numbers) and required at least one cited source; all 950 pending pages passed. Each approval is a normal noting para and git commit with reviewer "AI review, authorised by Jay Naik" and role "AI reviewer (not engineer-verified)". This checks form (citations present), not engineering judgement. A page whose content changes on a recompile goes back to draft.
20. **Volve daily drilling reports (30 Sept 2026).** 1,759 real daily reports from 23 Volve wellbores (Equinor release, republished on HuggingFace as `bengsoon/volve_alpaca`, CC-BY-2.0) were added as 23,447 timed activities.
    - Extraction on these reports found 654 problem events (269 flagged for review). Precision on a random sample of 40 trusted events is **0.75** (AI-labelled, pending human check; `data/eval/volve_ddr_events_check.csv`). The main remaining false hits are planned operations (setting plugs, completion and P&A steps) and normal torque figures.
    - Sodir publishes formation tops only for Volve's exploration wells (15/9-19 S, A, B), not the development "F" wells. For those, a formation is used only where the report line itself names it (86 activities); otherwise it is left unknown, never taken from a neighbouring well.
    - With these events the Hindsight test grew from 449 to 578 real problems on 306 wells. The headline moved: AUC 0.86 → **0.84**; problem layer flagged at 15 alerts per well 79.5 % → **78.4 %**; right hazard in top 3 74.4 % → **68.2 %**; exact hazard forewarned **222/578** (field average 113/578), median **394 m** ahead. These replace the figures in item 15.
    - Fixed the same day: the per-well blind view stored the learned alert flags for only one layer (a loop-indentation bug), so every well's view showed no alerts although the summary counted them. The headline numbers were never affected.
