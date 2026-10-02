#!/usr/bin/env bash
# Daily backup of the live database (run by kupakosh-backup.timer).
#  * SQLite online backup API: safe while the site is running (no stop, no half-copied WAL).
#  * The copy is checked (PRAGMA quick_check) before it is kept; a bad copy is deleted and the run fails loudly.
#  * gzip, keep the newest $KEEP; skipped (and reported) when the disk is too full to hold one more.
#  * Optional off-machine copy: set KK_BACKUP_S3=s3://bucket/prefix in /etc/default/kupakosh-ops (needs the aws CLI
#    and an instance role allowed to write there). Without it, backups stay on this server's disk only.
set -euo pipefail
APP="${KK_APP_DIR:-$HOME/kupakosh}"
DB="$APP/data/kupakosh.db"
OUT="${KK_BACKUP_DIR:-$APP/backups}"
KEEP="${KK_BACKUP_KEEP:-7}"
mkdir -p "$OUT"
[ -f "$DB" ] || { echo "no database at $DB"; exit 1; }

need_kb=$(( $(stat -c %s "$DB") / 1024 * 2 ))
free_kb=$(df -Pk "$OUT" | awk 'NR==2 {print $4}')
if [ "$free_kb" -lt "$need_kb" ]; then
  echo "backup skipped: ${free_kb} KB free, need ${need_kb} KB"; exit 1
fi

stamp=$(date -u +%Y%m%dT%H%M%SZ)
tmp="$OUT/.kupakosh-$stamp.db"
if ! python3 - "$DB" "$tmp" <<'PY'
import sqlite3, sys
src = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
dst = sqlite3.connect(sys.argv[2])
src.backup(dst)
ok = dst.execute("pragma quick_check").fetchone()[0]
dst.close(); src.close()
sys.exit(0 if ok == "ok" else 1)
PY
then rm -f "$tmp"; echo "backup copy failed its integrity check"; exit 1; fi
gzip -6 -c "$tmp" > "$OUT/kupakosh-$stamp.db.gz.part" && mv "$OUT/kupakosh-$stamp.db.gz.part" "$OUT/kupakosh-$stamp.db.gz"
rm -f "$tmp"
# the reviewed wiki (git repo) is small: keep it with each backup
[ -d "$APP/wiki" ] && tar -czf "$OUT/wiki-$stamp.tar.gz" -C "$APP" wiki
echo "backup written: $OUT/kupakosh-$stamp.db.gz ($(du -h "$OUT/kupakosh-$stamp.db.gz" | cut -f1))"

ls -1t "$OUT"/kupakosh-*.db.gz 2>/dev/null | tail -n +$((KEEP + 1)) | xargs -r rm -f || true
ls -1t "$OUT"/wiki-*.tar.gz 2>/dev/null | tail -n +$((KEEP + 1)) | xargs -r rm -f || true

if [ -n "${KK_BACKUP_S3:-}" ] && command -v aws >/dev/null; then
  aws s3 cp --only-show-errors "$OUT/kupakosh-$stamp.db.gz" "$KK_BACKUP_S3/" && echo "copied to $KK_BACKUP_S3"
fi
