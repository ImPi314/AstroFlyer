"""
AstroFlyer HEO - Automated Verification & Regression Test Suite
Validates all 5 academic innovations, physics engines, and REST endpoints.
"""

import unittest
import numpy as np
import os
import json

from astroflyer.backend.ecr_mf_controller import ECRMFController
from astroflyer.backend.radiation_belts import RadiationParetoOptimizer, RadiationBeltModel
from astroflyer.backend.differential_corrector import MultiBurnPerigeePumpingPlanner, DifferentialCorrector
from astroflyer.backend.constellation_engine import MolniyaConstellationEngine
from astroflyer.backend.covariance_engine import CovarianceSteeredAdaptiveStepController, CovarianceEngine
from astroflyer.backend.astro_engine import ThirdReviewEngine, compute_acceleration_components


class TestAstroFlyerInnovations(unittest.TestCase):
    """Verifies all 5 core BE major project academic innovations."""

    def test_innovation_1_ecr_mf_controller(self):
        controller = ECRMFController()
        # Perigee state: altitude 600 km, speed 10.2 km/s, true anomaly 0 deg -> Tier 3
        decision_perigee = controller.evaluate_segment_mode(
            altitude_km=600.0,
            velocity_kms=10.2,
            true_anomaly_deg=0.0,
            r_vec=np.array([6978.137, 0.0, 0.0]),
            v_vec=np.array([0.0, 10.2, 0.0])
        )
        self.assertEqual(decision_perigee["tier_code"], "TIER_3")
        self.assertTrue(decision_perigee["certified"])

        # Apogee state: altitude 39,900 km, speed 1.5 km/s, true anomaly 180 deg -> Tier 1
        decision_apogee = controller.evaluate_segment_mode(
            altitude_km=39900.0,
            velocity_kms=1.5,
            true_anomaly_deg=180.0,
            r_vec=np.array([-46278.0, 0.0, 0.0]),
            v_vec=np.array([0.0, -1.5, 0.0])
        )
        self.assertEqual(decision_apogee["tier_code"], "TIER_1")

        # Generate formal safety certificate
        segment_data = {"energy_fractional_error": 1.42e-12}
        cert = controller.generate_safety_certificate(
            orbit_index=1,
            segment_data=segment_data,
            mode_info=decision_perigee
        )
        self.assertEqual(cert["verification_status"], "CERTIFIED_VALID")
        self.assertTrue(cert["sha256_verification_token"].startswith("0x"))

    def test_innovation_2_radiation_pareto(self):
        optimizer = RadiationParetoOptimizer()
        result = optimizer.evaluate_pareto_frontier()
        self.assertIn("pareto_sweet_spot", result)
        sweet_spot = result["pareto_sweet_spot"]
        self.assertGreater(sweet_spot["perigee_altitude_km"], 400.0)
        self.assertLess(sweet_spot["cumulative_5yr_tid_krad"], 50.0)

    def test_innovation_3_perigee_pumping(self):
        planner = MultiBurnPerigeePumpingPlanner()
        plan = planner.plan_perigee_pumping(
            r_perigee_km=6628.0,
            initial_apogee_km=35786.0,
            target_apogee_km=384400.0,
            wet_mass_kg=1500.0,
            num_burns=5
        )
        self.assertEqual(len(plan["maneuvers"]), 5)
        self.assertGreater(plan["gravity_loss_savings_ms"], 10.0)
        self.assertGreater(plan["gravity_loss_savings_propellant_kg"], 2.0)

    def test_innovation_4_molniya_constellation(self):
        engine = MolniyaConstellationEngine()
        sim = engine.propagate_constellation(duration_hours=24.0, num_steps=120)
        self.assertEqual(len(sim["satellites"]), 3)
        self.assertEqual(sim["handover_analysis"]["unbroken_coverage_availability_pct"], 100.0)
        self.assertGreater(sim["handover_analysis"]["total_handovers_in_24h"], 0)

    def test_innovation_5_covariance_steered_step(self):
        controller = CovarianceSteeredAdaptiveStepController(base_tolerance=1e-11)
        # Moderate condition number
        Phi_mild = np.eye(6) * 1.5
        P_mild = np.eye(6) * 100.0
        res_mild = controller.compute_covariance_steered_step_factor(Phi_mild, P_mild)
        self.assertGreaterEqual(res_mild["step_size_damping_multiplier"], 0.8)

        # Extreme condition number (near perigee singularity)
        Phi_extreme = np.diag([1e5, 1e5, 1e5, 1e-5, 1e-5, 1e-5])
        P_extreme = np.eye(6) * 10000.0
        res_extreme = controller.compute_covariance_steered_step_factor(Phi_extreme, P_extreme)
        self.assertLess(res_extreme["step_size_damping_multiplier"], res_mild["step_size_damping_multiplier"])
        self.assertEqual(res_extreme["steering_action"], "REDUCING_STEP (High Variational Gradient)")

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
        acc_dict = compute_acceleration_components(state, 0.0)
        self.assertIn("a_central", acc_dict)
        self.assertIn("a_j2", acc_dict)
        # Gravitational attraction directed inward (-X)
        self.assertLess(acc_dict["a_central"][0], 0.0)
        self.assertLess(acc_dict["a_j2"][0], 0.0)


if __name__ == '__main__':
    unittest.main()
