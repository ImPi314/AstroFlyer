"""
AstroCore Zeroeth Review Module Proxy - fsw_subsystems
Exposes FSW subsystems from third review/backend/fsw_subsystems.py
"""

import os
import sys
import importlib.util

_target_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "third review", "backend", "fsw_subsystems.py")
)

_spec = importlib.util.spec_from_file_location("third_fsw_subsystems", _target_path)
_mod = importlib.util.module_from_spec(_spec) # type: ignore
sys.modules["third_fsw_subsystems"] = _mod
_spec.loader.exec_module(_mod) # type: ignore

FlightAttitudeGuidance = _mod.FlightAttitudeGuidance
FlightSoftwareSubsystems = _mod.FlightSoftwareSubsystems
SpacecraftSubsystems = _mod.SpacecraftSubsystems
SpacecraftMissionSimulator = _mod.SpacecraftMissionSimulator

BasiliskAttitudeGuidance = _mod.BasiliskAttitudeGuidance
BasiliskSubsystems = _mod.BasiliskSubsystems
BasiliskMissionSimulator = _mod.BasiliskMissionSimulator
