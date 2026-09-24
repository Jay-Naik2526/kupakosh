#!/usr/bin/env bash
# Downloads the real public datasets used by Kupakosh. Re-runnable.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SODIR="$ROOT/data/raw/sodir"; FORGE="$ROOT/data/raw/forge"
mkdir -p "$SODIR" "$FORGE/16A" "$FORGE/16B"
BASE="https://factpages.sodir.no/public?/Factpages/external/tableview"
Q="&rs:Command=Render&rc:Toolbar=false&rc:Parameters=f&IpAddress=not_used&CultureCode=en&rs:Format=CSV&Top100=false"
for t in wellbore_all_long wellbore_coordinates wellbore_formation_top wellbore_casing_and_lot wellbore_mud wellbore_history wellbore_document; do
  [ -s "$SODIR/$t.csv" ] || curl -sS -m 900 "$BASE/$t$Q" -o "$SODIR/$t.csv"
  echo "sodir $t $(wc -l < "$SODIR/$t.csv") lines"
done
G="https://gdr.openei.org/files/1283"
dl(){ [ -s "$2" ] || curl -sS -L -m 1800 "$1" -o "$2"; echo "forge $(basename "$2") $(wc -c < "$2") bytes"; }
dl "$G/16A(78)-32_Daily_Reports.zip" "$FORGE/16A/daily_reports.zip"
dl "$G/16A(78)-32_time_data_10s_intervals.csv" "$FORGE/16A/time_10s.csv"
dl "$G/16A(78)-32%20Final%20mud%20log.las" "$FORGE/16A/mudlog.las"
dl "$G/16A(78)-32%20Survey.xlsx" "$FORGE/16A/survey.xlsx"
dl "$G/Composite-C%20(1).pdf" "$FORGE/16A/summary_daily_ops.pdf"
G="https://gdr.openei.org/files/1516"
dl "$G/16B%20Daily%20Reports.zip" "$FORGE/16B/daily_reports.zip"
dl "$G/16B(78)-32%20Well%20Survey.zip" "$FORGE/16B/survey.zip"
dl "$G/16B_Pason.zip" "$FORGE/16B/pason.zip"
# --- additional Utah FORGE wells (offsets for the 16B replay) ---
for w in 58-32 78B-32 68-32 78-32; do mkdir -p "$FORGE/$w"; done
dl "https://gdr.openei.org/files/1006/DailyDrillingReports_Well58-32.zip" "$FORGE/58-32/daily_reports.zip"
dl "https://gdr.openei.org/files/1006/Directional_Survey_well_58_32.zip" "$FORGE/58-32/survey.zip"
dl "https://gdr.openei.org/files/1330/78B-32-DailyDrillingReports-6-27thru7-31.pdf" "$FORGE/78B-32/daily_reports.pdf"
dl "https://gdr.openei.org/files/1330/78B-32%20directional%20survey%20(1).zip" "$FORGE/78B-32/survey.zip"
dl "https://gdr.openei.org/files/1330/78B-32%2010%20sec%20data%2027200701_standard.csv" "$FORGE/78B-32/time_10s_standard.csv"
dl "https://gdr.openei.org/files/1153/Well_68-32_data.zip" "$FORGE/68-32/data.zip"
dl "https://gdr.openei.org/files/1153/Well_78-32_data.zip" "$FORGE/78-32/data.zip"
dl "https://gdr.openei.org/files/1153/Utah%20FORGE%20Phase%202C%20Well%20Locations.zip" "$FORGE/phase2c_locations.zip"
