#!/usr/bin/env python3
"""Download headshots for all cast members into data/headshots/.

Sources: hadestown.com/broadway-cast for current company; scraped
atthisplaybill headshot URLs for performers not on the official page.
Writes data/headshots.json mapping performer -> local file.
"""

import json
import re
import urllib.request
from pathlib import Path

OUT = Path(__file__).parent / "data" / "headshots"
OFFICIAL = "https://hadestown.com/_img/_cast/_broadway/"

# name -> official filename slug
OFFICIAL_MAP = {
    "Kayko": "cast-kayko.jpg",
    "Jasmin Savoy Brown": "cast-jasmin.jpg",
    "Norbert Leo Butz": "cast-norbert.jpg",
    "Ben Davis": "cast-ben.jpg",
    "Amber Iman": "cast-amber.jpg",
    "Kelly Belarmino": "cast-kelly.jpg",
    "KC Dela Cruz": "cast-kc-dela-cruz.jpg",
    "Khori Michelle Petinaud": "cast-khori.jpg",
    "Malcolm Armwood": "cast-malcolm.jpg",
    "Emily Afton": "cast-emily.jpg",
    "Sojourner Brown": "cast-sojourner.jpg",
    "Jeffrey Cornelius": "cast-jeffrey.jpg",
    "Sydney Parra": "cast-sydney.jpg",
    "Alex Puette": "cast-alex-puette2.jpg",
    "Brandon Cameron": "cast-brandon.jpg",
    "Tara Jackson": "cast-tara.jpg",
    "Max Kumangai": "cast-max.jpg",
    "Alex Lugo": "cast-alex.jpg",
    "Tanner Ray Wilson": "cast-tanner.jpg",
}

UA = {"User-Agent": "Mozilla/5.0"}


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def download(url, dest):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        dest.write_bytes(r.read())


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    mapping = {}

    # scraped headshots for anyone in performances.json not on the official list
    perfs = json.loads((Path(__file__).parent / "data" / "performances.json").read_text())
    scraped = {}
    for r in perfs:
        for c in r.get("changes", []):
            scraped.setdefault(c["performer"], c.get("headshot"))

    for name in sorted(set(OFFICIAL_MAP) | set(scraped)):
        ext, url = "jpg", None
        if name in OFFICIAL_MAP:
            url = OFFICIAL + OFFICIAL_MAP[name]
        elif scraped.get(name):
            url = scraped[name]
            ext = url.rsplit(".", 1)[-1].split("?")[0]
        if not url:
            continue
        dest = OUT / f"{slugify(name)}.{ext}"
        if not dest.exists():
            try:
                download(url, dest)
                print(f"  {name} <- {url}")
            except Exception as e:
                print(f"  FAILED {name} <- {url}: {e}")
                if name in OFFICIAL_MAP and scraped.get(name):
                    dest2 = OUT / f"{slugify(name)}.{scraped[name].rsplit('.', 1)[-1].split('?')[0]}"
                    try:
                        download(scraped[name], dest2)
                        print(f"    fell back to scraped headshot")
                        mapping[name] = f"data/headshots/{dest2.name}"
                    except Exception as e2:
                        print(f"    fallback failed: {e2}")
                continue
        mapping[name] = f"data/headshots/{dest.name}"

    (OUT.parent / "headshots.json").write_text(json.dumps(mapping, indent=2))
    print(f"{len(mapping)} headshots -> {OUT}")


if __name__ == "__main__":
    main()
