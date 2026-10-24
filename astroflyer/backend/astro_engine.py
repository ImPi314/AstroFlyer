"""
AstroCore Astrodynamics Engine - Third Review
=============================================================================
Department of Aerospace Engineering, ACS College of Engineering
Part of Major Project: Precise Trajectory Propagation & Events Prediction for HEOs
Final Production Release: High-Fidelity Coupled Mechanics & V&V Certification

Features:
  - Coupled EOM: EGM2008 spherical-harmonic gravity (up to 70x70), see forces.py
  - Third-Body Sun & Moon gravity from the bundled JPL DE440 ephemeris
  - Atmospheric Drag with NRLMSISE-00 density and Earth co-rotation
  - Solar Radiation Pressure (SRP) with conical umbra/penumbra shadow
  - Instantaneous Perturbation Acceleration Decomposition
  - Machine-Precision Stiff Radau-IIA & RK45 Numerical Integrators
  - Energy Invariant Monitoring (|ΔE/E₀| ≤ 10⁻¹¹)
=============================================================================
"""

import math
import numpy as np
from scipy.integrate import solve_ivp

from . import forces
from .eclipse import drag_boundary_events, shadow_boundary_events, solve_ivp_segmented
from .epoch import Epoch
from .forces import ForceModelConfig, SimpleEarthRotation
from .frames import EarthOrientation, FastEarthRotation, gcrf_to_geodetic, transform_state
from . import analytic
from .integrators import integrate
from .covariance_engine import CovarianceEngine, CovarianceSteering
from .ecr_mf_controller import FidelitySchedule

# ==============================================================================
# LAYER 1: MATH CORE
# ==============================================================================
# The force model runs in NumPy, with the hot loops JIT-compiled by Numba when it
# is installed (forces.py, ephemeris.py). The old C++ kernel in cpp_engine/ is
# retired: it implemented the earlier simplified physics, and the full model
# runs a day of HEO propagation in about a second without it.


def get_engine_status():
    """Returns which math core the force model is using."""
    try:
        import numba
        jit = f"Numba {numba.__version__}"
    except ImportError:
        jit = "none (plain NumPy)"
    return {
        "c_plus_plus_kernel_loaded": False,
        "kernel_binary": "NumPy/SciPy force model (forces.py)",
        "jit": jit,
        "architecture_layer": "Layer 1 (The Math Core)"
    }


# ==============================================================================
# ASTRODYNAMICAL CONSTANTS (WGS-84 / IERS / NASA JPL Standards)
# ==============================================================================
MU_EARTH = forces.MU_EARTH          # EGM2008 GM, 3.986004415e14 m^3/s^2 (same value the gravity field uses)
R_EARTH = 6371000.0                # Mean Earth radius (m); display only, never a harmonic reference radius
R_EARTH_EQ = 6378137.0             # Equatorial Earth radius (m)
J2_EARTH = forces.J2_EARTH         # EGM2008 unnormalized zonals (reference radius forces.R_GRAVITY_REF)
J3_EARTH = forces.J3_EARTH
J4_EARTH = forces.J4_EARTH
OMEGA_EARTH = forces.OMEGA_EARTH   # Earth rotation rate (rad/s)

# Third-Body Parameters (NASA JPL DE440)
MU_SUN = forces.MU_SUN             # DE440 Sun gravitational parameter (m^3/s^2)
MU_MOON = forces.MU_MOON           # DE440 Moon gravitational parameter (m^3/s^2)
AU_METERS = 149597870700.0         # Astronomical Unit (m)
D_MOON_MEAN = 384400000.0          # Mean Earth-Moon distance (m)

# Environmental & Non-Gravitational Constants
P_SR_1AU = 4.56e-6                 # Solar radiation pressure at 1 AU (N/m^2)
RHO_0 = 1.225                      # Sea-level atmospheric density (kg/m^3)
H_SCALE = 8500.0                   # Mean atmospheric scale height (m)
SPEED_OF_LIGHT = 299792458.0      # Speed of light in vacuum (m/s)

# Tesseral & Sectoral Harmonics (EGM-96 / JGM-3 Standard)
C22_EARTH = 2.43914e-6             # Earth C22 sectoral harmonic (equatorial ellipticity)
S22_EARTH = -1.40016e-6            # Earth S22 sectoral harmonic

# Earth Albedo & Thermal Radiation
ALBEDO_REFLECTIVITY = 0.30         # Mean planetary bond albedo
TIR_SURFACE_FLUX = 237.0           # Terrestrial Infrared Radiation flux (W/m^2)


# ==============================================================================
# COORDINATE CONVERSIONS & KEPLER SOLVERS
# ==============================================================================
def solve_kepler_equation(M, e, tol=1e-12, max_iter=100):
    """Solves Kepler's equation M = E - e*sin(E) for Eccentric Anomaly (E)."""
    E = M if e < 0.8 else math.pi
    for _ in range(max_iter):
        f = E - e * math.sin(E) - M
        f_prime = 1.0 - e * math.cos(E)
        dE = -f / f_prime
        E += dE
        if abs(dE) < tol:
            return E
    return E


def true_anomaly_from_eccentric(E, e):
    """Computes True Anomaly (nu) from Eccentric Anomaly (E)."""
    sin_nu = (math.sqrt(max(0.0, 1.0 - e**2)) * math.sin(E)) / (1.0 - e * math.cos(E))
    cos_nu = (math.cos(E) - e) / (1.0 - e * math.cos(E))
    return math.atan2(sin_nu, cos_nu)


def keplerian_to_cartesian(a, e, inc, Omega, omega, nu, mu=MU_EARTH):
    """Converts Classical Keplerian Elements to Cartesian ECI state vectors r, v."""
    p = a * (1.0 - e**2)
    r_mag = p / (1.0 + e * math.cos(nu))

    r_pqw = np.array([r_mag * math.cos(nu), r_mag * math.sin(nu), 0.0])
    v_pqw = np.array([
        -math.sqrt(mu / p) * math.sin(nu),
         math.sqrt(mu / p) * (e + math.cos(nu)),
         0.0
    ])

    cos_O, sin_O = math.cos(Omega), math.sin(Omega)
    cos_i, sin_i = math.cos(inc), math.sin(inc)
    cos_w, sin_w = math.cos(omega), math.sin(omega)

    R_z_O = np.array([[cos_O, -sin_O, 0.0], [sin_O, cos_O, 0.0], [0.0, 0.0, 1.0]])
    R_x_i = np.array([[1.0, 0.0, 0.0], [0.0, cos_i, -sin_i], [0.0, sin_i, cos_i]])
    R_z_w = np.array([[cos_w, -sin_w, 0.0], [sin_w, cos_w, 0.0], [0.0, 0.0, 1.0]])

    Q_ECI_PQW = R_z_O @ R_x_i @ R_z_w
    return Q_ECI_PQW @ r_pqw, Q_ECI_PQW @ v_pqw


def cartesian_to_keplerian(r_vec, v_vec, mu=MU_EARTH):
    """Converts Cartesian ECI state vectors to Classical Keplerian elements."""
    r_vec = np.array(r_vec, dtype=np.float64)
    v_vec = np.array(v_vec, dtype=np.float64)

    r = float(np.linalg.norm(r_vec))
    v = float(np.linalg.norm(v_vec))

    h_vec = np.cross(r_vec, v_vec)
    h = float(np.linalg.norm(h_vec))

    k_hat = np.array([0.0, 0.0, 1.0])
    n_vec = np.cross(k_hat, h_vec)
    n = float(np.linalg.norm(n_vec))

    e_vec = (1.0 / mu) * ((v**2 - mu / r) * r_vec - np.dot(r_vec, v_vec) * v_vec)
    e = float(np.linalg.norm(e_vec))

    energy = (v**2 / 2.0) - (mu / r)
    a = -mu / (2.0 * energy) if abs(1.0 - e) > 1e-12 else np.inf
    period = 2.0 * math.pi * math.sqrt(abs(a**3) / mu) if a > 0 else 0.0

    inc = math.acos(max(-1.0, min(1.0, h_vec[2] / max(1e-12, h))))

    if n > 1e-12:
        Omega = math.acos(max(-1.0, min(1.0, n_vec[0] / n)))
        if n_vec[1] < 0:
            Omega = 2.0 * math.pi - Omega
    else:
        Omega = 0.0

    if n > 1e-12 and e > 1e-12:
        omega = math.acos(max(-1.0, min(1.0, np.dot(n_vec, e_vec) / (n * e))))
        if e_vec[2] < 0:
            omega = 2.0 * math.pi - omega
    else:
        omega = 0.0

    if e > 1e-12:
        nu = math.acos(max(-1.0, min(1.0, np.dot(e_vec, r_vec) / (e * r))))
        if np.dot(r_vec, v_vec) < 0:
            nu = 2.0 * math.pi - nu
    else:
        nu = 0.0

    return {
        'a': a,
        'e': e,
        'inc': inc,
        'Omega': Omega,
        'omega': omega,
        'nu': nu,
        'energy': energy,
        'h_mag': h,
        'period': period
    }


def calculate_theoretical_j2_drifts(a, e, inc, num_orbits, mu=MU_EARTH, r_e=forces.R_GRAVITY_REF, j2=J2_EARTH):
    """
    Calculates first-order theoretical secular precession rates from Lagrange Planetary Equations.
    """
    n = math.sqrt(mu / a**3)
    p = a * (1.0 - e**2)
    T = 2.0 * math.pi / n

    # Nodal Precession dOmega/dt (rad/s)
    dOmega_dt_rad_s = -1.5 * j2 * ((r_e / p)**2) * n * math.cos(inc)
    dOmega_dt_deg_day = math.degrees(dOmega_dt_rad_s) * 86400.0
    dOmega_total_deg = math.degrees(dOmega_dt_rad_s * (num_orbits * T))

    # Apsidal Precession domega/dt (rad/s)
    domega_dt_rad_s = 0.75 * j2 * ((r_e / p)**2) * n * (5.0 * math.cos(inc)**2 - 1.0)
    domega_dt_deg_day = math.degrees(domega_dt_rad_s) * 86400.0
    domega_total_deg = math.degrees(domega_dt_rad_s * (num_orbits * T))

    return {
        'dOmega_dt_deg_day': dOmega_dt_deg_day,
        'dOmega_total_deg': dOmega_total_deg,
        'domega_dt_deg_day': domega_dt_deg_day,
        'domega_total_deg': domega_total_deg,
        'period_hours': T / 3600.0
    }


def eci_to_ecef_geodetic(r_eci, t_seconds, omega_e=OMEGA_EARTH, epoch=None):
    """GCRF position (m) at t_seconds after `epoch` -> geodetic (lat_deg, lon_deg, height_km).

    Uses the IAU 2006/2000A Earth orientation chain with IERS EOP and the
    WGS-84 ellipsoid. `epoch` defaults to J2000.0; omega_e is kept for
    backward compatibility and no longer used.
    """
    lat, lon, h_m = gcrf_to_geodetic(np.asarray(r_eci, dtype=float), Epoch.coerce(epoch) + float(t_seconds))
    return lat, lon, h_m / 1000.0


# ==============================================================================
# DETAILED PERTURBATION ACCELERATION DECOMPOSITION
# ==============================================================================
def _legacy_force_config(j2, j3, j4, b_star, cr_area_over_m, enable_drag=True, enable_third_body=True,
                         enable_srp=True, enable_tesseral=True, enable_relativity=True):
    """Maps the older J2/J3/J4 + enable_* arguments onto a ForceModelConfig."""
    cfg = ForceModelConfig(cd_area_over_m=b_star, cr_area_over_m=cr_area_over_m, drag=enable_drag,
                           third_body=enable_third_body, srp=enable_srp, relativity=enable_relativity)
    if j2 == 0:
        cfg.gravity_degree, cfg.gravity_order = 0, 0
    elif j3 == 0 and j4 == 0:
        cfg.gravity_degree, cfg.gravity_order = 2, 0
    elif not enable_tesseral:
        cfg.gravity_order = 0
    return cfg


def _earth_rotation_at(t, epoch_tt_j2000_s, earth_rotation):
    rot = earth_rotation if earth_rotation is not None else SimpleEarthRotation(epoch_tt_j2000_s)
    return rot.matrix(t), rot.omega(t)


def compute_acceleration_components(
    state,
    t,
    mu=MU_EARTH,
    r_e=R_EARTH,
    j2=J2_EARTH,
    j3=J3_EARTH,
    j4=J4_EARTH,
    b_star=0.015,
    cr_area_over_m=0.02,
    force_config=None,
    epoch_tt_j2000_s=0.0,
    earth_rotation=None
):
    """
    Acceleration vectors and magnitudes for every force term (GCRF, m/s^2).
    b_star is Cd*A/m (m^2/kg). The J2/J3/J4 terms are reported separately for
    display; 'a_tesseral' is the rest of the spherical-harmonic field.
    mu and r_e are kept for backward compatibility; the gravity model's own
    GM and reference radius are always used.
    """
    cfg = force_config or _legacy_force_config(j2, j3, j4, b_star, cr_area_over_m)
    r = np.asarray(state[0:3], dtype=float)
    v = np.asarray(state[3:6], dtype=float)
    rot, omega = _earth_rotation_at(t, epoch_tt_j2000_s, earth_rotation)
    comps = forces.acceleration_components(epoch_tt_j2000_s + t, r, v, cfg, rot, omega)

    r_body = rot @ r
    zonal = {}
    for n in (2, 3, 4):
        if cfg.gravity_degree >= n:
            zonal[n] = rot.T @ forces.harmonic_acceleration_body(r_body, n, 0, n_min=n)
        else:
            zonal[n] = np.zeros(3)
    a_tesseral = comps["harmonics"] - zonal[2] - zonal[3] - zonal[4]

    vectors = {
        "a_central": comps["central"],
        "a_j2": zonal[2],
        "a_j3": zonal[3],
        "a_j4": zonal[4],
        "a_tesseral": a_tesseral,
        "a_relativity": comps["relativity"],
        "a_albedo": comps["albedo"],
        "a_moon": comps["moon"],
        "a_sun": comps["sun"],
        "a_drag": comps["drag"],
        "a_srp": comps["srp"],
    }
    vectors["a_total"] = sum(vectors.values())
    out = {}
    for key, vec in vectors.items():
        out[key] = vec
        out[key + "_mag"] = float(np.linalg.norm(vec))
    out["shadow_factor"] = comps["shadow_factor"]
    out["density_kg_m3"] = comps["density"]
    return out


def full_production_eom(
    t,
    state,
    mu=MU_EARTH,
    r_e=R_EARTH,
    j2=J2_EARTH,
    j3=J3_EARTH,
    j4=J4_EARTH,
    enable_drag=True,
    enable_third_body=True,
    enable_srp=True,
    enable_tesseral=True,
    enable_relativity=True,
    b_star=0.015,
    cr_area_over_m=0.02,
    epoch_tt_j2000_s=0.0,
    earth_rotation=None,
    force_config=None
):
    """Full coupled equations of motion.

    t is seconds after the initial epoch. epoch_tt_j2000_s is that epoch as TT
    seconds past J2000.0, so the force model's TT time is epoch_tt_j2000_s + t.
    earth_rotation is a frames.FastEarthRotation; earth_rotation.matrix(t) gives
    the GCRF -> ITRF rotation for gravity harmonics and co-rotating drag.
    force_config (a forces.ForceModelConfig) takes precedence over the legacy flags.
    """
    vx, vy, vz = state[3:6]

    cfg = force_config or _legacy_force_config(j2, j3, j4, b_star, cr_area_over_m, enable_drag,
                                               enable_third_body, enable_srp, enable_tesseral,
                                               enable_relativity)
    rot, omega = _earth_rotation_at(t, epoch_tt_j2000_s, earth_rotation)
    acc = forces.total_acceleration(epoch_tt_j2000_s + t, state[0:3], state[3:6], cfg, rot, omega)
    return [vx, vy, vz, acc[0], acc[1], acc[2]]


# ==============================================================================
# ORBIT EVENTS AND SUN DIRECTION FOR THE UI TIMELINE
# ==============================================================================
def _radial_rate(t, y):
    """r . v: negative before perigee and positive after it."""
    return y[0] * y[3] + y[1] * y[4] + y[2] * y[5]


def _z_position(t, y):
    return y[2]


def _make_event(fn, direction):
    def event(t, y):
        return fn(t, y)
    event.direction = direction
    return event


# Located by the integrator itself, so times are exact to its tolerance
_ORBIT_EVENT_FUNCTIONS = [
    _make_event(_radial_rate, 1.0),    # perigee
    _make_event(_radial_rate, -1.0),   # apogee
    _make_event(_z_position, 1.0),     # ascending node
    _make_event(_z_position, -1.0),    # descending node
]
_ORBIT_EVENT_TYPES = ("perigee", "apogee", "ascending_node", "descending_node")


def orbit_events(sol, epoch, apsides=True):
    """Apsis and node crossings from a solve_ivp run with _ORBIT_EVENT_FUNCTIONS.

    Returns [{"type", "t_s", "utc"}] sorted by time. Apsides are left out for
    near-circular orbits, where r . v is only numerical noise.
    """
    t_events = getattr(sol, "t_events", None) or []
    events = []
    # The integrator cannot see a crossing at its first point, so check the initial state
    t0, y0 = float(sol.t[0]), sol.y[:, 0]
    r0, v0 = np.linalg.norm(y0[:3]), np.linalg.norm(y0[3:])
    if apsides and abs(_radial_rate(t0, y0)) < 1e-9 * r0 * v0:
        r_dot_a = y0[:3] @ (-MU_EARTH * y0[:3] / r0 ** 3) + v0 ** 2   # d(r . v)/dt
        events.append({"type": "perigee" if r_dot_a > 0 else "apogee", "t_s": t0, "utc": (epoch + t0).iso("UTC")})
    if abs(y0[2]) < 1e-9 * r0:
        events.append({"type": "ascending_node" if y0[5] > 0 else "descending_node", "t_s": t0,
                       "utc": (epoch + t0).iso("UTC")})
    for kind, times in zip(_ORBIT_EVENT_TYPES, t_events):
        if kind in ("perigee", "apogee") and not apsides:
            continue
        for t in times:
            if any(ev["type"] == kind and abs(ev["t_s"] - t) < 1e-6 for ev in events):
                continue
            events.append({"type": kind, "t_s": float(t), "utc": (epoch + float(t)).iso("UTC")})
    events.sort(key=lambda ev: ev["t_s"])
    return events


def sun_directions(times, epoch_tt_j2000_s):
    """Unit geocentric Sun vector (GCRF) at each time, or None outside the bundled DE440."""
    try:
        from .ephemeris import get_ephemeris
        eph = get_ephemeris()
        sun = np.array([eph.sun_gcrf(epoch_tt_j2000_s + float(t)) for t in times])
    except (ImportError, OSError, ValueError):
        return None
    return sun / np.linalg.norm(sun, axis=1)[:, None]


# ==============================================================================
# THIRD REVIEW UNIFIED PRODUCTION PROPAGATOR
# ==============================================================================
# Propagator names accepted by propagate(method=...), normalized: upper case, no spaces, dashes or underscores
ANALYTIC_METHODS = {'KEPLER': 'kepler', 'TWOBODYANALYTIC': 'kepler', 'J2MEAN': 'j2_mean', 'SGP4': 'sgp4'}
OWN_INTEGRATORS = {'RKF78': 'RKF78', 'RK78': 'RKF78', 'BS': 'BS', 'BULIRSCHSTOER': 'BS', 'RK4': 'RK4'}


def _with_variational_equations(eom):
    """Right-hand side for [r, v, Phi]: the orbit's own EOM plus dPhi/dt = A Phi, with
    A = [[0, I], [G(r), 0]] and G the point-mass + J2 gravity gradient."""
    gradient = CovarianceEngine().compute_gravity_gradient

    def rhs(t, y):
        phi = y[6:42].reshape(6, 6)
        dphi = np.vstack([phi[3:6], gradient(y[0:3]) @ phi[0:3]])
        return np.concatenate([eom(t, y[0:6]), dphi.ravel()])
    return rhs


class _AnalyticSolution:
    """The solve_ivp fields propagate() reads, for a closed-form trajectory."""

    def __init__(self, t, r, v):
        self.t = np.asarray(t)
        self.y = np.hstack([r, v]).T
        self.t_events, self.y_events = [], []
        self.success = True


class ThirdReviewEngine:
    """
    Final Production Propagator & Mission Analysis Engine for the Third Review.
    """
    def __init__(self, initial_state, mu=MU_EARTH, r_e=R_EARTH, epoch=None):
        """initial_state is a GCRF state [m, m/s] at `epoch` (Epoch, ISO string, or None for J2000.0)."""
        self.y0 = np.array(initial_state, dtype=np.float64)
        self.epoch = Epoch.coerce(epoch)
        self.mu = mu
        self.r_e = r_e

        elem = cartesian_to_keplerian(self.y0[0:3], self.y0[3:6], mu=self.mu)
        self.initial_elements = elem
        self.initial_energy = elem['energy']
        self.initial_h = elem['h_mag']
        self.tle = None

    @classmethod
    def from_tle(cls, line1, line2, epoch=None, **kwargs):
        """Engine whose initial state is the SGP4 state of a TLE at `epoch` (default: the TLE epoch)."""
        tle = analytic.TLEPropagator(line1, line2)
        epoch = tle.epoch if epoch is None else Epoch.coerce(epoch)
        r, v = tle.states(epoch, np.zeros(1))
        engine = cls(np.concatenate([r[0], v[0]]), epoch=epoch, **kwargs)
        engine.tle = tle
        return engine

    def _analytic_state_function(self, kind):
        if kind == 'kepler':
            return lambda t: analytic.kepler_states(self.y0, t, mu=self.mu)
        if kind == 'j2_mean':
            return lambda t: analytic.j2_mean_states(self.y0, t, mu=self.mu)
        if self.tle is None:
            raise ValueError("SGP4 needs a TLE: build the engine with ThirdReviewEngine.from_tle(line1, line2)")
        return lambda t: self.tle.states(self.epoch, t)

    def propagate(
        self,
        t_span,
        num_points=3000,
        model='coupled',
        enable_drag=True,
        enable_third_body=True,
        enable_srp=True,
        method='Radau',
        rtol=1e-11,
        atol=1e-11,
        b_star=0.015,
        cr_area_over_m=0.02,
        steering=None,
        **kwargs
    ):
        """
        Integrates the trajectory with high-order implicit Stiff Radau-IIA.
        Computes true osculating orbital elements across all time steps.
        """
        t_eval = np.linspace(t_span[0], t_span[1], num_points)

        model_clean = str(model).lower()
        cfg = ForceModelConfig.for_model(
            model_clean,
            cd_area_over_m=b_star,
            cr_area_over_m=cr_area_over_m,
            gravity_degree=kwargs.get('gravity_degree'),
            gravity_order=kwargs.get('gravity_order'),
            relativity=kwargs.get('enable_relativity'),
            albedo=kwargs.get('enable_albedo'),
            f107=kwargs.get('f107'),
            f107a=kwargs.get('f107a'),
            ap=kwargs.get('ap'),
        )
        if model_clean not in ('two_body', 'j2', 'j2_j3_j4'):
            cfg.drag = bool(enable_drag)
            cfg.third_body = bool(enable_third_body)
            cfg.srp = bool(enable_srp)
        self.force_config = cfg
        # ECR-MF: the gravity degree follows the orbit's radius tier (backend/ecr_mf_controller.py)
        schedule = FidelitySchedule(cfg, epsilon=kwargs.get('ecr_epsilon', 1e-10))             if kwargs.get('fidelity') == 'ecr_mf' else None
        events = _ORBIT_EVENT_FUNCTIONS + (schedule.boundary_events() if schedule else [])
        j2_v = J2_EARTH if cfg.gravity_degree >= 2 else 0.0
        j3_v = J3_EARTH if cfg.gravity_degree >= 3 else 0.0
        j4_v = J4_EARTH if cfg.gravity_degree >= 4 else 0.0
        drag_v, third_b_v, srp_v = cfg.drag, cfg.third_body, cfg.srp

        epoch_tt = float(self.epoch - Epoch.j2000())     # TAI and TT differ by a constant
        earth_rotation = FastEarthRotation(self.epoch, t_span[0], t_span[1])

        eom = lambda t, y: full_production_eom(
            t, y,
            j2=j2_v, j3=j3_v, j4=j4_v,
            enable_drag=drag_v,
            enable_third_body=third_b_v,
            enable_srp=srp_v,
            b_star=b_star,
            cr_area_over_m=cr_area_over_m,
            epoch_tt_j2000_s=epoch_tt,
            earth_rotation=earth_rotation,
            force_config=schedule.config_at(y[0:3]) if schedule else cfg
        )

        # Propagator: analytic (no integration), one of ours (exact outputs), or SciPy's
        method_key = str(method).replace(' ', '').replace('-', '').replace('_', '').upper()
        analytic_kind = ANALYTIC_METHODS.get(method_key)
        own_integrator = OWN_INTEGRATORS.get(method_key)
        event_list = None
        if analytic_kind is not None:
            state_fn = self._analytic_state_function(analytic_kind)
            r_out, v_out = state_fn(t_eval)
            sol = _AnalyticSolution(t_eval, r_out, v_out)
            apsides = bool(cartesian_to_keplerian(self.y0[:3], self.y0[3:], mu=self.mu)['e'] > 1e-3)
            event_list = analytic.analytic_events(state_fn, t_eval, self.epoch, apsides=apsides)
        elif steering is not None:
            if steering != 'covariance' or own_integrator not in ('RKF78', 'BS'):
                raise ValueError("steering='covariance' runs with method 'RKF78' or 'BS'")
            # Variational equations dPhi/dt = A(t) Phi ride along; only the orbit sets the step size
            steerer = CovarianceSteering(P0=kwargs.get('covariance0'), eta=kwargs.get('steering_eta', 0.02))
            sol = integrate(_with_variational_equations(eom), t_span, np.concatenate([self.y0, np.eye(6).ravel()]),
                            method=own_integrator, t_eval=t_eval, events=events,
                            rtol=rtol, atol=atol, n_error=6, steering=steerer)
        elif own_integrator is not None:
            fixed_step = float(kwargs.get('fixed_step') or 10.0) if own_integrator == 'RK4' else None
            sol = integrate(eom, t_span, self.y0, method=own_integrator, t_eval=t_eval,
                            events=events, rtol=rtol, atol=atol, fixed_step=fixed_step)
        else:
            solver_method = method
            if solver_method in ('PD853', 'DOP853', 'RK89'):
                solver_method = 'DOP853'
            elif solver_method in ('Radau', 'RADAU', 'RadauIIA'):
                solver_method = 'Radau'
            # Restart at each shadow edge and atmosphere-model jump (see backend/eclipse.py)
            boundaries = []
            if cfg.srp or cfg.albedo:
                boundaries += shadow_boundary_events(epoch_tt)
            if cfg.drag:
                boundaries += drag_boundary_events(
                    epoch_tt, lambda t: _earth_rotation_at(t, epoch_tt, earth_rotation)[0])
            if boundaries:
                sol = solve_ivp_segmented(eom, t_span, self.y0, boundaries,
                                          method=solver_method, t_eval=t_eval, rtol=rtol, atol=atol,
                                          events=events)
            else:
                sol = solve_ivp(eom, t_span, self.y0, method=solver_method, t_eval=t_eval, rtol=rtol, atol=atol,
                                events=events)

        times = sol.t
        pos = sol.y[0:3].T
        vel = sol.y[3:6].T

        n_pts = len(times)
        r_mags = np.linalg.norm(pos, axis=1)
        v_mags = np.linalg.norm(vel, axis=1)

        # Earth orientation for the whole output grid, built once
        orientation = EarthOrientation(self.epoch, times)
        lat_arr, lon_arr, height_m = gcrf_to_geodetic(pos, self.epoch, orientation=orientation)
        alt_km = height_m / 1000.0

        a_arr = np.zeros(n_pts)
        e_arr = np.zeros(n_pts)
        inc_arr = np.zeros(n_pts)
        raan_arr = np.zeros(n_pts)
        argp_arr = np.zeros(n_pts)
        nu_arr = np.zeros(n_pts)
        energy_arr = np.zeros(n_pts)
        h_arr = np.zeros(n_pts)

        for i in range(n_pts):
            elem = cartesian_to_keplerian(pos[i], vel[i], mu=self.mu)
            a_arr[i] = elem['a']
            e_arr[i] = elem['e']
            inc_arr[i] = math.degrees(elem['inc'])
            raan_arr[i] = math.degrees(elem['Omega'])
            argp_arr[i] = math.degrees(elem['omega'])
            nu_arr[i] = math.degrees(elem['nu'])
            energy_arr[i] = elem['energy']
            h_arr[i] = elem['h_mag']

        energy_err = np.abs((energy_arr - self.initial_energy) / self.initial_energy)
        h_err = np.abs((h_arr - self.initial_h) / self.initial_h)

        # Full time-series Force Breakdown Diagnostics
        a_c = np.zeros(n_pts)
        a_j2 = np.zeros(n_pts)
        a_j3 = np.zeros(n_pts)
        a_j4 = np.zeros(n_pts)
        a_tess = np.zeros(n_pts)
        a_sun = np.zeros(n_pts)
        a_moon = np.zeros(n_pts)
        a_drag = np.zeros(n_pts)
        a_srp = np.zeros(n_pts)
        a_tot = np.zeros(n_pts)
        for i in range(n_pts):
            d = compute_acceleration_components(
                np.concatenate([pos[i], vel[i]]), float(times[i]),
                force_config=cfg, epoch_tt_j2000_s=epoch_tt, earth_rotation=earth_rotation
            )
            a_c[i] = d["a_central_mag"]
            a_j2[i] = d["a_j2_mag"]
            a_j3[i] = d["a_j3_mag"]
            a_j4[i] = d["a_j4_mag"]
            a_tess[i] = d["a_tesseral_mag"]
            a_sun[i] = d["a_sun_mag"]
            a_moon[i] = d["a_moon_mag"]
            a_drag[i] = d["a_drag_mag"]
            a_srp[i] = d["a_srp_mag"]
            a_tot[i] = d["a_total_mag"]
        force_diag = {
            'a_central_ms2': a_c.tolist(),
            'a_j2_ms2': a_j2.tolist(),
            'a_j3_ms2': a_j3.tolist(),
            'a_j4_ms2': a_j4.tolist(),
            'a_tesseral_ms2': a_tess.tolist(),
            'a_sun_ms2': a_sun.tolist(),
            'a_moon_ms2': a_moon.tolist(),
            'a_drag_ms2': a_drag.tolist(),
            'a_srp_ms2': a_srp.tolist(),
            'a_total_ms2': a_tot.tolist()
        }

        r_itrf, v_itrf = transform_state(pos, vel, self.epoch, "GCRF", "ITRF", orientation=orientation)

        return {
            'times': times,
            'time_hours': times / 3600.0,
            'position_m': pos,
            'velocity_ms': vel,
            'altitude_km': alt_km,
            'velocity_kms': v_mags / 1000.0,
            'semi_major_axis_km': a_arr / 1000.0,
            'eccentricity': e_arr,
            'inclination_deg': inc_arr,
            'raan_deg': raan_arr,
            'arg_perigee_deg': argp_arr,
            'true_anomaly_deg': nu_arr,
            'energy_joules_kg': energy_arr,
            'energy_fractional_error': energy_err,
            'h_fractional_error': h_err,
            'latitude_deg': lat_arr,
            'longitude_deg': lon_arr,
            'epoch_utc': self.epoch.iso('UTC'),
            'utc_iso': [(self.epoch + float(t)).iso('UTC') for t in times],
            'frame': 'GCRF',
            'eop_in_range': bool(orientation.eop_in_range),
            'epoch': {scale.lower(): self.epoch.iso(scale, 6) for scale in ('UTC', 'TAI', 'TT', 'TDB', 'UT1')},
            'events': event_list if event_list is not None else orbit_events(sol, self.epoch, apsides=bool(e_arr[0] > 1e-3)),
            'sun_direction_eci': sun_directions(times, epoch_tt),
            'position_itrf_m': r_itrf,
            'velocity_itrf_ms': v_itrf,
            'model': model_clean,
            'method': method,
            'force_diagnostics': force_diag,
            'stm': sol.y[6:42].T.reshape(-1, 6, 6) if steering is not None else None,
            'steps': steerer.record() if steering is not None else None,
            'ecr_mf': schedule.report(sol.t_events[len(_ORBIT_EVENT_FUNCTIONS):]) if schedule else None,
        }

# Aliases for backwards compatibility across tests and legacy scripts
TrajectoryEngine = ThirdReviewEngine
FirstReviewEngine = ThirdReviewEngine
SecondReviewEngine = ThirdReviewEngine
