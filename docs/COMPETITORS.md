# Competitor scan: PS 26121 public repos (27 Sept 2026)

**How we searched.**
- **Queries:** 168 keyword combinations in GitHub repository search. The ID variants were 26121, SIH26121 and PS 26121. The topics were Oil India, eRTMAC, offset well(s), daily drilling report, drilling hazard/risk, stuck pipe, lost circulation, drilling knowledge/copilot/RAG and wellbore. Each was also run with SIH, SIH 2026 and hackathon added.
- **Other searches:** README text search for the same IDs and phrases, and GitHub topics (sih2026 and similar) combined with oil or drilling.
- **Filtering:** 1,854 candidates, pre-screened to 752. For each, the description and README were read. A repo counts for PS 26121 only when its README names eRTMAC or offset wells, or 26121 together with drilling or wells.
- **Result:** **29 repos**. Others dropped: 9 false hits (stock, crypto and socket repos), plus 12 repos for other Oil India problem statements (26120, 26122, 26165).
- **Analysis:** each of the 29 was cloned read-only and judged from the **code**, not the README. A feature claimed in the README but missing from the code is marked "claimed". Every live link was checked with an HTTP request. No competitor code was copied into Kupakosh (SPEC.md §0.8).

## Headline
- **No competitor has any of Kupakosh's four core USPs:**
  - an engineer-approved, versioned Well Wiki;
  - fixes ranked by *outcome* with a Wilson lower bound;
  - a mud-weight window from LOT/FIT;
  - a report-conflict auditor.
- **None has Hindi.**
- **None uses real public data from more than 3 sources.** Kupakosh uses 8 countries, including real Indian public records.
- **Most competitors (about 17 of 29) run on synthetic or mock data.** Several give it names like "OIL-W###" or "@oil-india.in" that imply real Oil India data. A few have large gaps between what the README claims and what the code does:
  - a 57-line hand-tuned formula sold as "PINN + XGBoost + Llama-70B";
  - a "RAG assistant" that is a 6-answer lookup table citing PDFs that don't exist;
  - "Volve" sample PDFs that are fabricated.
- **Where they lead:**
  1. **Live deployments.** 6 repos have a working public link; Kupakosh has none yet.
  2. **Classic ML with explanations** (XGBoost + SHAP).
  3. **Visual polish:** 3D trajectories, scripted demo tours.
  4. **Safety guardrails:** prompt-injection checks and login/roles.

## Live links (checked 27 Sept 2026)
| Repo | Link | Status |
|---|---|---|
| CB-acc-tech/Hackathon2026 (RigMind) | https://rigmind-ten.vercel.app | up |
| IqraS-gif/DrillSight | https://drill-sight.vercel.app | up |
| SurveAnil/geodrill-ai | https://geodrill-ai.vercel.app | up |
| vidhiii1711/eRTMAC-NWIS | https://e-rtmac-nwis.vercel.app | up |
| rudrachauhan12999/eRTMAC-NWIS | https://ertmac-nwis-pi.vercel.app | up |
| nikunjgoyal0344-coder/eRTMAC-NWIS | https://frontend-kappa-roan-16.vercel.app | up |
| tech-nitin/wellwise | https://wellwise-rho.vercel.app | up (3D animation only; titled "Oil India Limited Control Room") |
| Nishchay-k/OIL | https://oil-linux4.vercel.app | down (Vercel login wall) |

The other 21 repos have no deployment.

## Feature matrix (judged from code)
Key: ● built · ◐ partial · ◌ claimed in the README, not in the code · · absent

| Repo | Map+radius | Report extraction | Chat / RAG | Risk prediction | Real-time | Formation correlation | Fix ranked by outcome | Approved / versioned KB | Mud window / LOT | Report auditor | Pre-drill PDF | Measured accuracy | Hindi | Tests | Upload | Knowledge graph | Data |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Kupakosh (ours)** | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | · | real, 8 countries, cited |
| [124priyanka/OilDrill-P4](https://github.com/124priyanka/OilDrill-P4) | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | synthetic |
| [bishopcommander/OffsetEye](https://github.com/bishopcommander/OffsetEye) | ● | ● | ● | · | · | ● | · | · | · | · | · | · | · | · | ● | · | synthetic |
| [BishrM/eRTMAC-NWIS](https://github.com/BishrM/eRTMAC-NWIS) | ◐ | ◐ | · | · | · | · | · | · | · | · | · | · | · | ● | · | · | real |
| [CB-acc-tech/Hackathon2026](https://github.com/CB-acc-tech/Hackathon2026) | ● | ◐ | ◐ | · | · | ◐ | · | · | · | · | · | · | · | · | ● | · | synthetic |
| [dhanwanth-dh/eRTMAC--NWIS-Nearby-Wells-Intelligence-Offset-Decision-Support](https://github.com/dhanwanth-dh/eRTMAC--NWIS-Nearby-Wells-Intelligence-Offset-Decision-Support) | ● | ◐ | ● | ● | · | ◐ | · | · | · | · | · | ● | · | · | ● | · | synthetic |
| [Het2239/SIH-2026-eRTMAC-NWIS](https://github.com/Het2239/SIH-2026-eRTMAC-NWIS) | ◌ | ◌ | ◌ | ◌ | ◌ | ◌ | · | · | · | · | · | · | · | · | ◌ | ◌ | synthetic |
| [IqraS-gif/DrillSight](https://github.com/IqraS-gif/DrillSight) | ● | ◐ | ● | ● | · | ◐ | · | · | ◌ | · | · | · | · | · | ● | · | synthetic |
| [jaldewarvaibhavi-web/ertmac-nwis](https://github.com/jaldewarvaibhavi-web/ertmac-nwis) | ● | ● | ● | · | · | ● | ◐ | · | · | · | · | ● | · | ● | ◐ | · | real + synthetic |
| [kriishna9/eRTMAC-NWIS](https://github.com/kriishna9/eRTMAC-NWIS) | ◐ | ● | ◐ | ● | · | ◐ | · | · | · | · | · | ● | · | · | · | · | real |
| [ManthanTerse/SpaceX-NWIS](https://github.com/ManthanTerse/SpaceX-NWIS) | ● | ● | ● | · | · | ● | · | · | · | · | · | · | · | · | ◐ | · | synthetic |
| [n3ssdub3y/SIH_2026_PLANNS](https://github.com/n3ssdub3y/SIH_2026_PLANNS) | ● | ● | ● | ● | ● | ● | ◐ | · | · | · | · | ● | · | ● | ● | ● | real |
| [nikunjgoyal0344-coder/eRTMAC-NWIS](https://github.com/nikunjgoyal0344-coder/eRTMAC-NWIS) | ◌ | ◌ | ◌ | · | · | ◐ | · | · | · | ◌ | · | · | · | · | · | · | synthetic |
| [Nishchay-k/OIL](https://github.com/Nishchay-k/OIL) | ◌ | · | ◌ | · | · | · | · | ◐ | · | · | · | · | · | · | ◌ | · | synthetic |
| [oki-dokii/baithe-baithe-bore-hua-karna-hai-kuch-kaam](https://github.com/oki-dokii/baithe-baithe-bore-hua-karna-hai-kuch-kaam) | ● | ● | ● | · | · | ● | ◐ | · | · | · | · | ● | · | ● | ● | · | real + synthetic |
| [pallavi-a11y/eRTMAC-NWIS](https://github.com/pallavi-a11y/eRTMAC-NWIS) | ● | ● | ● | · | ◐ | · | · | · | · | · | · | · | · | ◐ | ● | · | synthetic |
| [Physics0070/nwis](https://github.com/Physics0070/nwis) | ● | ● | ● | · | · | ● | ◐ | · | · | · | · | ● | · | ● | · | · | real |
| [rudrachauhan12999/eRTMAC-NWIS](https://github.com/rudrachauhan12999/eRTMAC-NWIS) | ● | ● | ● | ● | · | ◐ | · | · | ◐ | · | ● | · | · | ● | ● | · | real + synthetic |
| [rudraprasad333/eRTMAC-NWIS](https://github.com/rudraprasad333/eRTMAC-NWIS) | ● | ◌ | · | · | · | ● | · | · | · | · | · | · | · | · | ◌ | · | synthetic |
| [Shank2Stack/eRTMAC-NWIS](https://github.com/Shank2Stack/eRTMAC-NWIS) | · | · | · | ● | ◐ | · | · | · | · | · | · | · | · | ● | · | · | real + synthetic |
| [shaurya212121/BoreX](https://github.com/shaurya212121/BoreX) | ● | ◐ | · | · | · | ◐ | · | · | · | · | ● | ◌ | · | ◐ | · | · | synthetic |
| [Starlitakash/ERTMAC-NWS](https://github.com/Starlitakash/ERTMAC-NWS) | ● | ● | ● | ● | · | ● | · | · | · | · | · | ● | · | ● | · | · | synthetic |
| [sudhanshu-0109/DrillIntel](https://github.com/sudhanshu-0109/DrillIntel) | ◌ | ◌ | ● | · | · | ◌ | · | · | · | · | · | · | · | ● | ◌ | · | synthetic |
| [SujalPatil21/Drill-Insight](https://github.com/SujalPatil21/Drill-Insight) | ● | · | ◌ | ◐ | · | ◌ | · | · | · | · | · | · | · | · | · | · | synthetic |
| [SurveAnil/geodrill-ai](https://github.com/SurveAnil/geodrill-ai) | ● | ● | ● | · | ◐ | ● | ◐ | · | · | · | · | · | · | ● | ● | ● | synthetic |
| [suryanshkota07-oss/AROH-drilling-intelligence](https://github.com/suryanshkota07-oss/AROH-drilling-intelligence) | ◌ | · | · | ◐ | · | ◐ | · | · | · | · | · | · | · | ● | · | · | synthetic |
| [tarumishra22/eRTMAC-NWIS](https://github.com/tarumishra22/eRTMAC-NWIS) | ● | ◐ | ● | · | · | ● | · | · | · | · | · | · | · | · | ● | · | synthetic |
| [tech-nitin/wellwise](https://github.com/tech-nitin/wellwise) | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | synthetic |
| [vidhiii1711/eRTMAC-NWIS](https://github.com/vidhiii1711/eRTMAC-NWIS) | ● | ● | ● | · | · | ◐ | ◐ | · | · | · | · | ● | · | ◐ | ● | · | synthetic |
| [xarjunpatil/SIH26121-eRTMAC-NWIS-Nearby-Wells-Intelligence-System-An-AI-Powered-Offset-Well](https://github.com/xarjunpatil/SIH26121-eRTMAC-NWIS-Nearby-Wells-Intelligence-System-An-AI-Powered-Offset-Well) | · | · | · | · | · | · | · | · | · | · | · | · | · | ● | · | · | synthetic |

## All 29 repos, strongest first
| Repo | Live link | Status | Data | Size | Verdict |
|---|---|---|---|---|---|
| [n3ssdub3y/SIH_2026_PLANNS](https://github.com/n3ssdub3y/SIH_2026_PLANNS) | — | no homepage; module HTML dashboards are  | real |  | The strongest and most directly competitive repo in this batch: real Volve/FORCE2020 data, real-time replay, statistically rigorous risk/anomaly methods (Wilson CI, CUSUM), a genui |
| [rudrachauhan12999/eRTMAC-NWIS](https://github.com/rudrachauhan12999/eRTMAC-NWIS) | https://ertmac-nwis-pi.vercel.app | up | real + synthetic | ~15,300 lines | The strongest all-round competitor in this batch - live, tested, and unusually transparent about data provenance and limitations - but it has none of our core differentiators (comp |
| [SurveAnil/geodrill-ai](https://github.com/SurveAnil/geodrill-ai) | https://geodrill-ai.vercel.app | up | synthetic |  | The broadest 7-layer architecture in this batch, with a real knowledge-graph + hybrid RAG + multi-provider LLM stack and unusually honest rule-based risk disclosure, but its Volve- |
| [oki-dokii/baithe-baithe-bore-hua-karna-hai-kuch-kaam](https://github.com/oki-dokii/baithe-baithe-bore-hua-karna-hai-kuch-kaam) | — | no link | real + synthetic | ~8,573 lines | The strongest engineering-quality competitor found so far (real tests, real data-integrity gates, honest self-assessment) but functionally behind our product on the five USPs - the |
| [Starlitakash/ERTMAC-NWS](https://github.com/Starlitakash/ERTMAC-NWS) | — | no live link | synthetic | ~13,400 lines | The most test-disciplined and safety-conscious repo in the batch (142 tests, guardrails, human sign-off, train/validation well split), but it is a fully synthetic demo with no real |
| [jaldewarvaibhavi-web/ertmac-nwis](https://github.com/jaldewarvaibhavi-web/ertmac-nwis) | — | no homepage / not deployed | real + synthetic |  | The most methodologically honest of this batch — real LOO-validated RF model with disclosed insufficient-evidence gating and a genuine pytest suite — but feature-thin next to a Wel |
| [Physics0070/nwis](https://github.com/Physics0070/nwis) | — | no homepage / not deployed | real |  | The strongest and most honest of all competitors reviewed — real multi-country data, genuine ML with proper held-out evaluation and explicit 'insufficient evidence' gating — but it |
| [vidhiii1711/eRTMAC-NWIS](https://github.com/vidhiii1711/eRTMAC-NWIS) | https://e-rtmac-nwis.vercel.app | up | synthetic |  | The most ML-mature and best-explained risk model in this batch (real XGBoost + SHAP + well-level split + honest synthetic-data disclaimer) paired with a genuine cited RAG assistant |
| [dhanwanth-dh/eRTMAC--NWIS-Nearby-Wells-Intelligence-Offset-Decision-Support](https://github.com/dhanwanth-dh/eRTMAC--NWIS-Nearby-Wells-Intelligence-Offset-Decision-Support) | — | no live link | synthetic | ~7,100 lines | A competent full ML+RAG+dashboard build with real engineering effort, but entirely fictitious data and unvalidated (likely leaky) 'perfect' accuracy claims - it will not survive sc |
| [bishopcommander/OffsetEye](https://github.com/bishopcommander/OffsetEye) | — | no link | synthetic | ~6,547 lines | A well-architected but data-thin MVP shell; its 'real Volve data' headline claim does not hold up once you check what's actually committed to the repo - not a strong threat on data |
| [IqraS-gif/DrillSight](https://github.com/IqraS-gif/DrillSight) | https://drill-sight.vercel.app | up | synthetic |  | A visually polished, feature-broad prototype (ML risk + RAG chatbot + knowledge base + digitization + voice notes) but with unverifiable ML data provenance, hand-authored (not cita |
| [pallavi-a11y/eRTMAC-NWIS](https://github.com/pallavi-a11y/eRTMAC-NWIS) | — | no homepage; local-only | synthetic |  | A technically interesting, fully-local VLM-based document pipeline with real citations and refusal, but currently a thin, low-data-volume prototype (2 documents) rather than a broa |
| [kriishna9/eRTMAC-NWIS](https://github.com/kriishna9/eRTMAC-NWIS) | — | no live link | real | ~4,800 lines | One of the few repos using genuinely real (Volve WITSML) data end-to-end, which is worth noting, but the app is disjointed (broken map, unintegrated frontend/backend/vendored subpr |
| [ManthanTerse/SpaceX-NWIS](https://github.com/ManthanTerse/SpaceX-NWIS) | ['https://altair-viz.github.io/', 'https://python-visualization.github.io/folium/', 'https://rapidfuzz.github.io/RapidFuzz/'] | up | synthetic | ~1,688 lines | A small, honest, single-file-app synthetic-data prototype with a real RandomForest model and grounded chatbot instructions - competent craftsmanship but low ambition and no real-da |
| [tarumishra22/eRTMAC-NWIS](https://github.com/tarumishra22/eRTMAC-NWIS) | — | no link | synthetic | ~1,345 lines | Already tracked in our own competitor list; a small, honestly-scoped-in-code (if inflated-in-README) prototype with genuine but shallow vector RAG - low overall threat. |
| [CB-acc-tech/Hackathon2026](https://github.com/CB-acc-tech/Hackathon2026) | https://rigmind-ten.vercel.app | up | synthetic |  | A working full-stack demo with genuinely bad data-honesty practices (fake wells attributed to Oil India) and README claims well ahead of the code; weak as a credibility threat but  |
| [shaurya212121/BoreX](https://github.com/shaurya212121/BoreX) | — | no homepage / not deployed | synthetic |  | Strong visual/UX polish (3D, tactical dark theme) wrapped around an entirely synthetic, formula-based backend with almost none of the evidentiary or knowledge-management depth (Wik |
| [Shank2Stack/eRTMAC-NWIS](https://github.com/Shank2Stack/eRTMAC-NWIS) | — | no homepage found; local dev only | real + synthetic |  | Lowest threat of this batch to our specific USPs - a generically competent ML anomaly dashboard, but it does not implement the map/radius, report-extraction, formation-correlation, |
| [suryanshkota07-oss/AROH-drilling-intelligence](https://github.com/suryanshkota07-oss/AROH-drilling-intelligence) | — | no live link | synthetic | ~720 lines | An early-stage, honestly-labelled synthetic prototype with a promising 'analogue matching + why-this-risk' framing, but functionally thin (no map, no RAG, no live replay) and not a |
| [rudraprasad333/eRTMAC-NWIS](https://github.com/rudraprasad333/eRTMAC-NWIS) | — | no link | synthetic | ~8,136 lines | The most polished-looking UI/demo-tour in this batch, but its core 'grounded RAG' claim is fabricated (hardcoded canned answers with fake citations) - a strong warning sign for jud |
| [sudhanshu-0109/DrillIntel](https://github.com/sudhanshu-0109/DrillIntel) | — | no link | synthetic | ~13,445 lines | Largest codebase and best real-data roadmap in this batch, backed by a real test suite and lexical RAG engine, but still runs entirely on synthetic seed data in practice and uses a |
| [BishrM/eRTMAC-NWIS](https://github.com/BishrM/eRTMAC-NWIS) | — | no homepage/deployed link found | real |  | A well-engineered but narrow skeleton (similarity ranking + map only) with real Volve/Sodir data and strong anti-fabrication discipline, but it does not yet address most of the PS' |
| [SujalPatil21/Drill-Insight](https://github.com/SujalPatil21/Drill-Insight) | — | no homepage found | synthetic |  | Real geospatial plumbing wrapped around a fabricated Assam-flavored dataset and hardcoded/mocked risk and RAG endpoints - functionally a demo shell rather than working intelligence |
| [xarjunpatil/SIH26121-eRTMAC-NWIS-Nearby-Wells-Intelligence-System-An-AI-Powered-Offset-Well](https://github.com/xarjunpatil/SIH26121-eRTMAC-NWIS-Nearby-Wells-Intelligence-System-An-AI-Powered-Offset-Well) | — | no live link | synthetic | ~620 lines | A minimal random-data-generator REST API and static dashboard dressed up with an elaborate whitepaper; essentially no working intelligence and no competitive threat. |
| [Nishchay-k/OIL](https://github.com/Nishchay-k/OIL) | https://oil-linux4.vercel.app | placeholder/down - resolves to a Vercel  | synthetic |  | A wireframe/UI-only click-through prototype, self-described as such - no working intelligence, data, or backend; live demo is currently broken. Minimal competitive threat. |
| [nikunjgoyal0344-coder/eRTMAC-NWIS](https://github.com/nikunjgoyal0344-coder/eRTMAC-NWIS) | https://frontend-kappa-roan-16.vercel.app | up | synthetic | ~130 lines | The largest claims-to-code gap in this batch — an impressively worded README describing an enterprise/defense-grade AI platform sitting on top of a small hardcoded-constant formula |
| [124priyanka/OilDrill-P4](https://github.com/124priyanka/OilDrill-P4) | — | no live link | synthetic |  | Not a real competitor - a bare synthetic dataset with no application, no threat. |
| [Het2239/SIH-2026-eRTMAC-NWIS](https://github.com/Het2239/SIH-2026-eRTMAC-NWIS) | — | no link | synthetic |  | Pure scaffold - no working functionality of any kind; negligible competitive threat as-is. |
| [tech-nitin/wellwise](https://github.com/tech-nitin/wellwise) | https://wellwise-rho.vercel.app | up | synthetic |  | Not a competing product - a 3D visualization shell with no data, logic, or backend; zero threat to any of our USPs, but worth noting its live page's 'Oil India Limited Control Room |

## The 5 real threats and how Kupakosh answers each
1. **n3ssdub3y/SIH_2026_PLANNS** (strongest).
   - **What it has:** real Volve, FORCE 2020 and FORGE data; a Wilson interval on *analogue match rates*; CUSUM/z-score anomalies; a cited GraphRAG with refusal; PaddleOCR; tests.
   - **Our answer:** our Wilson bound ranks *which fix worked*, not how similar an analogue well is. We also have an approved and versioned wiki, the mud window, the report auditor, 8 countries of data, OCR with confidence scaling, a review queue, and Hindi.
2. **Physics0070/nwis.**
   - **What it has:** real FORCE 2020, Volve and Sodir data, held-out ML evaluation, and "hybrid indicator" gating, the same honesty stance as ours.
   - **Our answer:** it has no wiki, ledger, mud window, auditor or deployment.
3. **rudrachauhan12999/eRTMAC-NWIS.**
   - **What it has:** live; tested (13 test files); a `sourceType`/`isSimulation` provenance tag on every record; confidence-gated RAG.
   - **Our answer:** every fact carries a resolvable `source_ref` down to the page and line, and the REPLAY stamp. Its data is mostly synthetic.
4. **vidhiii1711/eRTMAC-NWIS.**
   - **What it has:** live; 5 XGBoost models with SHAP and a well-level train/test split.
   - **Weakness:** 100 % synthetic training data (disclosed).
   - **Our answer:** a probability with an 80 % range and n_eff, from real offset wells, with the evidence wells listed.
5. **oki-dokii/…** and **Starlitakash/ERTMAC-NWS.**
   - **What they have:** strong engineering: pytest and Playwright (oki-dokii), 142 tests and prompt-injection guardrails (Starlitakash).
   - **Our answer:** 36 backend tests, 14 Playwright tests including a WCAG AA contrast check, and 5 unit tests.

## What they have that we don't, and whether to add it
| Idea (seen in) | Worth it? | Note |
|---|---|---|
| **Public live demo link** (6 repos) | **Yes, top priority** | Judges click links. Deploy the one-port build (`make share`) to a host, or record a video. |
| Explainability panel, e.g. SHAP (vidhiii1711, dhanwanth-dh) | Maybe | We already list the evidence wells and prior per probability. Surface it as a clear "Why this number" panel. |
| What-if counterfactual (Shank2Stack) | Maybe | "If mud weight were X, the mud window says…" is cheap on top of the mud window. |
| Prompt-injection / unsafe-command guardrails (Starlitakash) | Small | Our copilot is extractive (no LLM), so injection risk is low. Say this in the pitch. |
| Login and roles (CB-acc-tech, Shank2Stack) | Small | We have demo users. Real auth matters only for deployment. |
| 3D trajectory viewer (CB-acc-tech, BoreX, wellwise) | Low | Looks good, but SPEC.md §11 forbids dark 3D "command centre" styling. |
| OCR human-correction UI (pallavi-a11y) | Maybe | We have a review queue for events. OCR text correction is not built. |
| Voice notes (DrillSight) | No | SPEC.md §3 says never make it a headline. |
| Knowledge graph (PLANNS, geodrill-ai) | No | A common idea in other teams, not a USP (SPEC.md §3). |

## Pitch lines backed by this scan
- "Of 29 public PS 26121 projects, none ranks fixes by what actually worked, none has an engineer-approved wiki, a mud window or a report auditor, and none speaks Hindi."
- "Most run on synthetic wells. Kupakosh runs on real public records from 8 countries, and every number opens the exact report line it came from."

Clones and the per-repo JSON checklists (20 items each, with evidence) are in the build session scratch folder. They were not copied into this repo.

## Second scan (30 Sept 2026)

- **How:** GitHub repository search (20 phrases, repos updated since 20 Sept) plus README search (7 phrases). A candidate counts only if its README or description names eRTMAC, 26121 or "nearby wells intelligence" **and** mentions drilling, wells or oil. Noise from USGS's unrelated water system, also called "NWIS", was removed by hand.
- **Result:** **143 PS 26121 repos, including ours** (123 new since 27 Sept). **45 list a live link: 40 up, 5 down or blocked.**
- **Code read:** the 13 largest new repos were cloned read-only and their code searched. None contains a held-out-well or blind evaluation (AUC, backtest, leave-one-well-out, GroupKFold, held-out). Most generate their data (numpy random, Faker or seed scripts), several with Upper Assam formation names.
- **Details:** what this changes for our pitch is in `docs/FINALE_USPS.md`. No competitor code was copied.

| Repo | Live link | HTTP (30 Sept) |
|---|---|---|
| [Agniv-ux/Sih_26_121](https://github.com/Agniv-ux/Sih_26_121) | https://sih-26-121.vercel.app | 200 |
| [Ash835/nwis-prototype](https://github.com/Ash835/nwis-prototype) | https://nwis-prototype.vercel.app | 200 |
| [CB-acc-tech/Hackathon2026](https://github.com/CB-acc-tech/Hackathon2026) | https://rigmind-ten.vercel.app | 200 |
| [Chandermani-web/SIH_26121](https://github.com/Chandermani-web/SIH_26121) | https://ertmac.vercel.app | 200 |
| [DaddyYoda7/NWIS-Across-Indian-Basins](https://github.com/DaddyYoda7/NWIS-Across-Indian-Basins) | https://nwis-across-indian-basins.vercel.app | 200 |
| [DataIntegrationGroup/DataIntegrationEngine](https://github.com/DataIntegrationGroup/DataIntegrationEngine) | https://weaver.newmexicowaterdata.org/die | 200 |
| [HarshProgrammingworks/drilllens](https://github.com/HarshProgrammingworks/drilllens) | https://drilllens.vercel.app | 200 |
| [IqraS-gif/DrillSight](https://github.com/IqraS-gif/DrillSight) | https://drill-sight.vercel.app | 200 |
| [MayurKolekar03/eRTMAC-NWIS-Nearby-Wells-Intelligence-System](https://github.com/MayurKolekar03/eRTMAC-NWIS-Nearby-Wells-Intelligence-System) | https://e-rtmac-nwis-nearby-wells-intellige.vercel.app | 200 |
| [Meghanareddy2007/DRILLNEX](https://github.com/Meghanareddy2007/DRILLNEX) | https://drillnex-frontend.vercel.app | 200 |
| [MradulSingh109/ProjectAlteration](https://github.com/MradulSingh109/ProjectAlteration) | https://projectalteration-brown.vercel.app | 200 |
| [Nishchay-k/OIL](https://github.com/Nishchay-k/OIL) | https://oil-linux4.vercel.app | 200 |
| [Nithish-1622/NWIS](https://github.com/Nithish-1622/NWIS) | https://wellvista-pied.vercel.app | 200 |
| [SathvikaSedimbi/NWIS](https://github.com/SathvikaSedimbi/NWIS) | https://nwis-beige.vercel.app | 200 |
| [Shrey0604/SIH_2026](https://github.com/Shrey0604/SIH_2026) | https://sih-2026-pi-swart.vercel.app | 200 |
| [SurveAnil/geodrill-ai](https://github.com/SurveAnil/geodrill-ai) | https://geodrill-ai.vercel.app | 200 |
| [Udaymakhija07/nwis-oil-india](https://github.com/Udaymakhija07/nwis-oil-india) | https://nwis-oil-india-five.vercel.app | 200 |
| [ab-rar-6024/NWIS](https://github.com/ab-rar-6024/NWIS) | https://nwis-ten.vercel.app | 200 |
| [adityasri2501/Oil-India-Limited](https://github.com/adityasri2501/Oil-India-Limited) | https://oil-india-limited.vercel.app | 404 |
| [aryabailur/sih26121](https://github.com/aryabailur/sih26121) | https://sih26121.vercel.app | 200 |
| [ashishsawkar2/SIH](https://github.com/ashishsawkar2/SIH) | https://ertmac-nwis-topaz.vercel.app | 200 |
| [ashishsawkar2/SIH2](https://github.com/ashishsawkar2/SIH2) | https://sih-ash-3ddf.vercel.app | 200 |
| [bishopcommander/OffsetEye](https://github.com/bishopcommander/OffsetEye) | https://offset-eye-client.vercel.app | 200 |
| [codexaras/nwis](https://github.com/codexaras/nwis) | https://nwis-sable.vercel.app | 307 |
| [cyanheads/usgs-water-mcp-server](https://github.com/cyanheads/usgs-water-mcp-server) | https://www.npmjs.com/package/@cyanheads/usgs-water-mcp-server | 403 |
| [divyanshikaushal/nwis-portal](https://github.com/divyanshikaushal/nwis-portal) | https://nwis-portal.vercel.app | 200 |
| [grv-io/sih2026-nwis-offset-well-intelligence](https://github.com/grv-io/sih2026-nwis-offset-well-intelligence) | https://grv-io.github.io/sih2026-nwis-offset-well-intelligence/ | 200 |
| [harshjadon07/NWIS-sih](https://github.com/harshjadon07/NWIS-sih) | https://nwis-sih-nine.vercel.app | 404 |
| [heera0812/DrillSarthi](https://github.com/heera0812/DrillSarthi) | https://drill-sarthi.vercel.app | 200 |
| [ian-cuh/sih-nwis](https://github.com/ian-cuh/sih-nwis) | https://sih-nwis.vercel.app | 404 |
| [nikunjgoyal0344-coder/NWIS-Solution-](https://github.com/nikunjgoyal0344-coder/NWIS-Solution-) | https://nwis-solution.vercel.app | 200 |
| [nikunjgoyal0344-coder/eRTMAC-NWIS](https://github.com/nikunjgoyal0344-coder/eRTMAC-NWIS) | https://frontend-kappa-roan-16.vercel.app | 200 |
| [nishanth418/hostelmanagementsystem](https://github.com/nishanth418/hostelmanagementsystem) | https://hostel-management-system-database-s.vercel.app | 200 |
| [niteshpaul99-ctrl/nwis-ai](https://github.com/niteshpaul99-ctrl/nwis-ai) | https://nwis-ai-five.vercel.app | 200 |
| [omshingade06/sih](https://github.com/omshingade06/sih) | https://geolookahead-sigma.vercel.app | 200 |
| [prasadjh-074/ertmac-nwis-sih](https://github.com/prasadjh-074/ertmac-nwis-sih) | https://ertmac-nwis-sih.vercel.app | 200 |
| [pratham1232/Oil-India](https://github.com/pratham1232/Oil-India) | https://oil-india-398b.vercel.app | 200 |
| [priy-anshugupta/SRISHTI-AI](https://github.com/priy-anshugupta/SRISHTI-AI) | https://srishti-ai-ruby.vercel.app | 200 |
| [rohitchaudhari045-eng/Well-Nexus](https://github.com/rohitchaudhari045-eng/Well-Nexus) | https://well-nexus-xi.vercel.app | 200 |
| [rudrachauhan12999/eRTMAC-NWIS](https://github.com/rudrachauhan12999/eRTMAC-NWIS) | https://ertmac-nwis-pi.vercel.app | 200 |
| [sivatce27-ops/121](https://github.com/sivatce27-ops/121) | https://nwis-khaki.vercel.app | 200 |
| [tech-nitin/wellwise](https://github.com/tech-nitin/wellwise) | https://wellwise-rho.vercel.app | 200 |
| [tharunsrisanth07-dotcom/well-badger](https://github.com/tharunsrisanth07-dotcom/well-badger) | https://well-badger-one.vercel.app | 200 |
| [thor11223344/PetrolQ](https://github.com/thor11223344/PetrolQ) | https://petrol-q.vercel.app | 200 |
| [vidhiii1711/eRTMAC-NWIS](https://github.com/vidhiii1711/eRTMAC-NWIS) | https://e-rtmac-nwis.vercel.app | 200 |

<details><summary>All 143 PS 26121 repos found (size in KB, language, last push)</summary>

| Repo | Size KB | Language | Last push |
|---|--:|---|---|
| [124priyanka/OilDrill-P4](https://github.com/124priyanka/OilDrill-P4) | 58 | - | 2026-08-28 |
| [2500030364/NWIS_SIH](https://github.com/2500030364/NWIS_SIH) | 5116 | PLpgSQL | 2026-09-30 |
| [5382Sarthak/Offset](https://github.com/5382Sarthak/Offset) | 68643 | JavaScript | 2026-09-27 |
| [Abhiraj07-07/eRTMAC-NWIS](https://github.com/Abhiraj07-07/eRTMAC-NWIS) | 0 | - | 2026-09-29 |
| [Abhiraj07-07/nwis-prototype](https://github.com/Abhiraj07-07/nwis-prototype) | 94 | TypeScript | 2026-09-28 |
| [Agniv-ux/Sih_26_121](https://github.com/Agniv-ux/Sih_26_121) | 3446 | TypeScript | 2026-09-29 |
| [Akgvs/SIH-NWIS](https://github.com/Akgvs/SIH-NWIS) | 109 | JavaScript | 2026-09-29 |
| [AnshulJangley/agate](https://github.com/AnshulJangley/agate) | 11462 | JavaScript | 2026-09-29 |
| [Arjundas08/eRTMAC-NWIS](https://github.com/Arjundas08/eRTMAC-NWIS) | 5609 | Python | 2026-09-30 |
| [Arpit1git/wellOil](https://github.com/Arpit1git/wellOil) | 76 | JavaScript | 2026-09-29 |
| [AryanSahu321/sih](https://github.com/AryanSahu321/sih) | 21 | - | 2026-09-24 |
| [Aryankushwaha-max/SIHPROTOTYPE](https://github.com/Aryankushwaha-max/SIHPROTOTYPE) | 2490 | Python | 2026-09-30 |
| [Ash835/nwis-prototype](https://github.com/Ash835/nwis-prototype) | 23 | CSS | 2026-09-29 |
| [Atharva130/smriti-nwis](https://github.com/Atharva130/smriti-nwis) | 5 | - | 2026-09-30 |
| [Ayush56GH/PetroNexus](https://github.com/Ayush56GH/PetroNexus) | 262 | Python | 2026-09-29 |
| [Bhanuveer/Synesis_SIH2026](https://github.com/Bhanuveer/Synesis_SIH2026) | 89 | JavaScript | 2026-09-29 |
| [BishrM/eRTMAC-NWIS](https://github.com/BishrM/eRTMAC-NWIS) | 217 | Python | 2026-09-26 |
| [CB-acc-tech/Hackathon2026](https://github.com/CB-acc-tech/Hackathon2026) | 196 | JavaScript | 2026-09-23 |
| [Chandermani-web/SIH_26121](https://github.com/Chandermani-web/SIH_26121) | 230 | TypeScript | 2026-09-29 |
| [CoderRaafey/eRTMAC-NWIS](https://github.com/CoderRaafey/eRTMAC-NWIS) | 154 | JavaScript | 2026-09-29 |
| [DaddyYoda7/NWIS-Across-Indian-Basins](https://github.com/DaddyYoda7/NWIS-Across-Indian-Basins) | 76179 | HTML | 2026-09-28 |
| [Dakshhhhh-ops/nwis](https://github.com/Dakshhhhh-ops/nwis) | 1121 | Python | 2026-09-29 |
| [DataIntegrationGroup/DataIntegrationEngine](https://github.com/DataIntegrationGroup/DataIntegrationEngine) | 1647 | Python | 2026-09-28 |
| [HarshProgrammingworks/drilllens](https://github.com/HarshProgrammingworks/drilllens) | 239 | Python | 2026-09-26 |
| [Het2239/SIH-2026-eRTMAC-NWIS](https://github.com/Het2239/SIH-2026-eRTMAC-NWIS) | 155 | Python | 2026-09-20 |
| [HimanshuGit3/SMRITI_WELL](https://github.com/HimanshuGit3/SMRITI_WELL) | 4995 | Python | 2026-09-28 |
| [IqraS-gif/DrillSight](https://github.com/IqraS-gif/DrillSight) | 111067 | JavaScript | 2026-09-12 |
| [Jay-Naik2526/kupakosh](https://github.com/Jay-Naik2526/kupakosh) | 61805 | Python | 2026-09-29 |
| [Lucky482-art/well_discovery](https://github.com/Lucky482-art/well_discovery) | 131 | TypeScript | 2026-09-30 |
| [MAYnk111/EKANSH_eRTMAC](https://github.com/MAYnk111/EKANSH_eRTMAC) | 151 | TypeScript | 2026-09-30 |
| [ManthanTerse/SpaceX-NWIS](https://github.com/ManthanTerse/SpaceX-NWIS) | 10606 | HTML | 2026-08-30 |
| [MayurKolekar03/eRTMAC-NWIS-Nearby-Wells-Intelligence-System](https://github.com/MayurKolekar03/eRTMAC-NWIS-Nearby-Wells-Intelligence-System) | 1741 | TypeScript | 2026-09-30 |
| [Meghanareddy2007/DRILLNEX](https://github.com/Meghanareddy2007/DRILLNEX) | 680 | HTML | 2026-09-29 |
| [Mohanarajan-24/NWIS](https://github.com/Mohanarajan-24/NWIS) | 0 | - | 2026-09-28 |
| [MoriAryan/CodeBlooded_SIH](https://github.com/MoriAryan/CodeBlooded_SIH) | 134 | TypeScript | 2026-09-30 |
| [MradulSingh109/ProjectAlteration](https://github.com/MradulSingh109/ProjectAlteration) | 2142 | TypeScript | 2026-09-30 |
| [Muhammad-Talha-MT/CONUS_Data_Download](https://github.com/Muhammad-Talha-MT/CONUS_Data_Download) | 121 | Python | 2026-09-22 |
| [NIVION-HUB/SIH2026-PS](https://github.com/NIVION-HUB/SIH2026-PS) | 26 | - | 2026-09-23 |
| [Neethushree21/SIH26121](https://github.com/Neethushree21/SIH26121) | 224 | Python | 2026-09-29 |
| [Nishchay-k/OIL](https://github.com/Nishchay-k/OIL) | 246 | TypeScript | 2026-09-30 |
| [Nithish-1622/NWIS](https://github.com/Nithish-1622/NWIS) | 188 | TypeScript | 2026-09-29 |
| [Physics0070/nwis](https://github.com/Physics0070/nwis) | 11875 | Python | 2026-09-08 |
| [Pooja-Rattan/DrillMind-AI-Python-MVP](https://github.com/Pooja-Rattan/DrillMind-AI-Python-MVP) | 5 | Python | 2026-09-19 |
| [Sahilbasu5101/WellSenseAI](https://github.com/Sahilbasu5101/WellSenseAI) | 173 | JavaScript | 2026-09-30 |
| [Sanjay190806/MindTwister-DrillMind](https://github.com/Sanjay190806/MindTwister-DrillMind) | 615 | Python | 2026-09-29 |
| [SathvikaSedimbi/NWIS](https://github.com/SathvikaSedimbi/NWIS) | 5213 | PLpgSQL | 2026-09-30 |
| [Sathwik797/WellMind-RAG](https://github.com/Sathwik797/WellMind-RAG) | 19591 | Jupyter Notebook | 2026-09-30 |
| [SatyajeetChavan30/SIH_Pototype](https://github.com/SatyajeetChavan30/SIH_Pototype) | 6547 | Python | 2026-09-27 |
| [Shank2Stack/eRTMAC-NWIS](https://github.com/Shank2Stack/eRTMAC-NWIS) | 27777 | TypeScript | 2026-09-11 |
| [Sheikh-Mujahid/TrustDrill](https://github.com/Sheikh-Mujahid/TrustDrill) | 510 | JavaScript | 2026-09-30 |
| [Shrey0604/SIH_2026](https://github.com/Shrey0604/SIH_2026) | 226 | JavaScript | 2026-09-20 |
| [SlothDevs-SIH/PS_121](https://github.com/SlothDevs-SIH/PS_121) | 3282 | Python | 2026-09-30 |
| [Starlitakash/ERTMAC-NWS](https://github.com/Starlitakash/ERTMAC-NWS) | 60580 | Python | 2026-09-07 |
| [SujalPatil21/Drill-Insight](https://github.com/SujalPatil21/Drill-Insight) | 5165 | TypeScript | 2026-09-15 |
| [SurveAnil/geodrill-ai](https://github.com/SurveAnil/geodrill-ai) | 400 | Python | 2026-09-27 |
| [Tarun-Gajjalwar/SIHPS_26121](https://github.com/Tarun-Gajjalwar/SIHPS_26121) | 145 | TypeScript | 2026-09-27 |
| [Udaymakhija07/nwis-oil-india](https://github.com/Udaymakhija07/nwis-oil-india) | 604 | JavaScript | 2026-09-29 |
| [Vaibhav-prog007/eRTMAC-NWIS](https://github.com/Vaibhav-prog007/eRTMAC-NWIS) | 1769 | JavaScript | 2026-09-30 |
| [VeeraVaishnaviK/NWIS---Nearby-Wells-Intelligence-System----MVP](https://github.com/VeeraVaishnaviK/NWIS---Nearby-Wells-Intelligence-System----MVP) | 1456 | Python | 2026-09-29 |
| [aaronparsons108/USGS-water-explorer](https://github.com/aaronparsons108/USGS-water-explorer) | 4926 | Python | 2026-09-22 |
| [ab-rar-6024/NWIS](https://github.com/ab-rar-6024/NWIS) | 182 | Python | 2026-09-30 |
| [aditya90001/ertmac_nwis](https://github.com/aditya90001/ertmac_nwis) | 30768 | Python | 2026-09-29 |
| [adityasri2501/Oil-India-Limited](https://github.com/adityasri2501/Oil-India-Limited) | 1867 | Python | 2026-09-30 |
| [aersews/nwis](https://github.com/aersews/nwis) | 241 | JavaScript | 2026-09-28 |
| [almostalok/nwis](https://github.com/almostalok/nwis) | 386 | TypeScript | 2026-09-29 |
| [ananditaa2/SIH_TheOutliers](https://github.com/ananditaa2/SIH_TheOutliers) | 96 | JavaScript | 2026-09-29 |
| [aneasystone/github-trending](https://github.com/aneasystone/github-trending) | 3534 | Python | 2026-09-30 |
| [aniketshelke191-commits/NWIS-PROJECT-](https://github.com/aniketshelke191-commits/NWIS-PROJECT-) | 748 | EJS | 2026-09-28 |
| [ankitsihag2406/NWIS](https://github.com/ankitsihag2406/NWIS) | 166 | CSS | 2026-09-29 |
| [anshu2k24/sih26](https://github.com/anshu2k24/sih26) | 48506 | JavaScript | 2026-09-26 |
| [api-evangelist/usgs-water](https://github.com/api-evangelist/usgs-water) | 722 | - | 2026-09-27 |
| [aryabailur/sih26121](https://github.com/aryabailur/sih26121) | 65664 | TypeScript | 2026-09-30 |
| [ashishsawkar2/SIH](https://github.com/ashishsawkar2/SIH) | 39 | JavaScript | 2026-09-28 |
| [ashishsawkar2/SIH2](https://github.com/ashishsawkar2/SIH2) | 44 | JavaScript | 2026-09-29 |
| [bishopcommander/OffsetEye](https://github.com/bishopcommander/OffsetEye) | 68668 | JavaScript | 2026-09-29 |
| [cipher425/SIH26121](https://github.com/cipher425/SIH26121) | 12690 | Python | 2026-09-29 |
| [codexaras/nwis](https://github.com/codexaras/nwis) | 1194 | TypeScript | 2026-09-27 |
| [cyanheads/usgs-water-mcp-server](https://github.com/cyanheads/usgs-water-mcp-server) | 1064 | TypeScript | 2026-09-25 |
| [dhanwanth-dh/eRTMAC--NWIS-Nearby-Wells-Intelligence-Offset-Decision-Support](https://github.com/dhanwanth-dh/eRTMAC--NWIS-Nearby-Wells-Intelligence-Offset-Decision-Support) | 6125 | JavaScript | 2026-09-26 |
| [dhruvgoel3/eRTMAC-NWIS](https://github.com/dhruvgoel3/eRTMAC-NWIS) | 40760 | TypeScript | 2026-09-29 |
| [divyanshikaushal/nwis-portal](https://github.com/divyanshikaushal/nwis-portal) | 7475 | TypeScript | 2026-09-29 |
| [g0c0de20-gif/SIH_PS-26121](https://github.com/g0c0de20-gif/SIH_PS-26121) | 150 | TypeScript | 2026-09-28 |
| [gaurang-developer-tech/NWIS](https://github.com/gaurang-developer-tech/NWIS) | 132 | JavaScript | 2026-09-29 |
| [grv-io/sih2026-nwis-offset-well-intelligence](https://github.com/grv-io/sih2026-nwis-offset-well-intelligence) | 9953 | Python | 2026-09-29 |
| [gurltff/eRTMAC-NWIS](https://github.com/gurltff/eRTMAC-NWIS) | 3817 | JavaScript | 2026-09-30 |
| [gurltff/oilsih](https://github.com/gurltff/oilsih) | 178 | JavaScript | 2026-09-26 |
| [gurltff/oilsihh](https://github.com/gurltff/oilsihh) | 1928 | TypeScript | 2026-09-29 |
| [harshjadon07/NWIS-sih](https://github.com/harshjadon07/NWIS-sih) | 406 | Python | 2026-09-30 |
| [heera0812/DrillSarthi](https://github.com/heera0812/DrillSarthi) | 2216 | Python | 2026-09-30 |
| [hiteshsaxena20/team-horizon---NEUROWELL](https://github.com/hiteshsaxena20/team-horizon---NEUROWELL) | 63 | TypeScript | 2026-09-29 |
| [ian-cuh/sih-nwis](https://github.com/ian-cuh/sih-nwis) | 99 | TypeScript | 2026-09-30 |
| [invo-coder19/Drill-IQ](https://github.com/invo-coder19/Drill-IQ) | 139 | TypeScript | 2026-09-27 |
| [jaldewarvaibhavi-web/ertmac-nwis](https://github.com/jaldewarvaibhavi-web/ertmac-nwis) | 16552 | Python | 2026-09-26 |
| [jayantbana/eRTMAC-NWIS](https://github.com/jayantbana/eRTMAC-NWIS) | 1558 | Python | 2026-09-29 |
| [jimmylowell/colorado_water](https://github.com/jimmylowell/colorado_water) | 937 | JavaScript | 2026-09-30 |
| [kartikvermagit-ds/KAVAAI-NWIS](https://github.com/kartikvermagit-ds/KAVAAI-NWIS) | 2525 | TypeScript | 2026-09-30 |
| [keerthi147-del/NWIS-OIL-India](https://github.com/keerthi147-del/NWIS-OIL-India) | 47 | Python | 2026-09-30 |
| [kittuarjun/SIH](https://github.com/kittuarjun/SIH) | 183 | JavaScript | 2026-09-26 |
| [kriishna9/eRTMAC-NWIS](https://github.com/kriishna9/eRTMAC-NWIS) | 38928 | Python | 2026-09-04 |
| [lakshmanan72/NWIS-OIL-INDIA](https://github.com/lakshmanan72/NWIS-OIL-INDIA) | 18953 | Python | 2026-09-28 |
| [mayurimore18/WELLSIGHT](https://github.com/mayurimore18/WELLSIGHT) | 67 | TypeScript | 2026-09-29 |
| [n3ssdub3y/SIH_2026_PLANNS](https://github.com/n3ssdub3y/SIH_2026_PLANNS) | 72814 | Python | 2026-09-29 |
| [narayanalikhitha/sih-oil](https://github.com/narayanalikhitha/sih-oil) | 696 | JavaScript | 2026-09-28 |
| [naved255/NWIS](https://github.com/naved255/NWIS) | 217 | Python | 2026-09-30 |
| [nikunjgoyal0344-coder/NWIS-Solution-](https://github.com/nikunjgoyal0344-coder/NWIS-Solution-) | 120 | TypeScript | 2026-09-27 |
| [nikunjgoyal0344-coder/eRTMAC-NWIS](https://github.com/nikunjgoyal0344-coder/eRTMAC-NWIS) | 233 | TypeScript | 2026-09-27 |
| [nishanth418/hostelmanagementsystem](https://github.com/nishanth418/hostelmanagementsystem) | 227 | JavaScript | 2026-09-18 |
| [niteshpaul99-ctrl/nwis-ai](https://github.com/niteshpaul99-ctrl/nwis-ai) | 187 | JavaScript | 2026-09-29 |
| [oki-dokii/baithe-baithe-bore-hua-karna-hai-kuch-kaam](https://github.com/oki-dokii/baithe-baithe-bore-hua-karna-hai-kuch-kaam) | 878 | Python | 2026-09-29 |
| [omshingade06/sih](https://github.com/omshingade06/sih) | 269 | TypeScript | 2026-09-29 |
| [p80227653-hub/nwis-hybrid-core](https://github.com/p80227653-hub/nwis-hybrid-core) | 20 | - | 2026-09-30 |
| [pallavi-a11y/eRTMAC-NWIS](https://github.com/pallavi-a11y/eRTMAC-NWIS) | 2181 | Python | 2026-09-27 |
| [patilireesh-ship-it/NWIS-Drilling-Intelligence](https://github.com/patilireesh-ship-it/NWIS-Drilling-Intelligence) | 1764 | Python | 2026-09-29 |
| [prajwaljadhav9793/Drill-Guard-Sih](https://github.com/prajwaljadhav9793/Drill-Guard-Sih) | 251 | TypeScript | 2026-09-29 |
| [prasadjh-074/ertmac-nwis](https://github.com/prasadjh-074/ertmac-nwis) | 63 | Python | 2026-09-29 |
| [prasadjh-074/ertmac-nwis-sih](https://github.com/prasadjh-074/ertmac-nwis-sih) | 488 | Python | 2026-09-30 |
| [pratham1232/Oil-India](https://github.com/pratham1232/Oil-India) | 170 | TypeScript | 2026-09-29 |
| [priy-anshugupta/SRISHTI-AI](https://github.com/priy-anshugupta/SRISHTI-AI) | 5921 | TypeScript | 2026-09-28 |
| [rajkeshavmi4/SIH-26121](https://github.com/rajkeshavmi4/SIH-26121) | 425 | Python | 2026-09-29 |
| [rehan95378/SIH](https://github.com/rehan95378/SIH) | 199 | JavaScript | 2026-09-29 |
| [rishabhbajpai627/NWIS-National-Well-Intelligence-System-](https://github.com/rishabhbajpai627/NWIS-National-Well-Intelligence-System-) | 99 | TypeScript | 2026-09-30 |
| [rohitchaudhari045-eng/Well-Nexus](https://github.com/rohitchaudhari045-eng/Well-Nexus) | 50913 | JavaScript | 2026-09-29 |
| [rudrachauhan12999/eRTMAC-NWIS](https://github.com/rudrachauhan12999/eRTMAC-NWIS) | 159771 | TypeScript | 2026-09-20 |
| [rudraprasad333/eRTMAC-NWIS](https://github.com/rudraprasad333/eRTMAC-NWIS) | 611 | TypeScript | 2026-09-27 |
| [sandeep0431/dristhi](https://github.com/sandeep0431/dristhi) | 1949 | TypeScript | 2026-09-28 |
| [shaurya212121/Well-Whisperer](https://github.com/shaurya212121/Well-Whisperer) | 1345 | TypeScript | 2026-09-30 |
| [shaurya212121/Well-Whisperer](https://github.com/shaurya212121/Well-Whisperer) | 1345 | TypeScript | 2026-09-30 |
| [shivarajsg/OIL-Is-Well](https://github.com/shivarajsg/OIL-Is-Well) | 35620 | - | 2026-09-27 |
| [shivauser02116/ertmac-nwis](https://github.com/shivauser02116/ertmac-nwis) | 1381 | TypeScript | 2026-09-29 |
| [sivatce27-ops/121](https://github.com/sivatce27-ops/121) | 262 | TypeScript | 2026-09-27 |
| [sparsh101sparsh/eRTMAC-NWIS](https://github.com/sparsh101sparsh/eRTMAC-NWIS) | 4477 | PLpgSQL | 2026-09-28 |
| [sudhanshu-0109/DrillIntel](https://github.com/sudhanshu-0109/DrillIntel) | 294 | TypeScript | 2026-09-27 |
| [sujalbistaa/drillsage](https://github.com/sujalbistaa/drillsage) | 3142 | Python | 2026-09-30 |
| [suryanshkota07-oss/AROH-drilling-intelligence](https://github.com/suryanshkota07-oss/AROH-drilling-intelligence) | 15276 | Python | 2026-08-29 |
| [tarumishra22/eRTMAC-NWIS](https://github.com/tarumishra22/eRTMAC-NWIS) | 54 | JavaScript | 2026-09-23 |
| [tech-nitin/wellwise](https://github.com/tech-nitin/wellwise) | 1105 | JavaScript | 2026-09-23 |
| [tharunsrisanth07-dotcom/well-badger](https://github.com/tharunsrisanth07-dotcom/well-badger) | 488 | Python | 2026-09-30 |
| [thor11223344/PetrolQ](https://github.com/thor11223344/PetrolQ) | 11599 | JavaScript | 2026-09-24 |
| [udayraj53793-byte/eRTMAC-NWIS](https://github.com/udayraj53793-byte/eRTMAC-NWIS) | 222 | JavaScript | 2026-09-29 |
| [vidhiii1711/eRTMAC-NWIS](https://github.com/vidhiii1711/eRTMAC-NWIS) | 19862 | Jupyter Notebook | 2026-09-23 |
| [vk9199kadam-hue/v-next](https://github.com/vk9199kadam-hue/v-next) | 1762 | Python | 2026-09-30 |
| [xarjunpatil/SIH26121-eRTMAC-NWIS-Nearby-Wells-Intelligence-System-An-AI-Powered-Offset-Well](https://github.com/xarjunpatil/SIH26121-eRTMAC-NWIS-Nearby-Wells-Intelligence-System-An-AI-Powered-Offset-Well) | 25 | HTML | 2026-08-31 |
| [yhiremath34-tech/WELL-INTEL](https://github.com/yhiremath34-tech/WELL-INTEL) | 169 | TypeScript | 2026-09-22 |

</details>
