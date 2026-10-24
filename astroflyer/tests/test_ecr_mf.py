"""
AstroFlyer HEO - ECR-MF regime switching (Innovation 1) through ThirdReviewEngine.propagate.

fidelity='ecr_mf' lowers the gravity degree away from perigee. The run is checked
against the same orbit propagated with the full model throughout.
"""

import math
import unittest

import numpy as np

from astroflyer.backend import forces
from astroflyer.backend.astro_engine import MU_EARTH, ThirdReviewEngine, keplerian_to_cartesian

EPOCH = "2026-01-01T00:00:00Z"
A_MOLNIYA = 26560e3
DAY = 86400.0


def molniya_state():
    r, v = keplerian_to_cartesian(A_MOLNIYA, 0.72, math.radians(63.4), math.radians(30.0),
                                  math.radians(270.0), math.radians(5.0))
    return np.concatenate([r, v])


def run(**extra):
    return ThirdReviewEngine(molniya_state(), epoch=EPOCH).propagate(
        (0.0, DAY), num_points=1441, method="DOP853", gravity_degree=20, gravity_order=20, **extra)


def crossing_times(t, r, radius):
    """Times where r(t) crosses `radius`, by linear interpolation between output samples."""
    g = r - radius
    idx = np.nonzero(np.sign(g[:-1]) != np.sign(g[1:]))[0]
    return t[idx] - g[idx] * (t[idx + 1] - t[idx]) / (g[idx + 1] - g[idx])


class TestECRMF(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.full = run()
        cls.ecr = run(fidelity="ecr_mf")

    def test_switches_where_the_orbit_crosses_each_tier_boundary_and_matches_the_full_model(self):
        t = np.asarray(self.full["times"])
        r = np.linalg.norm(np.asarray(self.full["position_m"]), axis=1)
        report = self.ecr["ecr_mf"]
        boundaries = sorted({tier["r_inner_m"] for tier in report["tiers"] if tier["r_inner_m"] > 0})
        self.assertGreaterEqual(len(boundaries), 2)

        expected = np.sort(np.concatenate([crossing_times(t, r, b) for b in boundaries]))
        switched = np.sort([s["t_s"] for s in report["switches"]])
        self.assertEqual(len(switched), len(expected))
        self.assertLess(np.max(np.abs(switched - expected)), 1.0)

        diff = np.linalg.norm(np.asarray(self.ecr["position_m"]) - np.asarray(self.full["position_m"]), axis=1)
        self.assertLess(diff.max(), 1.0, f"ECR-MF departs from the full model by {diff.max():.3f} m")

    def test_each_tier_certifies_a_bound_its_omitted_gravity_never_exceeds(self):
        """The certificate's bound must hold for the gravity actually left out along the run,
        and stay inside the run's epsilon; at least one tier must actually drop degrees."""
        report = self.ecr["ecr_mf"]
        pos = np.asarray(self.ecr["position_m"])
        r = np.linalg.norm(pos, axis=1)
        dropped = False
        for tier in report["tiers"]:
            self.assertLessEqual(tier["omitted_bound_ms2"], report["epsilon_ms2"])
            inside = (r >= tier["r_inner_m"]) & (r < tier["r_outer_m"])
            if tier["gravity_degree"] == 20 or not inside.any():
                continue
            dropped = True
            for p in pos[inside][::10]:
                omitted = forces.harmonic_acceleration_body(p, 20, 20) - forces.harmonic_acceleration_body(
                    p, tier["gravity_degree"], tier["gravity_order"])
                self.assertLessEqual(np.linalg.norm(omitted), tier["omitted_bound_ms2"])
        self.assertTrue(dropped)


if __name__ == "__main__":
    unittest.main()
