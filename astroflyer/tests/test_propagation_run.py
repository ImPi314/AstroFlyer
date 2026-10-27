"""
AstroFlyer HEO - The propagation run behind /api/propagate (backend/propagation_run.py), tested
without a server: what a request may contain, what is refused, and what the report holds.
Written before the implementation.
"""

import math
import unittest

from astroflyer.backend.forces import MU_EARTH, R_EARTH_EQ

MOLNIYA = {"a": 26600.0, "e": 0.74, "inc": 63.4, "raan": 90.0, "aop": 270.0, "ta": 0.0,
           "model": "two_body", "num_orbits": 1, "num_points": 300}


class PropagationRunTest(unittest.TestCase):

    def run_request(self, **changes):
        from astroflyer.backend.propagation_run import run
        return run({**MOLNIYA, **changes})

    def test_hyperbolic_elements_are_refused_not_clamped(self):
        # e = 1.2 used to become 0.99 without a word, a different orbit from the one asked for
        with self.assertRaisesRegex(ValueError, "position_km"):
            self.run_request(e=1.2)

    def test_perigee_below_the_surface_is_refused(self):
        with self.assertRaisesRegex(ValueError, "perigee"):
            self.run_request(a=6000.0, e=0.01)

    def test_cartesian_start_below_the_surface_is_refused(self):
        # 6360 km from the centre over the equator is 18 km underground (and 3 km above the pole's
        # 6356.8 km, so the check must use the WGS-84 ellipsoid, not a sphere)
        with self.assertRaisesRegex(ValueError, "below the Earth's surface"):
            self.run_request(position_km=[6360.0, 0.0, 0.0], velocity_kms=[0.0, 7.9, 0.0], duration_s=600)
        report = self.run_request(position_km=[0.0, 0.0, 6360.0], velocity_kms=[7.9, 0.0, 0.0],
                                  duration_s=60, a=None, e=None)
        self.assertGreater(report["altitude_km"][0], 0.0)

    def test_a_run_that_reaches_the_surface_reports_the_impact(self):
        # 300 km up at 5 km/s is a closed orbit whose perigee is inside the Earth: it comes down
        # within minutes, and the run must say so instead of carrying on underground
        report = self.run_request(position_km=[6678.137, 0.0, 0.0], velocity_kms=[0.0, 5.0, 0.0],
                                  duration_s=3600, a=None, e=None, epoch="2026-03-15T00:00:00Z")
        self.assertEqual(report["status"], "impact")
        impact = report["impact"]
        self.assertLess(impact["t_s"], 3600.0)
        self.assertEqual(report["times"][-1], impact["t_s"])
        self.assertAlmostEqual(report["altitude_km"][-1], 0.0, places=3)
        self.assertLess(min(report["altitude_km"]), 0.001)
        self.assertGreaterEqual(min(report["altitude_km"]), -0.001)
        self.assertTrue(impact["utc"].startswith("2026-03-15T00:"))
        self.assertTrue(-90.0 <= impact["latitude_deg"] <= 90.0 and -180.0 <= impact["longitude_deg"] <= 180.0)
        self.assertNotIn("events_suite", report)     # analyses of a whole orbit are not produced
        self.assertTrue(any("surface" in note for note in report["notes"]))

    def test_analytic_propagators_stop_at_the_surface_too(self):
        for method in ("KEPLER", "J2MEAN"):
            report = self.run_request(position_km=[6678.137, 0.0, 0.0], velocity_kms=[0.0, 5.0, 0.0],
                                      duration_s=3600, a=None, e=None, method=method)
            self.assertEqual(report["status"], "impact", method)
            self.assertAlmostEqual(report["altitude_km"][-1], 0.0, places=3, msg=method)
            self.assertGreaterEqual(min(report["altitude_km"]), -0.001, method)

    def test_apsis_altitudes_are_above_the_equatorial_radius(self):
        # The console states altitudes above the WGS-84 equatorial radius, as the engine's geodetic
        # altitudes are; the 6371 km mean radius put a 250 km x 35786 km GTO 7 km low
        report = self.run_request(hp=250.0, ha=35786.0, a=None, e=None)
        self.assertAlmostEqual(report["active_orbit_config"]["semi_major_axis_km"],
                               6378.137 + (250.0 + 35786.0) / 2.0, places=3)

    def test_report_states_the_space_weather_drag_used(self):
        report = self.run_request(model="coupled", epoch="2026-03-15T00:00:00Z", num_points=200)
        used = report["active_orbit_config"]["space_weather"]
        self.assertEqual(used["source"], "CelesTrak SW-All.csv (bundled)")
        self.assertEqual(used["kinds"], ["OBS"])        # observed values throughout March 2026
        self.assertNotEqual(used["start"]["f107"], 150.0)

    def test_closed_orbit_report(self):
        report = self.run_request()
        period = 2.0 * math.pi * math.sqrt((26600e3) ** 3 / MU_EARTH)
        self.assertTrue(report["closed_orbit"])
        self.assertAlmostEqual(report["duration_s"], period, delta=1e-6)
        self.assertAlmostEqual(report["times"][-1], period, delta=1e-6)
        config = report["active_orbit_config"]
        self.assertAlmostEqual(config["eccentricity"], 0.74, places=6)
        self.assertAlmostEqual(config["perigee_alt_km"], 26600.0 * 0.26 - R_EARTH_EQ / 1000.0, places=1)
        kinds = {ev["event_type"] for ev in report["events_suite"]["exact_apsidal_events"]}
        self.assertIn("PERIAPSIS_PASSAGE", kinds)


if __name__ == "__main__":
    unittest.main()
