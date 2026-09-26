import os
import sys
import ctypes
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
        
        # Configure compute_keplerian_to_cartesian
        _cpp_kernel.compute_keplerian_to_cartesian.argtypes = [
            ctypes.c_double, ctypes.c_double, ctypes.c_double,
            ctypes.c_double, ctypes.c_double, ctypes.c_double,
            ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_double)
        ]
        _cpp_kernel.compute_keplerian_to_cartesian.restype = None

        # Configure compute_total_acceleration
        _cpp_kernel.compute_total_acceleration.argtypes = [
            ctypes.c_double, ctypes.c_double, ctypes.c_double,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_double)
        ]
        _cpp_kernel.compute_total_acceleration.restype = None
        
        # Configure secular drifts
        _cpp_kernel.compute_j2_regression_rate_rad_s.argtypes = [ctypes.c_double, ctypes.c_double, ctypes.c_double]
        _cpp_kernel.compute_j2_regression_rate_rad_s.restype = ctypes.c_double
        
        _cpp_kernel.compute_j2_apsidal_precession_rad_s.argtypes = [ctypes.c_double, ctypes.c_double, ctypes.c_double]
        _cpp_kernel.compute_j2_apsidal_precession_rad_s.restype = ctypes.c_double
    except Exception as _err:
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
# ASTRODYNAMICAL CONSTANTS (WGS-84 / IERS Standard)
# ==============================================================================
MU_EARTH = 3.986004418e14       # Earth's gravitational parameter (m^3/s^2)
R_EARTH = 6371000.0             # Mean Earth radius (m)
J2_EARTH = 1.08262668e-3        # Earth's J2 zonal harmonic
OMEGA_EARTH = 7.2921159e-5      # Earth angular rotation rate (rad/s)


def solve_kepler_equation(M, e, tol=1e-12, max_iter=100):
    """
    Solves Kepler's equation M = E - e*sin(E) for Eccentric Anomaly (E)
    using the Newton-Raphson iteration.
    """
    E = M if e < 0.8 else np.pi
    for _ in range(max_iter):
        f = E - e * np.sin(E) - M
        f_prime = 1.0 - e * np.cos(E)
        dE = -f / f_prime
        E += dE
        if abs(dE) < tol:
            return E
    return E


def true_anomaly_from_eccentric(E, e):
    """Computes True Anomaly (nu) from Eccentric Anomaly (E) and eccentricity (e)."""
    sin_nu = (np.sqrt(1.0 - e**2) * np.sin(E)) / (1.0 - e * np.cos(E))
    cos_nu = (np.cos(E) - e) / (1.0 - e * np.cos(E))
    return np.arctan2(sin_nu, cos_nu)


def eccentric_anomaly_from_true(nu, e):
    """Computes Eccentric Anomaly (E) from True Anomaly (nu) and eccentricity (e)."""
    sin_E = (np.sqrt(1.0 - e**2) * np.sin(nu)) / (1.0 + e * np.cos(nu))
    cos_E = (e + np.cos(nu)) / (1.0 + e * np.cos(nu))
    return np.arctan2(sin_E, cos_E)


def keplerian_to_cartesian(a, e, inc, Omega, omega, nu, mu=MU_EARTH):
    """
    Converts Classical Keplerian Orbital Elements to Cartesian ECI state vectors.
    Accelerated via Layer 1 Compiled C++17 SIMD Kernel when available.
    """
    if _cpp_kernel is not None:
        try:
            r_arr = (ctypes.c_double * 3)()
            v_arr = (ctypes.c_double * 3)()
            _cpp_kernel.compute_keplerian_to_cartesian(
                ctypes.c_double(a), ctypes.c_double(e), ctypes.c_double(inc),
                ctypes.c_double(Omega), ctypes.c_double(omega), ctypes.c_double(nu),
                r_arr, v_arr
            )
            return np.array([r_arr[0], r_arr[1], r_arr[2]], dtype=np.float64), np.array([v_arr[0], v_arr[1], v_arr[2]], dtype=np.float64)
        except Exception:
            pass

    p = a * (1.0 - e**2)
    r_mag = p / (1.0 + e * np.cos(nu))
    
    # Perifocal State (PQW)
    r_pqw = np.array([
        r_mag * np.cos(nu),
        r_mag * np.sin(nu),
        0.0
    ])
    
    v_pqw = np.array([
        -np.sqrt(mu / p) * np.sin(nu),
         np.sqrt(mu / p) * (e + np.cos(nu)),
         0.0
    ])
    
    # Rotation PQW -> ECI
    R_z_Omega = np.array([
        [np.cos(Omega), -np.sin(Omega), 0.0],
        [np.sin(Omega),  np.cos(Omega), 0.0],
        [0.0,            0.0,           1.0]
    ])
    R_x_inc = np.array([
        [1.0, 0.0,          0.0],
        [0.0, np.cos(inc), -np.sin(inc)],
        [0.0, np.sin(inc),  np.cos(inc)]
    ])
    R_z_omega = np.array([
        [np.cos(omega), -np.sin(omega), 0.0],
        [np.sin(omega),  np.cos(omega), 0.0],
        [0.0,            0.0,           1.0]
    ])
    
    Q_ECI_PQW = R_z_Omega @ R_x_inc @ R_z_omega
    r_eci = Q_ECI_PQW @ r_pqw
    v_eci = Q_ECI_PQW @ v_pqw
    
    return r_eci, v_eci


def cartesian_to_keplerian(r_vec, v_vec, mu=MU_EARTH):
    """
    Converts Cartesian ECI state vectors to Classical Keplerian Orbital Elements.
    Accelerated via Layer 1 Compiled C++17 SIMD Kernel when available.
    """
    r_vec = np.array(r_vec, dtype=np.float64)
    v_vec = np.array(v_vec, dtype=np.float64)
    
    if _cpp_kernel is not None:
        try:
            out_arr = (ctypes.c_double * 8)()
            _cpp_kernel.compute_cartesian_to_keplerian(
                ctypes.c_double(r_vec[0]), ctypes.c_double(r_vec[1]), ctypes.c_double(r_vec[2]),
                ctypes.c_double(v_vec[0]), ctypes.c_double(v_vec[1]), ctypes.c_double(v_vec[2]),
                out_arr
            )
            h_vec = np.cross(r_vec, v_vec)
            return {
                'a': out_arr[0],
                'e': out_arr[1],
                'inc': out_arr[2],
                'Omega': out_arr[3],
                'omega': out_arr[4],
                'nu': out_arr[5],
                'energy': out_arr[6],
                'h_mag': float(np.linalg.norm(h_vec)),
                'period': out_arr[7]
            }
        except Exception:
            pass

    r = np.linalg.norm(r_vec)
    v = np.linalg.norm(v_vec)
    
    h_vec = np.cross(r_vec, v_vec)
    h = np.linalg.norm(h_vec)
    
    k_hat = np.array([0.0, 0.0, 1.0])
    n_vec = np.cross(k_hat, h_vec)
    n = np.linalg.norm(n_vec)
    
    e_vec = (1.0 / mu) * ((v**2 - mu / r) * r_vec - np.dot(r_vec, v_vec) * v_vec)
    e = np.linalg.norm(e_vec)
    
    energy = (v**2 / 2.0) - (mu / r)
    a = -mu / (2.0 * energy) if abs(1.0 - e) > 1e-12 else np.inf
    period = 2.0 * np.pi * np.sqrt(a**3 / mu) if a > 0 else 0.0
    
    inc = np.arccos(np.clip(h_vec[2] / h, -1.0, 1.0))
    
    if n > 1e-12:
        Omega = np.arccos(np.clip(n_vec[0] / n, -1.0, 1.0))
        if n_vec[1] < 0:
            Omega = 2.0 * np.pi - Omega
    else:
        Omega = 0.0
        
    if n > 1e-12 and e > 1e-12:
        omega = np.arccos(np.clip(np.dot(n_vec, e_vec) / (n * e), -1.0, 1.0))
        if e_vec[2] < 0:
            omega = 2.0 * np.pi - omega
    else:
        omega = 0.0
        
    if e > 1e-12:
        nu = np.arccos(np.clip(np.dot(e_vec, r_vec) / (e * r), -1.0, 1.0))
        if np.dot(r_vec, v_vec) < 0:
            nu = 2.0 * np.pi - nu
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
    """
    Converts ECI position vector to ECEF Latitude, Longitude, and Altitude.
    """
    theta_gst = (omega_e * t_seconds) % (2.0 * np.pi)
    cos_t = np.cos(theta_gst)
    sin_t = np.sin(theta_gst)
    
    x_ecef =  cos_t * r_eci[0] + sin_t * r_eci[1]
    y_ecef = -sin_t * r_eci[0] + cos_t * r_eci[1]
    z_ecef = r_eci[2]
    
    r_mag = np.sqrt(x_ecef**2 + y_ecef**2 + z_ecef**2)
    alt_km = (r_mag - R_EARTH) / 1000.0
    
    lat_rad = np.arcsin(np.clip(z_ecef / r_mag, -1.0, 1.0))
    lon_rad = np.arctan2(y_ecef, x_ecef)
    
    return np.degrees(lat_rad), np.degrees(lon_rad), alt_km


def calculate_theoretical_j2_drifts(a, e, inc, num_orbits, mu=MU_EARTH, r_e=R_EARTH, j2=J2_EARTH):
    """
    Calculates first-order theoretical secular precession rates from Lagrange Planetary Equations.
    Accelerated via Layer 1 Compiled C++17 Kernel when available.
    """
    if _cpp_kernel is not None:
        try:
            dOmega_dt_rad_s = _cpp_kernel.compute_j2_regression_rate_rad_s(ctypes.c_double(a), ctypes.c_double(e), ctypes.c_double(inc))
            domega_dt_rad_s = _cpp_kernel.compute_j2_apsidal_precession_rad_s(ctypes.c_double(a), ctypes.c_double(e), ctypes.c_double(inc))
            T = 2.0 * np.pi * np.sqrt(a**3 / mu)
            return {
                'dOmega_dt_deg_day': np.degrees(dOmega_dt_rad_s) * 86400.0,
                'dOmega_total_deg': np.degrees(dOmega_dt_rad_s * (num_orbits * T)),
                'domega_dt_deg_day': np.degrees(domega_dt_rad_s) * 86400.0,
                'domega_total_deg': np.degrees(domega_dt_rad_s * (num_orbits * T)),
                'period_hours': T / 3600.0
            }
        except Exception:
            pass

    n = np.sqrt(mu / a**3)
    p = a * (1.0 - e**2)
    T = 2.0 * np.pi / n
    
    # Nodal Precession dOmega/dt (rad/s)
    dOmega_dt_rad_s = -1.5 * j2 * ((r_e / p)**2) * n * np.cos(inc)
    dOmega_dt_deg_day = np.degrees(dOmega_dt_rad_s) * 86400.0
    dOmega_total_deg = np.degrees(dOmega_dt_rad_s * (num_orbits * T))
    
    # Apsidal Precession domega/dt (rad/s)
    domega_dt_rad_s = 0.75 * j2 * ((r_e / p)**2) * n * (5.0 * np.cos(inc)**2 - 1.0)
    domega_dt_deg_day = np.degrees(domega_dt_rad_s) * 86400.0
    domega_total_deg = np.degrees(domega_dt_rad_s * (num_orbits * T))
    
    return {
        'dOmega_dt_deg_day': dOmega_dt_deg_day,
        'dOmega_total_deg': dOmega_total_deg,
        'domega_dt_deg_day': domega_dt_deg_day,
        'domega_total_deg': domega_total_deg,
        'period_hours': T / 3600.0
    }


def two_body_eom(t, state, mu=MU_EARTH):
    """Pure Two-Body Point-Mass Equations of Motion (Layer 1 C++ Accelerated)."""
    x, y, z, vx, vy, vz = state
    if _cpp_kernel is not None:
        try:
            acc = (ctypes.c_double * 3)()
            _cpp_kernel.compute_total_acceleration(
                ctypes.c_double(x), ctypes.c_double(y), ctypes.c_double(z),
                ctypes.c_int(0), acc
            )
            return [vx, vy, vz, acc[0], acc[1], acc[2]]
        except Exception:
            pass
    r = np.sqrt(x**2 + y**2 + z**2)
    ax = -(mu / r**3) * x
    ay = -(mu / r**3) * y
    az = -(mu / r**3) * z
    return [vx, vy, vz, ax, ay, az]


def j2_perturbed_eom(t, state, mu=MU_EARTH, r_e=R_EARTH, j2=J2_EARTH):
    """J2 Geopotential Zonal Harmonic Equations of Motion (Layer 1 C++ Accelerated)."""
    x, y, z, vx, vy, vz = state
    if _cpp_kernel is not None:
        try:
            acc = (ctypes.c_double * 3)()
            _cpp_kernel.compute_total_acceleration(
                ctypes.c_double(x), ctypes.c_double(y), ctypes.c_double(z),
                ctypes.c_int(1), acc
            )
            return [vx, vy, vz, acc[0], acc[1], acc[2]]
        except Exception:
            pass
    r = np.sqrt(x**2 + y**2 + z**2)
    r2 = r**2
    z2 = z**2
    r_ratio2 = (r_e / r)**2
    
    # Base Central Gravity
    ax_0 = -(mu / r**3) * x
    ay_0 = -(mu / r**3) * y
    az_0 = -(mu / r**3) * z
    
    # J2 Oblateness Accelerations
    factor_j2 = (1.5 * j2 * mu / r2) * r_ratio2
    ax_j2 = -factor_j2 * (x / r) * (1.0 - 5.0 * (z2 / r2))
    ay_j2 = -factor_j2 * (y / r) * (1.0 - 5.0 * (z2 / r2))
    az_j2 = -factor_j2 * (z / r) * (3.0 - 5.0 * (z2 / r2))
    
    return [vx, vy, vz, ax_0 + ax_j2, ay_0 + ay_j2, az_0 + az_j2]


class TrajectoryEngine:
    """
    High-Fidelity Trajectory Propagation & Analysis Engine.
    """
    def __init__(self, initial_state, mu=MU_EARTH, r_e=R_EARTH, j2=J2_EARTH):
        self.y0 = np.array(initial_state, dtype=np.float64)
        self.mu = mu
        self.r_e = r_e
        self.j2 = j2
        
        elem = cartesian_to_keplerian(self.y0[0:3], self.y0[3:6], mu=self.mu)
        self.initial_elements = elem
        self.initial_energy = elem['energy']
        self.initial_h = elem['h_mag']
        
    def propagate(self, t_span, num_points=3000, model='two_body', method='Radau', rtol=1e-11, atol=1e-11):
        """
        Numerically integrates trajectory with high-precision Radau-IIA or RK45 solvers.
        """
        t_eval = np.linspace(t_span[0], t_span[1], num_points)
        
        if model.lower() == 'two_body':
            eom_func = lambda t, y: two_body_eom(t, y, mu=self.mu)
        elif model.lower() == 'j2':
            eom_func = lambda t, y: j2_perturbed_eom(t, y, mu=self.mu, r_e=self.r_e, j2=self.j2)
        else:
            raise ValueError(f"Unknown model '{model}'. Choose 'two_body' or 'j2'.")
            
        sol = solve_ivp(eom_func, t_span, self.y0, method=method, t_eval=t_eval, rtol=rtol, atol=atol)
        
        times = sol.t
        pos = sol.y[0:3].T
        vel = sol.y[3:6].T
        
        r_mags = np.linalg.norm(pos, axis=1)
        v_mags = np.linalg.norm(vel, axis=1)
        alt_km = (r_mags - self.r_e) / 1000.0
        
        n_pts = len(times)
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
            inc_arr[i] = np.degrees(elem['inc'])
            raan_arr[i] = np.degrees(elem['Omega'])
            argp_arr[i] = np.degrees(elem['omega'])
            nu_arr[i] = np.degrees(elem['nu'])
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
            'model': model,
            'method': method
        }
