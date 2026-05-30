# Self-hosting on a Linux laptop (Ubuntu + systemd)

Run the bot 24/7 on your own machine (e.g. the Dell Vostro). The bot uses
Telegram **long-polling**, so there are **no inbound ports, no firewall,
no public IP, no nginx** — the laptop just needs outbound internet.

> ⚠️ **Only one instance may run per bot token.** Telegram rejects a
> second long-poll with a `Conflict`. Before starting the laptop, **stop
> the Railway deployment** (and copy its data over — step 5), or the two
> will fight and the laptop will give up after a few retries.

Hardware note: a Core i7 + Iris Xe is plenty. Everything is CPU-bound;
there's no GPU requirement. Supertonic audio is faster here than on
Railway's shared vCPU, but still serialized — text/Edge scrapes are
instant.

---

## 1. Install system packages

```bash
sudo apt update
sudo apt install -y python3 python3-venv git ffmpeg
```
`ffmpeg` is required for voice messages (MP3 → Opus). `git` to clone/update.

## 2. Get the code + Python deps

```bash
git clone https://github.com/Avazbek-A/tez-news-bot.git ~/tez-news-bot
cd ~/tez-news-bot
bash scripts/setup_local.sh        # creates .venv, installs deps, smoke-tests
```

## 3. Create the durable-state directory

State (history, bookmarks, settings, metrics, the TTS model) lives under
`DATA_DIR`. Keep it **outside** the repo so `git pull` never touches it:

```bash
sudo mkdir -p /var/lib/spot-bot
sudo chown "$USER":"$USER" /var/lib/spot-bot
```

## 4. Configure secrets + env

```bash
sudo cp deploy/spot-bot.env.example /etc/spot-bot.env
sudo nano /etc/spot-bot.env        # set BOT_TOKEN, DATA_DIR, ALERT_CHAT_ID, …
sudo chmod 600 /etc/spot-bot.env   # it holds secrets
```
At minimum set `BOT_TOKEN` and `DATA_DIR=/var/lib/spot-bot`. Get
`ALERT_CHAT_ID` by sending **/chatid** to the bot once it's running.

## 5. Migrate existing data from Railway (if applicable)

So your history/bookmarks/settings carry over:

1. **Stop the Railway service** (Railway dashboard → the service → Remove/Pause
   deploy). This frees the long-poll.
2. Download `history.db` and `user_settings.json` from the Railway volume.
3. Copy them into the new data dir:
   ```bash
   cp history.db user_settings.json /var/lib/spot-bot/
   ```
Skip this if you're starting fresh.

## 6. Install the systemd service

Edit the placeholders in `deploy/spot-bot.service`:
- `__USER__` → your login name (run `whoami`)
- `__APP_DIR__` → `/home/<you>/tez-news-bot` (run `pwd` in the repo)

```bash
# quick in-place edit:
sed -e "s#__USER__#$USER#g" -e "s#__APP_DIR__#$PWD#g" \
    deploy/spot-bot.service | sudo tee /etc/systemd/system/spot-bot.service >/dev/null

sudo systemctl daemon-reload
sudo systemctl enable --now spot-bot
```

## 7. Verify

```bash
systemctl status spot-bot         # should say active (running)
journalctl -u spot-bot -f         # live logs; Ctrl-C to stop tailing
```
Then in Telegram: **/status**, **/metrics**, and a quick **/scrape 3**.

---

## Keep a *laptop* alive as a server

A laptop sleeps when you close the lid — which kills the bot. Disable that:

```bash
sudo nano /etc/systemd/logind.conf
#   HandleLidSwitch=ignore
#   HandleLidSwitchExternalPower=ignore
sudo systemctl restart systemd-logind
```
Also keep it plugged in, and consider disabling auto-suspend:
```bash
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
```

## Updating the bot

```bash
cd ~/tez-news-bot
git pull
./.venv/bin/pip install -r requirements.txt   # in case deps changed
sudo systemctl restart spot-bot
```
State in `DATA_DIR` is untouched. Schema migrations (DB + settings) run
automatically on restart — take a backup first if a release bumps a
version (it'll be noted in the changelog).

## Backups

```bash
# simple daily copy (cron / systemd timer)
cp /var/lib/spot-bot/history.db /var/lib/spot-bot/user_settings.json /path/to/backup/
```

## Operations

Day-to-day monitoring, alerting, and incident response are the same as
the hosted setup — see **docs/RUNBOOK.md**. The canary
(`python -m scripts.healthcheck`) and `/metrics` work identically here.

## Common issues

| Symptom | Fix |
|---|---|
| `Conflict` in logs, bot won't start | Another instance is polling — stop Railway / any other copy. |
| No audio | `ffmpeg` not installed: `sudo apt install -y ffmpeg`, then `sudo systemctl restart spot-bot`. |
| Dies when you close the lid | Set `HandleLidSwitch=ignore` (above). |
| State lost after an update | `DATA_DIR` not set or pointed inside the repo — set it to `/var/lib/spot-bot` in `/etc/spot-bot.env`. |
| `BOT_TOKEN not set` | Check `/etc/spot-bot.env` and that the unit's `EnvironmentFile=` path matches. |
