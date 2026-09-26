"""
AstroCore Root Module Proxy - mission_plan_io
Exposes mission plan export/import from zeroeth review/core/mission_plan_io.py
"""

import os
import sys
import importlib.util

_target_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "zeroeth review", "core", "mission_plan_io.py")
)

_spec = importlib.util.spec_from_file_location("zeroeth_mission_plan_io", _target_path)
_mod = importlib.util.module_from_spec(_spec) # type: ignore
sys.modules["zeroeth_mission_plan_io"] = _mod
_spec.loader.exec_module(_mod) # type: ignore

export_to_mission_plan = _mod.export_to_mission_plan
import_from_mission_plan = _mod.import_from_mission_plan
