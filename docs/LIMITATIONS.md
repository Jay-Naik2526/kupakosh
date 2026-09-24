# Limitations (read before quoting any number)

1. **Stand-in data.** Norwegian (Sodir) and US (Utah FORGE) public records. No Assam / Oil India data.
2. **Summaries, not diaries.** Sodir well histories under-record problems and cover exploration wells only.
   A Kupakosh rate is a rate of *recorded* problems; "no record" ≠ "no problem".
3. **Hazard model has no measured skill.** Leave-one-well-out Brier: model 0.002377 vs base rate 0.002378
   (41,848 formation × hazard cases, 0.24 % positive). The prior strength (100) was chosen on the same
   LOO data. The UI therefore shows rates with ranges and evidence counts, and "insufficient evidence"
   when n_eff < 3 — never a claim of prediction.
4. **Rule-based extraction** (no LLM key). Precision 0.90 / recall 0.92 on 50 lines; 13 % of sampled
   episodes were not real problems (e.g. "junk core", "a total loss of 28 days").
5. **Gold labels are AI-made** on real report lines and need human verification before any claim.
6. **Copilot is extractive**; its eval questions are templated, so 1.00 citation accuracy is optimistic.
7. **Depths are MD.** Sodir exploration wells have no public trajectory here; mud window and correlation
   are approximate for deviated wells. FORGE wells have full surveys (TVD shown on Command).
8. **Lithology patterns** for Norwegian units come from the lithostratigraphic lexicon (dominant rock type).
9. **Live look-ahead** only has two wells with sensor data (FORGE 16A/16B, 37 m apart) → it usually says
   "insufficient evidence", which is the honest answer.
10. **Not built:** Volve DDR XML ingest, OCR for scanned PDFs, LLM extraction pass, embeddings/pgvector,
    Postgres migrations, upload endpoint, WCR-vs-DDR auditor rule (R5), Playwright tests, full Hindi text.
11. Demo reviewer names (R. Das, A. Sharma) are placeholders from `config/default.yaml`.
