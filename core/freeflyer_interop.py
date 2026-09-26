"""
AstroCore Root Module Proxy - Mission Plan Compatibility
Exposes mission plan export/import from zeroeth review/core/mission_plan_io.py
"""

import os
import sys
import importlib.util

_target_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "zeroeth review", "core", "freeflyer_interop.py")
)

_spec = importlib.util.spec_from_file_location("zeroeth_freeflyer_interop", _target_path)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["zeroeth_freeflyer_interop"] = _mod
_spec.loader.exec_module(_mod)

export_to_mission_plan = _mod.export_to_mission_plan
import_from_mission_plan = _mod.import_from_mission_plan
