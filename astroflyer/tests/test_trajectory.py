"""
AstroFlyer HEO - One trajectory integration for every propagation (backend/trajectory.py).
Every integrator restarts at shadow edges and drag-model jumps, so the choice of integrator
does not change the answer beyond its own tolerance. Written before the implementation.
"""

import unittest

import numpy as np

from astroflyer.backend.astro_engine import keplerian_to_cartesian
from astroflyer.backend.epoch import Epoch
from astroflyer.backend.forces import ForceModelConfig
from astroflyer.validation import cases as C

EPOCH = Epoch.from_iso(C.EPOCH_ISO_TT, scale="TT")
WEEK = 7 * 86400.0


def _state(orbit):
    a, e, i, raan, argp, nu = C.ORBITS[orbit]
    r, v = keplerian_to_cartesian(a, e, *np.radians([i, raan, argp, nu]))
    return np.concatenate([r, v])


def _srp_model():
    # 8x8 gravity, Sun and Moon, SRP with its shadow, drag: the cross-check's L6
    return ForceModelConfig.for_model("coupled", gravity_degree=8, gravity_order=8, relativity=False,
                                      albedo=False, cd_area_over_m=C.CD_AREA_OVER_M,
                                      cr_area_over_m=C.CR_AREA_OVER_M)


class TrajectoryIntegrationTest(unittest.TestCase):

    def test_every_integrator_restarts_at_shadow_edges(self):
        # Tundra crosses the Earth's shadow; without restarts RKF7(8) ended 24.8 m from DOP853 here
        from astroflyer.backend.trajectory import integrate_trajectory
        y0 = _state("tundra")
        ends = {m: integrate_trajectory(y0, (0.0, WEEK), EPOCH, _srp_model(), method=m,
                                        rtol=1e-12, atol=1e-6).y[:3, -1]
                for m in ("DOP853", "RKF78")}
        self.assertLess(np.linalg.norm(ends["RKF78"] - ends["DOP853"]), 1.0)


class SurfaceImpactTest(unittest.TestCase):

    def test_every_integrator_stops_at_the_surface(self):
        # 300 km up over the equator at 5 km/s, far below circular speed: it falls in within minutes.
        # The run must end on the WGS-84 surface, not carry on through the Earth.
        from astroflyer.backend.frames import gcrf_to_geodetic
        from astroflyer.backend.trajectory import integrate_trajectory
        y0 = np.array([6678137.0, 0.0, 0.0, 0.0, 5000.0, 0.0])
        model = ForceModelConfig.for_model("two_body")
        hour = 3600.0
        impacts = {}
        for method in ("DOP853", "RKF78"):
            for t_eval in (None, np.linspace(0.0, hour, 61)):
                sol = integrate_trajectory(y0, (0.0, hour), EPOCH, model, method=method, t_eval=t_eval)
                self.assertIsNotNone(sol.impact, method)
                self.assertLess(sol.impact["t_s"], hour)
                self.assertEqual(sol.t[-1], sol.impact["t_s"])          # the run ends at the impact
                height = np.ravel(gcrf_to_geodetic(np.atleast_2d(sol.y[:3, -1]), EPOCH)[2])[0]
                self.assertLess(abs(height), 1.0, method)
                impacts[method] = sol.impact["t_s"]
        self.assertAlmostEqual(impacts["DOP853"], impacts["RKF78"], delta=1e-3)

    def test_an_orbit_clear_of_the_surface_has_no_impact(self):
        from astroflyer.backend.trajectory import integrate_trajectory
        sol = integrate_trajectory(_state("molniya"), (0.0, 3600.0), EPOCH, ForceModelConfig.for_model("two_body"))
        self.assertIsNone(sol.impact)
        self.assertEqual(sol.t[-1], 3600.0)


if __name__ == "__main__":
    unittest.main()
