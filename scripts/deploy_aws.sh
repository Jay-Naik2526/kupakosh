#!/usr/bin/env bash
# Update the live site (https://kupakosh.duckdns.org) from this Mac.
# Needs: `aws login` done in this terminal, and ~/.ssh/kupakosh.pem.
# Steps: allow SSH from this Mac's current IP -> build the static site -> upload code, config and site -> restart -> check.
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

echo "Restarting…"
ssh -i "$KEY" "$HOST" 'source ~/.local/bin/env && cd ~/kupakosh/backend && uv pip install -q --python .venv -r requirements.txt && sudo systemctl restart kupakosh'
for i in $(seq 1 40); do
  code=$(curl -s -o /dev/null -w "%{http_code}" https://kupakosh.duckdns.org/api/status || true)
  [ "$code" = 200 ] && break; sleep 3
done
echo "Live status: $code"
curl -s -m 120 https://kupakosh.duckdns.org/api/analogs/assam | python3 -c "import json,sys; d=json.load(sys.stdin); print('Assam column:', len(d['formations']), 'formations')"
