"""
AstroFlyer HEO - integration across Earth-shadow boundaries

SRP switches on and off at penumbra entry and exit, so the acceleration has a
kink there. An adaptive integrator that steps across the kink loses accuracy
(metres per day on Molniya), so the propagator restarts at each boundary, as
Orekit does with its eclipse detectors. These tests check:
  - the boundary functions agree with the shadow function
  - the segmented solver stops at a kink, still fills t_eval, and keeps user events
  - a Molniya arc with eclipses converges as the tolerances tighten
"""

import math
import unittest

import numpy as np

from astroflyer.backend import forces
from astroflyer.backend.astro_engine import ThirdReviewEngine, keplerian_to_cartesian
from astroflyer.backend.epoch import Epoch

EPOCH = Epoch.from_iso("2026-01-01T00:00:00", scale="TT")


class TestShadowBoundaries(unittest.TestCase):

    def test_boundary_functions_classify_shadow(self):
        r_sun = np.array([forces.AU_METERS, 0.0, 0.0])
        for radius in (7000e3, 26600e3, 42164e3):
            # Sweep through the shadow cone behind the Earth (-x side)
            for ang in np.linspace(math.pi - 0.4, math.pi + 0.4, 801):
                r = radius * np.array([math.cos(ang), math.sin(ang), 0.0])
                g_pen, g_umb = forces.shadow_boundaries(r, r_sun)
                nu = forces.shadow_function(r, r_sun)
                if g_pen > 1e-9:
                    self.assertEqual(nu, 1.0)
                elif g_umb < -1e-9:
                    self.assertEqual(nu, 0.0)
                elif g_pen < -1e-9 and g_umb > 1e-9:
                    self.assertGreater(nu, 0.0)
                    self.assertLess(nu, 1.0)

    def test_shadow_events_follow_epoch(self):
        """The event functions use the Sun at epoch + t, like the equations of motion."""
        from astroflyer.backend.eclipse import shadow_boundary_events
        epoch_tt = float(EPOCH - Epoch.j2000())
        events = shadow_boundary_events(epoch_tt)
        self.assertEqual(len(events), 2)
        r_sun = forces.get_ephemeris().sun_gcrf(epoch_tt + 3600.0)
        r = -7000e3 * r_sun / np.linalg.norm(r_sun)      # deep in umbra
        y = np.concatenate([r, np.zeros(3)])
        g_pen, g_umb = forces.shadow_boundaries(r, r_sun)
        self.assertAlmostEqual(events[0](3600.0, y), g_pen, places=12)
        self.assertAlmostEqual(events[1](3600.0, y), g_umb, places=12)
        self.assertLess(events[1](3600.0, y), 0.0)


def solve_ivp_segmented(*args, **kwargs):
    from astroflyer.backend.eclipse import solve_ivp_segmented as solver
    return solver(*args, **kwargs)


class TestSegmentedSolver(unittest.TestCase):
    KINK = 1.2345

    def _fun(self, t, y):
        return [max(0.0, t - self.KINK)]

    def test_restarts_at_kink_and_fills_t_eval(self):
        t_eval = np.linspace(0.0, 3.0, 31)
        sol = solve_ivp_segmented(self._fun, (0.0, 3.0), [0.0], boundaries=[lambda t, y: t - self.KINK],
                                  t_eval=t_eval, method="DOP853", rtol=1e-12, atol=1e-14)
        self.assertTrue(sol.success)
        np.testing.assert_array_equal(sol.t, t_eval)
        exact = 0.5 * np.maximum(0.0, t_eval - self.KINK) ** 2
        np.testing.assert_allclose(sol.y[0], exact, rtol=0, atol=1e-12)
        self.assertEqual(len(sol.boundary_times), 1)
        self.assertAlmostEqual(sol.boundary_times[0], self.KINK, places=10)

    def test_user_events_pass_through(self):
        def half(t, y):
            return y[0] - 0.5
        sol = solve_ivp_segmented(self._fun, (0.0, 3.0), [0.0], boundaries=[lambda t, y: t - self.KINK],
                                  events=[half], method="DOP853", rtol=1e-12, atol=1e-14)
        self.assertEqual(len(sol.t_events), 1)
        self.assertEqual(len(sol.t_events[0]), 1)
        self.assertAlmostEqual(sol.t_events[0][0], self.KINK + 1.0, places=9)
        self.assertAlmostEqual(sol.y_events[0][0][0], 0.5, places=9)

    def test_no_boundaries_matches_solve_ivp(self):
        from scipy.integrate import solve_ivp
        fun = lambda t, y: [y[1], -y[0]]
        t_eval = np.linspace(0, 10, 11)
        a = solve_ivp(fun, (0, 10), [1.0, 0.0], t_eval=t_eval, method="DOP853", rtol=1e-11, atol=1e-12)
        b = solve_ivp_segmented(fun, (0, 10), [1.0, 0.0], boundaries=[], t_eval=t_eval,
                                method="DOP853", rtol=1e-11, atol=1e-12)
        np.testing.assert_allclose(b.y, a.y, rtol=0, atol=1e-12)


class TestEclipsePropagation(unittest.TestCase):

    def test_molniya_srp_converges_through_eclipses(self):
        """Default and tight tolerances agree, so the shadow kinks no longer cost accuracy."""
        r, v = keplerian_to_cartesian(26600e3, 0.74, math.radians(63.435), math.radians(90.0),
                                      math.radians(270.0), 0.0)
        state = np.concatenate([r, v])

        def run(rtol, atol):
            sol = ThirdReviewEngine(state, epoch=EPOCH).propagate(
                (0.0, 86400.0), num_points=145, model="coupled", method="DOP853", rtol=rtol, atol=atol,
                enable_drag=False, enable_third_body=True, enable_srp=True, enable_relativity=False,
                enable_albedo=False, gravity_degree=8, gravity_order=8, b_star=0.01, cr_area_over_m=0.02)
            return sol["position_m"]

        loose = run(1e-12, 1e-6)
        tight = run(1e-13, 1e-9)
        self.assertLess(np.linalg.norm(loose - tight, axis=1).max(), 0.05)


if __name__ == "__main__":
    unittest.main()
