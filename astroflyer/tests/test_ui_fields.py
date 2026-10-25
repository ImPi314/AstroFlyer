"""
AstroFlyer HEO - fields the UI reads from a propagation run:
timeline events, Sun direction, Earth-fixed states and the epoch in each time scale.
"""

import math
import unittest

import erfa
import numpy as np

from astroflyer.backend import frames as F
from astroflyer.backend.astro_engine import MU_EARTH, ThirdReviewEngine, keplerian_to_cartesian
from astroflyer.backend.epoch import Epoch

EPOCH = "2026-10-23T00:00:00Z"
A_MOLNIYA = 26560e3


def molniya_state(ta_deg=0.0, e=0.72):
    r, v = keplerian_to_cartesian(A_MOLNIYA, e, math.radians(63.4), math.radians(30.0),
                                  math.radians(270.0), math.radians(ta_deg))
    return np.concatenate([r, v])


def run(y0, t_end, epoch=EPOCH, points=200):
    return ThirdReviewEngine(y0, epoch=epoch).propagate((0.0, t_end), num_points=points, model="two_body")


class TestOrbitEvents(unittest.TestCase):

    def test_analytic_kepler_over_whole_orbits_from_perigee(self):
        """A run that starts and ends at perigee has r.v = 0 to rounding at both ends; the
        analytic propagator must still find its events instead of failing in the root finder."""
        from astroflyer.backend.propagation_run import run as run_propagation
        for orbits in (1, 2, 3):
            out = run_propagation({"hp": 1000, "ha": 39350, "inc": 63.4, "raan": 45, "aop": 270, "ta": 0,
                                   "method": "KEPLER", "model": "two_body", "num_orbits": orbits,
                                   "epoch": "2026-01-01T00:00:00"})
            kinds = [ev["type"] for ev in out["events"]]
            self.assertEqual((kinds.count("perigee"), kinds.count("apogee")), (orbits, orbits))

    def test_apsides_and_nodes_on_a_kepler_orbit(self):
        period = 2.0 * math.pi * math.sqrt(A_MOLNIYA ** 3 / MU_EARTH)
        # Start a little after perigee so the first perigee is not at t = 0
        sol = run(molniya_state(ta_deg=5.0), 2.0 * period)
        events = sol["events"]
        self.assertEqual([ev["t_s"] for ev in events], sorted(ev["t_s"] for ev in events))

        perigees = [ev["t_s"] for ev in events if ev["type"] == "perigee"]
        apogees = [ev["t_s"] for ev in events if ev["type"] == "apogee"]
        self.assertEqual(len(perigees), 2)
        self.assertEqual(len(apogees), 2)
        self.assertAlmostEqual(perigees[1] - perigees[0], period, delta=1e-3)
        self.assertAlmostEqual(apogees[0] - (perigees[0] - period / 2.0), 0.0, delta=1e-3)

        # Argument of perigee 270 deg puts perigee farthest south, so starting just past it
        # the order is ascending node, apogee, descending node, perigee
        kinds = [ev["type"] for ev in events]
        self.assertEqual(kinds, ["ascending_node", "apogee", "descending_node", "perigee"] * 2)

        first = events[0]
        self.assertEqual(first["utc"], (Epoch.from_iso(EPOCH) + first["t_s"]).iso("UTC"))

    def test_events_survive_the_shadow_restarts(self):
        # With SRP on, SciPy runs restart at each shadow edge; apsides and nodes must still come through
        period = 2.0 * math.pi * math.sqrt(A_MOLNIYA ** 3 / MU_EARTH)
        sol = ThirdReviewEngine(molniya_state(ta_deg=5.0), epoch=EPOCH).propagate(
            (0.0, 1.1 * period), num_points=200, model="coupled", method="DOP853", enable_srp=True)
        kinds = [ev["type"] for ev in sol["events"]]
        self.assertEqual(kinds[:4], ["ascending_node", "apogee", "descending_node", "perigee"])

    def test_starting_at_perigee_and_on_a_node_is_reported_once(self):
        sol = run(molniya_state(ta_deg=0.0), 3600.0)
        starts = [ev["type"] for ev in sol["events"] if ev["t_s"] == 0.0]
        self.assertEqual(starts, ["perigee"])
        # Argument of perigee 0 puts the start on the ascending node as well
        r, v = keplerian_to_cartesian(A_MOLNIYA, 0.72, math.radians(63.4), 0.0, 0.0, 0.0)
        sol = run(np.concatenate([r, v]), 3600.0)
        starts = sorted(ev["type"] for ev in sol["events"] if ev["t_s"] == 0.0)
        self.assertEqual(starts, ["ascending_node", "perigee"])

    def test_node_is_on_the_equator_and_apogee_is_farthest(self):
        period = 2.0 * math.pi * math.sqrt(A_MOLNIYA ** 3 / MU_EARTH)
        sol = run(molniya_state(ta_deg=5.0), period, points=2000)
        t = sol["times"]
        r = np.linalg.norm(sol["position_m"], axis=1)
        apogee = next(ev for ev in sol["events"] if ev["type"] == "apogee")
        self.assertAlmostEqual(apogee["t_s"], t[np.argmax(r)], delta=2.0 * (t[1] - t[0]))
        node = next(ev for ev in sol["events"] if ev["type"] == "ascending_node")
        z = np.interp(node["t_s"], t, sol["position_m"][:, 2])
        self.assertLess(abs(z), 5e3)    # linear interpolation of the samples

    def test_near_circular_orbit_has_no_apsides(self):
        r, v = keplerian_to_cartesian(7000e3, 1e-6, math.radians(51.6), 0.0, 0.0, 0.0)
        sol = run(np.concatenate([r, v]), 12000.0)
        kinds = {ev["type"] for ev in sol["events"]}
        self.assertNotIn("perigee", kinds)
        self.assertNotIn("apogee", kinds)
        self.assertIn("ascending_node", kinds)


class TestUiFields(unittest.TestCase):

    def test_epoch_in_each_scale(self):
        sol = run(molniya_state(), 600.0, points=5)
        self.assertEqual(set(sol["epoch"]), {"utc", "tai", "tt", "tdb", "ut1"})
        self.assertEqual(sol["epoch"]["utc"], "2026-10-23T00:00:00.000000Z")
        self.assertEqual(sol["epoch"]["tai"], "2026-10-23T00:00:37.000000 TAI")
        self.assertEqual(sol["epoch"]["tt"], "2026-10-23T00:01:09.184000 TT")

    def test_itrf_states_match_the_frame_transform(self):
        sol = run(molniya_state(), 3600.0, points=7)
        ep = Epoch.from_iso(EPOCH)
        for i, t in enumerate(sol["times"]):
            r, v = F.transform_state(sol["position_m"][i], sol["velocity_ms"][i], ep + float(t), "GCRF", "ITRF")
            np.testing.assert_allclose(sol["position_itrf_m"][i], r, atol=1e-6)
            np.testing.assert_allclose(sol["velocity_itrf_ms"][i], v, atol=1e-9)

    def test_sun_direction_matches_erfa(self):
        sol = run(molniya_state(), 86400.0, points=5)
        ep = Epoch.from_iso(EPOCH)
        sun = np.asarray(sol["sun_direction_eci"])
        np.testing.assert_allclose(np.linalg.norm(sun, axis=1), 1.0, atol=1e-12)
        for i, t in enumerate(sol["times"]):
            tdb1, tdb2 = (ep + float(t)).jd("TDB")
            pvh, _ = erfa.epv00(tdb1, tdb2)        # heliocentric Earth, BCRS
            ref = -pvh[0] / np.linalg.norm(pvh[0])
            # ERFA's series is good to a few arcsec; aberration is not applied in either
            self.assertLess(math.degrees(math.acos(min(1.0, float(sun[i] @ ref)))), 0.01)

    def test_sun_direction_is_none_outside_bundled_ephemeris(self):
        sol = run(molniya_state(), 600.0, epoch="1980-01-01T00:00:00Z", points=3)
        self.assertIsNone(sol["sun_direction_eci"])
        self.assertEqual(len(sol["position_itrf_m"]), 3)


if __name__ == "__main__":
    unittest.main()
