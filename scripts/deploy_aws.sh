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
  ssh -i "$KEY" "$HOST" 'sudo systemctl stop kupakosh'
  rsync -az --partial --progress -e "ssh -i $KEY" data/kupakosh.db data/processed "$HOST":kupakosh/data/
  rsync -az -e "ssh -i $KEY" wiki "$HOST":kupakosh/
fi

echo "Restarting…"
ssh -i "$KEY" "$HOST" 'source ~/.local/bin/env && cd ~/kupakosh/backend && uv pip install -q --python .venv -r requirements.txt && sudo systemctl restart kupakosh'
for i in $(seq 1 40); do
  code=$(curl -s -o /dev/null -w "%{http_code}" https://kupakosh.duckdns.org/api/status || true)
  [ "$code" = 200 ] && break; sleep 3
done
echo "Live status: $code"
curl -s -m 120 https://kupakosh.duckdns.org/api/analogs/assam | python3 -c "import json,sys; d=json.load(sys.stdin); print('Assam column:', len(d['formations']), 'formations')"
