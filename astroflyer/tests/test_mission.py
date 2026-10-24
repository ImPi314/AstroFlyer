"""
AstroFlyer HEO - Phase 3 gate: spacecraft, element sets, maneuvers and targeting.
"""

import math
import unittest

import numpy as np

from astroflyer.backend import mission as M
from astroflyer.backend.forces import MU_EARTH, R_EARTH_EQ

EPOCH = "2026-10-23T00:00:00Z"


def molniya(**properties):
    return M.Spacecraft.from_keplerian(EPOCH, 26560e3, 0.72, 63.4, 30.0, 270.0, 40.0, **properties)


class TestElementSets(unittest.TestCase):

    def test_round_trips(self):
        for args in ((26560e3, 0.72, 63.4, 30.0, 270.0, 40.0), (7000e3, 0.001, 98.2, 200.0, 10.0, 300.0),
                     (42164e3, 0.0, 0.0, 0.0, 0.0, 75.0)):
            sc = M.Spacecraft.from_keplerian(EPOCH, *args)
            eq = sc.equinoctial()
            back = M.Spacecraft.from_equinoctial(EPOCH, *(eq[k] for k in ("a", "h", "k", "p", "q", "mean_longitude")))
            np.testing.assert_allclose(back.r, sc.r, atol=1e-5)
            np.testing.assert_allclose(back.v, sc.v, atol=1e-8)
            mee = sc.modified_equinoctial()
            back = M.Spacecraft.from_modified_equinoctial(EPOCH, *(mee[k] for k in ("p", "f", "g", "h", "k", "L")))
            np.testing.assert_allclose(back.r, sc.r, atol=1e-5)
            np.testing.assert_allclose(back.v, sc.v, atol=1e-8)

    def test_keplerian_matches_inputs(self):
        k = molniya().keplerian()
        self.assertAlmostEqual(k["a"], 26560e3, delta=1e-4)
        self.assertAlmostEqual(k["e"], 0.72, places=12)
        for key, deg in (("inc", 63.4), ("raan", 30.0), ("argp", 270.0), ("ta", 40.0)):
            self.assertAlmostEqual(math.degrees(k[key]), deg, places=9, msg=key)


class TestManeuvers(unittest.TestCase):

    def test_impulsive_burn_frames_and_rocket_equation(self):
        sc = molniya(dry_mass_kg=1000.0, fuel_mass_kg=500.0)
        v_hat = sc.v / np.linalg.norm(sc.v)
        out = M.ImpulsiveBurn([10.0, 0.0, 0.0], "VNC", isp_s=300.0).apply(sc)
        np.testing.assert_allclose((sc.v - molniya().v) / 10.0, v_hat, atol=1e-12)
        self.assertAlmostEqual(out["fuel_used_kg"], 1500.0 * (1.0 - math.exp(-10.0 / (300.0 * M.G0))), places=9)
        self.assertAlmostEqual(sc.mass_kg, 1500.0 - out["fuel_used_kg"], places=9)

        sc = molniya()
        M.ImpulsiveBurn([5.0, 0.0, 0.0], "RTN").apply(sc)
        np.testing.assert_allclose((sc.v - molniya().v) / 5.0, sc.r / np.linalg.norm(sc.r), atol=1e-12)

    def test_burn_refused_without_fuel(self):
        with self.assertRaises(ValueError):
            M.ImpulsiveBurn([3000.0, 0.0, 0.0]).apply(molniya(fuel_mass_kg=10.0))

    def test_finite_burn_mass_flow_and_gravity_loss(self):
        leo = M.Spacecraft.from_keplerian(EPOCH, R_EARTH_EQ + 700e3, 0.0, 28.5, 0.0, 0.0, 0.0,
                                          dry_mass_kg=1000.0, fuel_mass_kg=800.0)
        burn = M.FiniteBurn(thrust_n=2000.0, isp_s=320.0)
        prop = M.Propagator("two_body")
        sc = prop.step(leo.copy(), duration=600.0, burn=burn)
        self.assertAlmostEqual(800.0 - sc.fuel_mass_kg, burn.mass_flow_kg_s * 600.0, places=6)
        # The same apogee from one impulsive burn needs less delta-v than the finite burn spent
        dv_finite = 320.0 * M.G0 * math.log(1800.0 / sc.mass_kg)
        r0 = np.linalg.norm(leo.r)
        ra = sc.keplerian()["ra"]
        dv_impulsive = math.sqrt(MU_EARTH / r0) * (math.sqrt(2.0 * ra / (r0 + ra)) - 1.0)
        self.assertGreater(dv_finite, dv_impulsive)
        self.assertLess(dv_finite, 1.1 * dv_impulsive)


class TestPropagator(unittest.TestCase):

    def test_step_to_events(self):
        prop = M.Propagator("two_body")
        sc = prop.step(molniya(), until="apogee")
        k = sc.keplerian()
        self.assertAlmostEqual(math.degrees(k["ta"]), 180.0, places=6)
        prop.step(sc, until="ascending_node")
        self.assertLess(abs(sc.r[2]), 1e-3)
        self.assertGreater(sc.v[2], 0.0)
        prop.step(sc, until="perigee")
        self.assertLess(abs(sc.r @ sc.v) / (np.linalg.norm(sc.r) * np.linalg.norm(sc.v)), 1e-10)
        self.assertEqual([h[0] for h in sc.history], ["to apogee", "to ascending_node", "to perigee"])

    def test_step_by_duration_matches_kepler(self):
        sc = molniya()
        period = sc.keplerian()["period"]
        M.Propagator("two_body").step(sc, duration=period)
        np.testing.assert_allclose(sc.r, molniya().r, atol=0.05)
        self.assertAlmostEqual(sc.epoch - molniya().epoch, period, places=6)


class TestDifferentialCorrector(unittest.TestCase):

    def test_solves_a_nonlinear_system(self):
        dc = M.DifferentialCorrector().vary("x", 1.0, 1e-6).vary("y", 1.0, 1e-6)
        dc.achieve("f", 0.0, 1e-10).achieve("g", 0.0, 1e-10)
        res = dc.solve(lambda v: {"f": v["x"] ** 2 + v["y"] ** 2 - 4.0, "g": v["x"] - v["y"]})
        self.assertTrue(res.converged)
        self.assertAlmostEqual(res.values["x"], math.sqrt(2.0), places=6)

    def test_gto_to_geo(self):
        out = M.target_gto_to_geo(EPOCH)
        self.assertTrue(out["converged"], out["message"])
        self.assertLess(out["final_orbit"]["ecc"], 1e-5)
        self.assertLess(out["final_orbit"]["inc_deg"], 1e-3)
        # Textbook combined circularize + 28.5 deg plane change at GEO is about 1.83 km/s
        self.assertAlmostEqual(out["delta_v_ms"], 1835.0, delta=10.0)

    def test_molniya_perigee_raise(self):
        out = M.target_perigee_raise(EPOCH, perigee_alt_km=450.0, target_perigee_alt_km=600.0)
        self.assertTrue(out["converged"], out["message"])
        self.assertAlmostEqual(out["achieved"]["perigee_alt_km"], 600.0, delta=0.01)
        self.assertTrue(5.0 < out["delta_v_ms"] < 30.0)

    def test_finite_burn_duration_targeting(self):
        leo = M.Spacecraft.from_keplerian(EPOCH, R_EARTH_EQ + 700e3, 0.0, 28.5, 0.0, 0.0, 0.0,
                                          dry_mass_kg=1000.0, fuel_mass_kg=1500.0)
        burn = M.FiniteBurn(thrust_n=2000.0, isp_s=320.0)
        prop = M.Propagator("two_body")
        dc = M.DifferentialCorrector().vary("t", 300.0, 1.0, max_step=300.0, lower=0.0)
        dc.achieve("ha_km", 12000.0, 1.0)

        def mission(v):
            sc = prop.step(leo.copy(), duration=v["t"], burn=burn)
            return {"ha_km": (sc.keplerian()["ra"] - R_EARTH_EQ) / 1e3}

        res = dc.solve(mission)
        self.assertTrue(res.converged, res.message)
        self.assertAlmostEqual(res.achieved["ha_km"], 12000.0, delta=1.0)


if __name__ == "__main__":
    unittest.main()
