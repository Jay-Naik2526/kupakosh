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
