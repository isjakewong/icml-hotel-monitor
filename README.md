# ICML 2026 hotel monitor (GitHub Actions, self-looping)

Cloud watcher that checks every **5 minutes**, 24/7, with your laptop off, and pushes an
**ntfy.sh** alert to your phone the moment a room opens for **Jul 8 → 9, 2026 (1 night, 1 guest)** at:

- The Westin Seoul Parnas
- Grand InterContinental Seoul Parnas by IHG

Booking site: https://book.resiada.com/43rdICML2026/Attendees
Repo: https://github.com/isjakewong/icml-hotel-monitor  (**public** — see "Why public" below)

## How it works (reliability design)
GitHub's *scheduled* cron is unreliable for short intervals (it delays/drops `*/5` runs under load).
So instead of trusting it, the workflow runs a **long-lived job with an internal 5-min loop**
(`python3 check.py; sleep 300`) for ~5.5 h, then **re-launches itself** (`gh workflow run` via the
built-in `GITHUB_TOKEN`, which is exempt from the no-recursion rule) for near-seamless handoff.
The `schedule:` cron (~every 15 min) is only a **keepalive** that restarts coverage if a chain ever dies.

`check.py` queries the Resiada API (token → `/v1/Hotel`). When a target hotel reports `roomCount > 0` /
`roomsLeft` ≠ "Unavailable" (or a waitlist opens), it POSTs an alert to your ntfy topic. `state.json`
is committed back on change, so you're alerted once per *becomes-available* event (re-alert ≤ every
30 min while it persists) — no spam.

## Why public (and is it safe?)
Public repos get **unlimited free Actions minutes** (private free tier is ~2000/mo, which a 5-min
loop would blow through). Safe because the ntfy topic is stored as the **secret `NTFY_TOPIC`** and is
masked in logs; `state.json` only holds avail/timestamp values; the code contains no credentials.

## ⚠️ Booking window
Closes **2026-06-11 21:00 UTC** (Jun 11, 5 PM US-Eastern). Useful through ~June 11 — **disable/delete after**.

## Manage
```bash
export PATH="/opt/homebrew/bin:$PATH"; cd ~/Documents/icml_hotel/github-actions-monitor
gh run list --workflow=monitor.yml            # see runs (one long in-progress chain = healthy)
gh workflow run "ICML hotel monitor" -f test=true   # fire a TEST phone push from the cloud

# STOP everything (do both, or just delete the repo):
gh workflow disable "ICML hotel monitor"      # stop future chains/keepalive
gh run cancel $(gh run list --workflow=monitor.yml -L1 --json databaseId --jq '.[0].databaseId')  # stop the current chain now
# or nuke it entirely:
gh repo delete isjakewong/icml-hotel-monitor --yes
```

## Files
- `.github/workflows/monitor.yml` — self-looping workflow (5-min loop + chain handoff + keepalive)
- `check.py` — availability checker (stdlib only); `--test` fires a sample push
- `state.json` — last-known availability per hotel (alert de-dup), committed on change
