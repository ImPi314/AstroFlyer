"""
AstroFlyer HEO - Earth Orientation Parameters and Leap Seconds
=============================================================================
Loads the bundled IERS files from astroflyer/resources/iers so the app works offline:
  - Leap_Second.dat   (IERS Bulletin C table of TAI-UTC)
  - finals2000A.all   (IERS Bulletin A/B: polar motion, UT1-UTC, dX/dY)
Newer copies of either file can be dropped into that folder (or loaded with
load_eop_file / load_leap_second_file) without a network connection.

UT1-UTC is interpolated as UT1-TAI, which is continuous across leap seconds.
=============================================================================
"""

import os
import sys
import warnings
from datetime import datetime

import erfa
import numpy as np

ARCSEC_TO_RAD = np.pi / (180.0 * 3600.0)


def _data_dir():
    candidates = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources", "iers"),
        os.path.join(getattr(sys, "_MEIPASS", ""), "astroflyer", "resources", "iers"),
    ]
    return next((p for p in candidates if os.path.isdir(p)), candidates[0])


IERS_DIR = _data_dir()
LEAP_SECOND_FILE = os.path.join(IERS_DIR, "Leap_Second.dat")
EOP_FILE = os.path.join(IERS_DIR, "finals2000A.all")


# ==============================================================================
# LEAP SECONDS
# ==============================================================================
def load_leap_second_file(path=LEAP_SECOND_FILE):
    """Installs the TAI-UTC table from an IERS Leap_Second.dat file into ERFA.

    ERFA ships its own table; loading the file lets users update leap seconds
    offline. Returns the number of entries loaded, or 0 if the file is missing.
    """
    if not os.path.exists(path):
        return 0
    rows = []
    expires = None
    with open(path) as fh:
        for line in fh:
            if "File expires on" in line:
                expires = line.split("File expires on", 1)[1].strip()
            parts = line.split()
            if not parts or line.lstrip().startswith("#") or len(parts) < 5:
                continue
            _, _, month, year, tai_utc = parts[:5]
            rows.append((int(year), int(month), float(tai_utc)))
    if not rows:
        return 0
    table = np.array(rows, dtype=[("year", "i4"), ("month", "i4"), ("tai_utc", "f8")])
    try:
        erfa.leap_seconds.update(table)
        if expires:
            erfa.leap_seconds.expires = datetime.strptime(expires, "%d %B %Y")
    except Exception as exc:  # keep ERFA's built-in table
        warnings.warn(f"Leap second file not applied ({exc}); using ERFA built-in table.")
        return 0
    return len(rows)


# ==============================================================================
# EARTH ORIENTATION PARAMETERS
# ==============================================================================
class EarthOrientationData:
    """Tabulated EOP with linear interpolation in MJD(UTC).

    Outside the table, values are held at the nearest end point and
    `in_range` returns False so callers can flag reduced accuracy.
    With no table loaded, every parameter is zero (UT1 = UTC, no polar motion).
    """

    def __init__(self, mjd=None, xp=None, yp=None, ut1_tai=None, dx=None, dy=None, lod=None, source=None):
        self.mjd = np.asarray(mjd if mjd is not None else [], dtype=float)
        self.xp = np.asarray(xp if xp is not None else [], dtype=float)            # arcsec
        self.yp = np.asarray(yp if yp is not None else [], dtype=float)            # arcsec
        self.ut1_tai = np.asarray(ut1_tai if ut1_tai is not None else [], dtype=float)  # s
        self.dx = np.asarray(dx if dx is not None else [], dtype=float)            # mas
        self.dy = np.asarray(dy if dy is not None else [], dtype=float)            # mas
        self.lod = np.asarray(lod if lod is not None else [], dtype=float)         # ms
        self.source = source

    @property
    def loaded(self):
        return self.mjd.size > 0

    def in_range(self, mjd_utc):
        if not self.loaded:
            return False
        mjd_utc = np.asarray(mjd_utc, dtype=float)
        return bool(np.all((mjd_utc >= self.mjd[0]) & (mjd_utc <= self.mjd[-1])))

    def _interp(self, column, mjd_utc):
        if not self.loaded:
            return np.zeros_like(np.asarray(mjd_utc, dtype=float))
        return np.interp(mjd_utc, self.mjd, column)

    def polar_motion_arcsec(self, mjd_utc):
        return self._interp(self.xp, mjd_utc), self._interp(self.yp, mjd_utc)

    def ut1_minus_tai(self, mjd_utc):
        return self._interp(self.ut1_tai, mjd_utc)

    def celestial_pole_offsets_mas(self, mjd_utc):
        return self._interp(self.dx, mjd_utc), self._interp(self.dy, mjd_utc)

    def length_of_day_ms(self, mjd_utc):
        return self._interp(self.lod, mjd_utc)


def _field(line, start, end):
    text = line[start - 1:end].strip()
    return float(text) if text else None


def load_eop_file(path=EOP_FILE):
    """Parses an IERS finals2000A file (Bulletin B values preferred over A)."""
    if not os.path.exists(path):
        warnings.warn(f"EOP file not found at {path}; using zero EOP (UT1 = UTC, no polar motion).")
        return EarthOrientationData(source=None)

    mjd, xp, yp, ut1_tai, dx, dy, lod = [], [], [], [], [], [], []
    with open(path) as fh:
        for line in fh:
            if len(line) < 68:
                continue
            m = _field(line, 8, 15)
            ut1_utc = _field(line, 155, 165) if len(line) >= 165 else None
            if ut1_utc is None:
                ut1_utc = _field(line, 59, 68)
            if m is None or ut1_utc is None:
                continue
            x = _field(line, 135, 144) if len(line) >= 154 else None
            y = _field(line, 145, 154) if len(line) >= 154 else None
            if x is None or y is None:
                x, y = _field(line, 19, 27), _field(line, 38, 46)
            ddx = _field(line, 166, 175) if len(line) >= 185 else None
            ddy = _field(line, 176, 185) if len(line) >= 185 else None
            if ddx is None or ddy is None:
                ddx, ddy = _field(line, 98, 106), _field(line, 117, 125)
            day_lod = _field(line, 80, 86)

            # TAI-UTC at 0h UTC of this MJD, so UT1-TAI is continuous across leap seconds
            year, month, day, _ = erfa.jd2cal(2400000.5, m)
            tai_utc = erfa.dat(int(year), int(month), int(day), 0.0)

            mjd.append(m)
            xp.append(x or 0.0)
            yp.append(y or 0.0)
            ut1_tai.append(ut1_utc - tai_utc)
            dx.append(ddx or 0.0)
            dy.append(ddy or 0.0)
            lod.append(day_lod or 0.0)

    return EarthOrientationData(mjd, xp, yp, ut1_tai, dx, dy, lod, source=path)


_EOP = None


def get_eop():
    """Returns the process-wide EOP table, loading the bundled file on first use."""
    global _EOP
    if _EOP is None:
        load_leap_second_file()
        _EOP = load_eop_file()
    return _EOP


def set_eop(eop):
    """Replaces the process-wide EOP table (e.g. zero EOP for tests)."""
    global _EOP
    _EOP = eop
