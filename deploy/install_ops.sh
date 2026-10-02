#!/usr/bin/env bash
# Install the reliability pieces on the server (run by scripts/deploy_aws.sh; safe to run again):
#   kupakosh-health.timer   every minute: ask the app, restart after 3 failed checks in a row
#   kupakosh-backup.timer   daily 02:30 IST: checked, compressed database backup, newest 7 kept
#   kupakosh.service drop-in: always restart on a crash, without systemd's give-up limit
# Usage on the server: sudo bash ~/kupakosh/deploy/install_ops.sh <app user>
set -euo pipefail
USER_NAME="${1:-ubuntu}"
HOME_DIR=$(getent passwd "$USER_NAME" | cut -d: -f6)
SRC="$HOME_DIR/kupakosh/deploy"

install -m 0755 "$SRC/kupakosh-health.sh" /usr/local/bin/kupakosh-health
install -m 0755 "$SRC/kupakosh-backup.sh" /usr/local/bin/kupakosh-backup
[ -f /etc/default/kupakosh-ops ] || printf '# KK_BACKUP_S3=s3://bucket/prefix\n# KK_BACKUP_KEEP=7\n' > /etc/default/kupakosh-ops

mkdir -p /etc/systemd/system/kupakosh.service.d
cat > /etc/systemd/system/kupakosh.service.d/restart.conf <<'EOF'
[Unit]
StartLimitIntervalSec=0
[Service]
Restart=always
RestartSec=5
EOF

cat > /etc/systemd/system/kupakosh-health.service <<'EOF'
[Unit]
Description=Kupakosh health check (restart after repeated failures)
[Service]
Type=oneshot
ExecStart=/usr/local/bin/kupakosh-health
EOF
cat > /etc/systemd/system/kupakosh-health.timer <<'EOF'
[Unit]
Description=Kupakosh health check every minute
[Timer]
OnBootSec=3min
OnUnitActiveSec=1min
AccuracySec=10s
[Install]
WantedBy=timers.target
EOF

cat > /etc/systemd/system/kupakosh-backup.service <<EOF
[Unit]
Description=Kupakosh daily database backup
[Service]
Type=oneshot
User=$USER_NAME
EnvironmentFile=-/etc/default/kupakosh-ops
Environment=HOME=$HOME_DIR
ExecStart=/usr/local/bin/kupakosh-backup
Nice=10
IOSchedulingClass=idle
EOF
cat > /etc/systemd/system/kupakosh-backup.timer <<'EOF'
[Unit]
Description=Kupakosh database backup, daily 02:30 IST
[Timer]
OnCalendar=*-*-* 21:00:00 UTC
Persistent=true
[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now kupakosh-health.timer kupakosh-backup.timer
echo "installed: $(systemctl is-active kupakosh-health.timer) health timer, $(systemctl is-active kupakosh-backup.timer) backup timer"
