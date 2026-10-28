"""
AstroFlyer HEO - Impulsive burns in a propagation run, and continuing a run from its final state
(backend/propagation_run.py): the request's burns list, the burn report, the final_state every run
reports, and that a run continued from its final state carries on the same trajectory.
Written before the implementation.
"""

import math
import unittest

import numpy as np

from astroflyer.backend.forces import MU_EARTH, R_EARTH_EQ
from astroflyer.backend.mission import G0

MU_KM = MU_EARTH / 1e9
MOLNIYA = {"a": 26600.0, "e": 0.74, "inc": 63.4, "raan": 90.0, "aop": 270.0, "ta": 0.0,
           "model": "two_body", "num_orbits": 1, "num_points": 400, "mass": 1500.0}


def run(**request):
    from astroflyer.backend.propagation_run import run as run_request
    return run_request({**MOLNIYA, **request})


def elements_at(report, t_s):
    """Semi-major axis (km) and eccentricity of the first sample at or after t_s."""
    i = int(np.searchsorted(report["times"], t_s - 1e-6))
    return report["semi_major_axis_km"][i], report["eccentricity"][i]


class FinalStateTest(unittest.TestCase):

    def test_every_run_reports_its_final_state_at_full_precision(self):
        report = run()
        final = report["final_state"]
        self.assertAlmostEqual(final["t_s"], report["times"][-1], places=9)
        self.assertAlmostEqual(final["t_s"], report["duration_s"], places=6)
        np.testing.assert_allclose(final["position_km"], np.array(report["position_m"][-1]) / 1000.0, rtol=0, atol=1e-9)
        np.testing.assert_allclose(final["velocity_kms"], np.array(report["velocity_ms"][-1]) / 1000.0, rtol=0, atol=1e-12)
        self.assertEqual(final["mass_kg"], 1500.0)
        # Microseconds, so a restart from it is placed within 1 microsecond of the true end
        self.assertRegex(final["utc"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{6}Z$")

    def test_a_run_continued_from_its_final_state_follows_the_uninterrupted_run(self):
        full = {"model": "coupled", "gravity_degree": 8, "epoch": "2026-01-01T00:00:00Z"}
        period = 2 * math.pi * math.sqrt(26600.0 ** 3 / MU_KM)
        whole = run(**full, duration_s=2 * period, num_points=800)
        first = run(**full, duration_s=period)
        end = first["final_state"]
        second = run(**{**full, "epoch": end["utc"]}, a=None, e=None, inc=None, raan=None, aop=None, ta=None,
                     position_km=end["position_km"], velocity_kms=end["velocity_kms"], duration_s=period,
                     mass=end["mass_kg"])
        gap_m = np.linalg.norm(np.array(second["final_state"]["position_km"])
                               - np.array(whole["final_state"]["position_km"])) * 1000.0
        # Same equations from the same state; only the integrator's fresh start and the microsecond
        # epoch rounding differ (about 1 cm at perigee speed)
        self.assertLess(gap_m, 1.0)


class ImpulsiveBurnTest(unittest.TestCase):

    def test_a_perigee_burn_raises_the_apogee_as_the_vis_viva_equation_says(self):
        dv = 100.0
        report = run(ta=180.0, burns=[{"timing": "perigee", "dv_ms": [dv, 0, 0], "isp_s": 300}])
        burn = report["burns"][0]
        self.assertTrue(burn["applied"])
        rp = 26600.0 * (1 - 0.74)
        vp = math.sqrt(MU_KM * (2 / rp - 1 / 26600.0))
        a_after = 1.0 / (2 / rp - (vp + dv / 1000.0) ** 2 / MU_KM)
        period = 2 * math.pi * math.sqrt(26600.0 ** 3 / MU_KM)
        self.assertAlmostEqual(burn["t_s"], period / 2, delta=1e-3)       # from apogee to perigee
        a, _ = elements_at(report, burn["t_s"])
        self.assertAlmostEqual(a, a_after, delta=1e-3)
        self.assertAlmostEqual(report["semi_major_axis_km"][-1], a_after, delta=1e-3)
        self.assertAlmostEqual(burn["delta_v_ms"], dv, places=9)

    def test_propellant_follows_the_rocket_equation_and_the_mass_carries_on(self):
        report = run(burns=[{"timing": "elapsed", "t_s": 3600.0, "dv_ms": [50.0, 10.0, -5.0], "isp_s": 320}])
        burn = report["burns"][0]
        dv = math.sqrt(50.0 ** 2 + 10.0 ** 2 + 5.0 ** 2)
        m_after = 1500.0 * math.exp(-dv / (320 * G0))
        self.assertAlmostEqual(burn["t_s"], 3600.0, places=9)
        self.assertAlmostEqual(burn["mass_before_kg"], 1500.0)
        self.assertAlmostEqual(burn["mass_after_kg"], m_after, places=9)
        self.assertAlmostEqual(burn["propellant_kg"], 1500.0 - m_after, places=9)
        self.assertAlmostEqual(report["final_state"]["mass_kg"], m_after, places=9)

    def test_a_hohmann_transfer_ends_circular(self):
        r1, r2 = 7000.0, 42164.0
        v1 = math.sqrt(MU_KM / r1)
        at = (r1 + r2) / 2
        dv1 = (math.sqrt(MU_KM * (2 / r1 - 1 / at)) - v1) * 1000.0
        dv2 = (math.sqrt(MU_KM / r2) - math.sqrt(MU_KM * (2 / r2 - 1 / at))) * 1000.0
        transfer = math.pi * math.sqrt(at ** 3 / MU_KM)
        report = run(a=r1, e=0.0, inc=0.0, aop=0.0, num_orbits=None, duration_s=transfer + 7200.0,
                     burns=[{"timing": "elapsed", "t_s": 0.0, "dv_ms": [dv1, 0, 0]},
                            {"timing": "apogee", "dv_ms": [dv2, 0, 0]}])
        self.assertEqual([b["applied"] for b in report["burns"]], [True, True])
        self.assertAlmostEqual(report["burns"][1]["t_s"], transfer, delta=1.0)
        self.assertLess(report["eccentricity"][-1], 1e-5)
        self.assertAlmostEqual(report["semi_major_axis_km"][-1], r2, delta=0.5)

    def test_the_samples_jump_at_the_burn_and_keep_time_order(self):
        report = run(burns=[{"timing": "elapsed", "t_s": 5000.0, "dv_ms": [200.0, 0, 0]}])
        times = np.array(report["times"])
        self.assertTrue(np.all(np.diff(times) > 0))
        self.assertIn(5000.0, report["times"])     # the state just after the burn is a sample
        self.assertEqual(len(times), len(report["eccentricity"]))
        self.assertEqual(len(times), len(report["force_diagnostics"]["a_central_ms2"]))
        i = report["times"].index(5000.0)
        a_before, a_after = report["semi_major_axis_km"][i - 1], report["semi_major_axis_km"][i]
        self.assertGreater(a_after - a_before, 100.0)

    def test_burns_are_in_the_events_with_their_times(self):
        report = run(burns=[{"timing": "elapsed", "t_s": 5000.0, "dv_ms": [20.0, 0, 0], "name": "Raise"}])
        burns = [ev for ev in report["events"] if ev["type"] == "burn"]
        self.assertEqual([(ev["t_s"], ev["name"]) for ev in burns], [(5000.0, "Raise")])
        self.assertEqual(report["burns"][0]["utc"], burns[0]["utc"])

    def test_an_apsis_burn_the_run_never_reaches_is_reported_not_applied(self):
        report = run(num_orbits=None, duration_s=600.0, ta=10.0,
                     burns=[{"timing": "apogee", "dv_ms": [10.0, 0, 0]}])
        self.assertFalse(report["burns"][0]["applied"])
        self.assertTrue(any("apogee" in note for note in report["notes"]))
        self.assertEqual(report["final_state"]["mass_kg"], 1500.0)

    def test_a_run_without_burns_is_unchanged(self):
        plain = run()
        empty = run(burns=[])
        self.assertEqual(plain["times"], empty["times"])
        self.assertEqual(plain["position_m"], empty["position_m"])
        self.assertEqual(empty["burns"], [])


class BurnRefusalTest(unittest.TestCase):

    def test_burn_times_must_follow_each_other_and_fall_inside_the_run(self):
        with self.assertRaisesRegex(ValueError, "before"):
            run(burns=[{"timing": "elapsed", "t_s": 5000.0, "dv_ms": [1, 0, 0]},
                       {"timing": "elapsed", "t_s": 4000.0, "dv_ms": [1, 0, 0]}])
        with self.assertRaisesRegex(ValueError, "after the run ends"):
            run(burns=[{"timing": "elapsed", "t_s": 1e6, "dv_ms": [1, 0, 0]}])

    def test_bad_burn_fields_are_refused(self):
        for burn, message in (({"timing": "noon", "dv_ms": [1, 0, 0]}, "timing"),
                              ({"timing": "elapsed", "t_s": 10.0, "dv_ms": [1, 0]}, "dv_ms"),
                              ({"timing": "elapsed", "t_s": 10.0, "dv_ms": [1, 0, 0], "isp_s": 0}, "isp_s"),
                              ({"timing": "elapsed", "t_s": 10.0, "dv_ms": [1, 0, 0], "frame": "XYZ"}, "frame")):
            with self.assertRaisesRegex(ValueError, message):
                run(burns=[burn])

    def test_a_burn_needing_more_mass_than_the_spacecraft_has_is_refused(self):
        with self.assertRaisesRegex(ValueError, "10 kg"):
            run(burns=[{"timing": "elapsed", "t_s": 10.0, "dv_ms": [20000.0, 0, 0], "isp_s": 200}])

    def test_covariance_steering_runs_without_burns(self):
        with self.assertRaisesRegex(ValueError, "steering"):
            run(method="RKF78", steering="covariance",
                burns=[{"timing": "elapsed", "t_s": 10.0, "dv_ms": [1, 0, 0]}])


if __name__ == "__main__":
    unittest.main()
