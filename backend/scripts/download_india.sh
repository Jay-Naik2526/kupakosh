#!/usr/bin/env bash
# Public Indian sources (NDR / DGH). Well-level data needs NDR registration — see docs/INDIA_DATA.md.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; D="$ROOT/data/raw/india"; mkdir -p "$D/basins"
for pair in 647:krishna-godavari 651:mumbai-offshore 617:assam-arakan 656:rajasthan 640:cauvery 629:cambay 822:saurashtra 742:kutch \
  831:vindhyan 759:mahanadi 790:andaman-nicobar 814:kerala-konkan 797:bengal-purnea 1092:ganga-punjab 879:pranhita-godavari \
  886:satpura-south-rewa-damodar 808:himalayan-foreland 853:chhattisgarh 891:spiti-zanskar 866:deccan-syneclise 860:cuddapah 873:karewa 846:bhima-kaladgi; do
  id=${pair%%:*}; n=${pair#*:}; [ -s "$D/basins/$n.html" ] || curl -sS -L -m 60 "https://www.ndrdgh.gov.in/NDR/?page_id=$id" -o "$D/basins/$n.html"
done
for n in 01 03 05 06 07; do [ -s "$D/ndr_paper_$n.pdf" ] || curl -sS -m 120 "https://www.ndrdgh.gov.in/NDR/pdf/$n.pdf" -o "$D/ndr_paper_$n.pdf"; done
[ -s "$D/ndr_geoscientific_policy.pdf" ] || curl -sS -m 120 "https://www.ndrdgh.gov.in/NDR/pdf/Geo-scientific_Policy.pdf" -o "$D/ndr_geoscientific_policy.pdf"
echo "india sources in $D"
# OISD safety alerts (public, by id)
mkdir -p "$D/oisd"
for i in $(seq 1 90); do f="$D/oisd/alert_$i.pdf"; [ -s "$f" ] || curl -sS -L -m 60 -A "Mozilla/5.0" "https://oisd.gov.in/Image/GetSafetyAlertAttachmentByID?safetyAlertID=$i" -o "$f" || true; done
# DGH activity reports 2005-06 .. 2014-15 (hosted on NDR)
mkdir -p "$D/dgh_activity"
for y in 2005-06 2006-07 2007-08 2008-09 2009-10 2010-11 2011-12 2012-13 2013-14 2014-15; do
  f="$D/dgh_activity/$y.pdf"; [ -s "$f" ] || curl -sS -m 300 "https://www.ndrdgh.gov.in/NDR/pdf/$y.pdf" -o "$f" || true; done
# MoPNG Indian Petroleum & Natural Gas Statistics (recent years)
mkdir -p "$D/ipng" "$D/oil_annual" "$D/cag" "$D/legal"
M="https://mopng.gov.in/files/TableManagements"
for f in 2026-02-25-141451-b06fw-IPNG_Statistics-Report_2024-25.pdf IPNG-Statistics-Report_2023-24_Final.pdf IPNG-Annual-Report-2022-23-web.pdf IPNG-2021-22_L.pdf IPNG-2019-20.pdf; do
  [ -s "$D/ipng/$f" ] || curl -sS -L -m 600 -A "Mozilla/5.0" "$M/$f" -o "$D/ipng/$f" || true; done
# Oil India annual reports (company publications)
O="https://www.oil-india.com/files/financial_results_documents"
for f in IntegratedAnnualReport2025-26.pdf OIL_India_Annual_Report_2024_25_0.pdf AnnualReport202324.pdf Annual_Report_2022_23.pdf Integrated_Annual_Report_2021_22new.pdf \
  Integrated_Annual_Report_2020_21.pdf OIL_Annual_Report_2019_20_Searchable.pdf Final_OIL_India_annual_report_2018_19_compressed.pdf OIL_India_Annual_Report_17_18.pdf \
  Oil_ANNUAL_REPORT_16_17.pdf Annual_Report_15_16_For_Mail.pdf; do
  [ -s "$D/oil_annual/$f" ] || curl -sS -L -m 900 -A "Mozilla/5.0" "$O/$f" -o "$D/oil_annual/$f" || true; done
# CAG performance audit: hydrocarbon exploration by ONGC/OIL (Report 42 of 2015, chapter 5)
[ -s "$D/cag/cag_42_2015_ch5.pdf" ] || curl -sS -L -m 300 -A "Mozilla/5.0" "https://cag.gov.in/uploads/download_audit_report/2015/Union_Commercial_Performace_Hydrocarbon_Exploration_42_2015_chap_5.pdf" -o "$D/cag/cag_42_2015_ch5.pdf" || true
# Baghjan-5 blowout: NGT judgments (public court records)
for id in 171129976 99288607; do [ -s "$D/legal/indiankanoon_$id.html" ] || curl -sS -L -m 120 -A "Mozilla/5.0" "https://indiankanoon.org/doc/$id/" -o "$D/legal/indiankanoon_$id.html" || true; done
echo done-extra
[ -s "$D/cag/cag_39_2015_rigs.pdf" ] || curl -sS -L -m 600 -A "Mozilla/5.0" "https://cag.gov.in/webroot/uploads/download_audit_report/2015/Union_Commercial_Performance_Utilisation_Rigs_39_2015.pdf" -o "$D/cag/cag_39_2015_rigs.pdf" || true
mkdir -p "$D/papers"
[ -s "$D/papers/gji_upper_assam_pore_pressure.html" ] || curl -sS -L -m 120 -A "Mozilla/5.0" "https://academic.oup.com/gji/article/216/1/659/5144768" -o "$D/papers/gji_upper_assam_pore_pressure.html" || true
echo done-extra2
