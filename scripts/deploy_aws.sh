#!/usr/bin/env bash
# Update the live site (https://kupakosh.duckdns.org) from this Mac.
# Needs: `aws login` done in this terminal, and ~/.ssh/kupakosh.pem.
# Steps: allow SSH from this Mac's current IP -> build the static site -> upload code, config and site -> restart -> check.
#   bash scripts/deploy_aws.sh          code + site only
#   bash scripts/deploy_aws.sh --data   also the database, search index and wiki (needed after new data, e.g. the Volve DDRs;
#                                       ~400 MB, slow on a mobile connection)
set -euo pipefail
cd "$(dirname "$0")/.."

REGION=ap-south-1
SG=sg-00f3cbc21455fb961
HOST=ubuntu@13.232.60.188
KEY=~/.ssh/kupakosh.pem

MYIP=$(curl -s https://checkip.amazonaws.com)
echo "This Mac's IP: $MYIP"
aws ec2 authorize-security-group-ingress --region "$REGION" --group-id "$SG" --protocol tcp --port 22 --cidr "$MYIP/32" >/dev/null 2>&1 \
  && echo "SSH allowed from $MYIP" || echo "SSH rule for $MYIP already present"

echo "Building the static site…"
(cd frontend && KK_EXPORT=1 npx next build >/dev/null)

echo "Uploading…"
rsync -az -e "ssh -i $KEY" --exclude __pycache__ backend/app backend/scripts backend/tests backend/requirements.txt "$HOST":kupakosh/backend/
rsync -az -e "ssh -i $KEY" config "$HOST":kupakosh/
rsync -az --delete -e "ssh -i $KEY" frontend/out "$HOST":kupakosh/frontend/
if [ "${1:-}" = "--data" ]; then
  echo "Uploading data (database, search index, wiki)…"
  sqlite3 data/kupakosh.db "PRAGMA wal_checkpoint(TRUNCATE);" >/dev/null
  sqlite3 data/kupakosh.db "PRAGMA quick_check;" | grep -qx ok || { echo "local database fails its integrity check — not uploading"; exit 1; }
  # upload to a temporary name; a dropped connection can then never leave a half-written database in place
  rsync -az --partial --progress -e "ssh -i $KEY" data/kupakosh.db "$HOST":kupakosh/data/kupakosh.db.new
  rsync -az --partial -e "ssh -i $KEY" data/processed "$HOST":kupakosh/data/
  rsync -az -e "ssh -i $KEY" wiki "$HOST":kupakosh/
  # swap in only after the server-side copy passes its own check; drop the old database's journal files (-wal/-shm),
  # which SQLite would otherwise replay onto the new file ("database disk image is malformed")
  ssh -i "$KEY" "$HOST" 'cd ~/kupakosh/data && python3 -c "import sqlite3,sys; sys.exit(0 if sqlite3.connect(\"kupakosh.db.new\").execute(\"pragma quick_check\").fetchone()[0]==\"ok\" else 1)" \
    && sudo systemctl stop kupakosh && rm -f kupakosh.db-wal kupakosh.db-shm && mv kupakosh.db.new kupakosh.db && echo "database swapped in" \
    || { echo "uploaded database failed its check on the server — keeping the old one"; exit 1; }' 
fi

echo "Restarting…"
ssh -i "$KEY" "$HOST" 'source ~/.local/bin/env && cd ~/kupakosh/backend && uv pip install -q --python .venv -r requirements.txt && sudo systemctl daemon-reload && sudo systemctl restart kupakosh'
for i in $(seq 1 100); do   # up to 5 minutes: the first start builds caches over a bigger database
  code=$(curl -s -o /dev/null -w "%{http_code}" https://kupakosh.duckdns.org/api/status || true)
  [ "$code" = 200 ] && break; sleep 3
done
echo "Live status: $code"
[ "$code" = 200 ] && curl -s -m 120 https://kupakosh.duckdns.org/api/hindsight/summary | python3 -c "import json,sys; d=json.load(sys.stdin); print('Hindsight:', d['n_testable'], 'wells, AUC', d['learned']['auc']['learned_live']['auc'])" || echo "site not up yet — see: ssh -i $KEY $HOST 'sudo journalctl -u kupakosh -n 50'"
