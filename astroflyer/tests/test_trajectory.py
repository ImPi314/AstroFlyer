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


if __name__ == "__main__":
    unittest.main()
