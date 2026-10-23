"""
AstroCore Root Module Proxy - astro_engine
Exposes core astrodynamics engine from astroflyer/backend/astro_engine.py
"""

import os
import sys

_curr_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_curr_dir)
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)

from astroflyer.backend.astro_engine import (
    MU_EARTH, R_EARTH, R_EARTH_EQ, J2_EARTH, J3_EARTH, J4_EARTH, OMEGA_EARTH,
    MU_SUN, MU_MOON, AU_METERS, D_MOON_MEAN, P_SR_1AU, RHO_0, H_SCALE, SPEED_OF_LIGHT,
    C22_EARTH, S22_EARTH, ALBEDO_REFLECTIVITY, TIR_SURFACE_FLUX,
    cartesian_to_keplerian, keplerian_to_cartesian, solve_kepler_equation,
    calculate_theoretical_j2_drifts, eci_to_ecef_geodetic,
    compute_acceleration_components, full_production_eom,
    ThirdReviewEngine, get_engine_status
)

# Backwards compatibility alias
TrajectoryEngine = ThirdReviewEngine
