"""
AstroFlyer HEO - covariance-steered stepping (Innovation 5) through ThirdReviewEngine.propagate.

The state transition matrix the steered run returns is checked against central finite
differences of independently propagated neighbouring trajectories.
"""

import math
import unittest

import numpy as np

from astroflyer.backend.astro_engine import MU_EARTH, ThirdReviewEngine, keplerian_to_cartesian

EPOCH = "2026-10-23T00:00:00Z"
A_MOLNIYA = 26560e3
PERIOD = 2.0 * math.pi * math.sqrt(A_MOLNIYA ** 3 / MU_EARTH)


def molniya_state(ta_deg=5.0):
    r, v = keplerian_to_cartesian(A_MOLNIYA, 0.72, math.radians(63.4), math.radians(30.0),
                                  math.radians(270.0), math.radians(ta_deg))
    return np.concatenate([r, v])


def final_state(y0, duration):
    sol = ThirdReviewEngine(y0, epoch=EPOCH).propagate((0.0, duration), num_points=2, model="j2",
                                                       method="RKF78", rtol=1e-12, atol=1e-12)
    return np.concatenate([sol["position_m"][-1], sol["velocity_ms"][-1]])


class TestCovarianceSteering(unittest.TestCase):

    def test_stm_matches_finite_differences(self):
        y0 = molniya_state()
        duration = 0.25 * PERIOD
        sol = ThirdReviewEngine(y0, epoch=EPOCH).propagate((0.0, duration), num_points=5, model="j2",
                                                           method="RKF78", steering="covariance")
        phi = np.asarray(sol["stm"][-1])
        self.assertEqual(phi.shape, (6, 6))

        deltas = [1.0] * 3 + [1e-3] * 3      # m, m/s
        phi_fd = np.empty((6, 6))
        for j, d in enumerate(deltas):
            dy = np.zeros(6)
            dy[j] = d
            phi_fd[:, j] = (final_state(y0 + dy, duration) - final_state(y0 - dy, duration)) / (2.0 * d)

        rel = np.linalg.norm(phi - phi_fd) / np.linalg.norm(phi_fd)
        self.assertLess(rel, 1e-3, f"STM relative error {rel:.2e}")

    def test_steering_bounds_uncertainty_growth_per_step(self):
        """Each accepted step grows the 1-sigma position uncertainty by at most eta; an
        unsteered run (eta = inf) of the same orbit does not stay inside that bound."""
        eta = 0.02

        def growth(e):
            sol = ThirdReviewEngine(molniya_state(), epoch=EPOCH).propagate(
                (0.0, PERIOD), num_points=3, model="j2", method="RKF78", steering="covariance", steering_eta=e)
            sigma = np.asarray(sol["steps"]["sigma_pos_m"])
            return np.abs(np.diff(sigma)) / sigma[:-1], len(sigma)

        steered, n_steered = growth(eta)
        free, n_free = growth(np.inf)
        self.assertGreater(free.max(), 1.5 * eta)
        self.assertLess(steered.max(), 1.1 * eta)
        self.assertGreater(n_steered, n_free)

    def test_eta_must_be_positive(self):
        for eta in (0.0, -0.1, float("nan")):
            with self.subTest(eta=eta), self.assertRaises(ValueError):
                ThirdReviewEngine(molniya_state(), epoch=EPOCH).propagate(
                    (0.0, 600.0), num_points=2, model="j2", method="RKF78", steering="covariance", steering_eta=eta)


if __name__ == "__main__":
    unittest.main()
