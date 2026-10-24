"""
AstroFlyer HEO - shadow prediction follows the engine's real Sun direction, not a fixed Sun on +X.
"""

import json
import threading
import unittest
import urllib.request

import numpy as np

from astroflyer.backend.app_server import create_server
from astroflyer.backend.event_predictor import EventPredictor

R_EQ = 6378137.0


class TestEclipseSunDirection(unittest.TestCase):

    def test_per_sample_sun_direction_moves_the_shadow(self):
        times = np.linspace(0.0, 100.0, 11)
        # Parked on -X: shadowed by a Sun on +X, sunlit when the Sun is on +Y.
        positions = np.tile([-7000e3, 0.0, 0.0], (11, 1))
        sun_y = np.tile([0.0, 1.0, 0.0], (11, 1))
        result = EventPredictor().predict_solar_eclipses(times, positions, sun_y)
        self.assertEqual(result["mission_eclipse_fraction_pct"], 0.0)

        # Same Sun, parked on -Y: in shadow for the whole arc.
        shadowed = EventPredictor().predict_solar_eclipses(times, np.tile([0.0, -7000e3, 0.0], (11, 1)), sun_y)
        self.assertTrue(all(r == "UMBRA" for r in shadowed["regimes"]))

    def test_propagate_shadow_matches_its_own_sun_direction(self):
        server = create_server(port=0)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        body = json.dumps({"hp": 250, "ha": 35786, "inc": 28.5, "raan": 0, "aop": 180, "ta": 0, "num_orbits": 2}).encode()
        request = urllib.request.Request(f"http://127.0.0.1:{server.server_address[1]}/api/propagate", body,
                                         {"Content-Type": "application/json"})
        payload = json.load(urllib.request.urlopen(request, timeout=600))

        r = np.array(payload["position_m"])
        s = np.array(payload["sun_direction_eci"])
        along = np.sum(r * s, axis=1)
        across = np.linalg.norm(r - along[:, None] * s, axis=1)
        cylinder_pct = np.mean((along < 0) & (across < R_EQ)) * 100.0
        engine_pct = payload["events_suite"]["solar_eclipses"]["mission_eclipse_fraction_pct"]
        self.assertGreater(cylinder_pct, 1.0)   # this GTO does pass through the shadow
        self.assertAlmostEqual(engine_pct, cylinder_pct, delta=0.5)

    def test_eclipses_endpoint_uses_the_real_sun(self):
        # /api/events/eclipses runs its own propagation; its shadow fraction must follow the DE440 Sun
        from astroflyer.backend.astro_engine import ThirdReviewEngine, keplerian_to_cartesian
        server = create_server(port=0)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        url = f"http://127.0.0.1:{server.server_address[1]}/api/events/eclipses?a=24389&e=0.728525&inc=28.5"
        payload = json.load(urllib.request.urlopen(url, timeout=600))

        r0, v0 = keplerian_to_cartesian(24389e3, 0.728525, np.radians(28.5), np.radians(45.0), np.radians(30.0), 0.0)
        sol = ThirdReviewEngine(np.concatenate([r0, v0])).propagate((0.0, 37905.5), num_points=1000)
        r, s = np.asarray(sol["position_m"]), np.asarray(sol["sun_direction_eci"])
        along = np.sum(r * s, axis=1)
        across = np.linalg.norm(r - along[:, None] * s, axis=1)
        cylinder_pct = np.mean((along < 0) & (across < R_EQ)) * 100.0
        self.assertAlmostEqual(payload["mission_eclipse_fraction_pct"], cylinder_pct, delta=0.5)


if __name__ == "__main__":
    unittest.main()
