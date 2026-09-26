#!/usr/bin/env bash
# Kupakosh — fetch every public raw dataset the ingesters in backend/app/ingest/ext/*.py read,
# for ANY country, so a fresh clone can rebuild data/raw/ from scratch without a browser.
#
# Idempotent: every file is skipped if it already exists and is non-empty. Safe to re-run.
# Override the destination with DATA_DIR=/some/path (default: <repo>/data), e.g. to verify into a
# scratch directory without touching the real data/raw/.
#
# Usage:
#   bash backend/scripts/download_world.sh            # everything (core + all countries)
#   bash backend/scripts/download_world.sh core        # Sodir + Utah FORGE + India only (fast path)
#   bash backend/scripts/download_world.sh uk nz india  # just the named section(s)
#   DATA_DIR=/tmp/verify bash backend/scripts/download_world.sh nz
#
# Sections: core (sodir+forge), india, uk, netherlands, australia, usa, nz, canada, force2020
set -uo pipefail   # NOT -e: one failed source must not stop the rest

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DATA_DIR="${DATA_DIR:-$ROOT/data}"
RAW="$DATA_DIR/raw"
CURL_OPTS=(-sS -L --retry 5 --retry-delay 3 --connect-timeout 15 -m "${DL_TIMEOUT:-900}" -A "Mozilla/5.0 (Kupakosh data fetch; +https://github.com/)")
ARCGIS_PAGE_SIZE=2000

mkdir -p "$RAW"

STATUS_OK=()
STATUS_SKIPPED_NOURL=()
STATUS_MISSING=()

# ---------------------------------------------------------------------------------------------
# dl URL OUT_FILE — plain GET, retried, skipped if OUT_FILE already exists and is non-empty.
dl() {
  local url="$1" out="$2"
  if [ -s "$out" ]; then
    STATUS_OK+=("$out")
    echo "  [ok]   $out (already present)"
    return 0
  fi
  mkdir -p "$(dirname "$out")"
  if curl "${CURL_OPTS[@]}" "$url" -o "$out.part" && [ -s "$out.part" ]; then
    mv "$out.part" "$out"
    STATUS_OK+=("$out")
    echo "  [ok]   $out"
  else
    rm -f "$out.part"
    STATUS_MISSING+=("$out (GET $url)")
    echo "  [FAIL] $out <- $url"
  fi
}

# ---------------------------------------------------------------------------------------------
# replay_manifest DIR [FILE_PREFIX]
#   Reads DIR/MANIFEST.csv (file,url,licence,retrieved_at,notes) and re-downloads every row whose
#   `url` is a plain http(s) GET (skips rows that record a POST call, an ArcGIS query already
#   handled by page_arcgis, or a "derived from ..." / no-URL note — those need the special-cased
#   functions below, or are genuinely not scriptable; see the final report).
replay_manifest() {
  local dir="$1" prefix="${2:-}"
  local manifest="$dir/MANIFEST.csv"
  if [ ! -f "$manifest" ]; then
    echo "  [warn] no MANIFEST.csv in $dir — nothing to replay"
    return 0
  fi
  while IFS=$'\t' read -r f u; do
    [ -z "$f" ] && continue
    dl "$u" "$dir/$f"
  done < <(python3 - "$manifest" "$prefix" <<'PY'
import csv, sys
path, prefix = sys.argv[1], sys.argv[2]
with open(path, newline="", encoding="utf-8") as fh:
    for row in csv.reader(fh):
        if not row or row[0] == "file":
            continue
        # Normal, well-quoted row: exactly file,url,licence,retrieved_at,notes.
        if len(row) == 5:
            f, u = row[0].strip(), row[1].strip()
        elif len(row) > 5:
            # A handful of rows have unescaped commas inside `file`/`url` (e.g. a Wikipedia title
            # like "Moran, Assam"). licence/retrieved_at/notes never contain a bare comma in this
            # data, so treat the last 3 fields as those and rejoin everything before the first
            # http-looking field as `file`, and from there to the split point as `url`.
            head = row[:-3]
            idx = next((i for i, v in enumerate(head) if v.strip().startswith("http")), None)
            if idx is None:
                continue
            f = ",".join(head[:idx]).strip()
            u = ",".join(head[idx:]).strip()
        else:
            continue
        if prefix and not f.startswith(prefix):
            continue
        if not (u.startswith("http://") or u.startswith("https://")):
            continue  # POST call, ArcGIS query (handled separately), or "derived from ..." note
        print(f"{f}\t{u}")
PY
  )
}

# ---------------------------------------------------------------------------------------------
# page_arcgis QUERY_URL OUT_FILE MODE [MAX_RECORDS]
#   QUERY_URL must already end in ".../query?where=...&outFields=*&f=json[&outSR=...]" (no
#   resultOffset/resultRecordCount — this adds those and pages until a short page is returned).
#   MODE: "attributes" -> flat list of each feature's `attributes` dict (drops geometry)
#         "features"   -> list of full {"attributes":..., "geometry":...} feature dicts
#   MAX_RECORDS (optional, 0 = unlimited): stop after this many records (for a documented subset).
page_arcgis() {
  local url="$1" out="$2" mode="$3" maxrec="${4:-0}"
  if [ -s "$out" ]; then
    STATUS_OK+=("$out")
    echo "  [ok]   $out (already present)"
    return 0
  fi
  mkdir -p "$(dirname "$out")"
  local tmpdir; tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/kk_arcgis.XXXXXX")"
  local offset=0 got="$ARCGIS_PAGE_SIZE" total=0 sep="&" failed=0
  [[ "$url" == *"?"* ]] || sep="?"
  while [ "$got" -eq "$ARCGIS_PAGE_SIZE" ]; do
    local pf="$tmpdir/page_$(printf '%09d' "$offset").json"
    local attempt=1 page_ok=0
    while [ "$attempt" -le 3 ]; do
      if curl "${CURL_OPTS[@]}" --http1.1 "${url}${sep}resultOffset=${offset}&resultRecordCount=${ARCGIS_PAGE_SIZE}" -o "$pf" \
          && python3 -c "import json,sys; json.load(open('$pf'))" 2>/dev/null; then
        page_ok=1; break
      fi
      attempt=$((attempt + 1)); sleep 2
    done
    if [ "$page_ok" -ne 1 ]; then
      echo "  [warn] page fetch failed at offset $offset for $out (after 3 tries)"
      failed=1
      break
    fi
    got=$(python3 -c "
import json
try:
    d = json.load(open('$pf'))
    print(len(d.get('features', [])))
except Exception:
    print(0)
" 2>/dev/null || echo 0)
    total=$((total + got))
    offset=$((offset + ARCGIS_PAGE_SIZE))
    if [ "$got" -eq 0 ]; then break; fi
    if [ "$maxrec" != "0" ] && [ "$total" -ge "$maxrec" ]; then break; fi
  done
  if [ "$failed" -eq 1 ]; then
    # Don't write a partial/empty file — an incomplete result must not look "present" to a re-run.
    rm -rf "$tmpdir"
    STATUS_MISSING+=("$out (ArcGIS paging failed partway — re-run this script to retry)")
    echo "  [FAIL] $out"
    return 1
  fi
  python3 - "$tmpdir" "$out" "$mode" "$maxrec" <<'PY'
import glob, json, os, sys
tmpdir, out, mode, maxrec = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
feats = []
for pf in sorted(glob.glob(os.path.join(tmpdir, "page_*.json"))):
    try:
        d = json.load(open(pf))
    except Exception:
        continue
    feats.extend(d.get("features", []))
if maxrec > 0:
    feats = feats[:maxrec]
rows = [f.get("attributes", f) for f in feats] if mode == "attributes" else feats
with open(out, "w") as fh:
    json.dump(rows, fh)
print(f"  [ok]   {out}  ({len(rows)} rows)")
PY
  rm -rf "$tmpdir"
  if [ -s "$out" ]; then
    STATUS_OK+=("$out")
  else
    STATUS_MISSING+=("$out (ArcGIS paging returned 0 rows)")
  fi
}

# =================================================================================================
# core: Sodir (Norway) + Utah FORGE — existing script, unchanged.
core() {
  echo "== core: Sodir + Utah FORGE =="
  DATA_DIR="$DATA_DIR" bash "$ROOT/backend/scripts/download_data.sh" || true
}

# india: NDR/DGH/OISD/company reports + the india_more.py sources (legal/pib/papers/wikipedia).
india() {
  echo "== India (NDR/DGH/OISD/annual reports) =="
  DATA_DIR="$DATA_DIR" bash "$ROOT/backend/scripts/download_india.sh" || true
  DATA_DIR="$DATA_DIR" bash "$ROOT/backend/scripts/download_india_more.sh" || true
  echo "== India (more): legal orders, PIB releases, papers, Wikipedia reference articles =="
  mkdir -p "$RAW/india_more"
  replay_manifest "$RAW/india_more"
}

# force2020: 98-well lithology-competition dataset (small, needed for the FORCE-2020 similarity work).
force2020() {
  echo "== FORCE 2020 (lithology competition) =="
  mkdir -p "$RAW/force2020"
  replay_manifest "$RAW/force2020"
  if [ ! -s "$RAW/force2020/lithology_key.csv" ]; then
    echo "  [note] lithology_key.csv has no direct URL (hand-transcribed from the competition"
    echo "         README's code table) — cannot be scripted; see data/raw/force2020/MANIFEST.csv."
  fi
}

# UK: NSTA (North Sea Transition Authority) — 3 ArcGIS feature layers + a sample of linked report PDFs.
uk() {
  echo "== UK (NSTA) =="
  local BASE="https://services-eu1.arcgis.com/OZMfUznmLTnWccBc/arcgis/rest/services"
  mkdir -p "$RAW/uk/nsta/reports"
  page_arcgis "$BASE/UKCS_offshore_wellbore_top_holes_(WGS84)/FeatureServer/0/query?where=1=1&outFields=*&f=json" \
    "$RAW/uk/nsta/wellbore_top_holes.json" attributes
  page_arcgis "$BASE/UKCS_offshore_petroleum_wells_with_linked_reports_(WGS84)/FeatureServer/0/query?where=1=1&outFields=*&f=json" \
    "$RAW/uk/nsta/linked_reports.json" attributes
  page_arcgis "$BASE/UKCS_offshore_petroleum_exploration_and_appraisal_well_results_(ED50)/FeatureServer/2/query?where=1=1&outFields=*&f=json" \
    "$RAW/uk/nsta/expl_appraisal_results.json" attributes
  echo "  -- replaying the sampled legacy-report PDFs (exact URLs recorded in MANIFEST.csv) --"
  replay_manifest "$RAW/uk" "uk/nsta/reports/"
}

# Netherlands: NLOG — own REST API (POST), not ArcGIS. Headers + details are bulk POST calls;
# stratstelsel is a bulk zip; the sampled report PDFs have per-document URLs already in MANIFEST.csv.
netherlands() {
  echo "== Netherlands (NLOG) =="
  local NL="$RAW/netherlands/nlog"
  mkdir -p "$NL/reports"

  if [ -s "$NL/nlog_boreholes_headers.json" ]; then
    STATUS_OK+=("$NL/nlog_boreholes_headers.json"); echo "  [ok]   $NL/nlog_boreholes_headers.json (already present)"
  elif curl "${CURL_OPTS[@]}" -H "Content-Type: application/json" -d '{}' \
        "https://www.nlog.nl/nlog-mapviewer/rest/brh/boreholes" -o "$NL/nlog_boreholes_headers.json.part" \
        && [ -s "$NL/nlog_boreholes_headers.json.part" ]; then
    mv "$NL/nlog_boreholes_headers.json.part" "$NL/nlog_boreholes_headers.json"
    STATUS_OK+=("$NL/nlog_boreholes_headers.json"); echo "  [ok]   $NL/nlog_boreholes_headers.json"
  else
    rm -f "$NL/nlog_boreholes_headers.json.part"
    STATUS_MISSING+=("$NL/nlog_boreholes_headers.json (POST boreholes)"); echo "  [FAIL] $NL/nlog_boreholes_headers.json"
  fi

  if [ -s "$NL/nlog_boreholes_details.json" ]; then
    STATUS_OK+=("$NL/nlog_boreholes_details.json"); echo "  [ok]   $NL/nlog_boreholes_details.json (already present)"
  elif [ -s "$NL/nlog_boreholes_headers.json" ]; then
    if python3 - "$NL/nlog_boreholes_headers.json" "$NL/nlog_boreholes_details.json" <<'PY'
import json, sys, urllib.request
headers_path, out_path = sys.argv[1], sys.argv[2]
headers = json.load(open(headers_path))
dbks = [h["boreholeDbk"] for h in headers if h.get("boreholeDbk") is not None]
details = []
for i in range(0, len(dbks), 1000):
    batch = dbks[i:i + 1000]
    req = urllib.request.Request(
        "https://www.nlog.nl/nlog-mapviewer/rest/brh/details",
        data=json.dumps(batch).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        details.extend(json.load(resp))
sys.exit(1) if not details else json.dump(details, open(out_path, "w")) or print(f"  [ok]   {out_path} ({len(details)} rows)")
PY
    then :; else
      STATUS_MISSING+=("$NL/nlog_boreholes_details.json (POST details, batched)"); echo "  [FAIL] $NL/nlog_boreholes_details.json"
    fi
    [ -s "$NL/nlog_boreholes_details.json" ] && STATUS_OK+=("$NL/nlog_boreholes_details.json")
  else
    echo "  [warn] no headers file present — cannot fetch details (need boreholeDbk list)"
  fi

  if [ -s "$NL/nlog_stratstelsel.csv" ] && [ -s "$NL/stratstelsel_beschrijving.pdf" ]; then
    STATUS_OK+=("$NL/nlog_stratstelsel.csv" "$NL/stratstelsel_beschrijving.pdf")
    echo "  [ok]   nlog_stratstelsel.csv + stratstelsel_beschrijving.pdf (already present)"
  else
    local zf tmpd
    zf="$(mktemp "${TMPDIR:-/tmp}/nlog_strat.XXXXXX.zip")"
    tmpd="$(mktemp -d "${TMPDIR:-/tmp}/nlog_strat_extract.XXXXXX")"
    if curl "${CURL_OPTS[@]}" "https://www.nlog.nl/sites/default/files/2026-09/thematische_data_boringen.zip" -o "$zf" && [ -s "$zf" ]; then
      unzip -oq "$zf" -d "$tmpd" 2>/dev/null || true
      local csv_src pdf_src
      csv_src="$(find "$tmpd" -iname 'nlog_stratstelsel_*.csv' | head -1)"
      pdf_src="$(find "$tmpd" -iname 'stratstelsel_beschrijving.pdf' | head -1)"
      if [ -n "$csv_src" ]; then cp "$csv_src" "$NL/nlog_stratstelsel.csv"; STATUS_OK+=("$NL/nlog_stratstelsel.csv"); echo "  [ok]   $NL/nlog_stratstelsel.csv"; else STATUS_MISSING+=("$NL/nlog_stratstelsel.csv (in bulk zip)"); fi
      if [ -n "$pdf_src" ]; then cp "$pdf_src" "$NL/stratstelsel_beschrijving.pdf"; STATUS_OK+=("$NL/stratstelsel_beschrijving.pdf"); echo "  [ok]   $NL/stratstelsel_beschrijving.pdf"; else STATUS_MISSING+=("$NL/stratstelsel_beschrijving.pdf (in bulk zip)"); fi
    else
      STATUS_MISSING+=("$NL/nlog_stratstelsel.csv + stratstelsel_beschrijving.pdf (bulk zip download failed)")
      echo "  [FAIL] thematische_data_boringen.zip"
    fi
    rm -f "$zf"; rm -rf "$tmpd"
  fi

  echo "  -- replaying the sampled well-report PDFs (per-document URLs recorded in MANIFEST.csv) --"
  replay_manifest "$RAW/netherlands" "nlog/reports/"

  if [ ! -s "$NL/docs_index_sample.json" ] || [ ! -s "$NL/selected_reports.json" ]; then
    echo "  [note] nlog/docs_index_sample.json and nlog/selected_reports.json cannot be re-fetched:"
    echo "         they record a one-off editorial sample (which ~280 of 6,737 wells' document lists"
    echo "         were inspected, and which 117 PDFs were picked) rather than a stable URL. The"
    echo "         nl_nlog ingester still works from nlog/reports/*.pdf alone (falls back to the"
    echo "         filename as the document title — see backend/app/ingest/ext/nl_nlog.py)."
  fi
}

# Australia: SARIG (South Australia, one WFS GetFeature call) + GSQ (Queensland CKAN portal, WAF-gated).
australia() {
  echo "== Australia (SARIG + GSQ) =="
  mkdir -p "$RAW/australia/sarig" "$RAW/australia/gsq/wcr"
  echo "  -- SARIG petroleum wells (single WFS request) --"
  replay_manifest "$RAW/australia" "sarig/"
  echo "  -- GSQ well-completion-report PDF sample (needs the portal's WAF cookie; best-effort) --"
  local cookiejar; cookiejar="$(mktemp "${TMPDIR:-/tmp}/gsq_cookies.XXXXXX")"
  curl -sS -L -c "$cookiejar" -A "Mozilla/5.0 (Kupakosh data fetch)" -m 30 \
    "https://geoscience.data.qld.gov.au/" -o /dev/null || true
  while IFS=$'\t' read -r f u; do
    [ -z "$f" ] && continue
    if [ -s "$RAW/australia/$f" ]; then
      STATUS_OK+=("$RAW/australia/$f")
    else
      mkdir -p "$(dirname "$RAW/australia/$f")"
      if curl -sS -L -b "$cookiejar" -A "Mozilla/5.0 (Kupakosh data fetch)" --retry 3 --retry-delay 5 \
          -m 120 "$u" -o "$RAW/australia/$f.part" && [ -s "$RAW/australia/$f.part" ]; then
        mv "$RAW/australia/$f.part" "$RAW/australia/$f"
        STATUS_OK+=("$RAW/australia/$f"); echo "  [ok]   $RAW/australia/$f"
      else
        rm -f "$RAW/australia/$f.part"
        STATUS_MISSING+=("$RAW/australia/$f (GSQ WAF; retry manually if this keeps failing)")
        echo "  [FAIL] $RAW/australia/$f"
      fi
      sleep 0.5   # the portal's WAF rate-limits parallel/rapid downloads (see REPORT.md)
    fi
  done < <(python3 - "$RAW/australia/MANIFEST.csv" "gsq/wcr/" <<'PY'
import csv, sys
path, prefix = sys.argv[1], sys.argv[2]
with open(path, newline="", encoding="utf-8") as fh:
    for row in csv.reader(fh):
        if not row or row[0] == "file" or not row[0].startswith(prefix):
            continue
        print(f"{row[0].strip()}\t{row[1].strip()}")
PY
  )
  rm -f "$cookiejar"
  if [ ! -s "$RAW/australia/gsq/wcr_meta.json" ]; then
    echo "  [note] gsq/wcr_meta.json cannot be re-fetched by a plain GET: it was built by querying"
    echo "         the CKAN package_search API with several filters (georesource_report_type=" \
      "well-completion-report; commodity in petroleum/oil/gaseous-hydrocarbons; capped 4 reports"
    echo "         per company) and is not a single stable URL — see data/raw/australia/REPORT.md."
    echo "  [note] South Australian WCR PDFs (SARIG catalogue) were never obtained by the original"
    echo "         agent either: catalog.sarig.sa.gov.au / data.sa.gov.au return 403 from a WAF to"
    echo "         every scripted or headless-browser request — a genuine manual-only gap."
  fi
}

# USA: BSEE bulk borehole file + historical incident-narrative PDFs + annual incident workbooks.
usa() {
  echo "== USA (BSEE) =="
  mkdir -p "$RAW/usa/bsee_well" "$RAW/usa/bsee_reports" "$RAW/usa/bsee_incidents"
  replay_manifest "$RAW/usa"
}

# New Zealand: NZP&M ArcGIS "Petroleum Wells" layer (paged; single-layer, no login).
nz() {
  echo "== New Zealand (NZP&M) =="
  mkdir -p "$RAW/nz/nzpam_wells"
  page_arcgis "https://services3.arcgis.com/fp1tibNcN9mbExhG/arcgis/rest/services/Petroleum_and_minerals/FeatureServer/18/query?where=1=1&outFields=*&f=json&outSR=4326" \
    "$RAW/nz/nzpam_wells/wells_raw.json" features
}

# Canada: CNSOPB (Nova Scotia), C-NLOPB (Newfoundland & Labrador, 4 layers), Saskatchewan — all ArcGIS.
canada() {
  echo "== Canada (CNSOPB + C-NLOPB + Saskatchewan) =="
  mkdir -p "$RAW/canada/cnsopb_wells" "$RAW/canada/cnlopb_wells" "$RAW/canada/sask_wells"
  page_arcgis "https://maps-cartes.services.geo.ca/server_serveur/rest/services/NRCan/Nova_Scotia_Offshore_Petroleum_en/MapServer/0/query?where=1=1&outFields=*&f=json&outSR=4326" \
    "$RAW/canada/cnsopb_wells/directory_of_wells.json" features
  local layer
  for layer in Exploration_Wells_View Delineation_Wells_View Development_Wells_View Dual_Classified_Wells_View; do
    page_arcgis "https://services5.arcgis.com/JZPISF0sj1UatnZ8/arcgis/rest/services/${layer}/FeatureServer/0/query?where=1=1&outFields=*&f=json" \
      "$RAW/canada/cnlopb_wells/${layer}.json" features
  done
  # Documented subset: the 6,000 most recently added Saskatchewan wells with a non-null TVD (the
  # depth column is free text, so the server can't filter on it numerically — see canada/REPORT.md).
  page_arcgis "https://gis.saskatchewan.ca/arcgis/rest/services/Economy/Petroleum/MapServer/0/query?where=WELLBORE_BH_TRUEVERTICALDEPTH+IS+NOT+NULL&outFields=*&orderByFields=OBJECTID+DESC&f=json&outSR=4326" \
    "$RAW/canada/sask_wells/wells_recent.json" features 6000
}

# =================================================================================================
ALL_SECTIONS=(core india force2020 uk netherlands australia usa nz canada)
ARGS=("$@")
[ "${#ARGS[@]}" -eq 0 ] && ARGS=("${ALL_SECTIONS[@]}")
if [ "${ARGS[0]}" = "core" ] && [ "${#ARGS[@]}" -eq 1 ]; then
  ARGS=(core india)   # `core` alone = the fast path: Sodir + FORGE + India
fi

echo "Kupakosh data fetch — DATA_DIR=$DATA_DIR — sections: ${ARGS[*]}"
echo

for s in "${ARGS[@]}"; do
  case "$s" in
    core) core ;;
    india) india ;;
    force2020) force2020 ;;
    uk) uk ;;
    netherlands) netherlands ;;
    australia) australia ;;
    usa) usa ;;
    nz) nz ;;
    canada) canada ;;
    *) echo "unknown section: $s (known: ${ALL_SECTIONS[*]})" ;;
  esac
  echo
done

echo "=================================================================================="
echo "Summary: $(printf '%s\n' "${STATUS_OK[@]}" | sort -u | wc -l | tr -d ' ') files present"
if [ "${#STATUS_MISSING[@]}" -gt 0 ]; then
  echo "MISSING (${#STATUS_MISSING[@]}) — re-run this script later, or see the [note]s above for" \
    "sources that need a manual/registered download:"
  printf '  - %s\n' "${STATUS_MISSING[@]}"
else
  echo "Nothing reported missing."
fi
