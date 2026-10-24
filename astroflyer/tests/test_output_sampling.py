"""
AstroFlyer HEO - output points follow the orbit, not the clock.

Evenly spaced times leave a high-eccentricity perigee with a handful of points (a
10,000 x 393,508 km orbit sampled every 43 min jumped 67 deg of true anomaly between
points). With sampling="anomaly" the engine spaces its output points evenly in
eccentric anomaly of the trajectory it actually integrated (time step proportional to
distance), so every orbit, perturbed or not, closed or escaping, is drawn from points
a few degrees apart, at no loss of accuracy.
Written before the implementation (tests-first rule).
"""

import json
import math
import unittest
import urllib.request

import numpy as np

from astroflyer.backend.astro_engine import ThirdReviewEngine
from astroflyer.backend.forces import MU_EARTH, R_EARTH_EQ
from astroflyer.backend.epoch import Epoch

MAX_SWEEP_DEG = 10.0            # largest angle round the Earth between two output points


def _rotation(inc, raan, argp):
    """Perifocal -> inertial."""
    def rz(t):
        c, s = math.cos(t), math.sin(t)
        return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])

    def rx(t):
        c, s = math.cos(t), math.sin(t)
        return np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]])
    return rz(raan) @ rx(inc) @ rz(argp)


class KeplerOrbit:
    """Independent two-body truth: Kepler's equation solved by Newton's method."""

    def __init__(self, rp, e, inc, raan, argp, nu0):
        self.e = e
        self.p = rp * (1.0 + e)
        self.a = self.p / (1.0 - e * e) if abs(e - 1.0) > 1e-12 else math.inf
        self.n = math.sqrt(MU_EARTH / abs(self.a) ** 3)
        self.rot = _rotation(inc, raan, argp)
        self.m0 = self._mean_anomaly(nu0)

    def _mean_anomaly(self, nu):
        e = self.e
        if e < 1.0:
            ea = 2.0 * math.atan2(math.sqrt(1.0 - e) * math.sin(nu / 2), math.sqrt(1.0 + e) * math.cos(nu / 2))
            return ea - e * math.sin(ea)
        fa = 2.0 * math.atanh(math.sqrt((e - 1.0) / (e + 1.0)) * math.tan(nu / 2))
        return e * math.sinh(fa) - fa

    def _true_anomaly(self, m):
        e = self.e
        if e < 1.0:
            m = math.remainder(m, 2.0 * math.pi)          # one revolution, so Newton starts on the right one
            ea = m if e < 0.8 else math.copysign(math.pi, m)
            for _ in range(60):
                ea -= (ea - e * math.sin(ea) - m) / (1.0 - e * math.cos(ea))
            return 2.0 * math.atan2(math.sqrt(1.0 + e) * math.sin(ea / 2), math.sqrt(1.0 - e) * math.cos(ea / 2))
        fa = math.asinh(m / e)
        for _ in range(60):
            fa -= (e * math.sinh(fa) - fa - m) / (e * math.cosh(fa) - 1.0)
        return 2.0 * math.atan(math.sqrt((e + 1.0) / (e - 1.0)) * math.tanh(fa / 2))

    def state(self, t):
        nu = self._true_anomaly(self.m0 + self.n * t)
        r = self.p / (1.0 + self.e * math.cos(nu))
        r_pf = np.array([r * math.cos(nu), r * math.sin(nu), 0.0])
        v_pf = math.sqrt(MU_EARTH / self.p) * np.array([-math.sin(nu), self.e + math.cos(nu), 0.0])
        return self.rot @ r_pf, self.rot @ v_pf

    def period(self):
        return 2.0 * math.pi / self.n


def _sweeps_deg(pos):
    u = pos / np.linalg.norm(pos, axis=1)[:, None]
    return np.degrees(np.arccos(np.clip(np.sum(u[1:] * u[:-1], axis=1), -1.0, 1.0)))


def _random_orbits(count, seed=20261025):
    """Perigee 200-40,000 km above the surface, e from 0 to 0.99, and escape orbits up to e = 3."""
    rng = np.random.default_rng(seed)
    for k in range(count):
        e = 3.0 * rng.random() + 1.05 if k % 5 == 4 else 0.99 * rng.random() ** 0.5
        rp = R_EARTH_EQ + rng.uniform(200e3, 40000e3)
        inc, raan, argp = math.radians(rng.uniform(0, 180)), math.radians(rng.uniform(0, 360)), math.radians(rng.uniform(0, 360))
        if e < 1.0:
            nu0 = math.radians(rng.uniform(-180, 180))
        else:
            nu_max = math.acos(-1.0 / e)
            nu0 = rng.uniform(-0.8 * nu_max, 0.0)
        yield KeplerOrbit(rp, e, inc, raan, argp, nu0)


class OutputSamplingTest(unittest.TestCase):

    def test_random_two_body_orbits_are_sampled_smoothly_and_exactly(self):
        for orbit in _random_orbits(15):
            with self.subTest(e=round(orbit.e, 3), rp_km=round(orbit.p / (1 + orbit.e) / 1000)):
                span = 2.0 * orbit.period() if orbit.e < 1.0 else 3.0 * 86400.0
                r0, v0 = orbit.state(0.0)
                sol = ThirdReviewEngine(np.concatenate([r0, v0])).propagate(
                    (0.0, span), num_points=1200, model='two_body', method='DOP853',
                    rtol=1e-12, atol=1e-6, sampling='anomaly')
                times, pos = np.asarray(sol['times']), np.asarray(sol['position_m'])

                self.assertEqual(times[0], 0.0)
                self.assertAlmostEqual(times[-1], span, delta=1e-6 * span)
                self.assertTrue(np.all(np.diff(times) > 0))
                self.assertLessEqual(len(times), 1200)
                self.assertGreaterEqual(len(times), 1000)     # the point budget is used, not wasted
                self.assertLess(_sweeps_deg(pos).max(), MAX_SWEEP_DEG)

                truth = np.array([orbit.state(t)[0] for t in times])
                err = np.linalg.norm(pos - truth, axis=1) / np.linalg.norm(truth, axis=1)
                self.assertLess(err.max(), 1e-6)              # as accurate as the integration itself

    def test_moon_perturbed_orbit_is_dense_at_its_real_perigees(self):
        # The case that failed in the app: 10,000 x 393,508 km at 71 deg. The Moon moves each perigee by
        # hours, so points must be placed from the integrated trajectory, not the starting orbit.
        rp, ra = R_EARTH_EQ + 10000e3, R_EARTH_EQ + 393508e3
        e = (ra - rp) / (ra + rp)
        orbit = KeplerOrbit(rp, e, math.radians(71), math.radians(32), math.radians(290), 0.0)
        r0, v0 = orbit.state(0.0)
        span = 3.3 * orbit.period()
        sol = ThirdReviewEngine(np.concatenate([r0, v0]), epoch=Epoch.from_iso('2026-01-01T00:00:00', scale='UTC')).propagate(
            (0.0, span), num_points=1200, model='coupled', method='DOP853', rtol=1e-10, atol=1e-6, sampling='anomaly')
        pos = np.asarray(sol['position_m'])
        self.assertLess(_sweeps_deg(pos).max(), MAX_SWEEP_DEG)
        perigees = [ev['t_s'] for ev in sol['events'] if ev['type'] == 'perigee']
        self.assertGreaterEqual(len(perigees), 3)
        times = np.asarray(sol['times'])
        for t_p in perigees[1:]:
            near = np.abs(times - t_p) < 3600.0
            self.assertGreaterEqual(int(near.sum()), 8, f"perigee at {t_p:.0f} s has too few points")

    def test_uniform_time_stays_the_default(self):
        orbit = KeplerOrbit(R_EARTH_EQ + 500e3, 0.7, 0.5, 0.0, 0.0, 0.0)
        r0, v0 = orbit.state(0.0)
        sol = ThirdReviewEngine(np.concatenate([r0, v0])).propagate((0.0, 36000.0), num_points=61, model='two_body', method='DOP853')
        np.testing.assert_allclose(np.diff(sol['times']), 600.0)


class PropagateApiSamplingTest(unittest.TestCase):
    """The app's run endpoint uses it: the failing random input from the app is now sampled smoothly."""

    def test_api_run_follows_the_orbit(self):
        import importlib.util
        import os
        spec = importlib.util.spec_from_file_location(
            "astroflyer_launcher_sampling", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py"))
        launcher = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(launcher)
        _, port = launcher.start_server_thread(0)
        query = ("hp=10000&ha=393508&inc=71&raan=32&aop=290&ta=0&num_orbits=3.3&num_points=1200"
                 "&model=two_body&method=DOP853&epoch=2026-01-01T00:00:00Z")
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/propagate?{query}", timeout=300) as resp:
            data = json.load(resp)
        self.assertEqual(data['status'], 'ok')
        self.assertLess(_sweeps_deg(np.asarray(data['position_m'])).max(), MAX_SWEEP_DEG)


if __name__ == "__main__":
    unittest.main()
