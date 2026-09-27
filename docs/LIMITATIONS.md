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
13. **Reviewer names are demo placeholders** (R. Das, A. Sharma) from `config/default.yaml`. No wiki page is approved until a person approves it.
14. **Not built:**
    - Volve DDR XML ingest (licence access);
    - "Send for review" on the brief;
    - Dutch-language text rules (English patterns only);
    - Tesseract refuses a few extremely long log-strip pages, so their own text is kept.
15. **Hindsight has thin coverage and a small FORGE-driven lift.**
    - It forewarns only 15 of 438 real problems (3.4 %). Its 81× lift comes from just 14 alerts, mostly in the small FORGE set, and a field-average baseline already reaches 74×.
    - The stricter "elevated" rule flags nothing yet. Testable wells are Norway and USA only.
16. **India Analogs** use lithology and depth analogues from outside India. They are not Indian well records, and the fixes shown are scoped per well, not per interval.
17. **3D view assumptions.** Wells without a survey are drawn vertical (labelled "assumed vertical"). Positions are projected locally, which is valid within about 50 km.
