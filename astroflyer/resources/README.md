Bundled offline data. See manifest.json for sources and validity.

- iers/          Leap seconds and Earth orientation (owned by backend/eop.py)
- spaceweather/  CelesTrak F10.7 / Ap history and predictions for drag models
- ephemeris/     Optional JPL DE440s kernel (about 32 MB, not committed)

Refresh space weather and the optional ephemeris with:

    python tools/fetch_offline_data.py
