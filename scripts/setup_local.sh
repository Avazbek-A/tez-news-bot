#!/usr/bin/env bash
# One-shot local setup for self-hosting the bot on Ubuntu/Linux.
# Creates the Python venv, installs deps, and checks for ffmpeg.
# Does NOT touch systemd or secrets — see docs/SELF_HOST.md for those.
#
#   bash scripts/setup_local.sh
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"
echo "Project: $ROOT"

# --- system prerequisites ---
if ! command -v python3 >/dev/null 2>&1; then
  echo "✗ python3 not found. Install it:  sudo apt update && sudo apt install -y python3 python3-venv"
  exit 1
fi
echo "✓ $(python3 --version)"

if ! python3 -c 'import venv' >/dev/null 2>&1; then
  echo "✗ python3-venv missing. Install it:  sudo apt install -y python3-venv"
  exit 1
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "⚠ ffmpeg not found — audio (voice messages) will not work."
  echo "  Install it:  sudo apt install -y ffmpeg"
else
  echo "✓ ffmpeg present"
fi

# --- python venv + deps ---
if [ ! -d .venv ]; then
  echo "Creating virtualenv (.venv)..."
  python3 -m venv .venv
fi
echo "Installing dependencies..."
./.venv/bin/python -m pip install --quiet --upgrade pip
./.venv/bin/pip install --quiet -r requirements.txt
echo "✓ Dependencies installed"

# --- quick smoke (build the app, no network) ---
if BOT_TOKEN=setup:dummy ./.venv/bin/python -m scripts.smoke_test >/dev/null 2>&1; then
  echo "✓ Smoke test passed (app builds)"
else
  echo "⚠ Smoke test failed — check the output of: BOT_TOKEN=setup:dummy ./.venv/bin/python -m scripts.smoke_test"
fi

cat <<EOF

Next steps (see docs/SELF_HOST.md):
  1. mkdir the data dir:   sudo mkdir -p /var/lib/spot-bot && sudo chown \$USER:\$USER /var/lib/spot-bot
  2. config + secrets:     sudo cp deploy/spot-bot.env.example /etc/spot-bot.env && sudo nano /etc/spot-bot.env && sudo chmod 600 /etc/spot-bot.env
  3. install the service:  edit deploy/spot-bot.service placeholders, then enable it
  4. start it:             sudo systemctl enable --now spot-bot && journalctl -u spot-bot -f
EOF
