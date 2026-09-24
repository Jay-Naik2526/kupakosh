# Data report (P0) — what real data the prototype runs on

All data is public and used as a **stand-in** for Oil India data. Nothing is synthetic. Downloaded by
`backend/scripts/download_data.sh` on 24 Sept 2026.

## Sources actually loaded

| Source | What we took | Licence | Loaded |
|---|---|---|---|
| **Sodir FactPages** (Norwegian Offshore Directorate), CSV table exports | `wellbore_all_long`, `wellbore_formation_top`, `wellbore_casing_and_lot`, `wellbore_mud`, `wellbore_history`, `wellbore_document` | NLOD 2.0 | 9,840 wellbores (138 fields), 41,418 formation/group tops, 8,741 casing rows, 3,750 LOT/FIT (3,047 LOT + 703 FIT), 35,783 mud-weight checks, 1,979 well-history narratives → 50,453 sentences |
| **Utah FORGE 16A(78)-32** — GDR submission 1283 | daily drilling reports (PDF, WellEz), survey (xlsx), Pason 10-second sensor data (csv) | CC-BY 4.0 | 77 unique DDRs (duplicates removed by content hash), 623 time-breakdown activities, 422 survey stations, 101,204 sensor samples (1-min, 25 Oct 2020 → 5 Jan 2021) |
| **Utah FORGE 16B(78)-32** — GDR submission 1516 | daily drilling reports (PDF, RIMBase), survey (txt), Pason 10-second data (zip, 1.8 GB) | CC-BY 4.0 | 88 unique DDRs, 1,383 activities, 850 survey stations, 248,968 sensor samples (30-s, 26 Apr → 21 Jul 2023) |

## Sources in SPEC.md that were NOT used, and why

| Source | Status |
|---|---|
| Equinor **Volve** DDR XML / WITSML | Now distributed only via Databricks Marketplace (account + licence acceptance). Not accessible from the build session. The Volve wells (15/9-F-*) are present **from Sodir** (location, tops, casing/LOT), but without their DDRs. |
| Volve real-time CSV (UiS, Tunkiel) | `ux.uis.no/~atunkiel/file_list.html` returned HTTP 403. Replaced by Utah FORGE Pason data (real, similar channels). |
| FORCE 2020 | Reachable, not yet ingested (would add well logs / lithology for correlation). |
| NOPIMS (Australia) scanned WCRs | Needs registration → OCR path not exercised. **OCR (Tesseract) is not installed / not built.** |
| India NDR (DGH) | Requires academic registration letter; deployment path only. |

## Checks from the P0 acceptance list

| Check | Result |
|---|---|
| Activity fields / DDR structure | FORGE DDRs have a time-breakdown table (from, to, hours, code, text, NPT flag on 16B), report MD, mud check, casing table, surveys. Parsed for both vendor formats. |
| % report lines with a depth | Of 1,097 extracted events, 538 (49 %) carry a depth; 528 resolve to a formation. |
| LOT/FIT availability | 3,750 Sodir LOT/FIT results with EMW; 3,730 assigned to a formation → **USP3 (mud window) = GO**. |
| Pit volume / ROP non-zero | Sensor data: pit volume > 0 in 349,903 of 350,172 samples; ROP > 0 in 42,592 (on-bottom drilling). **Replay = GO.** |
| DDR ↔ real-time overlap | FORGE 16A and 16B: DDRs and sensor data cover the same days → auditor rules R1/R6 run. **USP4 (auditor) = GO** (also R2/R3 on Sodir text vs tables). |
| Well-ID variants | `canonical()` handles Sodir, Volve spellings (`NO 15/9-F-5`, `15_9-F-5`, `15$47$9-F-5`) and FORGE spellings; unit-tested. |

## Validation applied (rejected, never "fixed")

- Mud weight outside 7–20 ppg: 645 Sodir mud rows rejected; depth > well TD: 286 rejected.
- LOT/FIT density `0.00` = "no test" → not loaded.
- Event depths outside [0, TD] dropped; feet numbers followed by FPH / ft-lbs / "(…') total" are rates or footage, not depths.
- FORGE formation tops are taken only from verbatim report lines (`config/forge_tops.yaml`); a top whose quote is not found in the PDFs is rejected.

## Important property of the data

Sodir well histories are **summaries** written after the well, covering exploration wells only. They
mention problems selectively. Therefore every rate in Kupakosh is a rate of **recorded** problems and
"no record" never means "no problem".
