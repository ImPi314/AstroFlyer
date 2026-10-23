"""
Refreshes the offline data bundled in astroflyer/resources/ (run on a machine with internet, then rebuild).

    python tools/fetch_offline_data.py              # space weather (CelesTrak SW-All.csv)

Leap seconds and EOP (resources/iers/), the DE440 ephemeris subset (resources/ephemeris/) and EGM2008
gravity (resources/gravity/) are committed with the code that reads them and are not fetched here.
The app itself never downloads anything.
"""

import argparse
import os
import shutil
import sys
import tempfile
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESOURCES = os.path.join(ROOT, "astroflyer", "resources")

SOURCES = {
    "spaceweather/SW-All.csv": "https://celestrak.org/SpaceData/SW-All.csv",
}


def download(url: str, dest: str) -> None:
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    print(f"[*] {url}")
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(dest))
    try:
        with os.fdopen(fd, "wb") as out, urllib.request.urlopen(url, timeout=120) as resp:
            shutil.copyfileobj(resp, out)
        if os.path.getsize(tmp) == 0:
            raise RuntimeError("empty download")
        os.replace(tmp, dest)  # keep the previous file if anything above failed
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    print(f"    -> {os.path.relpath(dest, ROOT)} ({os.path.getsize(dest) / 1e6:.1f} MB)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.parse_args()

    targets = dict(SOURCES)

    failed = 0
    for rel_path, url in targets.items():
        try:
            download(url, os.path.join(RESOURCES, *rel_path.split("/")))
        except Exception as exc:
            failed += 1
            print(f"[!] {rel_path}: {exc} (previous copy, if any, kept)")

    sys.path.insert(0, os.path.join(ROOT, "astroflyer"))
    import offline_data
    offline_data._load_space_weather.cache_clear()
    print()
    for item in offline_data.data_status():
        mark = "ok" if item["present"] else ("MISSING" if item["required"] else "absent")
        print(f"  {mark:8} {item['file']:32} valid until {item['valid_until']}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
