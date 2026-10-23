"""
AstroFlyer HEO - Reference Frames (IAU 2006/2000A, IERS 2010 conventions)
=============================================================================
Earth frames, all reached through GCRF:

  GCRF        Geocentric Celestial Reference Frame (ICRF axes); the propagation frame
  EME2000     Mean equator and equinox of J2000 (GCRF with the frame bias removed)
  ECLIPJ2000  Mean ecliptic and equinox of J2000
  MOD         Mean of date (bias + IAU 2006 precession)
  TOD         True of date (bias + precession + IAU 2000A nutation)
  TEME        True equator, mean equinox (the SGP4 / TLE frame)
  CIRS        Celestial Intermediate Reference System
  TIRS        Terrestrial Intermediate Reference System (rotating, no polar motion)
  ITRF        International Terrestrial Reference Frame (Earth fixed, with polar motion)

Local orbit frames: RTN (RIC), VNC, LVLH.

Matrices come from ERFA (IAU SOFA). Celestial pole offsets dX/dY, UT1-UTC and
polar motion come from the bundled IERS EOP file. Units: metres, m/s.
=============================================================================
"""

import erfa
import numpy as np

from .eop import ARCSEC_TO_RAD, get_eop
from .epoch import MJD_ZERO, SEC_PER_DAY, Epoch

# Nominal Earth rotation rate (IERS 2010), rad/s
OMEGA_EARTH = 7.292115146706979e-5
MAS_TO_RAD = ARCSEC_TO_RAD / 1000.0
OBLIQUITY_J2000_RAD = 84381.406 * ARCSEC_TO_RAD

INERTIAL_FRAMES = ("GCRF", "EME2000", "ECLIPJ2000", "MOD", "TOD", "TEME", "CIRS")
ROTATING_FRAMES = ("TIRS", "ITRF")
FRAMES = INERTIAL_FRAMES + ROTATING_FRAMES

ALIASES = {
    "ICRF": "GCRF", "ECI": "GCRF", "J2000": "EME2000", "MJ2000": "EME2000",
    "MEANJ2000": "EME2000", "ECLIPTIC": "ECLIPJ2000", "PEF": "TIRS", "TIRF": "TIRS",
    "CIRF": "CIRS", "ECEF": "ITRF", "ITRS": "ITRF", "EARTHFIXED": "ITRF",
}


def canonical_frame(name):
    key = str(name).upper().replace(" ", "").replace("_", "").replace("-", "")
    key = ALIASES.get(key, key)
    if key not in FRAMES:
        raise ValueError(f"Unknown frame '{name}'. Use one of {FRAMES}.")
    return key


def _rot3(angle):
    """Frame rotation about z (passive), vectorized over angle."""
    angle = np.asarray(angle, dtype=float)
    c, s = np.cos(angle), np.sin(angle)
    m = np.zeros(angle.shape + (3, 3))
    m[..., 0, 0], m[..., 0, 1] = c, s
    m[..., 1, 0], m[..., 1, 1] = -s, c
    m[..., 2, 2] = 1.0
    return m


def _rot1(angle):
    c, s = np.cos(angle), np.sin(angle)
    return np.array([[1.0, 0.0, 0.0], [0.0, c, s], [0.0, -s, c]])


class EarthOrientation:
    """All time-dependent Earth orientation quantities for one or many instants.

    Build it once per output grid and reuse it for every frame conversion.
    """

    def __init__(self, epoch, offsets_s=None):
        epoch = Epoch.coerce(epoch)
        offsets = np.atleast_1d(np.asarray(0.0 if offsets_s is None else offsets_s, dtype=float))
        self.scalar = offsets_s is None or np.ndim(offsets_s) == 0
        eop = get_eop()

        tai1, tai2 = epoch.jd("TAI")
        tai2 = tai2 + offsets / SEC_PER_DAY
        tai1 = np.full_like(tai2, tai1)
        tt1, tt2 = erfa.taitt(tai1, tai2)

        mjd_utc = (tai1 - MJD_ZERO) + tai2 - 37.0 / SEC_PER_DAY
        ut1_1, ut1_2 = tai1, tai2 + eop.ut1_minus_tai(mjd_utc) / SEC_PER_DAY
        xp, yp = eop.polar_motion_arcsec(mjd_utc)
        dx, dy = eop.celestial_pole_offsets_mas(mjd_utc)
        lod_ms = eop.length_of_day_ms(mjd_utc)

        self.n = offsets.size
        self.eop_in_range = eop.in_range(mjd_utc)
        self.omega = OMEGA_EARTH * (1.0 - lod_ms / 86400000.0)

        # CIO-based chain: GCRS -> CIRS -> TIRS -> ITRS
        x, y = erfa.xy06(tt1, tt2)
        x = x + dx * MAS_TO_RAD
        y = y + dy * MAS_TO_RAD
        s = erfa.s06(tt1, tt2, x, y)
        self.c2i = erfa.c2ixys(x, y, s)                         # GCRF -> CIRS
        self.era = erfa.era00(ut1_1, ut1_2)
        self.r_era = _rot3(self.era)                            # CIRS -> TIRS
        sp = erfa.sp00(tt1, tt2)
        self.pom = erfa.pom00(xp * ARCSEC_TO_RAD, yp * ARCSEC_TO_RAD, sp)   # TIRS -> ITRF

        # Equinox-based chain
        self.bias, _, self.bias_prec = erfa.bp06(tt1, tt2)[:3]  # GCRF -> EME2000, GCRF -> MOD
        self.bpn = erfa.pnm06a(tt1, tt2)                        # GCRF -> TOD
        self.gmst82 = erfa.gmst82(ut1_1, ut1_2)

    def stacked(self, frame):
        """Nx3x3 rotations taking GCRF vectors into `frame` axes."""
        frame = canonical_frame(frame)
        if frame == "GCRF":
            return np.broadcast_to(np.eye(3), (self.n, 3, 3)).copy()
        if frame == "EME2000":
            return self.bias
        if frame == "ECLIPJ2000":
            return _rot1(OBLIQUITY_J2000_RAD) @ self.bias
        if frame == "MOD":
            return self.bias_prec
        if frame == "TOD":
            return self.bpn
        if frame == "CIRS":
            return self.c2i
        if frame == "TIRS":
            return self.r_era @ self.c2i
        if frame == "ITRF":
            return self.pom @ self.r_era @ self.c2i
        # TEME = R3(-GMST82) * PEF, with PEF realised as TIRS (Vallado et al. 2006)
        return _rot3(-self.gmst82) @ self.r_era @ self.c2i

    def gcrf_to(self, frame):
        """3x3 rotation (Nx3x3 for a grid) taking GCRF vectors into `frame` axes."""
        m = self.stacked(frame)
        return m[0] if self.scalar else m


def _as_rows(vectors):
    v = np.asarray(vectors, dtype=float)
    return v.reshape(-1, 3), v.ndim == 1


def transform_state(r, v, epoch, from_frame, to_frame, offsets_s=None, orientation=None):
    """Converts position (m) and velocity (m/s) between any two frames.

    r and v may be single 3-vectors or Nx3 arrays (with N offsets in seconds from
    `epoch`). Rotating frames (TIRS, ITRF) get the omega x r velocity term.
    Pass a prebuilt EarthOrientation to reuse it across calls.
    """
    src, dst = canonical_frame(from_frame), canonical_frame(to_frame)
    rr, single = _as_rows(r)
    vv, _ = _as_rows(v)
    if src == dst:
        return np.asarray(r, dtype=float).copy(), np.asarray(v, dtype=float).copy()

    if orientation is None:
        if offsets_s is None:
            offsets_s = None if single else np.zeros(len(rr))
        orientation = EarthOrientation(epoch, offsets_s)
    eo = orientation
    if eo.n not in (1, len(rr)):
        raise ValueError(f"{len(rr)} states but Earth orientation built for {eo.n} instants")

    w = np.zeros((len(rr), 3))
    w[:, 2] = np.broadcast_to(np.atleast_1d(eo.omega), (len(rr),))

    def mats(frame):
        return np.broadcast_to(eo.stacked(frame), (len(rr), 3, 3))

    def apply(m, x):
        return np.einsum("nij,nj->ni", m, x)

    def apply_t(m, x):
        return np.einsum("nji,nj->ni", m, x)

    # source -> GCRF
    if src in ROTATING_FRAMES:
        if src == "ITRF":
            pom = np.broadcast_to(eo.pom, (len(rr), 3, 3))
            r_tirs, v_tirs = apply_t(pom, rr), apply_t(pom, vv)
        else:
            r_tirs, v_tirs = rr, vv
        m_tirs = mats("TIRS")
        r_g = apply_t(m_tirs, r_tirs)
        v_g = apply_t(m_tirs, v_tirs + np.cross(w, r_tirs))
    else:
        m_src = mats(src)
        r_g, v_g = apply_t(m_src, rr), apply_t(m_src, vv)

    # GCRF -> destination
    if dst in ROTATING_FRAMES:
        m_tirs = mats("TIRS")
        r_out = apply(m_tirs, r_g)
        v_out = apply(m_tirs, v_g) - np.cross(w, r_out)
        if dst == "ITRF":
            pom = np.broadcast_to(eo.pom, (len(rr), 3, 3))
            r_out, v_out = apply(pom, r_out), apply(pom, v_out)
    else:
        m_dst = mats(dst)
        r_out, v_out = apply(m_dst, r_g), apply(m_dst, v_g)

    if single:
        return r_out[0], v_out[0]
    return r_out, v_out


def transform_position(r, epoch, from_frame, to_frame, offsets_s=None, orientation=None):
    r_out, _ = transform_state(r, np.zeros_like(np.asarray(r, dtype=float)), epoch, from_frame, to_frame,
                               offsets_s=offsets_s, orientation=orientation)
    return r_out


# ==============================================================================
# GEODETIC COORDINATES (WGS-84)
# ==============================================================================
WGS84 = 1


def itrf_to_geodetic(r_itrf):
    """ITRF position(s) in metres -> (lat_deg, lon_deg, height_m) on the WGS-84 ellipsoid."""
    rr, single = _as_rows(r_itrf)
    lon, lat, h = erfa.gc2gd(WGS84, rr)
    lat, lon = np.degrees(lat), np.degrees(lon)
    if single:
        return float(lat[0]), float(lon[0]), float(h[0])
    return lat, lon, h


def geodetic_to_itrf(lat_deg, lon_deg, height_m):
    return erfa.gd2gc(WGS84, np.radians(lon_deg), np.radians(lat_deg), height_m)


def gcrf_to_geodetic(r_gcrf, epoch, offsets_s=None, orientation=None):
    """Sub-satellite latitude, longitude and WGS-84 height for GCRF positions."""
    r_itrf = transform_position(r_gcrf, epoch, "GCRF", "ITRF", offsets_s=offsets_s, orientation=orientation)
    return itrf_to_geodetic(r_itrf)


# ==============================================================================
# LOCAL ORBIT FRAMES
# ==============================================================================
def _unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 0 else v


def rtn_matrix(r, v):
    """Rows R (radial), T (in-track), N (orbit normal); maps inertial -> RTN."""
    r_hat = _unit(np.asarray(r, float))
    n_hat = _unit(np.cross(r, v))
    return np.vstack([r_hat, np.cross(n_hat, r_hat), n_hat])


def vnc_matrix(r, v):
    """Rows V (velocity), N (orbit normal), C (co-normal = V x N)."""
    v_hat = _unit(np.asarray(v, float))
    n_hat = _unit(np.cross(r, v))
    return np.vstack([v_hat, n_hat, np.cross(v_hat, n_hat)])


def lvlh_matrix(r, v):
    """Rows X = Y x Z, Y = -orbit normal, Z = nadir (CCSDS LVLH)."""
    z_hat = -_unit(np.asarray(r, float))
    y_hat = -_unit(np.cross(r, v))
    return np.vstack([np.cross(y_hat, z_hat), y_hat, z_hat])


# ==============================================================================
# FAST EARTH ROTATION FOR FORCE-MODEL CALLS
# ==============================================================================
class FastEarthRotation:
    """GCRF -> ITRF rotation cheap enough to call inside the equations of motion.

    Precession-nutation (GCRF -> CIRS) and polar motion change slowly, so they are
    tabulated every `step_s` seconds over [t0, t1] and interpolated linearly. The
    Earth rotation angle is evaluated exactly from UT1 at every call.
    Times are SI seconds after `epoch`. With step_s = 3600 the interpolation error
    is about 3e-11 rad (roughly 1 mm at GEO distance).
    """

    def __init__(self, epoch, t0_s, t1_s, step_s=3600.0):
        self.epoch = Epoch.coerce(epoch)
        lo, hi = min(t0_s, t1_s), max(t0_s, t1_s)
        n = max(2, int(np.ceil((hi - lo) / step_s)) + 1)
        self.grid = np.linspace(lo, hi, n) if hi > lo else np.array([lo, lo + 1.0])
        eo = EarthOrientation(self.epoch, self.grid)
        self._c2i = eo.c2i
        self._pom = eo.pom
        self._omega = np.atleast_1d(eo.omega)
        # ERA is linear in UT1; UT1-TAI is tabulated on the grid
        self._era0 = float(eo.era[0])
        tai1, tai2 = self.epoch.jd("TAI")
        mjd_utc = (tai1 - MJD_ZERO) + tai2 + self.grid / SEC_PER_DAY - 37.0 / SEC_PER_DAY
        self._ut1_tai = get_eop().ut1_minus_tai(mjd_utc)

    def _weights(self, t):
        i = int(np.clip(np.searchsorted(self.grid, t) - 1, 0, len(self.grid) - 2))
        w = (t - self.grid[i]) / (self.grid[i + 1] - self.grid[i])
        return i, w

    def earth_rotation_angle(self, t):
        i, w = self._weights(t)
        ut1_tai = (1.0 - w) * self._ut1_tai[i] + w * self._ut1_tai[i + 1]
        d_ut1 = (t - self.grid[0]) + (ut1_tai - self._ut1_tai[0])
        return (self._era0 + 2.0 * np.pi * 1.00273781191135448 * d_ut1 / SEC_PER_DAY) % (2.0 * np.pi)

    def matrix(self, t):
        """3x3 rotation taking GCRF vectors to ITRF at t seconds after the epoch."""
        i, w = self._weights(t)
        c2i = (1.0 - w) * self._c2i[i] + w * self._c2i[i + 1]
        pom = (1.0 - w) * self._pom[i] + w * self._pom[i + 1]
        return pom @ _rot3(self.earth_rotation_angle(t)) @ c2i

    def omega(self, t):
        i, w = self._weights(t)
        return (1.0 - w) * self._omega[i] + w * self._omega[i + 1]
