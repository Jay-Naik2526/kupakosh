#!/usr/bin/env bash
# Put a backup back in place (on the server): checks it, keeps the current database as kupakosh.db.before-restore.
#   bash ~/kupakosh/deploy/restore_backup.sh                 newest backup
#   bash ~/kupakosh/deploy/restore_backup.sh <file.db.gz>    a chosen one (ls ~/kupakosh/backups)
set -euo pipefail
APP="$HOME/kupakosh"
F="${1:-$(ls -1t "$APP"/backups/kupakosh-*.db.gz | head -1)}"
[ -f "$F" ] || { echo "no backup found"; exit 1; }
echo "restoring $F"
gunzip -c "$F" > "$APP/data/kupakosh.db.restore"
python3 -c "import sqlite3,sys; sys.exit(0 if sqlite3.connect('$APP/data/kupakosh.db.restore').execute('pragma quick_check').fetchone()[0]=='ok' else 1)" \
  || { rm -f "$APP/data/kupakosh.db.restore"; echo "backup fails its check - nothing changed"; exit 1; }
sudo systemctl stop kupakosh
cd "$APP/data" && mv kupakosh.db kupakosh.db.before-restore && rm -f kupakosh.db-wal kupakosh.db-shm && mv kupakosh.db.restore kupakosh.db
sudo systemctl start kupakosh
echo "restored; previous database kept as $APP/data/kupakosh.db.before-restore"
