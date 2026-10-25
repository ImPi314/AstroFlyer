Offline data bundled in astroflyer/resources/. See manifest.json for sources and validity.

- iers/          Leap seconds and Earth orientation (backend/eop.py)
- ephemeris/     JPL DE440 subset, 1990-2060, for Sun/Moon positions (backend/ephemeris.py)
- gravity/       EGM2008 coefficients to degree/order 70 (backend/forces.py)
- spaceweather/  CelesTrak F10.7 / Ap history and predictions for drag models (offline_data.py)
