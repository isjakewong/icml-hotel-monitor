# ICML 2026 hotel monitor (GitHub Actions)

Cloud watcher that runs every ~5 min on GitHub Actions (no laptop needed) and pushes an
**ntfy.sh** alert to your phone the moment a room opens for **Jul 8 → 9, 2026 (1 night, 1 guest)** at:

- The Westin Seoul Parnas
- Grand InterContinental Seoul Parnas by IHG

Booking site: https://book.resiada.com/43rdICML2026/Attendees

## How it works
`.github/workflows/monitor.yml` runs `check.py` on a `*/5 * * * *` schedule. The script queries the
Resiada API (token → `/v1/Hotel` availability), and when a target hotel reports `roomCount > 0` /
`roomsLeft` ≠ "Unavailable" (or a waitlist opens), it POSTs an alert to your ntfy topic. `state.json`
is committed back to the repo so you're alerted once per *becomes-available* event (re-alert ≤ every
30 min while it persists) — no spam.

The ntfy topic is stored as the repo secret **`NTFY_TOPIC`** (not in code).

## ⚠️ Notes
- **Booking window closes 2026-06-11 21:00 UTC** (Jun 11, 5 PM US-Eastern). Useful through ~June 11.
- GitHub's scheduled workflows have a 5-min minimum and **can be delayed** several minutes under load —
  fine for hotel cancellations, which don't appear by the second.
- This complements the Mac monitor (same ntfy topic) for redundancy.

## Manage
```bash
gh workflow run "ICML hotel monitor"   # run now
gh run list --workflow=monitor.yml     # recent runs
gh run watch                           # watch latest
# stop: disable the workflow in the repo's Actions tab, or delete the repo
gh secret set NTFY_TOPIC               # rotate the push topic
```
