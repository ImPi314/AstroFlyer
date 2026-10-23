"""
AstroCore Root Module Proxy - trajectory_engine
Exposes trajectory engine from astroflyer.backend.trajectory_engine
"""

import os
import sys

_curr_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_curr_dir)
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)

from astroflyer.backend.trajectory_engine import (
    SpacecraftForceModel, NumericalPropagator, MissionScriptWorkbench, ManeuverTargeter,
    GMATForceModel, GMATPropagator, GMATScriptWorkbench, GMATTargeter
)
