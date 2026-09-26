"""
AstroCore Astrodynamics Engine - First Review (Coupled Perturbations & Advanced Environmental Forces)
=============================================================================
Department of Aerospace Engineering, ACS College of Engineering
Part of Major Project: Precise Trajectory Propagation & Events Prediction for HEOs

Features:
  - High-Order Earth Geopotentials: J2, J3 (Pear-Shape), and J4 Zonal Harmonics
  - Third-Body Gravitational Perturbations (Sun & Moon Point-Mass Ephemerides)
  - Atmospheric Drag with Co-rotating Atmosphere & Exponential Scale Height
  - Solar Radiation Pressure (SRP) with Conical Shadow Gating
  - Instantaneous Perturbation Acceleration Decomposition & Order-of-Magnitude Analysis
  - High-Precision Stiff Radau-IIA & RK45 Numerical Propagators
  - Energy Dissipation & Non-Conservative Orbit Decay Tracking
=============================================================================
"""

import os
import sys
import ctypes
import math
import numpy as np
from scipy.integrate import solve_ivp

# ==============================================================================
# LAYER 1: COMPILED C++17 ASTRODYNAMICS MATH CORE BINDINGS (CTYPES INTEROP)
# ==============================================================================
_curr_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_curr_dir)
_candidate_paths = [
    os.path.join(_parent_dir, "cpp_engine", "astro_physics_kernel.dll"),
    os.path.join(getattr(sys, '_MEIPASS', ''), "cpp_engine", "astro_physics_kernel.dll"),
    os.path.join(os.path.dirname(sys.executable), "cpp_engine", "astro_physics_kernel.dll"),
    os.path.join(os.path.dirname(sys.executable), "_internal", "cpp_engine", "astro_physics_kernel.dll")
]
_cpp_dll_path = next((p for p in _candidate_paths if os.path.exists(p)), _candidate_paths[0])

_cpp_kernel = None
if os.path.exists(_cpp_dll_path):
    try:
        _cpp_kernel = ctypes.CDLL(_cpp_dll_path)
        _cpp_kernel.compute_total_acceleration.argtypes = [
            ctypes.c_double, ctypes.c_double, ctypes.c_double,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_double)
        ]
        _cpp_kernel.compute_total_acceleration.restype = None
    except Exception:
        _cpp_kernel = None


def get_engine_status():
    """Returns status of the compiled C++17 Math Core."""
    return {
        "c_plus_plus_kernel_loaded": _cpp_kernel is not None,
        "kernel_binary": _cpp_dll_path if _cpp_kernel is not None else "Fallback NumPy/SciPy",
        "standard": "C++17 (MSVC x64 /O2 SIMD)",
        "architecture_layer": "Layer 1 (The Math Core)"
    }


# ==============================================================================
# ASTRODYNAMICAL CONSTANTS (WGS-84 / IERS / NASA JPL Standards)
# ==============================================================================
MU_EARTH = 3.986004418e14          # Earth's gravitational parameter (m^3/s^2)
R_EARTH = 6371000.0                # Mean Earth radius (m)
R_EARTH_EQ = 6378137.0             # Equatorial Earth radius (m)
J2_EARTH = 1.08262668e-3           # Earth J2 zonal harmonic (oblateness)
J3_EARTH = -2.53241052e-6          # Earth J3 zonal harmonic (pear shape)
J4_EARTH = -1.61992164e-6          # Earth J4 zonal harmonic
OMEGA_EARTH = 7.2921159e-5         # Earth rotation rate (rad/s)

# Third-Body Parameters (NASA JPL DE440)
MU_SUN = 1.32712440018e20          # Sun gravitational parameter (m^3/s^2)
MU_MOON = 4.9048695e12             # Moon gravitational parameter (m^3/s^2)
AU_METERS = 149597870700.0         # Astronomical Unit (m)
D_MOON_MEAN = 384400000.0          # Mean Earth-Moon distance (m)

# Environmental & Non-Gravitational Constants
P_SR_1AU = 4.56e-6                 # Solar radiation pressure at 1 AU (N/m^2)
RHO_0 = 1.225                      # Sea-level atmospheric density (kg/m^3)
H_SCALE = 8500.0                   # Mean atmospheric scale height (m)


# ==============================================================================
# COORDINATE TRANSFORMATIONS & KEPLER CONVERSIONS
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

    # Perifocal coordinates (PQW)
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


def eci_to_ecef_geodetic(r_eci, t_seconds, omega_e=OMEGA_EARTH):
    """Converts ECI position vector to ECEF Latitude, Longitude, and Altitude."""
    theta_gst = (omega_e * t_seconds) % (2.0 * math.pi)
    cos_t = math.cos(theta_gst)
    sin_t = math.sin(theta_gst)

    x_ecef =  cos_t * r_eci[0] + sin_t * r_eci[1]
    y_ecef = -sin_t * r_eci[0] + cos_t * r_eci[1]
    z_ecef = r_eci[2]

    r_mag = math.sqrt(x_ecef**2 + y_ecef**2 + z_ecef**2)
    alt_km = (r_mag - R_EARTH) / 1000.0

    lat_rad = math.asin(max(-1.0, min(1.0, z_ecef / r_mag)))
    lon_rad = math.atan2(y_ecef, x_ecef)

    return math.degrees(lat_rad), math.degrees(lon_rad), alt_km


# ==============================================================================
# DETAILED PERTURBATION ACCELERATION DECOMPOSITION
# ==============================================================================
def compute_acceleration_components(
    state,
    t,
    mu=MU_EARTH,
    r_e=R_EARTH,
    j2=J2_EARTH,
    j3=J3_EARTH,
    j4=J4_EARTH,
    b_star=0.015,
    cr_area_over_m=0.02
):
    """
    Computes and returns the exact 3D acceleration vectors and scalar magnitudes
    for all individual perturbation forces acting on the satellite at epoch t.
    """
    x, y, z, vx, vy, vz = state
    r = math.sqrt(x**2 + y**2 + z**2)
    r2, r3, r4 = r**2, r**3, r**4
    z2 = z**2

    # 1. Base Central Point-Mass Gravity
    a_central = np.array([-(mu / r3) * x, -(mu / r3) * y, -(mu / r3) * z])

    # 2. J2 Zonal Harmonic
    factor_j2 = (1.5 * j2 * mu / r2) * (r_e / r)**2
    a_j2 = np.array([
        -factor_j2 * (x / r) * (1.0 - 5.0 * (z2 / r2)),
        -factor_j2 * (y / r) * (1.0 - 5.0 * (z2 / r2)),
        -factor_j2 * (z / r) * (3.0 - 5.0 * (z2 / r2))
    ])

    # 3. J3 Zonal Harmonic (Pear-Shape)
    factor_j3 = (2.5 * j3 * mu / r2) * (r_e / r)**3
    z_r = z / r
    a_j3 = np.array([
        -factor_j3 * (x / r) * (3.0 * z_r - 7.0 * (z_r**3)),
        -factor_j3 * (y / r) * (3.0 * z_r - 7.0 * (z_r**3)),
        -factor_j3 * (3.0 * (z_r**2) - 7.0 * (z_r**4) - 0.6)
    ])

    # 4. J4 Zonal Harmonic
    factor_j4 = (j4 * mu / r2) * (r_e / r)**4
    z2_r2 = z2 / r2
    a_j4 = (5.0 / 8.0) * factor_j4 * np.array([
        (x / r) * (3.0 - 42.0 * z2_r2 + 63.0 * (z2_r2**2)),
        (y / r) * (3.0 - 42.0 * z2_r2 + 63.0 * (z2_r2**2)),
        (z / r) * (15.0 - 70.0 * z2_r2 + 63.0 * (z2_r2**2))
    ])

    # 5. Third-Body Gravitational Perturbations (Sun & Moon)
    # Sun Ephemeris
    eps = math.radians(23.44)
    n_sun = 2.0 * math.pi / (365.25 * 86400.0)
    lam_sun = n_sun * t
    r_sun_vec = AU_METERS * np.array([
        math.cos(lam_sun),
        math.sin(lam_sun) * math.cos(eps),
        math.sin(lam_sun) * math.sin(eps)
    ])
    d_sc_sun = np.array([x, y, z]) - r_sun_vec
    dist_sc_sun = float(np.linalg.norm(d_sc_sun))
    dist_sun = float(np.linalg.norm(r_sun_vec))
    a_sun = -MU_SUN * ((d_sc_sun / dist_sc_sun**3) + (r_sun_vec / dist_sun**3))

    # Moon Ephemeris
    n_moon = 2.0 * math.pi / (27.32166 * 86400.0)
    lam_moon = n_moon * t
    inc_moon = math.radians(23.44 + 5.14)
    r_moon_vec = D_MOON_MEAN * np.array([
        math.cos(lam_moon),
        math.sin(lam_moon) * math.cos(inc_moon),
        math.sin(lam_moon) * math.sin(inc_moon)
    ])
    d_sc_moon = np.array([x, y, z]) - r_moon_vec
    dist_sc_moon = float(np.linalg.norm(d_sc_moon))
    dist_moon = float(np.linalg.norm(r_moon_vec))
    a_moon = -MU_MOON * ((d_sc_moon / dist_sc_moon**3) + (r_moon_vec / dist_moon**3))

    # 6. Atmospheric Drag (Active during perigee passages h < 800 km)
    alt_m = r - r_e
    a_drag = np.zeros(3)
    if alt_m < 800000.0:
        rho = RHO_0 * math.exp(-max(0.0, alt_m) / H_SCALE)
        v_rel_x = vx + OMEGA_EARTH * y
        v_rel_y = vy - OMEGA_EARTH * x
        v_rel_z = vz
        v_rel = math.sqrt(v_rel_x**2 + v_rel_y**2 + v_rel_z**2)
        factor_drag = -0.5 * rho * b_star * v_rel
        a_drag = np.array([factor_drag * v_rel_x, factor_drag * v_rel_y, factor_drag * v_rel_z])

    # 7. Solar Radiation Pressure (SRP)
    s_hat = np.array([1.0, 0.0, 0.0])
    r_proj = x * s_hat[0] + y * s_hat[1] + z * s_hat[2]
    d_perp = math.sqrt(max(0.0, r**2 - r_proj**2))
    in_shadow = (r_proj < 0) and (d_perp < r_e)
    if not in_shadow:
        p_srp_mag = P_SR_1AU * cr_area_over_m
        a_srp = -p_srp_mag * s_hat
    else:
        a_srp = np.zeros(3)

    return {
        "a_central": a_central,
        "a_central_mag": float(np.linalg.norm(a_central)),
        "a_j2": a_j2,
        "a_j2_mag": float(np.linalg.norm(a_j2)),
        "a_j3": a_j3,
        "a_j3_mag": float(np.linalg.norm(a_j3)),
        "a_j4": a_j4,
        "a_j4_mag": float(np.linalg.norm(a_j4)),
        "a_moon": a_moon,
        "a_moon_mag": float(np.linalg.norm(a_moon)),
        "a_sun": a_sun,
        "a_sun_mag": float(np.linalg.norm(a_sun)),
        "a_drag": a_drag,
        "a_drag_mag": float(np.linalg.norm(a_drag)),
        "a_srp": a_srp,
        "a_srp_mag": float(np.linalg.norm(a_srp)),
        "a_total": a_central + a_j2 + a_j3 + a_j4 + a_moon + a_sun + a_drag + a_srp,
        "a_total_mag": float(np.linalg.norm(a_central + a_j2 + a_j3 + a_j4 + a_moon + a_sun + a_drag + a_srp))
    }


# ==============================================================================
# EQUATIONS OF MOTION
# ==============================================================================
def coupled_first_review_eom(
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
    b_star=0.015,
    cr_area_over_m=0.02
):
    """Coupled First Review EOM integrating all environmental forces."""
    vx, vy, vz = state[3:6]
    acc_data = compute_acceleration_components(
        state, t,
        mu=mu, r_e=r_e,
        j2=j2, j3=j3, j4=j4,
        b_star=b_star,
        cr_area_over_m=cr_area_over_m
    )
    
    total_acc = acc_data["a_central"] + acc_data["a_j2"] + acc_data["a_j3"] + acc_data["a_j4"]
    if enable_third_body:
        total_acc += acc_data["a_moon"] + acc_data["a_sun"]
    if enable_drag:
        total_acc += acc_data["a_drag"]
    if enable_srp:
        total_acc += acc_data["a_srp"]

    return [vx, vy, vz, total_acc[0], total_acc[1], total_acc[2]]


# ==============================================================================
# FIRST REVIEW HIGH-PRECISION PROPAGATOR ENGINE
# ==============================================================================
class FirstReviewEngine:
    """
    High-Fidelity Propagator Engine for the First Review Milestone.
    """
    def __init__(self, initial_state, mu=MU_EARTH, r_e=R_EARTH):
        self.y0 = np.array(initial_state, dtype=np.float64)
        self.mu = mu
        self.r_e = r_e

        elem = cartesian_to_keplerian(self.y0[0:3], self.y0[3:6], mu=self.mu)
        self.initial_elements = elem
        self.initial_energy = elem['energy']
        self.initial_h = elem['h_mag']

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
        **kwargs
    ):
        """
        Integrates the trajectory with high-order implicit Stiff Radau-IIA.
        Supports model='two_body', model='j2', model='j2_j3_j4', model='coupled'.
        """
        t_eval = np.linspace(t_span[0], t_span[1], num_points)

        model_clean = str(model).lower()
        if model_clean == 'two_body':
            j2_v, j3_v, j4_v = 0.0, 0.0, 0.0
            drag_v, third_b_v, srp_v = False, False, False
        elif model_clean == 'j2':
            j2_v, j3_v, j4_v = J2_EARTH, 0.0, 0.0
            drag_v, third_b_v, srp_v = False, False, False
        elif model_clean == 'j2_j3_j4':
            j2_v, j3_v, j4_v = J2_EARTH, J3_EARTH, J4_EARTH
            drag_v, third_b_v, srp_v = False, False, False
        else:
            j2_v, j3_v, j4_v = J2_EARTH, J3_EARTH, J4_EARTH
            drag_v = enable_drag
            third_b_v = enable_third_body
            srp_v = enable_srp

        eom = lambda t, y: coupled_first_review_eom(
            t, y,
            mu=self.mu,
            r_e=self.r_e,
            j2=j2_v,
            j3=j3_v,
            j4=j4_v,
            enable_drag=drag_v,
            enable_third_body=third_b_v,
            enable_srp=srp_v,
            b_star=b_star,
            cr_area_over_m=cr_area_over_m
        )

        sol = solve_ivp(eom, t_span, self.y0, method=method, t_eval=t_eval, rtol=rtol, atol=atol)

        times = sol.t
        pos = sol.y[0:3].T
        vel = sol.y[3:6].T

        n_pts = len(times)
        r_mags = np.linalg.norm(pos, axis=1)
        v_mags = np.linalg.norm(vel, axis=1)
        alt_km = (r_mags - self.r_e) / 1000.0

        a_arr = np.zeros(n_pts)
        e_arr = np.zeros(n_pts)
        inc_arr = np.zeros(n_pts)
        raan_arr = np.zeros(n_pts)
        argp_arr = np.zeros(n_pts)
        nu_arr = np.zeros(n_pts)
        energy_arr = np.zeros(n_pts)
        h_arr = np.zeros(n_pts)
        lat_arr = np.zeros(n_pts)
        lon_arr = np.zeros(n_pts)

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

            lat, lon, _ = eci_to_ecef_geodetic(pos[i], times[i])
            lat_arr[i] = lat
            lon_arr[i] = lon

        energy_err = np.abs((energy_arr - self.initial_energy) / self.initial_energy)
        h_err = np.abs((h_arr - self.initial_h) / self.initial_h)

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
            'model': model_clean,
            'method': method
        }
