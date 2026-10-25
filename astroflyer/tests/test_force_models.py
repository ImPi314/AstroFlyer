"""
AstroFlyer HEO - Force Model Verification

Checks each force term against an independent reference:
  - two-body propagation vs closed-form Kepler
  - spherical-harmonic gravity vs finite differences of an independently coded potential
  - DE440 Sun/Moon positions vs published J2000 values
  - shadow, SRP and drag geometry and magnitudes
  - J2 secular rates vs first-order theory (incl. Molniya critical inclination)
"""

import math
import unittest

import numpy as np
from scipy.integrate import solve_ivp
from scipy.special import lpmv

from astroflyer.backend import forces
from astroflyer.backend.astro_engine import (
    ThirdReviewEngine, keplerian_to_cartesian, cartesian_to_keplerian, solve_kepler_equation,
    true_anomaly_from_eccentric, calculate_theoretical_j2_drifts, compute_acceleration_components,
)
from astroflyer.backend.ephemeris import get_ephemeris

MU = forces.MU_EARTH
RE = forces.R_GRAVITY_REF

MOLNIYA = dict(a=26600e3, e=0.74, inc=63.435, raan=90.0, argp=270.0)
GTO = dict(a=24396.137e3, e=0.72832, inc=28.5, raan=45.0, argp=30.0)


def _state(orbit, nu_deg=0.0):
    r, v = keplerian_to_cartesian(orbit["a"], orbit["e"], math.radians(orbit["inc"]),
                                  math.radians(orbit["raan"]), math.radians(orbit["argp"]),
                                  math.radians(nu_deg), mu=MU)
    return np.concatenate([r, v])


def _kepler_position(orbit, t):
    n = math.sqrt(MU / orbit["a"] ** 3)
    E = solve_kepler_equation(n * t, orbit["e"])
    nu = true_anomaly_from_eccentric(E, orbit["e"])
    r, _ = keplerian_to_cartesian(orbit["a"], orbit["e"], math.radians(orbit["inc"]),
                                  math.radians(orbit["raan"]), math.radians(orbit["argp"]), nu, mu=MU)
    return r


def _potential(r_body, degree, order):
    """Disturbing potential from normalized coefficients via scipy Legendre functions."""
    data = np.load(forces._resource_path("gravity", "EGM2008_70.npz"))
    c_bar, s_bar = data["C"], data["S"]
    x, y, z = r_body
    r = math.sqrt(x * x + y * y + z * z)
    sin_phi = z / r
    lam = math.atan2(y, x)
    total = 0.0
    for n in range(2, degree + 1):
        for m in range(0, min(n, order) + 1):
            k = 1.0 if m == 0 else 2.0
            norm = math.sqrt(k * (2 * n + 1) * math.exp(math.lgamma(n - m + 1) - math.lgamma(n + m + 1)))
            p_nm = (-1) ** m * lpmv(m, n, sin_phi) * norm   # remove Condon-Shortley phase
            total += (RE / r) ** n * p_nm * (c_bar[n, m] * math.cos(m * lam) + s_bar[n, m] * math.sin(m * lam))
    return MU / r * total


class TestGravityField(unittest.TestCase):

    def test_harmonics_match_potential_gradient(self):
        rng = np.random.default_rng(7)
        for degree, order in ((2, 0), (3, 0), (4, 0), (8, 8)):
            for _ in range(5):
                u = rng.normal(size=3)
                r = u / np.linalg.norm(u) * rng.uniform(6.7e6, 4.2e7)
                accel = forces.harmonic_acceleration_body(r, degree, order)
                h = 1.0
                grad = np.array([(_potential(r + h * e, degree, order) - _potential(r - h * e, degree, order)) / (2 * h)
                                 for e in np.eye(3)])
                np.testing.assert_allclose(accel, grad, rtol=1e-6, atol=1e-13,
                                           err_msg=f"degree {degree} order {order}")

    def test_j3_z_component_regression(self):
        # The old model had the wrong z-term (3 instead of 6); a mid-latitude point exposes it.
        r = np.array([5.1e6, -3.2e6, 4.4e6])
        accel = forces.harmonic_acceleration_body(r, 3, 0, n_min=3)
        grad_z = (_potential(r + [0, 0, 1.0], 3, 0) - _potential(r - [0, 0, 1.0], 3, 0)) / 2.0
        grad_z -= (_potential(r + [0, 0, 1.0], 2, 0) - _potential(r - [0, 0, 1.0], 2, 0)) / 2.0
        self.assertAlmostEqual(accel[2] / grad_z, 1.0, places=6)

    def test_reference_radius_and_j2(self):
        self.assertAlmostEqual(RE, 6378136.3, places=1)
        self.assertAlmostEqual(forces.J2_EARTH, 1.08262617e-3, delta=1e-11)


class TestTwoBody(unittest.TestCase):

    def test_two_body_matches_kepler(self):
        cfg = forces.ForceModelConfig.for_model("two_body")
        y0 = _state(MOLNIYA)
        period = 2 * math.pi * math.sqrt(MOLNIYA["a"] ** 3 / MU)

        def eom(t, y):
            a = forces.total_acceleration(t, y[:3], y[3:], cfg)
            return np.concatenate([y[3:], a])

        t_eval = np.linspace(0, 10 * period, 41)
        sol = solve_ivp(eom, (0, 10 * period), y0, method="DOP853", rtol=1e-13, atol=1e-6, t_eval=t_eval)
        err = max(np.linalg.norm(sol.y[:3, i] - _kepler_position(MOLNIYA, t)) for i, t in enumerate(sol.t))
        self.assertLess(err, 1.0, f"two-body position error {err:.3f} m over 10 revs")

        e0 = cartesian_to_keplerian(y0[:3], y0[3:], mu=MU)["energy"]
        e1 = cartesian_to_keplerian(sol.y[:3, -1], sol.y[3:, -1], mu=MU)["energy"]
        self.assertLess(abs((e1 - e0) / e0), 1e-10)

    def test_two_body_mode_has_no_extra_terms(self):
        y0 = _state(GTO)
        eng = ThirdReviewEngine(y0)
        cfg = forces.ForceModelConfig.for_model("two_body")
        comps = forces.acceleration_components(0.0, y0[:3], y0[3:], cfg)
        for key in ("harmonics", "sun", "moon", "srp", "drag", "relativity", "albedo"):
            self.assertFalse(np.any(comps[key]), key)
        self.assertIsNotNone(eng)


class TestEphemeris(unittest.TestCase):

    def test_de440_at_j2000(self):
        r_sun, r_moon = get_ephemeris().sun_moon_gcrf(0.0)
        self.assertAlmostEqual(np.linalg.norm(r_moon) / 1e3, 402448.64, delta=0.05)
        self.assertAlmostEqual(np.linalg.norm(r_sun) / forces.AU_METERS, 0.983328, delta=1e-5)

    def test_moon_distance_range_2026(self):
        eph = get_ephemeris()
        t0 = (2461041.5 - 2451545.0) * 86400.0  # 2026-01-01 TT
        d = [np.linalg.norm(eph.moon_gcrf(t0 + k * 6 * 3600.0)) / 1e3 for k in range(4 * 365)]
        self.assertGreater(min(d), 356000.0)
        self.assertLess(max(d), 407000.0)

    def test_out_of_range_epoch_raises(self):
        with self.assertRaises(ValueError):
            get_ephemeris().sun_gcrf(-20 * 365.25 * 86400.0)


class TestNonGravitational(unittest.TestCase):

    def setUp(self):
        self.r_sun, _ = get_ephemeris().sun_moon_gcrf(0.0)
        self.s_hat = self.r_sun / np.linalg.norm(self.r_sun)

    def test_shadow_function(self):
        self.assertEqual(forces.shadow_function(7.0e6 * self.s_hat, self.r_sun), 1.0)
        self.assertEqual(forces.shadow_function(-7.0e6 * self.s_hat, self.r_sun), 0.0)
        # Walk out of the shadow perpendicular to the Sun line: nu goes 0 -> partial -> 1
        perp = np.cross(self.s_hat, [0, 0, 1.0])
        perp /= np.linalg.norm(perp)
        values = [forces.shadow_function(-2.0e7 * self.s_hat + k * 1e4 * perp, self.r_sun)
                  for k in range(500, 800)]
        self.assertEqual(values[0], 0.0)
        self.assertEqual(values[-1], 1.0)
        self.assertTrue(any(0.0 < v < 1.0 for v in values))
        self.assertTrue(all(b >= a for a, b in zip(values, values[1:])))

    def test_srp_points_away_from_sun(self):
        r = 4.2e7 * np.array([0, 0, 1.0])
        accel, nu = forces.srp_acceleration(r, self.r_sun, 0.02)
        self.assertEqual(nu, 1.0)
        self.assertLess(np.dot(accel, self.s_hat), 0.0)
        expected = forces.P_SR_1AU * 0.02 * (forces.AU_METERS / np.linalg.norm(self.r_sun - r)) ** 2
        self.assertAlmostEqual(np.linalg.norm(accel) / expected, 1.0, places=9)

    def test_msis_density_and_drag_direction(self):
        rho = forces.atmospheric_density(8.1e8, 0.3, 1.0, 300e3, 150.0, 150.0, 15.0)
        self.assertGreater(rho, 5e-12)
        self.assertLess(rho, 1e-10)
        cfg = forces.ForceModelConfig(cd_area_over_m=0.01)
        y0 = _state(GTO)
        rot = forces.SimpleEarthRotation(8.1e8)
        accel, rho_p = forces.drag_acceleration(y0[:3], y0[3:], rot.matrix(0), rot.omega(0), 8.1e8, cfg)
        self.assertGreater(rho_p, 1e-12)
        self.assertLess(np.dot(accel, y0[3:]), 0.0)

    def test_drag_off_above_cutoff(self):
        cfg = forces.ForceModelConfig()
        r = np.array([3.0e7, 0, 0])
        rot = forces.SimpleEarthRotation(0.0)
        accel, rho = forces.drag_acceleration(r, np.array([0, 3e3, 0]), rot.matrix(0), rot.omega(0), 0.0, cfg)
        self.assertEqual(rho, 0.0)
        self.assertFalse(np.any(accel))


class TestSecularRates(unittest.TestCase):

    def _fit_rates(self, orbit, days):
        eng = ThirdReviewEngine(_state(orbit))
        sol = eng.propagate((0.0, days * 86400.0), num_points=400, model="j2", method="DOP853",
                            rtol=1e-12, atol=1e-6)
        t_days = sol["times"] / 86400.0
        raan = np.unwrap(np.radians(sol["raan_deg"]))
        argp = np.unwrap(np.radians(sol["arg_perigee_deg"]))
        return math.degrees(np.polyfit(t_days, raan, 1)[0]), math.degrees(np.polyfit(t_days, argp, 1)[0])

    def test_gto_j2_rates(self):
        raan_rate, argp_rate = self._fit_rates(GTO, 10)
        theory = calculate_theoretical_j2_drifts(GTO["a"], GTO["e"], math.radians(GTO["inc"]), 1, mu=MU)
        self.assertAlmostEqual(raan_rate / theory["dOmega_dt_deg_day"], 1.0, delta=0.01)
        self.assertAlmostEqual(argp_rate / theory["domega_dt_deg_day"], 1.0, delta=0.01)

    def test_molniya_frozen_perigee(self):
        _, argp_rate = self._fit_rates(MOLNIYA, 10)
        tilted = dict(MOLNIYA, inc=60.0)
        _, argp_rate_60 = self._fit_rates(tilted, 10)
        self.assertLess(abs(argp_rate), 0.01 * abs(argp_rate_60))


class TestForceBreakdown(unittest.TestCase):

    def test_component_breakdown_sums(self):
        y0 = _state(GTO)
        d = compute_acceleration_components(y0, 0.0, forces.ForceModelConfig())
        parts = sum(d[k] for k in ("a_central", "a_j2", "a_j3", "a_j4", "a_tesseral", "a_sun", "a_moon",
                                   "a_drag", "a_srp", "a_relativity", "a_albedo"))
        np.testing.assert_allclose(parts, d["a_total"], rtol=1e-14)
        self.assertGreater(d["a_drag_mag"], 0.0)  # 250 km perigee


if __name__ == "__main__":
    unittest.main()
