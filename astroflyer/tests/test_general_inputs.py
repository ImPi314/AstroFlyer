"""
AstroFlyer HEO - /api/propagate and /api/script/propagate take any mission:
a run length in seconds and a Cartesian GCRF initial state, besides Keplerian elements.
Written before the implementation (tests-first rule, 2026-10-24).
"""

import json
import math
import threading
import unittest
import urllib.error
import urllib.request

import numpy as np

from astroflyer.backend import analytic
from astroflyer.backend.app_server import create_server
from astroflyer.backend.forces import MU_EARTH
from astroflyer.backend.trajectory_engine import MissionScriptWorkbench

FAST = {"model": "two_body", "method": "RKF78", "num_points": 200, "epoch": "2026-10-23T00:00:00Z"}


class TestGeneralMissionInputs(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.server = create_server(port=0)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def post(self, path, body):
        req = urllib.request.Request(self.base + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                return resp.status, json.load(resp)
        except urllib.error.HTTPError as err:
            return err.code, json.load(err)

    def test_duration_s_sets_the_run_length(self):
        status, out = self.post("/api/propagate", dict(FAST, sma_km=7000.0, ecc=0.001, inc_deg=51.6,
                                                        duration_s=5400.0, num_orbits=7))
        self.assertEqual(status, 200)
        self.assertAlmostEqual(out["times"][-1], 5400.0, places=6)
        self.assertEqual(out["duration_s"], 5400.0)
        self.assertEqual(out["active_orbit_config"]["duration_s"], 5400.0)

    def test_num_orbits_still_works_and_reports_its_length(self):
        status, out = self.post("/api/propagate", dict(FAST, sma_km=7000.0, ecc=0.001, inc_deg=51.6, num_orbits=2))
        self.assertEqual(status, 200)
        period = 2.0 * math.pi * math.sqrt((7000e3) ** 3 / MU_EARTH)
        self.assertAlmostEqual(out["duration_s"], 2.0 * period, delta=1e-6)
        self.assertAlmostEqual(out["times"][-1], 2.0 * period, delta=1e-6)

    def test_cartesian_initial_state(self):
        r_km = [-2384.46, 5729.01, 3050.46]
        v_kms = [-7.36138, -2.98997, 1.64354]
        status, out = self.post("/api/propagate", dict(FAST, position_km=r_km, velocity_kms=v_kms, duration_s=3000.0,
                                                        sma_km=42164.0, ecc=0.7))       # elements are ignored
        self.assertEqual(status, 200)
        np.testing.assert_allclose(out["position_m"][0], np.array(r_km) * 1e3, atol=1e-6)
        np.testing.assert_allclose(out["velocity_ms"][0], np.array(v_kms) * 1e3, atol=1e-9)
        y0 = np.concatenate([np.array(r_km) * 1e3, np.array(v_kms) * 1e3])
        r_end, _ = analytic.kepler_states(y0, [3000.0])
        np.testing.assert_allclose(out["position_m"][-1], r_end[0], atol=1.0)
        cfg = out["active_orbit_config"]
        self.assertEqual(cfg["initial_state"], "cartesian")
        a = 1.0 / (2.0 / np.linalg.norm(y0[:3]) - (y0[3:] @ y0[3:]) / MU_EARTH)
        self.assertAlmostEqual(cfg["semi_major_axis_km"], a / 1e3, delta=1e-3)

    def test_cartesian_state_as_query_text(self):
        # GET-style values arrive as text; "x, y, z" works too
        status, out = self.post("/api/propagate", dict(FAST, position_km="7000, 0, 0", velocity_kms="0, 7.546, 0",
                                                        duration_s=600.0))
        self.assertEqual(status, 200)
        np.testing.assert_allclose(out["position_m"][0], [7000e3, 0.0, 0.0], atol=1e-6)

    def test_bad_cartesian_input_is_a_400(self):
        status, out = self.post("/api/propagate", dict(FAST, position_km=[7000.0, 0.0], velocity_kms=[0.0, 7.5, 0.0]))
        self.assertEqual(status, 400)
        self.assertIn("position_km", out["error"])
        # Escape trajectories are refused with a clear message, with or without duration_s
        for extra in ({}, {"duration_s": 3600.0}):
            status, out = self.post("/api/propagate", dict(FAST, position_km=[7000.0, 0.0, 0.0],
                                                            velocity_kms=[0.0, 12.0, 0.0], **extra))
            self.assertEqual(status, 400)
            self.assertIn("escape", out["error"])

    def test_script_propagate_takes_duration_s(self):
        script = MissionScriptWorkbench.generate_mission_script(sma_km=26560.0, ecc=0.72, num_orbits=1)
        status, out = self.post("/api/script/propagate", dict(FAST, script_text=script, duration_s=7200.0))
        self.assertEqual(status, 200)
        self.assertAlmostEqual(out["times"][-1], 7200.0, places=6)
        self.assertAlmostEqual(out["active_orbit_config"]["semi_major_axis_km"], 26560.0, delta=1e-3)


if __name__ == "__main__":
    unittest.main()
