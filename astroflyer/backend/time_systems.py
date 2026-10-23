"""
AstroFlyer HEO - Time Systems & Coordinate Frames (compatibility layer)
=============================================================================
The real implementations live in:
  backend/epoch.py   Epoch type: UTC, TAI, TT, TDB, UT1, GPS with IERS leap seconds
  backend/eop.py     Bundled IERS Earth orientation parameters
  backend/frames.py  IAU 2006/2000A frames: GCRF, EME2000, MOD, TOD, TEME, CIRS, TIRS, ITRF

This module keeps the older TimeStandardEngine / CoordinateFrameEngine API
used by app_server.py, now backed by those modules. "Seconds since epoch"
means SI seconds after the engine's reference epoch (J2000.0 by default).
=============================================================================
"""

import numpy as np

from .epoch import SEC_PER_DAY, TT_MINUS_TAI, Epoch
from .frames import OMEGA_EARTH, EarthOrientation, rtn_matrix, transform_state, vnc_matrix

MJD_J2000 = 51544.5
JD_J2000 = 2451545.0


class TimeStandardEngine:
    """Converts elapsed seconds after a reference epoch into every time scale."""

    def __init__(self, epoch=None):
        self.epoch = Epoch.coerce(epoch)

    def epoch_at(self, t_sec_since_epoch):
        return self.epoch + float(t_sec_since_epoch)

    def epoch_seconds_to_all_scales(self, t_sec_since_epoch):
        ep = self.epoch_at(t_sec_since_epoch)
        tai_utc = float(ep.tai_minus_utc())
        dut1 = float(ep.ut1_minus_utc())
        t_utc = float(t_sec_since_epoch)
        summary = ep.all_scales()
        summary.update({
            "t_utc_s": round(t_utc, 3),
            "t_tai_s": round(t_utc + tai_utc, 3),
            "t_tt_s": round(t_utc + tai_utc + TT_MINUS_TAI, 3),
            "t_ut1_s": round(t_utc + dut1, 3),
            "t_tdb_s": round(t_utc + tai_utc + TT_MINUS_TAI + ep.tdb_minus_tt(), 3),
            "leap_seconds": int(round(tai_utc)),
            "delta_ut1_ms": round(dut1 * 1000.0, 2),
        })
        return summary

    def earth_rotation_angle(self, t_sec_since_epoch):
        """IAU 2000 Earth Rotation Angle (rad) from UT1."""
        return float(EarthOrientation(self.epoch_at(t_sec_since_epoch)).era[0])


class CoordinateFrameEngine:
    """GCRF <-> ITRF and local orbit frames for states given as seconds after the epoch."""

    def __init__(self, time_engine=None):
        self.time_engine = time_engine if time_engine is not None else TimeStandardEngine()

    def gcrf_to_itrf(self, r_gcrf, v_gcrf, t_sec):
        return transform_state(r_gcrf, v_gcrf, self.time_engine.epoch_at(t_sec), "GCRF", "ITRF")

    def itrf_to_gcrf(self, r_itrf, v_itrf, t_sec):
        return transform_state(r_itrf, v_itrf, self.time_engine.epoch_at(t_sec), "ITRF", "GCRF")

    def transform(self, r, v, t_sec, from_frame, to_frame):
        return transform_state(r, v, self.time_engine.epoch_at(t_sec), from_frame, to_frame)

    def eci_to_rtn_matrix(self, r_vec, v_vec):
        if np.linalg.norm(r_vec) < 1e-6:
            return np.eye(3)
        return rtn_matrix(r_vec, v_vec)

    def eci_to_vnc_matrix(self, r_vec, v_vec):
        if np.linalg.norm(v_vec) < 1e-6:
            return np.eye(3)
        return vnc_matrix(r_vec, v_vec)


__all__ = [
    "TimeStandardEngine", "CoordinateFrameEngine", "Epoch",
    "OMEGA_EARTH", "SEC_PER_DAY", "MJD_J2000", "JD_J2000",
]
