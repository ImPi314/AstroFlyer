"""
AstroFlyer HEO - Epochs and Time Scales
=============================================================================
An Epoch is one instant, stored internally as a two-part TAI Julian Date
(about 20 ps resolution). It converts to and from:
  UTC, TAI, TT, TDB, UT1, GPS
and to calendar strings, JD, MJD and GPS week / seconds-of-week.

Conversions use ERFA (the open-source build of the IAU SOFA library):
leap seconds from the bundled IERS table, UT1-UTC from the bundled EOP file,
TDB-TT from the Fairhead & Bretagnon series (erfa.dtdb, geocentric).
=============================================================================
"""

import re
import warnings

import erfa
import numpy as np

from .eop import get_eop

SEC_PER_DAY = 86400.0
MJD_ZERO = 2400000.5
JD_J2000 = 2451545.0
TT_MINUS_TAI = 32.184
TAI_MINUS_GPS = 19.0
GPS_EPOCH_MJD_UTC = 44244.0     # 1980-01-06T00:00:00 UTC (TAI-UTC = 19 s)

SCALES = ("UTC", "TAI", "TT", "TDB", "UT1", "GPS")

_ISO_RE = re.compile(
    r"^\s*(\d{4})-(\d{1,2})-(\d{1,2})"
    r"(?:[T ](\d{1,2}):(\d{2})(?::(\d{2}(?:\.\d*)?))?)?\s*(Z|UTC|TAI|TT|TDB|UT1|GPS)?\s*$",
    re.IGNORECASE,
)


def _normalize(jd1, jd2):
    """Keeps jd1 a whole-or-half day and |jd2| < 1 for precision."""
    whole = np.floor(jd2)
    return jd1 + whole, jd2 - whole


class Epoch:
    """A single instant in time. Immutable; arithmetic is in SI seconds of TAI."""

    __slots__ = ("_tai1", "_tai2")

    def __init__(self, tai1, tai2=0.0):
        self._tai1, self._tai2 = _normalize(float(tai1), float(tai2))

    # ------------------------------------------------------------------ builders
    @classmethod
    def from_jd(cls, jd1, jd2=0.0, scale="UTC"):
        """Builds an Epoch from a (two-part) Julian Date in the given scale."""
        scale = scale.upper()
        if scale == "TAI":
            return cls(jd1, jd2)
        if scale == "TT":
            return cls(*erfa.tttai(jd1, jd2))
        if scale == "GPS":
            return cls(jd1, jd2 + TAI_MINUS_GPS / SEC_PER_DAY)
        if scale == "UTC":
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", erfa.ErfaWarning)
                return cls(*erfa.utctai(jd1, jd2))
        if scale == "TDB":
            # Iterate: TT = TDB - (TDB-TT); the correction varies by < 1 ns over 2 ms.
            tt1, tt2 = jd1, jd2
            for _ in range(3):
                dtr = erfa.dtdb(tt1, tt2, 0.0, 0.0, 0.0, 0.0)   # geocentric: UT term vanishes
                tt1, tt2 = jd1, jd2 - dtr / SEC_PER_DAY
            return cls(*erfa.tttai(tt1, tt2))
        if scale == "UT1":
            # Iterate on UT1-TAI, which is continuous.
            eop = get_eop()
            tai1, tai2 = jd1, jd2
            for _ in range(3):
                mjd_utc = (tai1 - MJD_ZERO) + tai2 - 37.0 / SEC_PER_DAY   # same lookup as mjd_utc_approx
                tai2 = jd2 - eop.ut1_minus_tai(mjd_utc) / SEC_PER_DAY
            return cls(tai1, tai2)
        raise ValueError(f"Unknown time scale '{scale}'. Use one of {SCALES}.")

    @classmethod
    def from_mjd(cls, mjd, scale="UTC"):
        return cls.from_jd(MJD_ZERO, mjd, scale)

    @classmethod
    def from_calendar(cls, year, month, day, hour=0, minute=0, second=0.0, scale="UTC"):
        """Builds an Epoch from calendar fields. UTC seconds may be 60.x during a leap second."""
        scale = scale.upper()
        if scale == "UTC":
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", erfa.ErfaWarning)
                jd1, jd2 = erfa.dtf2d("UTC", year, month, day, hour, minute, second)
        else:
            jd1, jd2 = erfa.cal2jd(year, month, day)
            jd2 = jd2 + (hour * 3600.0 + minute * 60.0 + second) / SEC_PER_DAY
        return cls.from_jd(jd1, jd2, scale)

    @classmethod
    def from_iso(cls, text, scale=None):
        """Parses 'YYYY-MM-DD[THH:MM[:SS.sss]][Z|UTC|TAI|TT|TDB|UT1|GPS]'.

        A trailing scale tag wins over `scale`; with neither, UTC is assumed.
        """
        match = _ISO_RE.match(str(text))
        if not match:
            raise ValueError(f"Cannot parse epoch '{text}'. Expected e.g. 2026-10-23T19:00:00.000Z")
        y, mo, d, h, mi, s, tag = match.groups()
        tag = (tag or "").upper()
        use = "UTC" if tag == "Z" else (tag or (scale or "UTC").upper())
        return cls.from_calendar(int(y), int(mo), int(d), int(h or 0), int(mi or 0), float(s or 0.0), use)

    @classmethod
    def from_gps_week(cls, week, seconds_of_week):
        start = cls.from_mjd(GPS_EPOCH_MJD_UTC, "UTC")
        return start + (week * 7 * SEC_PER_DAY + seconds_of_week)

    @classmethod
    def j2000(cls):
        """J2000.0 = 2000-01-01T12:00:00 TT."""
        return cls.from_jd(JD_J2000, 0.0, "TT")

    @classmethod
    def coerce(cls, value):
        """Accepts an Epoch, an ISO string, or None (meaning J2000)."""
        if value is None:
            return cls.j2000()
        if isinstance(value, Epoch):
            return value
        return cls.from_iso(value)

    # ------------------------------------------------------------------ scales
    def jd(self, scale="UTC"):
        """Two-part Julian Date (jd1, jd2) in the given scale."""
        scale = scale.upper()
        t1, t2 = self._tai1, self._tai2
        if scale == "TAI":
            return t1, t2
        if scale == "TT":
            return erfa.taitt(t1, t2)
        if scale == "GPS":
            return t1, t2 - TAI_MINUS_GPS / SEC_PER_DAY
        if scale == "UTC":
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", erfa.ErfaWarning)
                return erfa.taiutc(t1, t2)
        if scale == "TDB":
            tt1, tt2 = erfa.taitt(t1, t2)
            return tt1, tt2 + self.tdb_minus_tt() / SEC_PER_DAY
        if scale == "UT1":
            return t1, t2 + self.ut1_minus_tai() / SEC_PER_DAY
        raise ValueError(f"Unknown time scale '{scale}'. Use one of {SCALES}.")

    def jd_value(self, scale="UTC"):
        a, b = self.jd(scale)
        return a + b

    def mjd(self, scale="UTC"):
        a, b = self.jd(scale)
        return (a - MJD_ZERO) + b

    def tai_minus_utc(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", erfa.ErfaWarning)
            u1, u2 = erfa.taiutc(self._tai1, self._tai2)
            y, m, d, frac = erfa.jd2cal(u1, u2)
            return erfa.dat(int(y), int(m), int(d), float(frac))

    def ut1_minus_tai(self):
        return float(get_eop().ut1_minus_tai(self.mjd_utc_approx()))

    def ut1_minus_utc(self):
        return self.ut1_minus_tai() + self.tai_minus_utc()

    def tdb_minus_tt(self):
        tt1, tt2 = erfa.taitt(self._tai1, self._tai2)
        return float(erfa.dtdb(tt1, tt2, 0.0, 0.0, 0.0, 0.0))   # geocentric: UT term vanishes

    def mjd_utc_approx(self):
        """MJD of TAI minus ~37 s; accurate enough to look up daily EOP values."""
        return (self._tai1 - MJD_ZERO) + self._tai2 - 37.0 / SEC_PER_DAY

    def julian_centuries_tt(self):
        a, b = self.jd("TT")
        return ((a - JD_J2000) + b) / 36525.0

    def gps_week_seconds(self):
        elapsed = self - Epoch.from_mjd(GPS_EPOCH_MJD_UTC, "UTC")
        week = int(elapsed // (7 * SEC_PER_DAY))
        return week, elapsed - week * 7 * SEC_PER_DAY

    # ------------------------------------------------------------------ strings
    def iso(self, scale="UTC", decimals=3):
        """Calendar string, e.g. '2026-10-23T19:00:00.000' (with 'Z' for UTC)."""
        scale = scale.upper()
        a, b = self.jd(scale)
        erfa_scale = "UTC" if scale == "UTC" else "TAI"   # non-UTC scales have no leap seconds
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", erfa.ErfaWarning)
            y, mo, d, hmsf = erfa.d2dtf(erfa_scale, decimals, a, b)
        h, mi, s, f = (int(v) for v in hmsf)
        frac = f"{f:0{decimals}d}" if decimals > 0 else ""
        text = f"{int(y):04d}-{int(mo):02d}-{int(d):02d}T{h:02d}:{mi:02d}:{s:02d}" + (f".{frac}" if frac else "")
        return text + ("Z" if scale == "UTC" else f" {scale}")

    def all_scales(self):
        """Summary used by the UI and reports."""
        week, sow = self.gps_week_seconds()
        return {
            "utc_iso": self.iso("UTC"),
            "tai_iso": self.iso("TAI"),
            "tt_iso": self.iso("TT"),
            "tdb_iso": self.iso("TDB", 6),
            "ut1_iso": self.iso("UT1", 6),
            "gps_iso": self.iso("GPS"),
            "jd_utc": self.jd_value("UTC"),
            "mjd_utc": self.mjd("UTC"),
            "jd_tt": self.jd_value("TT"),
            "tai_minus_utc_s": self.tai_minus_utc(),
            "ut1_minus_utc_s": self.ut1_minus_utc(),
            "tdb_minus_tt_s": self.tdb_minus_tt(),
            "gps_week": week,
            "gps_seconds_of_week": sow,
            "eop_in_range": get_eop().in_range(self.mjd_utc_approx()),
        }

    # ------------------------------------------------------------------ arithmetic
    def __add__(self, seconds):
        return Epoch(self._tai1, self._tai2 + float(seconds) / SEC_PER_DAY)

    def __sub__(self, other):
        if isinstance(other, Epoch):
            return ((self._tai1 - other._tai1) + (self._tai2 - other._tai2)) * SEC_PER_DAY
        return self + (-float(other))

    def __eq__(self, other):
        return isinstance(other, Epoch) and abs(self - other) < 1e-9

    def __lt__(self, other):
        return (self - other) < 0.0

    def __hash__(self):
        return hash(round((self._tai1 - JD_J2000 + self._tai2) * SEC_PER_DAY, 6))

    def __repr__(self):
        return f"Epoch('{self.iso('UTC', 6)}')"


def epoch_grid_jd(epoch0, offsets_s, scale):
    """Two-part JDs for epoch0 + offsets (array of seconds) in one scale, vectorized.

    UTC/UT1/TDB need per-instant offsets, so they are computed point by point
    only where they change (leap seconds, daily EOP), which is cheap.
    """
    offsets_s = np.asarray(offsets_s, dtype=float)
    a0, b0 = epoch0.jd(scale)
    if scale.upper() in ("TAI", "TT", "GPS"):
        return np.full_like(offsets_s, a0), b0 + offsets_s / SEC_PER_DAY
    if scale.upper() == "UT1":
        eop = get_eop()
        tai1, tai2 = epoch0.jd("TAI")
        mjd = (tai1 - MJD_ZERO) + tai2 + offsets_s / SEC_PER_DAY - 37.0 / SEC_PER_DAY
        return np.full_like(offsets_s, tai1), tai2 + (offsets_s + eop.ut1_minus_tai(mjd)) / SEC_PER_DAY
    out1 = np.empty_like(offsets_s)
    out2 = np.empty_like(offsets_s)
    for i, dt in enumerate(offsets_s):
        out1[i], out2[i] = (epoch0 + dt).jd(scale)
    return out1, out2
