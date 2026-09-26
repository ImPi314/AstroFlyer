"""
Two-Body Keplerian Solver - Zeroeth Review Baseline Engine
Department of Aerospace Engineering, ACS College of Engineering
"""

import math
import numpy as np

MU_EARTH = 398600.4418  # km^3/s^2
R_EARTH = 6378.137      # km

def solve_kepler(M, e, tol=1e-12, max_iter=100):
    """Solve Kepler's equation M = E - e*sin(E) for Eccentric Anomaly E."""
    # Normalize M to [-pi, pi]
    M = (M + math.pi) % (2.0 * math.pi) - math.pi
    
    # Initial guess
    if e < 0.8:
        E = M
    else:
        E = math.pi if M < 0 else -math.pi
        
    for _ in range(max_iter):
        f = E - e * math.sin(E) - M
        f_prime = 1.0 - e * math.cos(E)
        dE = -f / f_prime
        E += dE
        if abs(dE) < tol:
            break
    return E

def true_anomaly_from_E(E, e):
    """Compute True Anomaly nu from Eccentric Anomaly E."""
    sin_nu = (math.sqrt(1.0 - e**2) * math.sin(E)) / (1.0 - e * math.cos(E))
    cos_nu = (math.cos(E) - e) / (1.0 - e * math.cos(E))
    return math.atan2(sin_nu, cos_nu)

def elements_to_eci(a, e, inc_rad, raan_rad, argp_rad, nu_rad, mu=MU_EARTH):
    """Convert Classical Orbital Elements to Cartesian Position & Velocity in ECI frame."""
    p = a * (1.0 - e**2)
    r_mag = p / (1.0 + e * math.cos(nu_rad))
    
    # Position in Perifocal (PQW) frame
    r_pqw = np.array([
        r_mag * math.cos(nu_rad),
        r_mag * math.sin(nu_rad),
        0.0
    ])
    
    # Velocity in Perifocal (PQW) frame
    v_factor = math.sqrt(mu / p)
    v_pqw = np.array([
        -v_factor * math.sin(nu_rad),
        v_factor * (e + math.cos(nu_rad)),
        0.0
    ])
    
    # Rotation matrix from PQW to ECI
    cos_O = math.cos(raan_rad)
    sin_O = math.sin(raan_rad)
    cos_w = math.cos(argp_rad)
    sin_w = math.sin(argp_rad)
    cos_i = math.cos(inc_rad)
    sin_i = math.sin(inc_rad)
    
    R = np.array([
        [cos_O * cos_w - sin_O * sin_w * cos_i, -cos_O * sin_w - sin_O * cos_w * cos_i, sin_O * sin_i],
        [sin_O * cos_w + cos_O * sin_w * cos_i, -sin_O * sin_w + cos_O * cos_w * cos_i, -cos_O * sin_i],
        [sin_w * sin_i, cos_w * sin_i, cos_i]
    ])
    
    r_eci = R @ r_pqw
    v_eci = R @ v_pqw
    
    return r_eci, v_eci

def propagate_kepler(a, e, inc_deg, raan_deg, argp_deg, nu0_deg, duration_sec, num_points=300):
    """Generate unperturbed Keplerian trajectory points over a given duration."""
    inc = math.radians(inc_deg)
    raan = math.radians(raan_deg)
    argp = math.radians(argp_deg)
    nu0 = math.radians(nu0_deg)
    
    n = math.sqrt(MU_EARTH / (a**3))  # Mean motion rad/s
    period_sec = 2.0 * math.pi / n
    
    # Initial Eccentric and Mean Anomaly
    E0 = 2.0 * math.atan(math.sqrt((1.0 - e) / (1.0 + e)) * math.tan(nu0 / 2.0))
    M0 = E0 - e * math.sin(E0)
    
    times = np.linspace(0, duration_sec, num_points)
    trajectory = []
    
    for t in times:
        M = M0 + n * t
        E = solve_kepler(M, e)
        nu = true_anomaly_from_E(E, e)
        r_eci, v_eci = elements_to_eci(a, e, inc, raan, argp, nu)
        
        r_mag = np.linalg.norm(r_eci)
        v_mag = np.linalg.norm(v_eci)
        altitude = r_mag - R_EARTH
        
        # Specific mechanical energy and angular momentum
        energy = 0.5 * (v_mag**2) - (MU_EARTH / r_mag)
        h_vec = np.cross(r_eci, v_eci)
        h_mag = np.linalg.norm(h_vec)
        
        trajectory.append({
            "time_sec": float(t),
            "x_km": float(r_eci[0]),
            "y_km": float(r_eci[1]),
            "z_km": float(r_eci[2]),
            "vx_kms": float(v_eci[0]),
            "vy_kms": float(v_eci[1]),
            "vz_kms": float(v_eci[2]),
            "radius_km": float(r_mag),
            "altitude_km": float(altitude),
            "velocity_kms": float(v_mag),
            "true_anomaly_deg": float(math.degrees(nu) % 360.0),
            "energy_km2_s2": float(energy),
            "ang_momentum_km2_s": float(h_mag)
        })
        
    return {
        "period_sec": period_sec,
        "period_hr": period_sec / 3600.0,
        "mean_motion_rad_s": n,
        "points": trajectory
    }
