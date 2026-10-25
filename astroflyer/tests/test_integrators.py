"""
AstroFlyer HEO - Phase 2 gate for integrators and analytic propagators.

Numerical integrators are checked against the exact Kepler solution, the
analytic J2 rates against textbook values and a J2-only integration, and SGP4
against Vallado's published test case (Revisiting Spacetrack Report #3, 2006).
"""

import math
import unittest

import numpy as np

from astroflyer.backend import analytic
from astroflyer.backend import frames as F
from astroflyer.backend import integrators as I
from astroflyer.backend.astro_engine import MU_EARTH, ThirdReviewEngine, keplerian_to_cartesian
from astroflyer.backend.epoch import Epoch

EPOCH = "2026-10-23T00:00:00Z"
A_MOLNIYA = 26560e3
PERIOD = 2.0 * math.pi * math.sqrt(A_MOLNIYA ** 3 / MU_EARTH)


def molniya_state(ta_deg=5.0):
    r, v = keplerian_to_cartesian(A_MOLNIYA, 0.72, math.radians(63.4), math.radians(30.0),
                                  math.radians(270.0), math.radians(ta_deg))
    return np.concatenate([r, v])


def kepler_rhs(t, y):
    return np.concatenate([y[3:], -MU_EARTH * y[:3] / np.linalg.norm(y[:3]) ** 3])


class TestTableau(unittest.TestCase):

    def test_rkf78_rows_are_consistent(self):
        for i, row in enumerate(I._A78):
            self.assertAlmostEqual(sum(row), I._C78[i], places=14, msg=f"row {i}")
        self.assertAlmostEqual(I._B78.sum(), 1.0, places=14)
        self.assertAlmostEqual(I._E78.sum(), 0.0, places=14)


class TestIntegratorsAgainstKepler(unittest.TestCase):

    def setUp(self):
        self.y0 = molniya_state()
        self.t_eval = np.linspace(0.0, 3.0 * PERIOD, 61)
        self.r_ref, self.v_ref = analytic.kepler_states(self.y0, self.t_eval)

    def test_adaptive_methods_match_to_a_metre(self):
        for method in ("RKF78", "BS"):
            res = I.integrate(kepler_rhs, (0.0, 3.0 * PERIOD), self.y0, method, t_eval=self.t_eval)
            np.testing.assert_array_equal(res.t, self.t_eval)     # outputs land exactly
            err = np.abs(res.y[:3].T - self.r_ref).max()
            self.assertLess(err, 1.0, f"{method}: {err:.3f} m after 3 Molniya orbits")

    def test_rk4_is_fourth_order(self):
        errors = []
        for step in (20.0, 10.0):
            res = I.integrate(kepler_rhs, (0.0, PERIOD), self.y0, "RK4", t_eval=[0.0, PERIOD], fixed_step=step)
            r_end, _ = analytic.kepler_states(self.y0, [PERIOD])
            errors.append(np.linalg.norm(res.y[:3, -1] - r_end[0]))
        self.assertTrue(12.0 < errors[0] / errors[1] < 20.0, f"error ratio {errors[0] / errors[1]:.1f}")

    def test_backward_integration_returns_to_start(self):
        fwd = I.integrate(kepler_rhs, (0.0, PERIOD), self.y0, "RKF78")
        back = I.integrate(kepler_rhs, (PERIOD, 0.0), fwd.y[:, -1], "RKF78")
        self.assertLess(np.abs(back.y[:3, -1] - self.y0[:3]).max(), 0.1)

    def test_events_match_the_closed_form(self):
        engine = ThirdReviewEngine(self.y0, epoch=EPOCH)
        exact = engine.propagate((0.0, 2.0 * PERIOD), num_points=400, model="two_body", method="Kepler")["events"]
        for method in ("RKF78", "BS", "DOP853"):
            got = engine.propagate((0.0, 2.0 * PERIOD), num_points=50, model="two_body", method=method)["events"]
            self.assertEqual([e["type"] for e in got], [e["type"] for e in exact], method)
            dt = max(abs(a["t_s"] - b["t_s"]) for a, b in zip(got, exact))
            self.assertLess(dt, 1e-3, f"{method}: event times off by {dt:.2e} s")


class TestPropagateMethods(unittest.TestCase):

    def test_every_method_runs_through_the_engine(self):
        engine = ThirdReviewEngine(molniya_state(), epoch=EPOCH)
        ref = engine.propagate((0.0, 3600.0), num_points=7, model="two_body", method="Kepler")
        for method in ("RKF78", "RK78", "BS", "Bulirsch-Stoer", "RK4", "DOP853", "Radau"):
            sol = engine.propagate((0.0, 3600.0), num_points=7, model="two_body", method=method, fixed_step=5.0)
            err = np.abs(sol["position_m"] - ref["position_m"]).max()
            self.assertLess(err, 0.05, f"{method}: {err:.4f} m")

    def test_sgp4_without_tle_is_refused(self):
        with self.assertRaises(ValueError):
            ThirdReviewEngine(molniya_state(), epoch=EPOCH).propagate((0.0, 60.0), num_points=3, method="SGP4")


class TestJ2Mean(unittest.TestCase):

    def test_sun_synchronous_node_rate(self):
        # 700 km circular at 98.19 deg precesses ~0.9856 deg/day eastward
        raan_dot, _, _ = analytic.j2_secular_rates(7078.137e3, 0.0, math.radians(98.19))
        self.assertAlmostEqual(math.degrees(raan_dot) * 86400.0, 360.0 / 365.2422, delta=0.01)

    def test_critical_inclination_freezes_perigee(self):
        _, argp_dot, _ = analytic.j2_secular_rates(A_MOLNIYA, 0.72, math.acos(math.sqrt(0.2)))
        self.assertLess(abs(argp_dot), 1e-15)

    def test_matches_j2_integration_over_ten_days(self):
        y0 = molniya_state(0.0)
        t = np.linspace(0.0, 10 * 86400.0, 2001)
        num = ThirdReviewEngine(y0, epoch=EPOCH).propagate((0.0, t[-1]), num_points=len(t), model="j2", method="DOP853")
        # Least-squares slope of the osculating node strips the short-period terms
        raan_num = np.degrees(np.unwrap(np.radians(num["raan_deg"])))
        rate_num = np.polyfit(t, raan_num, 1)[0]
        a, e, inc = analytic.state_to_elements(y0[:3], y0[3:])[:3]
        rate_mean = math.degrees(analytic.j2_secular_rates(a, e, inc)[0])
        self.assertAlmostEqual(rate_num / rate_mean, 1.0, delta=0.02)
        r_mean, v_mean = analytic.j2_mean_states(y0, t[-1:])
        raan_end = math.degrees(analytic.state_to_elements(r_mean[0], v_mean[0])[3])
        self.assertAlmostEqual(raan_end, (30.0 + rate_mean * t[-1]) % 360.0, delta=1e-6)


class TestSGP4(unittest.TestCase):
    # Vallado et al. 2006, test case 00005 (SGP4 near-Earth), t = 0 TEME state
    LINE1 = "1 00005U 58002B   00179.78495062  .00000023  00000-0  28098-4 0  4753"
    LINE2 = "2 00005  34.2682 348.7242 1859667 331.7664  19.3264 10.82419157413667"
    R_TEME_KM = np.array([7022.46529266, -1400.08296755, 0.03995155])
    V_TEME_KMS = np.array([1.893841015, 6.405893759, 4.534807250])

    def test_vallado_case_00005(self):
        tle = analytic.TLEPropagator(self.LINE1, self.LINE2)
        r, v = tle.states(None, np.zeros(1))
        r_teme, v_teme = F.transform_state(r[0], v[0], tle.epoch, "GCRF", "TEME")
        np.testing.assert_allclose(r_teme / 1e3, self.R_TEME_KM, atol=1e-6)
        np.testing.assert_allclose(v_teme / 1e3, self.V_TEME_KMS, atol=1e-9)

    def test_engine_from_tle(self):
        engine = ThirdReviewEngine.from_tle(self.LINE1, self.LINE2)
        self.assertEqual(engine.epoch.iso("UTC")[:19], "2000-06-27T18:50:19")
        sol = engine.propagate((0.0, 6 * 3600.0), num_points=361, model="two_body", method="SGP4")
        np.testing.assert_allclose(sol["position_m"][0], engine.y0[:3], atol=1e-6)
        kinds = {e["type"] for e in sol["events"]}
        self.assertTrue({"perigee", "apogee", "ascending_node", "descending_node"} <= kinds)


if __name__ == "__main__":
    unittest.main()
