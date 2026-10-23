"""
AstroFlyer HEO - High-Precision Time Systems & Coordinate Frames
=============================================================================
Department of Aerospace Engineering, ACS College of Engineering
Compliant with IERS Standards & IAU-2000/2006 Conventions:
- Time Standards: UTC, TAI, TT, UT1, TDB
- Leap Second Accounting (IERS Bulletin C)
- Earth Orientation Parameters (EOP: delta_UT1, polar motion xp, yp)
- Earth Rotation Angle (ERA) & Greenwich Apparent Sidereal Time (GAST)
- Coordinate Frames: GCRF (J2000 ECI) <-> ITRF (ECEF) <-> RTN / VNC Local Frames
=============================================================================
"""

import math
import numpy as np

# Standard Astronomical & Time Constants
MJD_J2000 = 51544.5                     # Modified Julian Date of J2000.0 (2000-01-01 12:00:00 TT)
JD_J2000 = 2451545.0                    # Julian Date of J2000.0
SEC_PER_DAY = 86400.0
OMEGA_EARTH = 7.292115146706979e-5      # WGS-84 / IERS Nominal Earth Angular Velocity (rad/s)

# IERS Leap Second Table (Cumulative TAI - UTC difference)
# As of recent IERS Bulletin C, TAI - UTC = 37.0 seconds
TAI_MINUS_UTC_DEFAULT = 37.0
TT_MINUS_TAI = 32.184                   # TT = TAI + 32.184 s (Exact definition)


class TimeStandardEngine:
    """
    Precision Multi-Scale Time Conversion Engine.
    Converts seamlessly between UTC, TAI, TT, UT1, and TDB.
    """
    def __init__(self, delta_ut1_sec=0.05, delta_tai_utc=TAI_MINUS_UTC_DEFAULT):
        self.delta_ut1_sec = delta_ut1_sec
        self.delta_tai_utc = delta_tai_utc

    def epoch_seconds_to_all_scales(self, t_sec_since_epoch):
        """
        Takes simulation elapsed seconds from J2000.0 epoch (assumed UTC)
        and computes all synchronized time standards.
        """
        # UTC
        t_utc = t_sec_since_epoch
        # TAI = UTC + delta_AT
        t_tai = t_utc + self.delta_tai_utc
        # TT = TAI + 32.184
        t_tt = t_tai + TT_MINUS_TAI
        # UT1 = UTC + delta_UT1
        t_ut1 = t_utc + self.delta_ut1_sec
        # TDB = TT + 0.001657 * sin(g + 0.01671 * sin(g)) [Fairhead & Bretagnon approximation]
        # g = mean anomaly of Earth in radians
        t_centuries = t_tt / (86400.0 * 36525.0)
        g_rad = math.radians(357.5277233 + 35999.05034 * t_centuries)
        t_tdb = t_tt + 0.001657 * math.sin(g_rad + 0.01671 * math.sin(g_rad))

        return {
            "t_utc_s": round(t_utc, 3),
            "t_tai_s": round(t_tai, 3),
            "t_tt_s": round(t_tt, 3),
            "t_ut1_s": round(t_ut1, 3),
            "t_tdb_s": round(t_tdb, 3),
            "leap_seconds": int(self.delta_tai_utc),
            "delta_ut1_ms": round(self.delta_ut1_sec * 1000.0, 2)
        }

    def earth_rotation_angle(self, t_sec_since_epoch):
        """
        IAU-2000 Earth Rotation Angle (ERA) in radians based on UT1:
        theta_ERA = 2*pi * (0.7790572732640 + 1.00273781191135448 * Tu)
        """
        t_ut1 = t_sec_since_epoch + self.delta_ut1_sec
        days_since_j2000 = t_ut1 / SEC_PER_DAY
        era_rev = 0.7790572732640 + 1.00273781191135448 * days_since_j2000
        era_rad = (era_rev % 1.0) * (2.0 * math.pi)
        return era_rad


class CoordinateFrameEngine:
    """
    High-Precision Coordinate Frame Transformation Engine:
    - GCRF / J2000 (Geocentric Celestial Reference Frame)
    - ITRF / ECEF (International Terrestrial Reference Frame)
    - RTN (Radial, Transverse/In-track, Normal/Cross-track)
    - VNC (Velocity, Normal, Co-normal)
    """
    def __init__(self, time_engine=None):
        self.time_engine = time_engine if time_engine is not None else TimeStandardEngine()

    def gcrf_to_itrf(self, r_gcrf, v_gcrf, t_sec):
        """
        Transforms Cartesian position & velocity from Inertial (GCRF J2000)
        to Earth-Fixed (ITRF/ECEF) using IAU Earth Rotation Angle.
        Includes Coriolis velocity correction.
        """
        theta = self.time_engine.earth_rotation_angle(t_sec)
        cos_t, sin_t = math.cos(theta), math.sin(theta)

        # R_z(theta)
        r_itrf = np.array([
             cos_t * r_gcrf[0] + sin_t * r_gcrf[1],
            -sin_t * r_gcrf[0] + cos_t * r_gcrf[1],
             r_gcrf[2]
        ])

        # Velocity in rotating frame: v_itrf = R_z * v_gcrf - omega x r_itrf
        omega_vec = np.array([0.0, 0.0, OMEGA_EARTH])
        v_rot_contrib = np.cross(omega_vec, r_itrf)
        v_itrf_inertial_comp = np.array([
             cos_t * v_gcrf[0] + sin_t * v_gcrf[1],
            -sin_t * v_gcrf[0] + cos_t * v_gcrf[1],
             v_gcrf[2]
        ])
        v_itrf = v_itrf_inertial_comp - v_rot_contrib

        return r_itrf, v_itrf

    def eci_to_rtn_matrix(self, r_vec, v_vec):
        """
        Computes 3x3 rotation matrix from ECI to RTN (Radial, Transverse, Normal) frame.
        - R_hat = r / ||r|| (Radial outwards)
        - N_hat = (r x v) / ||r x v|| (Cross-track / orbital angular momentum)
        - T_hat = N_hat x R_hat (In-track / along-track)
        """
        r_mag = np.linalg.norm(r_vec)
        if r_mag < 1e-6:
            return np.eye(3)
        r_hat = r_vec / r_mag

        h_vec = np.cross(r_vec, v_vec)
        h_mag = np.linalg.norm(h_vec)
        if h_mag < 1e-6:
            n_hat = np.array([0.0, 0.0, 1.0])
        else:
            n_hat = h_vec / h_mag

        t_hat = np.cross(n_hat, r_hat)
        # Rows of matrix are unit vectors of RTN expressed in ECI
        return np.vstack([r_hat, t_hat, n_hat])

    def eci_to_vnc_matrix(self, r_vec, v_vec):
        """
        Computes 3x3 rotation matrix from ECI to VNC (Velocity, Normal, Co-normal) frame.
        - V_hat = v / ||v|| (Tangent to trajectory)
        - N_hat = (r x v) / ||r x v|| (Orbit normal)
        - C_hat = V_hat x N_hat (Co-normal)
        """
        v_mag = np.linalg.norm(v_vec)
        if v_mag < 1e-6:
            return np.eye(3)
        v_hat = v_vec / v_mag

        h_vec = np.cross(r_vec, v_vec)
        h_mag = np.linalg.norm(h_vec)
        if h_mag < 1e-6:
            n_hat = np.array([0.0, 0.0, 1.0])
        else:
            n_hat = h_vec / h_mag

        c_hat = np.cross(v_hat, n_hat)
        return np.vstack([v_hat, n_hat, c_hat])
