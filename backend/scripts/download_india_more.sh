#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; D="$ROOT/data/raw/india"; mkdir -p "$D/ongc_annual" "$D/papers"
[ -s "$D/ongc_annual/ar2023-24.pdf" ] || curl -sS -L -m 900 -A "Mozilla/5.0" "https://ongcindia.com/documents/77751/2660534/ar2023-24.pdf" -o "$D/ongc_annual/ar2023-24.pdf"
[ -s "$D/ongc_annual/annual_report15-16.pdf" ] || curl -sS -L -m 900 -A "Mozilla/5.0" "http://www.ongcindia.com/wps/wcm/PDF/AnnualReport/annual_report15-16.pdf" -o "$D/ongc_annual/annual_report15-16.pdf"
[ -s "$D/papers/aapg_kg_onshore_deviated_wells.html" ] || curl -sS -L -m 120 -A "Mozilla/5.0" "https://www.searchanddiscovery.com/abstracts/html/2018/australia.90324/abstracts/2018.Perth.Pore.50.html" -o "$D/papers/aapg_kg_onshore_deviated_wells.html"
echo done-more
