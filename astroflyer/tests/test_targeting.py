"""
AstroFlyer HEO - the Targeting page solves on the run's own force model.

The apogee raise used to be vis-viva (two-body) from a typed radius and speed, and the finite
burn a rocket-equation estimate with a fixed 0.35 deg flight-path angle for gravity losses. Both
now start from the run's first perigee (its epoch, state, force model and spacecraft), the apogee
raise is a differential corrector on the propagated apogee, and the finite burn is integrated
with mass flow and compared with the impulsive burn of the same velocity change. Written before
the implementation.
"""

import json
import math
import threading
import unittest
import urllib.request

import numpy as np

from astroflyer.backend import mission as M
from astroflyer.backend.differential_corrector import G0, simulate_finite_burn, solve_apogee_raise
from astroflyer.backend.forces import MU_EARTH, ForceModelConfig

GTO = {"hp": 250.0, "ha": 35786.0, "inc": 28.5, "raan": 45.0, "aop": 30.0, "ta": 200.0,
       "epoch": "2026-03-15T00:00:00Z", "mass": 1500.0, "cd": 2.2, "drag_area": 15.0, "cr": 1.2,
       "srp_area": 15.0, "tolerance": 1e-10, "method": "DOP853"}


def perigee_state(req):
    """The run's first perigee found independently with mission.Propagator."""
    from astroflyer.backend.propagation_run import _Request, initial_conditions
    q = _Request(req)
    _, r0, v0, _ = initial_conditions(q)
    sc = M.Spacecraft(req["epoch"], r0, v0, dry_mass_kg=0.0, fuel_mass_kg=req["mass"], cd=req["cd"],
                      drag_area_m2=req["drag_area"], cr=req["cr"], srp_area_m2=req["srp_area"])
    prop = M.Propagator(ForceModelConfig.for_model(req["model"]), "DOP853", rtol=1e-10, atol=1e-10)
    return prop, prop.step(sc, until="perigee")


class ApogeeRaiseTest(unittest.TestCase):

    def test_two_body_matches_vis_viva(self):
        req = {**GTO, "model": "two_body"}
        out = solve_apogee_raise(req, 42164.0)
        _, sc = perigee_state(req)
        rp, vp = np.linalg.norm(sc.r), np.linalg.norm(sc.v)
        a = (rp + 42164e3) / 2.0
        dv = math.sqrt(MU_EARTH * (2.0 / rp - 1.0 / a)) - vp
        self.assertTrue(out["converged"])
        self.assertAlmostEqual(out["optimal_delta_v_ms"], dv, delta=0.01)
        self.assertAlmostEqual(out["achieved_apogee_km"], 42164.0, delta=0.01)
        self.assertAlmostEqual(out["perigee_radius_km"], rp / 1000.0, delta=1e-3)

    def test_j2_solution_reaches_the_target_on_the_j2_model(self):
        req = {**GTO, "model": "j2"}
        out = solve_apogee_raise(req, 60000.0)
        self.assertTrue(out["converged"])
        prop, sc = perigee_state(req)
        sc.v = sc.v + out["optimal_delta_v_ms"] * sc.v / np.linalg.norm(sc.v)
        prop.step(sc, until="apogee")
        self.assertAlmostEqual(np.linalg.norm(sc.r) / 1000.0, 60000.0, delta=0.05)
        # J2 moves the answer away from the two-body one by more than the targeting tolerance
        self.assertGreater(abs(out["optimal_delta_v_ms"] - out["two_body_delta_v_ms"]), 0.01)

    def test_burn_is_at_the_first_perigee_after_the_epoch(self):
        out = solve_apogee_raise({**GTO, "model": "two_body"}, 42164.0)
        self.assertGreater(out["perigee_offset_s"], 0.0)
        self.assertEqual(out["model"], "two_body")


class FiniteBurnTest(unittest.TestCase):

    def test_mass_flow_and_duration_follow_the_rocket_equation(self):
        out = simulate_finite_burn({**GTO, "model": "two_body"}, 500.0, thrust_n=450.0, isp_s=315.0)
        prop = 1500.0 * (1.0 - math.exp(-500.0 / (315.0 * G0)))
        self.assertAlmostEqual(out["propellant_consumed_kg"], prop, delta=0.01)
        self.assertAlmostEqual(out["burn_duration_s"], prop / (450.0 / (315.0 * G0)), delta=0.01)
        self.assertAlmostEqual(out["final_mass_kg"], 1500.0 - prop, delta=0.01)

    def test_a_long_burn_loses_against_the_impulsive_burn(self):
        out = simulate_finite_burn({**GTO, "model": "two_body"}, 500.0, thrust_n=450.0, isp_s=315.0)
        self.assertLess(out["apogee_after_finite_km"], out["apogee_after_impulsive_km"])
        self.assertGreater(out["gravity_losses_ms"], 0.0)
        self.assertAlmostEqual(out["actual_effective_delta_v_ms"] + out["gravity_losses_ms"], 500.0, delta=1e-6)

    def test_a_short_burn_is_nearly_impulsive(self):
        out = simulate_finite_burn({**GTO, "model": "two_body"}, 5.0, thrust_n=4000.0, isp_s=315.0)
        self.assertLess(out["gravity_losses_ms"], 0.01)

    def test_a_burn_to_escape_reports_mass_and_duration_without_an_apogee(self):
        # 1,478 m/s at a 250 km GTO perigee exceeds escape speed: there is no apogee to compare
        out = simulate_finite_burn({**GTO, "model": "two_body"}, 1478.0, thrust_n=450.0, isp_s=315.0)
        self.assertIsNone(out["apogee_after_impulsive_km"])
        self.assertIsNone(out["gravity_losses_ms"])
        self.assertIn("escape", out["note"])
        self.assertAlmostEqual(out["propellant_consumed_kg"], 1500.0 * (1.0 - math.exp(-1478.0 / (315.0 * G0))),
                               delta=0.01)

    def test_a_spacecraft_without_mass_the_spacecraft_holds_is_refused(self):
        with self.assertRaisesRegex(ValueError, "mass"):
            simulate_finite_burn({**GTO, "model": "two_body"}, 5.0, thrust_n=450.0, isp_s=315.0, mass_kg=0.0)


class TargetingEndpointTest(unittest.TestCase):

    def test_endpoints_take_the_run_request(self):
        from astroflyer.backend.app_server import create_server
        server = create_server(port=0)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        base = f"http://127.0.0.1:{server.server_address[1]}"
        for path, extra in (("/api/targeting/differential_corrector", {"target_ra_km": 42164.0}),
                            ("/api/targeting/finite_burn", {"delta_v_ms": 100.0, "thrust_n": 450.0,
                                                            "isp_s": 315.0})):
            body = json.dumps({**GTO, "model": "two_body", **extra}).encode()
            req = urllib.request.Request(base + path, body, {"Content-Type": "application/json"})
            out = json.load(urllib.request.urlopen(req, timeout=300))
            self.assertIsNone(out.get("error"), out.get("error"))
            self.assertEqual(out["model"], "two_body")


if __name__ == "__main__":
    unittest.main()
