"""
AstroFlyer HEO - a run reports only what the engine computed for it.

The run endpoint used to attach demo-era sections to every result: simulated flight-software
telemetry (battery, solar power, wheels), hand-typed benchmark figures, invented radiation
doses, a lifetime from a single-exponential atmosphere, and fixed-target B-plane, Hohmann,
constellation and Pareto reports unrelated to the run. The endpoints behind them are gone too.
Written before the implementation (tests-first rule).
"""

import json
import threading
import unittest
import urllib.error
import urllib.request

from astroflyer.backend.app_server import create_server

RUN = ("hp=1000&ha=39350&inc=63.4&raan=0&aop=270&ta=0&num_orbits=1&num_points=200"
       "&model=two_body&method=DOP853&epoch=2026-01-01T00:00:00Z")

DEMO_SECTIONS = ("fsw_subsystems", "benchmark_summary", "benchmark_certificates", "numerical_targeting",
                 "time_standards")
DEMO_EVENTS = ("b_plane_targeting", "apogee_boost_maneuver", "lunar_eclipses", "reentry_hazard_assessment",
               "multi_decadal_lifetime")
DEMO_INNOVATIONS = ("radiation_pareto", "multi_burn_perigee_pumping", "molniya_constellation_handover")
GONE_ENDPOINTS = ("/api/benchmark/summary", "/api/fsw/telemetry", "/api/constellation/molniya",
                  "/api/radiation/pareto", "/api/radiation/belts", "/api/targeting/perigee_pumping",
                  "/api/targeting/bplane", "/api/targeting/bplane_analytic", "/api/targeting/hohmann",
                  "/api/targeting/maneuver", "/api/maneuver/what_if", "/api/lifetime/predict",
                  "/api/astroflyer/theme", "/api/mission_plan/export", "/api/mission_plan/validate")


class RunReportsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.server = create_server(port=0)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        with urllib.request.urlopen(f"{cls.base}/api/propagate?{RUN}", timeout=300) as resp:
            cls.result = json.load(resp)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def test_no_demo_sections_in_a_run(self):
        self.assertEqual(self.result["status"], "ok")
        for key in DEMO_SECTIONS:
            self.assertNotIn(key, self.result)
        for key in DEMO_EVENTS:
            self.assertNotIn(key, self.result["events_suite"])
        for key in DEMO_INNOVATIONS:
            self.assertNotIn(key, self.result["innovations_suite"])
        self.assertNotIn("bplane_solution", self.result["script_workbench"])
        self.assertNotIn("hohmann_solution", self.result["script_workbench"])

    def test_what_the_run_did_compute_is_still_reported(self):
        for key in ("solar_eclipses", "ground_stations"):
            self.assertIn(key, self.result["events_suite"])
        self.assertTrue(self.result["script_workbench"]["script_content"].strip())
        self.assertIn("covariance_dispersion", self.result)
        self.assertIn("force_diagnostics", self.result)
        self.assertIn("ecr_mf", self.result["innovations_suite"])

    def test_radiation_reports_belt_crossings_without_invented_doses(self):
        radiation = self.result["radiation_belts"]
        self.assertIn("crossing_events", radiation)
        self.assertIn("l_shell_series", radiation)
        text = json.dumps(radiation)
        self.assertNotIn("dose", text)

    def test_a_run_that_names_no_method_uses_dop853(self):
        # DOP853 is the integrator validated against Orekit; Radau (implicit) was ~10x slower on these orbits
        query = "hp=1000&ha=39350&inc=63.4&raan=0&aop=270&ta=0&num_orbits=1&num_points=200&model=two_body"
        with urllib.request.urlopen(f"{self.base}/api/propagate?{query}", timeout=300) as resp:
            self.assertEqual(json.load(resp)["active_orbit_config"]["integrator"], "DOP853")
        with urllib.request.urlopen(f"{self.base}/api/propagate?{query}&method=Radau", timeout=300) as resp:
            self.assertEqual(json.load(resp)["active_orbit_config"]["integrator"], "Radau")

    def test_demo_endpoints_are_gone(self):
        for path in GONE_ENDPOINTS:
            with self.subTest(path=path):
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    urllib.request.urlopen(f"{self.base}{path}", timeout=60)
                self.assertEqual(caught.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
