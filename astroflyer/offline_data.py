"""
Offline data access for bundled files under astroflyer/resources/ (see resources/manifest.json).

Leap seconds and Earth orientation are owned by backend/eop.py. This module covers space weather
for drag models and reports what data is bundled and how long it stays valid, so the UI can warn
when a run goes past it. Nothing here touches the network.
"""

import csv
import datetime
import json
import os
from functools import lru_cache
from typing import Any, Dict, List, Optional

try:
    from .resource_paths import resource_path
except ImportError:  # astroflyer/ itself on sys.path (main.py layout)
    from resource_paths import resource_path

# Moderate solar activity, used when no space-weather file covers the requested date
FALLBACK_F107 = 150.0
FALLBACK_AP = 15.0

SPACE_WEATHER_FILE = ("resources", "spaceweather", "SW-All.csv")
MANIFEST_FILE = ("resources", "manifest.json")


def _to_float(value: Optional[str]) -> Optional[float]:
    try:
        return float(value) if value not in (None, "") else None
    except ValueError:
        return None


@lru_cache(maxsize=1)
def _load_space_weather() -> Dict[datetime.date, Dict[str, Any]]:
    path = resource_path(*SPACE_WEATHER_FILE)
    table: Dict[datetime.date, Dict[str, Any]] = {}
    if not os.path.exists(path):
        return table
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                day = datetime.date.fromisoformat(row["DATE"].strip())
            except (KeyError, ValueError):
                continue
            f107 = _to_float(row.get("F10.7_OBS"))
            if f107 is None:
                continue
            table[day] = {
                "f107": f107,
                "f107a": _to_float(row.get("F10.7_OBS_CENTER81")) or f107,
                "ap": _to_float(row.get("AP_AVG")) or FALLBACK_AP,
                "ap_3h": [_to_float(row.get(f"AP{i}")) for i in range(1, 9)],
                "kind": row.get("F10.7_DATA_TYPE", "").strip(),
            }
    return table


def space_weather(day: datetime.date) -> Dict[str, Any]:
    """F10.7 (daily and 81-day centred mean) and Ap for a UTC date, for MSIS-type drag models.

    Uses the bundled CelesTrak file when it covers the date (source "file"); otherwise returns
    moderate-activity defaults (source "fallback") so propagation never fails on missing data.
    F10.7 for the model day is normally the previous day's value; callers pass the date they need.
    """
    entry = _load_space_weather().get(day)
    if entry is not None:
        return {**entry, "source": "file"}
    return {
        "f107": FALLBACK_F107,
        "f107a": FALLBACK_F107,
        "ap": FALLBACK_AP,
        "ap_3h": [FALLBACK_AP] * 8,
        "kind": "",
        "source": "fallback",
    }


def space_weather_coverage() -> Optional[List[str]]:
    """[first, last] ISO dates covered by the bundled space-weather file, or None when absent."""
    table = _load_space_weather()
    if not table:
        return None
    return [min(table).isoformat(), max(table).isoformat()]


def data_status() -> List[Dict[str, Any]]:
    """One entry per manifest file: whether it is bundled, its size and validity."""
    with open(resource_path(*MANIFEST_FILE), encoding="utf-8") as f:
        manifest = json.load(f)
    status = []
    for rel_path, info in manifest.get("files", {}).items():
        path = resource_path("resources", *rel_path.split("/"))
        present = os.path.exists(path)
        valid_until = info.get("valid_until")
        if rel_path.startswith("spaceweather/") and present:
            coverage = space_weather_coverage()
            valid_until = coverage[1] if coverage else valid_until
        status.append({
            "file": rel_path,
            "present": present,
            "bytes": os.path.getsize(path) if present else 0,
            "required": bool(info.get("required")),
            "valid_until": valid_until,
            "source": info.get("source"),
        })
    return status


if __name__ == "__main__":
    for item in data_status():
        mark = "ok " if item["present"] else ("MISSING" if item["required"] else "absent")
        print(f"{mark:8} {item['file']:32} {item['bytes']:>10} bytes  valid until {item['valid_until']}")
