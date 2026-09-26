"""
AstroCore Root Module Proxy - trajectory_engine
Exposes trajectory engine from third review/backend/trajectory_engine.py
"""

import os
import sys
import importlib.util

_target_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "third review", "backend", "trajectory_engine.py")
)

_spec = importlib.util.spec_from_file_location("third_trajectory_engine", _target_path)
_mod = importlib.util.module_from_spec(_spec) # type: ignore
sys.modules["third_trajectory_engine"] = _mod
_spec.loader.exec_module(_mod) # type: ignore

SpacecraftForceModel = _mod.SpacecraftForceModel
NumericalPropagator = _mod.NumericalPropagator
MissionScriptWorkbench = _mod.MissionScriptWorkbench
ManeuverTargeter = _mod.ManeuverTargeter

MU_EARTH = _mod.MU_EARTH
R_EARTH = _mod.R_EARTH
FLATTENING_EARTH = _mod.FLATTENING_EARTH
OMEGA_EARTH = _mod.OMEGA_EARTH
MU_SUN = _mod.MU_SUN
MU_MOON = _mod.MU_MOON
MU_JUPITER = _mod.MU_JUPITER
MU_MARS = _mod.MU_MARS
MU_VENUS = _mod.MU_VENUS
AU_METERS = _mod.AU_METERS
D_MOON_MEAN = _mod.D_MOON_MEAN
R_SUN = _mod.R_SUN
P_SR_1AU = _mod.P_SR_1AU
SPEED_OF_LIGHT = _mod.SPEED_OF_LIGHT
ZONAL_HARMONICS = _mod.ZONAL_HARMONICS

# Compatibility aliases
GMATForceModel = _mod.GMATForceModel
GMATPropagator = _mod.GMATPropagator
GMATScriptWorkbench = _mod.GMATScriptWorkbench
GMATTargeter = _mod.GMATTargeter
GMAT_ZONAL_HARMONICS = _mod.GMAT_ZONAL_HARMONICS
AstroFlyerForceModel = _mod.AstroFlyerForceModel
AstroFlyerPropagator = _mod.AstroFlyerPropagator
AstroFlyerTargeter = _mod.AstroFlyerTargeter
