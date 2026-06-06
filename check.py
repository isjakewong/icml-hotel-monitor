#!/usr/bin/env python3
"""ICML 2026 hotel availability check — runs on GitHub Actions every ~5 min.

Polls the Resiada housing API for the target hotel on the night of
Jul 9 -> Jul 10, 2026 and pushes an ntfy.sh alert the moment a room opens.
State (state.json) is committed back to the repo so alerts fire once per
"becomes available" transition (re-alert at most every 30 min while it lasts).
Stdlib only — no dependencies.
"""
import json, os, sys, time, urllib.request

API = "https://api.resiada.com/v1"
EVENT_ID = "b5d011fc-0111-f111-a69c-002248548541"
SUBBLOCK_ID = "c9d011fc-0111-f111-a69c-002248548541"
CHECKIN = "2026-07-09"
CHECKOUT = "2026-07-10"
GUESTS = 1
BOOK_URL = "https://book.resiada.com/43rdICML2026/Attendees"
ORIGIN = "https://book.resiada.com"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
TARGETS = [
    {"id": "fdff689e-341f-f111-9a49-000d3ae43f90", "name": "The Westin Seoul Parnas"},
]
STATE_FILE = "state.json"
REALERT = 30 * 60  # seconds; re-alert at most this often while still available
TOPIC = os.environ.get("NTFY_TOPIC", "").strip()
TEST = "--test" in sys.argv


def http(url, data=None, headers=None, timeout=30):
    h = {"User-Agent": UA, "Origin": ORIGIN}
    if headers:
        h.update(headers)
    method = "POST" if data is not None else "GET"
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8", "replace")


def get_token():
    body = json.dumps({"culture": "en-US", "eventID": EVENT_ID}).encode()
    _, txt = http(f"{API}/BookingGroup/token", data=body,
                  headers={"Content-Type": "application/json"})
    return json.loads(txt)["token"]


def get_hotels(token):
    url = (f"{API}/Hotel?page=0&pagesize=50&culture=en-US&subBlockId={SUBBLOCK_ID}"
           f"&checkIn={CHECKIN}&checkOut={CHECKOUT}&guests={GUESTS}")
    _, txt = http(url, headers={"Authorization": f"Bearer {token}"})
    return json.loads(txt).get("items", [])


def assess(item):
    counts = [int(c.get("count", 0) or 0) for c in (item.get("roomCount") or [])]
    mincount = min(counts) if counts else 0
    roomsleft = str(item.get("roomsLeft") or "").strip()
    soldout = roomsleft.lower() in ("unavailable", "sold out", "soldout", "")
    waitlist = str(item.get("waitListAvailability") or "none").strip()
    wlopen = waitlist.lower() not in ("none", "")
    available = (mincount > 0) or (not soldout)
    return available, wlopen, mincount, roomsleft, waitlist


def ntfy(title, body):
    if not TOPIC:
        print("WARN: NTFY_TOPIC not set; cannot push")
        return
    safe_title = title.encode("ascii", "ignore").decode() or "ICML hotel alert"  # headers are latin-1
    headers = {
        "Title": safe_title, "Priority": "urgent", "Tags": "hotel,bell",
        "Click": BOOK_URL, "Actions": f"view, Book now, {BOOK_URL}, clear=true",
    }
    try:
        st, _ = http(f"https://ntfy.sh/{TOPIC}", data=body.encode("utf-8"), headers=headers)
        print(f"ntfy push -> HTTP {st}")
    except Exception as e:
        print("ntfy push failed:", e)


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def main():
    if TEST:
        ntfy("ROOM OPENED (TEST): The Westin Seoul Parnas",
             "TEST: The Westin Seoul Parnas - rooms available for Jul 9-10 (ICML). "
             "This is a GitHub Actions channel test. Book: " + BOOK_URL)
        print("sent test alert")
        return 0

    now = int(time.time())
    try:
        token = get_token()
        hotels = get_hotels(token)
    except Exception as e:
        print("ERROR fetching availability:", e)
        return 0  # transient; let the next scheduled run retry without a red X

    by_id = {h.get("id"): h for h in hotels}
    state = load_state()
    summary = []
    for tgt in TARGETS:
        item = by_id.get(tgt["id"])
        if not item:
            print(f"WARN: {tgt['name']} not in response (block may have closed)")
            continue
        available, wlopen, mincount, roomsleft, waitlist = assess(item)
        prev = state.get(tgt["id"], {"avail": False, "lastAlert": 0})
        signal = available or wlopen
        summary.append(f"{tgt['name']}: rooms={mincount} roomsLeft='{roomsleft}' wl={waitlist}")
        became = signal and not prev.get("avail")
        stale = signal and prev.get("avail") and (now - prev.get("lastAlert", 0) > REALERT)
        if became or stale:
            if available and mincount > 0:
                kind = f"{mincount} room(s) available"
            elif available:
                kind = "rooms available"
            else:
                kind = "waitlist open"
            verb = "ROOM OPENED" if became else "still available"
            ntfy(f"{verb}: {tgt['name']}",
                 f"{tgt['name']} - {kind} for Jul 9-10 (ICML). Book now: {BOOK_URL}")
            state[tgt["id"]] = {"avail": True, "lastAlert": now}
        elif signal:
            state[tgt["id"]] = {"avail": True, "lastAlert": prev.get("lastAlert", 0)}
        else:
            if prev.get("avail"):
                print(f"{tgt['name']} no longer available")
            state[tgt["id"]] = {"avail": False, "lastAlert": prev.get("lastAlert", 0)}

    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, sort_keys=True)
    print("check ok |", " || ".join(summary))
    return 0


sys.exit(main())
