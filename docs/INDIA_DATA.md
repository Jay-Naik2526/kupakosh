# Indian data — what we have and how to get more

## Loaded now (public, no registration)
| Source | What | In Kupakosh |
|---|---|---|
| NDR (DGH) basin summary pages, 23 basins | geology, stratigraphy, petroleum systems, fields, exploration counts, some well lists | 23 wiki pages "Indian basins", 4,439 citable passages, 35 named wells with drilled depth, Copilot tool `basin_facts` |
| NDR technical papers (01, 03, 05, 06, 07) incl. *Analyzing average rig time and ease of drilling in Indian sedimentary basins* (DGH, 19,000+ wells) | text, cited by page/paragraph | searchable in Copilot |
| NDR Geo-scientific data policy | policy text | searchable |

Not available publicly: daily drilling reports, well completion reports, logs, coordinates of Indian wells.

## Getting well-level Indian data: NDR academic access (free for academic research)
1. Register at https://www.ndrdgh.gov.in/NDR/index.php/?page_id=1486 with your **official college e-mail**.
2. E-mail **indr@dghindia.gov.in** with: scanned student ID + authority letter (below) on college letterhead, signed and stamped by HOD / Principal.
3. After approval, request: Well Completion Reports and Daily Drilling Reports for Upper Assam wells (e.g. Oil India fields), plus formation tops and well headers.
4. Data comes with a confidentiality agreement — keep it out of public repos and public demos unless permitted.

### E-mail draft (send from your college e-mail)
Subject: Request for academic access to NDR data — SIH 2026 (PS 26121), [College name]

Dear Sir/Madam,
We are students of [Department], [College], participating in Smart India Hackathon 2026 on problem statement 26121
(Oil India Limited: offset-well knowledge system for drilling hazards). We have registered on the NDR portal as
[user id]. We request academic access to well data (well completion reports, daily drilling reports, formation tops and
well headers) for wells in the Assam-Arakan basin, for non-commercial research only. Our student ID and the authority
letter from our HOD are attached. We will follow the NDR data policy and confidentiality terms.
Thank you,
[Name], [Roll no.], [Phone]

### Authority letter draft (college letterhead, signed + stamp)
To: The National Data Repository, Directorate General of Hydrocarbons, Noida
Subject: Authority letter for academic use of NDR data
This is to certify that [Name(s)], student(s) of [Programme, Year] in the Department of [ ] at [College], are working
on an academic research project for Smart India Hackathon 2026 (PS 26121) under my supervision. The data requested
from NDR will be used only for non-commercial academic research and will not be shared with third parties.
[HOD name], [Designation], [Date], [Signature and seal]

## Added (second India pass) — `scripts/download_india.sh`, `scripts/download_india_more.sh`, `app/ingest/india_docs.py`
| Source | Documents |
|---|---|
| DGH *India — Petroleum Exploration & Production Activities* 2005-06 … 2014-15 | 10 reports (discoveries with well names, E&P statistics) |
| MoPNG *Indian Petroleum & Natural Gas Statistics* 2019-20 … 2024-25 | 5 volumes (wells and metreage by basin/company) |
| Oil India Limited annual reports 2015-16 … 2025-26 | 11 reports |
| ONGC annual report 2023-24 | 1 report |
| CAG audits: Hydrocarbon exploration (42/2015 ch.5), Rig utilisation in ONGC (39/2015) | 2 |
| OISD safety alerts (public) | 55 unique alerts (21 from drilling rigs / well sites) |
| Baghjan-5 blowout (Oil India, 2020): NGT / Supreme Court records via Indian Kanoon | 2 |
| Papers / abstracts on Indian wells | 1 readable |
Total ≈ 43,000 new citable Indian passages; 29 Indian wells named in these texts; Baghjan-5 blowout events extracted
(flagged "needs review": the court text is mostly about environmental damage, no depths/operations).
Still not public: Indian daily drilling reports, WCRs, logs, well coordinates → NDR request (above).
