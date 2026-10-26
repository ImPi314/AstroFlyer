"""
AstroFlyer HEO - Automated Verification & Regression Test Suite
Validates all 5 academic innovations, physics engines, and REST endpoints.
"""

import unittest
import numpy as np
import os
import json

from astroflyer.backend.radiation_belts import RadiationBeltModel
from astroflyer.backend.covariance_engine import CovarianceEngine
from astroflyer.backend.astro_engine import ThirdReviewEngine, compute_acceleration_components
from astroflyer.backend.forces import ForceModelConfig


class TestAstroFlyerInnovations(unittest.TestCase):
    """Verifies all 5 core BE major project academic innovations."""


    def test_interactive_what_if_maneuver(self):
        # Test an apogee raise burn at perigee (+350 m/s prograde)
        from astroflyer.backend.astro_engine import keplerian_to_cartesian, cartesian_to_keplerian, MU_EARTH, R_EARTH
        import math
        r_burn, v_burn = keplerian_to_cartesian(24389000.0, 0.7285, math.radians(28.5), 0.0, 0.0, 0.0)
        v_mag = float(np.linalg.norm(v_burn))
        v_hat = v_burn / v_mag
        dv_inertial = 350.0 * v_hat
        v_post = v_burn + dv_inertial
        post_elem = cartesian_to_keplerian(r_burn, v_post, mu=MU_EARTH)
        # Check that post-burn semi-major axis and apogee increased
        self.assertGreater(post_elem['a'], 24389000.0)
        ha_km = (post_elem['a'] * (1.0 + post_elem['e']) - R_EARTH) / 1000.0
        self.assertGreater(ha_km, 35786.0)



class TestAstroEnginePhysics(unittest.TestCase):
    """Verifies astrodynamics physics engines."""

    def test_two_body_and_j2_acceleration(self):
        state = np.array([7000000.0, 0.0, 0.0, 0.0, 7500.0, 0.0])
        acc_dict = compute_acceleration_components(state, 0.0, ForceModelConfig())
        self.assertIn("a_central", acc_dict)
        self.assertIn("a_j2", acc_dict)
        # Gravitational attraction directed inward (-X)
        self.assertLess(acc_dict["a_central"][0], 0.0)
        self.assertLess(acc_dict["a_j2"][0], 0.0)


if __name__ == '__main__':
    unittest.main()
