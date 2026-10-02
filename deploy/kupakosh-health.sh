#!/usr/bin/env bash
# Health check (run every minute by kupakosh-health.timer).
#  * Asks the app itself (localhost:8010/health, 10 s timeout) — not only "is the process alive": a hung server fails too.
#  * Restarts kupakosh only after $FAILS failed checks in a row, so one slow answer never bounces the site,
#    and never while systemd is still starting it (the first start builds caches for a few minutes).
#  * Every restart is logged (journalctl -t kupakosh-health) with the reason.
set -uo pipefail
URL="${KK_HEALTH_URL:-http://127.0.0.1:8010/health}"
FAILS="${KK_HEALTH_FAILS:-3}"
STATE=/run/kupakosh-health.fails
log() { logger -t kupakosh-health "$*"; echo "$*"; }

state=$(systemctl is-active kupakosh || true)
if [ "$state" = "activating" ] || [ "$state" = "reloading" ]; then
  exit 0
fi
if [ "$state" != "active" ]; then
  log "service is '$state' - starting it"
  systemctl start kupakosh; echo 0 > "$STATE"; exit 0
fi
# within 5 minutes of a (re)start the app may still be warming up: give it time
since=$(systemctl show kupakosh -p ActiveEnterTimestampMonotonic --value)
now=$(awk '{printf "%d", $1 * 1000000}' /proc/uptime)
if [ -n "$since" ] && [ "$since" -gt 0 ] && [ $(( (now - since) / 1000000 )) -lt 300 ]; then
  exit 0
fi

if curl -fsS -m 10 -o /dev/null "$URL"; then
  echo 0 > "$STATE"; exit 0
fi
n=$(( $(cat "$STATE" 2>/dev/null || echo 0) + 1 ))
echo "$n" > "$STATE"
log "health check failed ($n of $FAILS in a row): $URL"
if [ "$n" -ge "$FAILS" ]; then
  log "restarting kupakosh after $n failed health checks"
  systemctl restart kupakosh
  echo 0 > "$STATE"
fi
