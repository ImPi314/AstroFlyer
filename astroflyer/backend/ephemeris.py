"""
AstroFlyer HEO - Offline Sun & Moon Ephemeris (JPL DE440)

Reads the bundled DE440 excerpt (astroflyer/resources/ephemeris/de440_1990_2060.bsp,
segments SSB->EMB, SSB->Sun, EMB->Moon, EMB->Earth) and returns geocentric
Sun and Moon positions in the ICRF/GCRF frame. Chebyshev records are loaded
once into memory and evaluated directly, so no network or SPICE install is needed.

Times are TT seconds past J2000 (2000-01-01 12:00:00 TT). DE440 is in TDB;
|TDB - TT| < 2 ms, which moves the Moon by under 2 m and is ignored here.
"""

import os
import sys

import numpy as np

try:
    from numba import njit
except ImportError:  # pure NumPy fallback
    def njit(*args, **kwargs):
        if args and callable(args[0]):
            return args[0]
        return lambda f: f

J2000_JD = 2451545.0
SECONDS_PER_DAY = 86400.0
KM = 1000.0

_EPHEMERIS_FILE = "de440_1990_2060.bsp"


def _resource_path(*parts):
    """Locates a bundled resource in the source tree or a PyInstaller bundle."""
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(os.path.dirname(here), "resources", *parts),
        os.path.join(getattr(sys, "_MEIPASS", ""), "astroflyer", "resources", *parts),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    raise FileNotFoundError(f"Bundled resource not found: {os.path.join(*parts)}")


@njit(cache=False)
def _chebyshev_position(init_jd, intlen_days, coef, jd):
    """Evaluates one SPK type-2 segment (km) at a TDB Julian date."""
    n_rec = coef.shape[1]
    idx = int((jd - init_jd) // intlen_days)
    if idx < 0 or idx >= n_rec:
        if jd == init_jd + n_rec * intlen_days:
            idx = n_rec - 1
        else:
            return np.full(3, np.nan)
    s = 2.0 * (jd - (init_jd + idx * intlen_days)) / intlen_days - 1.0
    n_coef = coef.shape[2]
    out = np.zeros(3)
    for k in range(3):
        # Clenshaw recurrence for sum c_j T_j(s)
        b1 = 0.0
        b2 = 0.0
        for j in range(n_coef - 1, 0, -1):
            b0 = 2.0 * s * b1 - b2 + coef[k, idx, j]
            b2 = b1
            b1 = b0
        out[k] = s * b1 - b2 + coef[k, idx, 0]
    return out


class DE440Ephemeris:
    """Geocentric Sun and Moon positions from the bundled DE440 excerpt."""

    def __init__(self, path=None):
        from jplephem.spk import SPK

        self.path = path or _resource_path("ephemeris", _EPHEMERIS_FILE)
        kernel = SPK.open(self.path)
        try:
            self._segments = {}
            for key in ((0, 3), (0, 10), (3, 301), (3, 399)):
                seg = kernel[key]
                init, intlen, coef = seg.load_array()
                self._segments[key] = (float(init), float(intlen), np.ascontiguousarray(coef))
            self.start_jd = max(seg.start_jd for seg in kernel.segments)
            self.end_jd = min(seg.end_jd for seg in kernel.segments)
        finally:
            kernel.close()

    def _pos(self, key, jd):
        init, intlen, coef = self._segments[key]
        return _chebyshev_position(init, intlen, coef, jd)

    def _jd(self, tt_seconds_j2000):
        jd = J2000_JD + tt_seconds_j2000 / SECONDS_PER_DAY
        if not (self.start_jd <= jd <= self.end_jd):
            raise ValueError(
                f"Epoch JD {jd:.3f} is outside the bundled DE440 range "
                f"({self.start_jd:.1f} to {self.end_jd:.1f}, years 1990-2060)"
            )
        return jd

    def moon_gcrf(self, tt_seconds_j2000):
        """Geocentric Moon position (m), GCRF."""
        jd = self._jd(tt_seconds_j2000)
        return (self._pos((3, 301), jd) - self._pos((3, 399), jd)) * KM

    def sun_gcrf(self, tt_seconds_j2000):
        """Geocentric Sun position (m), GCRF."""
        jd = self._jd(tt_seconds_j2000)
        earth_ssb = self._pos((0, 3), jd) + self._pos((3, 399), jd)
        return (self._pos((0, 10), jd) - earth_ssb) * KM

    def sun_moon_gcrf(self, tt_seconds_j2000):
        """Returns (r_sun, r_moon) geocentric positions in metres, GCRF."""
        jd = self._jd(tt_seconds_j2000)
        earth_emb = self._pos((3, 399), jd)
        earth_ssb = self._pos((0, 3), jd) + earth_emb
        r_sun = (self._pos((0, 10), jd) - earth_ssb) * KM
        r_moon = (self._pos((3, 301), jd) - earth_emb) * KM
        return r_sun, r_moon


_default_ephemeris = None


def get_ephemeris():
    """Shared, lazily loaded DE440 ephemeris instance."""
    global _default_ephemeris
    if _default_ephemeris is None:
        _default_ephemeris = DE440Ephemeris()
    return _default_ephemeris
