"""
AstroCore Package
"""
from .astro_engine import (
    MU_EARTH, R_EARTH, J2_EARTH, OMEGA_EARTH,
    solve_kepler_equation, true_anomaly_from_eccentric, eccentric_anomaly_from_true,
    keplerian_to_cartesian, cartesian_to_keplerian, eci_to_ecef_geodetic,
    calculate_theoretical_j2_drifts, two_body_eom, j2_perturbed_eom,
    TrajectoryEngine
)
