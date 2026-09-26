"""
J2 Secular Drift Model - Zeroeth Review Analytical Baseline
Department of Aerospace Engineering, ACS College of Engineering
"""

import math
import numpy as np
from .kepler_solver import MU_EARTH, R_EARTH, solve_kepler, true_anomaly_from_E, elements_to_eci

J2 = 1.08262668e-3

def compute_j2_rates(a, e, inc_rad):
    """
    Compute first-order secular rates for RAAN, argument of perigee, and mean anomaly due to J2 oblateness.
    Returns:
        raan_dot (rad/s), argp_dot (rad/s), M_dot_correction (rad/s)
    """
    n0 = math.sqrt(MU_EARTH / (a**3))
    p = a * (1.0 - e**2)
    gamma = 1.5 * J2 * ((R_EARTH / p)**2) * n0
    
    # RAAN precession rate (nodal regression)
    raan_dot = -gamma * math.cos(inc_rad)
    
    # Argument of perigee rotation rate
    argp_dot = 0.5 * gamma * (5.0 * (math.cos(inc_rad)**2) - 1.0)
    
    # Mean anomaly secular rate
    M_dot = n0 * (1.0 + 0.75 * J2 * ((R_EARTH / p)**2) * math.sqrt(1.0 - e**2) * (3.0 * (math.cos(inc_rad)**2) - 1.0))
    
    return raan_dot, argp_dot, M_dot

def propagate_with_j2_secular(a, e, inc_deg, raan0_deg, argp0_deg, nu0_deg, duration_sec, num_points=300):
    """Propagate orbit applying analytic J2 secular drift rates."""
    inc = math.radians(inc_deg)
    raan0 = math.radians(raan0_deg)
    argp0 = math.radians(argp0_deg)
    nu0 = math.radians(nu0_deg)
    
    raan_dot, argp_dot, M_dot = compute_j2_rates(a, e, inc)
    
    E0 = 2.0 * math.atan(math.sqrt((1.0 - e) / (1.0 + e)) * math.tan(nu0 / 2.0))
    M0 = E0 - e * math.sin(E0)
    
    times = np.linspace(0, duration_sec, num_points)
    trajectory = []
    
    for t in times:
        M = M0 + M_dot * t
        raan = (raan0 + raan_dot * t) % (2.0 * math.pi)
        argp = (argp0 + argp_dot * t) % (2.0 * math.pi)
        
        E = solve_kepler(M, e)
        nu = true_anomaly_from_E(E, e)
        r_eci, v_eci = elements_to_eci(a, e, inc, raan, argp, nu)
        
        r_mag = np.linalg.norm(r_eci)
        v_mag = np.linalg.norm(v_eci)
        
        trajectory.append({
            "time_sec": float(t),
            "x_km": float(r_eci[0]),
            "y_km": float(r_eci[1]),
            "z_km": float(r_eci[2]),
            "radius_km": float(r_mag),
            "altitude_km": float(r_mag - R_EARTH),
            "velocity_kms": float(v_mag),
            "raan_deg": float(math.degrees(raan)),
            "arg_perigee_deg": float(math.degrees(argp)),
            "true_anomaly_deg": float(math.degrees(nu) % 360.0)
        })
        
    return {
        "raan_dot_deg_day": float(math.degrees(raan_dot) * 86400.0),
        "argp_dot_deg_day": float(math.degrees(argp_dot) * 86400.0),
        "is_frozen_perigee": abs(math.degrees(argp_dot) * 86400.0) < 0.05,
        "points": trajectory
    }
