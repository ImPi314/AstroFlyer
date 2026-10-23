"""
AstroCore Root Module Proxy - freeflyer_interop
Exposes FreeFlyer mission plan serialization from astroflyer.backend.freeflyer_interop
"""

import os
import sys

_curr_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_curr_dir)
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)

from astroflyer.backend.freeflyer_interop import (
    export_to_mission_plan, import_from_mission_plan
)
