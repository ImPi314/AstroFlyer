"""
AstroFlyer HEO - covariance engine gravity gradient.

Every entry of the point-mass + J2 gravity gradient G = d(a)/d(r) is checked against central
finite differences of the point-mass + J2 acceleration with the engine's own constants.
"""

import unittest

import numpy as np

from astroflyer.backend.covariance_engine import J2_EARTH, MU_EARTH, R_EARTH, CovarianceEngine


def accel_pm_j2(r_vec):
    x, y, z = r_vec
    r = np.linalg.norm(r_vec)
    k = 1.5 * J2_EARTH * MU_EARTH * R_EARTH ** 2 / r ** 5
    s = 5.0 * z * z / (r * r)
    a_j2 = k * np.array([x * (s - 1.0), y * (s - 1.0), z * (s - 3.0)])
    return -MU_EARTH / r ** 3 * r_vec + a_j2


def finite_difference_gradient(r_vec, h=50.0):
    G = np.zeros((3, 3))
    for j in range(3):
        dr = np.zeros(3)
        dr[j] = h
        G[:, j] = (accel_pm_j2(r_vec + dr) - accel_pm_j2(r_vec - dr)) / (2.0 * h)
    return G


class GravityGradientTests(unittest.TestCase):
    POSITIONS = [
        np.array([6700e3, 1200e3, 2500e3]),
        np.array([-3000e3, 5000e3, -4800e3]),
        np.array([1000e3, -500e3, 7000e3]),
        np.array([30000e3, 20000e3, 25000e3]),
    ]

    def test_every_entry_matches_finite_differences(self):
        engine = CovarianceEngine()
        for r_vec in self.POSITIONS:
            G = engine.compute_gravity_gradient(r_vec)
            G_fd = finite_difference_gradient(r_vec)
            G_j2_fd = G_fd - (-(MU_EARTH / np.linalg.norm(r_vec) ** 3) * np.eye(3)
                              + 3.0 * MU_EARTH / np.linalg.norm(r_vec) ** 5 * np.outer(r_vec, r_vec))
            scale = np.max(np.abs(G_j2_fd))
            # The J2 part is ~1e-3 of the total; compare to 1e-4 of the J2 part.
            np.testing.assert_allclose(G, G_fd, rtol=0.0, atol=1e-4 * scale)

    def test_gradient_is_symmetric_and_trace_free(self):
        G = CovarianceEngine().compute_gravity_gradient(np.array([5000e3, 3000e3, 4000e3]))
        np.testing.assert_allclose(G, G.T, rtol=0.0, atol=1e-20)
        self.assertLess(abs(np.trace(G)), 1e-12 * np.max(np.abs(G)))


if __name__ == "__main__":
    unittest.main()
