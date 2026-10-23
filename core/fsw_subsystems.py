"""
AstroCore Root Module Proxy - fsw_subsystems
Exposes FSW subsystems from astroflyer.backend.fsw_subsystems
"""

import os
import sys

_curr_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_curr_dir)
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)

from astroflyer.backend.fsw_subsystems import (
    FlightSoftwareSubsystems, FlightAttitudeGuidance, SpacecraftMissionSimulator,
    BasiliskSubsystems, BasiliskAttitudeGuidance, BasiliskMissionSimulator
)
