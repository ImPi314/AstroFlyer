"""
AstroCore Root Module Proxy - astro_engine
Exposes core astrodynamics engine from zeroeth review/core/astro_engine.py
"""

import os
import sys
import importlib.util

_target_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "zeroeth review", "core", "astro_engine.py")
)

_spec = importlib.util.spec_from_file_location("zeroeth_astro_engine", _target_path)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["zeroeth_astro_engine"] = _mod
_spec.loader.exec_module(_mod)

# Explicitly export key astrodynamics symbols for IDE static analysis
MU_EARTH = _mod.MU_EARTH
R_EARTH = _mod.R_EARTH
J2_EARTH = _mod.J2_EARTH
OMEGA_EARTH = _mod.OMEGA_EARTH

TrajectoryEngine = _mod.TrajectoryEngine
cartesian_to_keplerian = _mod.cartesian_to_keplerian
keplerian_to_cartesian = _mod.keplerian_to_cartesian
two_body_eom = _mod.two_body_eom
j2_perturbed_eom = _mod.j2_perturbed_eom
calculate_theoretical_j2_drifts = _mod.calculate_theoretical_j2_drifts
eci_to_ecef_geodetic = _mod.eci_to_ecef_geodetic
get_engine_status = _mod.get_engine_status
