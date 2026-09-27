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
   - **What it has:** live; tested (13 test files); a / provenance tag on every record; confidence-gated RAG.
   - **Our answer:** every fact carries a resolvable  down to the page and line, and the REPLAY stamp. Its data is mostly synthetic.
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
| **Public live demo link** (6 repos) | **Yes, top priority** | Judges click links. Deploy the one-port build (cd frontend && KK_EXPORT=1 npx next build
  ▲ Next.js 14.2.35

   Creating an optimized production build ...
 ✓ Compiled successfully
   Linting and checking validity of types ...

./src/app/accuracy/page.tsx
36:30  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
42:73  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
43:19  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
62:64  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
63:65  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
64:76  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
65:75  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
66:63  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
72:69  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
73:74  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
74:85  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
75:83  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
76:79  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
77:81  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
89:64  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
90:66  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
92:57  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
93:63  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
100:85  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any

./src/app/brief/page.tsx
17:30  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
20:36  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
25:113  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
36:63  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
85:70  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
90:45  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
94:56  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
98:138  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
100:180  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
101:151  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
103:81  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any

./src/app/checker/page.tsx
29:38  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
32:30  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
33:30  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
74:67  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
75:68  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
76:78  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
77:71  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
78:97  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any

./src/app/copilot/page.tsx
24:40  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
32:17  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
59:105  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
63:45  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
75:35  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
87:40  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any

./src/app/dev/components/page.tsx
21:36  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
22:34  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
23:40  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
24:34  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
25:40  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
26:38  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
36:86  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
36:122  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
36:130  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
46:48  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
74:42  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
87:48  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
88:61  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
89:68  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
90:45  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any

./src/app/fixes/page.tsx
21:38  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
22:30  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
24:34  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
26:135  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
31:22  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
34:116  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
34:169  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
36:43  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
65:68  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
66:79  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
67:80  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
68:84  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
69:77  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
70:49  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
71:79  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
72:83  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
73:79  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
87:75  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
87:120  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
87:139  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any

./src/app/mudwindow/page.tsx
20:30  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
26:32  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
26:69  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
26:133  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
26:181  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
27:47  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
28:46  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
28:109  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
30:32  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
32:47  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
54:32  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
54:93  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
67:28  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
84:71  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
85:79  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
86:79  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
87:68  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
88:77  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
91:57  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
93:68  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
94:70  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
95:73  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
96:69  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any

./src/app/offsets/page.tsx
26:34  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
28:44  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
29:34  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
40:9  Warning: The 'cols' logical expression could make the dependencies of useMemo Hook (at line 45) change on every render. To fix this, wrap the initialization of 'cols' in its own useMemo() Hook.  react-hooks/exhaustive-deps
43:31  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
43:62  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
48:21  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
50:31  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
53:46  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
54:68  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
103:46  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
103:80  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
104:57  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
111:33  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
122:55  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
122:93  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any

./src/app/page.tsx
25:36  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
26:40  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
27:38  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
32:32  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
33:42  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
36:42  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
59:53  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
78:39  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
78:90  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
90:22  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
90:46  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
107:37  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
146:94  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
152:54  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
161:103  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
161:124  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
187:75  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
200:24  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any

./src/app/wiki/page.tsx
20:36  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
21:38  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
24:34  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
29:36  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
48:17  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any

./src/components/kk/CommandPalette.tsx
12:38  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
13:38  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any

./src/components/kk/EventReview.tsx
25:36  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
82:69  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
83:67  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
84:74  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
85:63  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
86:86  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any

./src/components/kk/MiniMap.tsx
33:274  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
36:64  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
49:23  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any

./src/components/kk/SourceFootnote.tsx
19:30  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
20:36  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
29:23  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
52:30  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any

./src/components/kk/UploadReport.tsx
23:34  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
46:17  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
71:81  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any

./src/components/kk/WellPicker.tsx
11:36  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
12:34  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any

./src/lib/api.ts
12:31  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
12:74  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
19:32  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any
19:57  Warning: Unexpected any. Specify a different type.  @typescript-eslint/no-explicit-any

info  - Need to disable some ESLint rules? Learn more here: https://nextjs.org/docs/basic-features/eslint#disabling-rules
   Collecting page data ...
   Generating static pages (0/14) ...
   Generating static pages (3/14) 
   Generating static pages (6/14) 
   Generating static pages (10/14) 
 ✓ Generating static pages (14/14)
   Finalizing page optimization ...
   Collecting build traces ...

Route (app)                              Size     First Load JS
┌ ○ /                                    7.32 kB         401 kB
├ ○ /_not-found                          873 B          88.3 kB
├ ○ /accuracy                            7.05 kB         104 kB
├ ○ /brief                               7.69 kB         379 kB
├ ○ /checker                             7.84 kB         105 kB
├ ○ /copilot                             5.67 kB         103 kB
├ ○ /dev/components                      5.82 kB         117 kB
├ ○ /fixes                               6.83 kB         104 kB
├ ○ /mudwindow                           7.27 kB         113 kB
├ ○ /offsets                             5.71 kB         391 kB
└ ○ /wiki                                7.66 kB         105 kB
+ First Load JS shared by all            87.5 kB
  ├ chunks/117-655d1a30eb0b655d.js       31.9 kB
  ├ chunks/fd9d1056-3054852c68a3097a.js  53.6 kB
  └ other shared chunks (total)          1.96 kB


○  (Static)  prerendered as static content

cd backend && DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8010) to a host, or record a video. |
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
