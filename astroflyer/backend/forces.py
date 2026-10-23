"""
AstroFlyer HEO - Force Models

All perturbing accelerations used by the propagator, computed in GCRF (m/s^2):

  - Earth gravity: point mass + EGM2008 spherical harmonics up to 70x70
    (Montenbruck & Gill V/W recursion, evaluated in ITRF and rotated to GCRF)
  - Sun and Moon point-mass third-body gravity from the bundled JPL DE440
  - Solar radiation pressure, cannonball, with a conical (umbra/penumbra) Earth shadow
  - Atmospheric drag with NRLMSISE-00 density (pymsis) and a co-rotating atmosphere
  - Schwarzschild general-relativity correction (IERS 2010)
  - Optional simplified Earth albedo + infrared pressure (radial, off by default)

Time is TT seconds past J2000. Earth orientation comes from the caller's
`earth_rotation` object (`.matrix(t)` -> GCRF->ITRF 3x3, `.omega(t)` -> rad/s);
without one, a z-axis GMST rotation is used, which is adequate only for tests.
"""

import math
import os
from dataclasses import dataclass

import numpy as np

from .ephemeris import _resource_path, get_ephemeris, njit

# Physical constants
MU_SUN = 1.32712440041279419e20      # DE440 GM_sun (m^3/s^2)
MU_MOON = 4.902800118457551e12       # DE440 GM_moon (m^3/s^2)
AU_METERS = 149597870700.0
R_SUN = 695700000.0                   # IAU 2015 nominal solar radius (m)
R_EARTH_EQ = 6378137.0                # WGS-84 equatorial radius (m)
WGS84_F = 1.0 / 298.257223563
OMEGA_EARTH = 7.292115146706979e-5    # IERS nominal rotation rate (rad/s)
P_SR_1AU = 4.56e-6                    # Solar radiation pressure at 1 AU (N/m^2)
SPEED_OF_LIGHT = 299792458.0
SOLAR_FLUX_1AU = 1361.0               # W/m^2
EARTH_ALBEDO = 0.30
EARTH_IR_FLUX = 237.0                 # W/m^2 at the surface
DRAG_CUTOFF_ALT_M = 1500.0e3          # above this, drag is below ~1e-12 m/s^2


# ==============================================================================
# GRAVITY FIELD
# ==============================================================================
def _load_gravity_field():
    data = np.load(_resource_path("gravity", "EGM2008_70.npz"))
    c_norm, s_norm = data["C"], data["S"]
    n_max = c_norm.shape[0] - 1
    c = np.zeros_like(c_norm)
    s = np.zeros_like(s_norm)
    # Convert fully normalized to unnormalized coefficients for the V/W recursion
    for n in range(n_max + 1):
        for m in range(n + 1):
            k = 1.0 if m == 0 else 2.0
            log_ratio = math.lgamma(n - m + 1) - math.lgamma(n + m + 1)
            fac = math.sqrt(k * (2 * n + 1) * math.exp(log_ratio))
            c[n, m] = c_norm[n, m] * fac
            s[n, m] = s_norm[n, m] * fac
    return float(data["gm"]), float(data["radius"]), c, s, n_max


MU_EARTH, R_GRAVITY_REF, _C_NM, _S_NM, GRAVITY_MAX_DEGREE = _load_gravity_field()

# Unnormalized zonal coefficients J_n = -C_n0 (EGM2008, tide free)
J2_EARTH = -_C_NM[2, 0]
J3_EARTH = -_C_NM[3, 0]
J4_EARTH = -_C_NM[4, 0]


@njit(cache=False)
def _harmonic_accel_body(r_body, gm, r_ref, c, s, n_max, m_max, n_min):
    """
    Spherical-harmonic acceleration in the body-fixed frame, degrees
    n_min..n_max and orders 0..min(n, m_max). Montenbruck & Gill (2000), 3.2.5.
    """
    x, y, z = r_body[0], r_body[1], r_body[2]
    r2 = x * x + y * y + z * z
    rho = r_ref * r_ref / r2
    x0 = r_ref * x / r2
    y0 = r_ref * y / r2
    z0 = r_ref * z / r2

    nn = n_max + 2
    v = np.zeros((nn + 1, nn + 1))
    w = np.zeros((nn + 1, nn + 1))
    v[0, 0] = r_ref / math.sqrt(r2)
    w[0, 0] = 0.0
    v[1, 0] = z0 * v[0, 0]
    w[1, 0] = 0.0
    for n in range(2, nn + 1):
        v[n, 0] = ((2 * n - 1) * z0 * v[n - 1, 0] - (n - 1) * rho * v[n - 2, 0]) / n
    for m in range(1, nn + 1):
        v[m, m] = (2 * m - 1) * (x0 * v[m - 1, m - 1] - y0 * w[m - 1, m - 1])
        w[m, m] = (2 * m - 1) * (x0 * w[m - 1, m - 1] + y0 * v[m - 1, m - 1])
        if m + 1 <= nn:
            v[m + 1, m] = (2 * m + 1) * z0 * v[m, m]
            w[m + 1, m] = (2 * m + 1) * z0 * w[m, m]
        for n in range(m + 2, nn + 1):
            v[n, m] = ((2 * n - 1) * z0 * v[n - 1, m] - (n + m - 1) * rho * v[n - 2, m]) / (n - m)
            w[n, m] = ((2 * n - 1) * z0 * w[n - 1, m] - (n + m - 1) * rho * w[n - 2, m]) / (n - m)

    ax = 0.0
    ay = 0.0
    az = 0.0
    for n in range(n_min, n_max + 1):
        for m in range(0, min(n, m_max) + 1):
            cnm = c[n, m]
            snm = s[n, m]
            if m == 0:
                ax -= cnm * v[n + 1, 1]
                ay -= cnm * w[n + 1, 1]
                az += (n + 1) * (-cnm * v[n + 1, 0])
            else:
                fac = 0.5 * (n - m + 1) * (n - m + 2)
                ax += 0.5 * (-cnm * v[n + 1, m + 1] - snm * w[n + 1, m + 1]) \
                    + fac * (cnm * v[n + 1, m - 1] + snm * w[n + 1, m - 1])
                ay += 0.5 * (-cnm * w[n + 1, m + 1] + snm * v[n + 1, m + 1]) \
                    + fac * (-cnm * w[n + 1, m - 1] + snm * v[n + 1, m - 1])
                az += (n - m + 1) * (-cnm * v[n + 1, m] - snm * w[n + 1, m])
    k = gm / (r_ref * r_ref)
    return np.array([k * ax, k * ay, k * az])


def harmonic_acceleration_body(r_body, degree, order, n_min=2, mu=MU_EARTH):
    """Non-central gravity (m/s^2) in the body-fixed frame for one position."""
    degree = int(min(degree, GRAVITY_MAX_DEGREE))
    order = int(min(order, degree))
    if degree < n_min:
        return np.zeros(3)
    return _harmonic_accel_body(np.asarray(r_body, dtype=float), mu, R_GRAVITY_REF,
                                _C_NM, _S_NM, degree, order, n_min)


# ==============================================================================
# EARTH ORIENTATION FALLBACK & GEODETIC CONVERSION
# ==============================================================================
class SimpleEarthRotation:
    """z-axis rotation by GMST (IAU 1982, UT1 ~ TT). Test fallback only: no precession/nutation/polar motion."""

    def __init__(self, epoch_tt_j2000_s=0.0):
        self.epoch_tt_j2000_s = float(epoch_tt_j2000_s)

    def gmst(self, t):
        d = (self.epoch_tt_j2000_s + t) / 86400.0
        return math.fmod(4.894961212823059 + 6.300388098984891 * d, 2.0 * math.pi)

    def matrix(self, t):
        th = self.gmst(t)
        c, s = math.cos(th), math.sin(th)
        return np.array([[c, s, 0.0], [-s, c, 0.0], [0.0, 0.0, 1.0]])

    def omega(self, t):
        return OMEGA_EARTH


def itrf_to_geodetic(r_itrf):
    """WGS-84 geodetic latitude, longitude (rad) and height (m) from ITRF position."""
    x, y, z = r_itrf
    e2 = WGS84_F * (2.0 - WGS84_F)
    p = math.hypot(x, y)
    lon = math.atan2(y, x)
    lat = math.atan2(z, p * (1.0 - e2))
    h = 0.0
    for _ in range(6):
        sin_lat = math.sin(lat)
        n_rad = R_EARTH_EQ / math.sqrt(1.0 - e2 * sin_lat * sin_lat)
        h = p * math.cos(lat) + (z + e2 * n_rad * sin_lat) * sin_lat - n_rad
        lat = math.atan2(z, p * (1.0 - e2 * n_rad / (n_rad + h)))
    return lat, lon, h


# ==============================================================================
# CONFIGURATION
# ==============================================================================
@dataclass
class ForceModelConfig:
    """Which forces are on, and the spacecraft/space-weather parameters they need."""
    gravity_degree: int = 8
    gravity_order: int = 8
    third_body: bool = True
    srp: bool = True
    drag: bool = True
    relativity: bool = True
    albedo: bool = False
    cd_area_over_m: float = 0.01     # Cd*A/m (m^2/kg)
    cr_area_over_m: float = 0.02     # Cr*A/m (m^2/kg)
    f107: float = 150.0              # daily F10.7 (sfu)
    f107a: float = 150.0             # 81-day mean F10.7 (sfu)
    ap: float = 15.0                 # daily Ap

    @classmethod
    def for_model(cls, model, **overrides):
        """Force-model ladder used by the propagator and the validation suite."""
        model = str(model).lower()
        presets = {
            "two_body": dict(gravity_degree=0, gravity_order=0, third_body=False, srp=False,
                             drag=False, relativity=False, albedo=False),
            "j2": dict(gravity_degree=2, gravity_order=0, third_body=False, srp=False,
                       drag=False, relativity=False, albedo=False),
            "j2_j3_j4": dict(gravity_degree=4, gravity_order=0, third_body=False, srp=False,
                             drag=False, relativity=False, albedo=False),
        }
        cfg = cls(**presets.get(model, {}))
        for key, value in overrides.items():
            if value is not None and hasattr(cfg, key):
                setattr(cfg, key, value)
        return cfg


# ==============================================================================
# INDIVIDUAL FORCES (GCRF)
# ==============================================================================
def third_body_acceleration(r, r_body, mu_body):
    """Point-mass third-body perturbation on a geocentric satellite."""
    d = r_body - r
    return mu_body * (d / np.linalg.norm(d) ** 3 - r_body / np.linalg.norm(r_body) ** 3)


def shadow_function(r, r_sun, r_occ=R_EARTH_EQ):
    """Fraction of the solar disc visible (1 sunlit, 0 umbra), conical model (M&G 3.4.2)."""
    d = r_sun - r
    dist_sun = np.linalg.norm(d)
    dist_occ = np.linalg.norm(r)
    a = math.asin(min(1.0, R_SUN / dist_sun))
    b = math.asin(min(1.0, r_occ / dist_occ))
    cos_c = -float(np.dot(r, d)) / (dist_occ * dist_sun)
    c = math.acos(max(-1.0, min(1.0, cos_c)))
    if c >= a + b:
        return 1.0
    if c < b - a:
        return 0.0
    if c < a - b:
        return 1.0 - (b * b) / (a * a)
    x = (c * c + a * a - b * b) / (2.0 * c)
    y = math.sqrt(max(0.0, a * a - x * x))
    area = a * a * math.acos(max(-1.0, min(1.0, x / a))) \
        + b * b * math.acos(max(-1.0, min(1.0, (c - x) / b))) - c * y
    return 1.0 - area / (math.pi * a * a)


def srp_acceleration(r, r_sun, cr_area_over_m, nu=None):
    """Cannonball solar radiation pressure, pointing away from the Sun."""
    if nu is None:
        nu = shadow_function(r, r_sun)
    if nu <= 0.0:
        return np.zeros(3), 0.0
    d = r - r_sun
    dist = np.linalg.norm(d)
    accel = nu * P_SR_1AU * (AU_METERS / dist) ** 2 * cr_area_over_m * d / dist
    return accel, nu


def relativity_acceleration(r, v, mu=MU_EARTH):
    """Schwarzschild term, IERS Conventions 2010 eq. 10.12 with beta = gamma = 1."""
    rn = np.linalg.norm(r)
    v2 = float(np.dot(v, v))
    return mu / (SPEED_OF_LIGHT ** 2 * rn ** 3) * ((4.0 * mu / rn - v2) * r + 4.0 * float(np.dot(r, v)) * v)


def albedo_ir_acceleration(r, r_sun, cr_area_over_m, nu):
    """Simplified radial Earth albedo + IR pressure (uniform Earth; ~20% model accuracy)."""
    rn = np.linalg.norm(r)
    r_hat = r / rn
    geom = (R_EARTH_EQ / rn) ** 2
    ir = EARTH_IR_FLUX / SPEED_OF_LIGHT * geom
    cos_phase = float(np.dot(r_hat, r_sun / np.linalg.norm(r_sun)))
    albedo = EARTH_ALBEDO * SOLAR_FLUX_1AU / SPEED_OF_LIGHT * geom * 0.5 * (1.0 + cos_phase)
    return (ir + albedo) * cr_area_over_m * r_hat


_msis = None


def atmospheric_density(tt_seconds_j2000, lat_rad, lon_rad, alt_m, f107, f107a, ap):
    """NRLMSISE-00 total mass density (kg/m^3) via pymsis, with fixed space weather."""
    global _msis
    if _msis is None:
        import pymsis
        _msis = pymsis
    # UTC = TT - 69.184 s since 2017; density is insensitive to this offset
    utc = np.datetime64("2000-01-01T11:58:55.816", "ms") + \
        np.timedelta64(int(round(tt_seconds_j2000 * 1000.0)), "ms")
    out = _msis.calculate(utc, math.degrees(lon_rad), math.degrees(lat_rad), alt_m / 1000.0,
                          f107s=f107, f107as=f107a, aps=[[ap] * 7], version=0)
    return float(np.asarray(out).reshape(-1)[0])


def drag_acceleration(r, v, rot_gcrf2itrf, omega, tt_seconds_j2000, cfg):
    """Drag with a co-rotating atmosphere. Returns (accel, density)."""
    r_itrf = rot_gcrf2itrf @ r
    lat, lon, h = itrf_to_geodetic(r_itrf)
    if h > DRAG_CUTOFF_ALT_M or cfg.cd_area_over_m <= 0.0:
        return np.zeros(3), 0.0
    rho = atmospheric_density(tt_seconds_j2000, lat, lon, max(h, 0.0), cfg.f107, cfg.f107a, cfg.ap)
    omega_gcrf = rot_gcrf2itrf.T @ np.array([0.0, 0.0, omega])
    v_rel = v - np.cross(omega_gcrf, r)
    return -0.5 * rho * cfg.cd_area_over_m * np.linalg.norm(v_rel) * v_rel, rho


# ==============================================================================
# TOTAL
# ==============================================================================
def acceleration_components(tt_seconds_j2000, r, v, cfg, rot_gcrf2itrf=None, omega=OMEGA_EARTH,
                            ephemeris=None):
    """
    Every enabled acceleration term for one GCRF state.
    Returns a dict of 3-vectors (m/s^2) plus 'shadow_factor' and 'density'.
    """
    r = np.asarray(r, dtype=float)
    v = np.asarray(v, dtype=float)
    zero = np.zeros(3)
    out = {"central": -MU_EARTH * r / np.linalg.norm(r) ** 3, "harmonics": zero, "sun": zero,
           "moon": zero, "srp": zero, "drag": zero, "relativity": zero, "albedo": zero,
           "shadow_factor": 1.0, "density": 0.0}

    need_rotation = cfg.gravity_degree >= 2 or cfg.drag
    if need_rotation and rot_gcrf2itrf is None:
        fallback = SimpleEarthRotation(tt_seconds_j2000)
        rot_gcrf2itrf, omega = fallback.matrix(0.0), fallback.omega(0.0)

    if cfg.gravity_degree >= 2:
        a_body = harmonic_acceleration_body(rot_gcrf2itrf @ r, cfg.gravity_degree, cfg.gravity_order)
        out["harmonics"] = rot_gcrf2itrf.T @ a_body

    r_sun = None
    if cfg.third_body or cfg.srp or cfg.albedo:
        r_sun, r_moon = (ephemeris or get_ephemeris()).sun_moon_gcrf(tt_seconds_j2000)
        if cfg.third_body:
            out["sun"] = third_body_acceleration(r, r_sun, MU_SUN)
            out["moon"] = third_body_acceleration(r, r_moon, MU_MOON)

    if cfg.srp or cfg.albedo:
        out["shadow_factor"] = shadow_function(r, r_sun)
    if cfg.srp:
        out["srp"], _ = srp_acceleration(r, r_sun, cfg.cr_area_over_m, out["shadow_factor"])
    if cfg.albedo:
        out["albedo"] = albedo_ir_acceleration(r, r_sun, cfg.cr_area_over_m, out["shadow_factor"])
    if cfg.drag:
        out["drag"], out["density"] = drag_acceleration(r, v, rot_gcrf2itrf, omega, tt_seconds_j2000, cfg)
    if cfg.relativity:
        out["relativity"] = relativity_acceleration(r, v)
    return out


_VECTOR_TERMS = ("central", "harmonics", "sun", "moon", "srp", "drag", "relativity", "albedo")


def total_acceleration(tt_seconds_j2000, r, v, cfg, rot_gcrf2itrf=None, omega=OMEGA_EARTH):
    """Sum of all enabled accelerations (m/s^2), GCRF."""
    comps = acceleration_components(tt_seconds_j2000, r, v, cfg, rot_gcrf2itrf, omega)
    total = np.zeros(3)
    for key in _VECTOR_TERMS:
        total += comps[key]
    return total
