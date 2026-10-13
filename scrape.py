#!/usr/bin/env python3
"""Scrape Hadestown per-performance cast changes from atthisplaybill.com.

The site is served via Cloudflare + Craft CMS. `?perf=<id>` pages are cached
aggressively (and stale entries show the current performance), so each request
includes a random cache-buster query param to force an origin fetch.

Outputs:
  data/raw/perf_<id>.html   raw HTML per performance
  data/performances.json    parsed data: date, role changes, performer bios
  data/cast_changes.csv     flat table: date, perf_id, role, performer, usual performer

Use `python3 scrape.py --refresh` to re-fetch every currently listed performance.
"""

import csv
import html as html_mod
import json
import random
import re
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

BASE = "https://atthisplaybill.com/hadestown"
OUT = Path(__file__).parent / "data"
RAW = OUT / "raw"

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def bust(url):
    return f"{url}&_={random.getrandbits(48)}" if "?" in url else f"{url}?_={random.getrandbits(48)}"


def strip_tags(s):
    return html_mod.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def norm_date(s):
    """'Thu, Oct 8, 2026 at 7:00 PM' -> (datetime, 'Oct 8, 2026 7:00 PM')"""
    s = re.sub(r"\s+", " ", s).strip()
    return datetime.strptime(s, "%a, %b %d, %Y at %I:%M %p")


def get_perf_list_from(page):
    """Parse the 'Select Performance' modal -> [(perf_id, label)]."""
    out = []
    for m in re.finditer(
        r'href="https://atthisplaybill\.com/hadestown\?perf=(\d+)"[^>]*>\s*([^<]+?)\s*</a>',
        page,
    ):
        out.append((int(m.group(1)), re.sub(r"\s+", " ", m.group(2))))
    return out


def parse_performance(html, perf_id, expected_label):
    m = re.search(r'performance-date">\s*([^<]+?)\s*<', html)
    date_text = m.group(1).strip() if m else None
    dt = norm_date(date_text) if date_text else None

    no_changes = bool(re.search(r'class="no-changes"', html))

    changes = []
    for block in re.finditer(r'class="role-change">(.*?)(?=class="role-change"|class="view-prior-btn")', html, re.S):
        b = block.group(1)
        role_m = re.search(r"The role of <strong>([^<]+)</strong>", b, re.S)
        usual_m = re.search(r"Usually played by\s*<strong>([^<]+)</strong>", b, re.S)
        will_m = re.search(r"Will be played by\s*<strong>([^<]+)</strong>", b, re.S)
        if not role_m or not will_m:
            continue
        role = strip_tags(role_m.group(1))
        performer = strip_tags(will_m.group(1))
        img = re.search(r'<img src="([^"]+)"', b)
        bio_m = re.search(r'class="performer-bio">(.*?)</div>', b, re.S)
        bio = re.sub(r"\s+", " ", strip_tags(bio_m.group(1))) if bio_m else None
        changes.append({
            "role": role,
            "performer": performer,
            "replaces": strip_tags(usual_m.group(1)) if usual_m else None,
            "bio": bio,
            "headshot": img.group(1) if img else None,
        })

    expected_dt = norm_date(expected_label) if expected_label else None
    date_match = (dt == expected_dt) if (dt and expected_dt) else None
    # The site falls back to the current performance when a perf record is
    # gone (records appear to expire ~30 days out). Never record stale data.
    if date_match is False:
        changes = []
        served = date_text          # what the server actually showed (current perf)
        date_text = expected_label  # label from the modal = the real performance
        dt = expected_dt
    else:
        served = None

    return {
        "perf_id": perf_id,
        "date_text": date_text,
        "datetime": dt.isoformat() if dt else None,
        "expected_label": expected_label,
        "date_match": date_match,
        "served_date": served,
        "no_changes": no_changes,
        "changes": changes,
    }


def main():
    refresh_all = "--refresh" in sys.argv[1:]
    RAW.mkdir(parents=True, exist_ok=True)

    print("Fetching performance list...")
    base_page = fetch(bust(BASE))
    perfs = get_perf_list_from(base_page)
    print(f"Found {len(perfs)} prior performances")

    # The base page itself shows the current/next performance.
    cur = parse_performance(base_page, None, None)
    cur["perf_id"] = "current"
    cur["expected_label"] = cur["date_text"]
    cur["date_match"] = True

    data_path = OUT / "performances.json"
    results = json.loads(data_path.read_text()) if data_path.exists() else []
    by_id = {
        str(record["perf_id"]): record
        for record in results
        if record.get("perf_id") is not None
    }
    by_datetime = {
        record["datetime"]: record
        for record in results
        if record.get("datetime") and not record.get("error")
    }

    def store(record, previous=None):
        if previous is not None:
            results[results.index(previous)] = record
            old_id = previous.get("perf_id")
            if old_id is not None:
                by_id.pop(str(old_id), None)
        else:
            results.append(record)
        if record.get("perf_id") is not None:
            by_id[str(record["perf_id"])] = record
        if record.get("datetime"):
            by_datetime[record["datetime"]] = record

    fetched = 0
    skipped = 0
    if refresh_all:
        print("Refreshing all listed performances")
    for i, (pid, label) in enumerate(perfs):
        pid_key = str(pid)
        known = by_id.get(pid_key)
        if known and not known.get("error") and not refresh_all:
            skipped += 1
            continue

        expected_dt = norm_date(label).isoformat()
        same_date = by_datetime.get(expected_dt)
        previous = known
        if same_date and not same_date.get("error"):
            if not refresh_all:
                if same_date.get("perf_id") == "current":
                    same_date["perf_id"] = pid
                    same_date["expected_label"] = label
                    by_id.pop("current", None)
                    by_id[pid_key] = same_date
                    print(f"  Reused saved current performance as perf={pid}: {label}")
                skipped += 1
                continue
            if previous is None:
                previous = same_date

        url = f"{BASE}?perf={pid}"
        try:
            html = fetch(bust(url))
        except Exception as e:
            print(f"  [{i+1}/{len(perfs)}] perf={pid} {label}: FETCH ERROR {e}")
            if refresh_all and previous:
                print("    keeping saved data")
            else:
                store(
                    {"perf_id": pid, "expected_label": label, "error": str(e)},
                    previous=previous,
                )
            continue
        (RAW / f"perf_{pid}.html").write_text(html)
        rec = parse_performance(html, pid, label)
        store(rec, previous=previous)
        fetched += 1
        flag = "" if rec["date_match"] else "  <-- MISMATCH (no data?)"
        print(f"  [{i+1}/{len(perfs)}] perf={pid} {label} -> {rec['date_text']} "
              f"({len(rec['changes'])} changes){flag}")
        time.sleep(0.4)

    existing_current = by_datetime.get(cur.get("datetime"))
    if existing_current:
        cur["perf_id"] = existing_current.get("perf_id")
        cur["expected_label"] = existing_current.get("expected_label") or cur["date_text"]
        store(cur, previous=existing_current)
        print(f"  Refreshed current performance: {cur['date_text']} ({len(cur['changes'])} changes)")
    else:
        previous_current = by_id.get("current")
        if previous_current:
            old_current_id = f"current-{previous_current.get('datetime', 'unknown')}"
            previous_current["perf_id"] = old_current_id
            by_id.pop("current", None)
            by_id[old_current_id] = previous_current
        store(cur)
        print(f"  [current] {cur['date_text']} ({len(cur['changes'])} changes)")

    results.sort(key=lambda r: r.get("datetime") or "")
    data_path.write_text(json.dumps(results, indent=2))

    with open(OUT / "cast_changes.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["datetime", "perf_id", "role", "performer", "replaces"])
        for r in results:
            for c in r.get("changes", []):
                w.writerow([r.get("datetime"), r["perf_id"], c["role"], c["performer"], c.get("replaces") or ""])

    bad = [r for r in results if r.get("date_match") is False or r.get("error")]
    print(f"\nDone. Fetched {fetched} performance(s); skipped {skipped} already saved.")
    print(f"{len(results)} performances -> data/performances.json, data/cast_changes.csv")
    if bad:
        print(f"WARNING: {len(bad)} performance(s) did not return their own data:")
        for r in bad:
            print(f"  perf={r['perf_id']} expected={r.get('expected_label')} got={r.get('date_text')}")


if __name__ == "__main__":
    sys.exit(main())
