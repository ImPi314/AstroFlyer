"""
AstroFlyer HEO - double-precision NRLMSISE-00

pymsis runs NRLMSISE-00 in single precision, so its density jitters by about
1e-6 between points a few millimetres apart. Under drag at a 250 km GTO
perigee that jitter changes the trajectory by metres per day, differently
on each computer. These tests check the double-precision port:
  - the 17 published test cases of the NRLMSISE-00 C release (gtd7)
  - smoothness in altitude at millimetre steps
  - agreement with pymsis (the single-precision Fortran)
  - that a GTO arc with drag now converges as the tolerances tighten
"""

import math
import unittest

import numpy as np

from astroflyer.backend import forces

# (d[0..8], t[0], t[1]) from the NRLMSISE-00 C release 20041227 test program (CGS units)
REFERENCE = [
    (6.665177E+05, 1.138806E+08, 1.998211E+07, 4.022764E+05, 3.557465E+03, 4.074714E-15, 3.475312E+04, 4.095913E+06, 2.667273E+04, 1.250540E+03, 1.241416E+03),
    (3.407293E+06, 1.586333E+08, 1.391117E+07, 3.262560E+05, 1.559618E+03, 5.001846E-15, 4.854208E+04, 4.380967E+06, 6.956682E+03, 1.166754E+03, 1.161710E+03),
    (1.123767E+05, 6.934130E+04, 4.247105E+01, 1.322750E-01, 2.618848E-05, 2.756772E-18, 2.016750E+04, 5.741256E+03, 2.374394E+04, 1.239892E+03, 1.239891E+03),
    (5.411554E+07, 1.918893E+11, 6.115826E+12, 1.225201E+12, 6.023212E+10, 3.584426E-10, 1.059880E+07, 2.615737E+05, 2.819879E-42, 1.027318E+03, 2.068878E+02),
    (1.851122E+06, 1.476555E+08, 1.579356E+07, 2.633795E+05, 1.588781E+03, 4.809630E-15, 5.816167E+04, 5.478984E+06, 1.264446E+03, 1.212396E+03, 1.208135E+03),
    (8.673095E+05, 1.278862E+08, 1.822577E+07, 2.922214E+05, 2.402962E+03, 4.355866E-15, 3.686389E+04, 3.897276E+06, 2.667273E+04, 1.220146E+03, 1.212712E+03),
    (5.776251E+05, 6.979139E+07, 1.236814E+07, 2.492868E+05, 1.405739E+03, 2.470651E-15, 5.291986E+04, 1.069814E+06, 2.667273E+04, 1.116385E+03, 1.112999E+03),
    (3.740304E+05, 4.782720E+07, 5.240380E+06, 1.759875E+05, 5.501649E+02, 1.571889E-15, 8.896776E+04, 1.979741E+06, 9.121815E+03, 1.031247E+03, 1.024848E+03),
    (6.748339E+05, 1.245315E+08, 2.369010E+07, 4.911583E+05, 4.578781E+03, 4.564420E-15, 3.244595E+04, 5.370833E+06, 2.667273E+04, 1.306052E+03, 1.293374E+03),
    (5.528601E+05, 1.198041E+08, 3.495798E+07, 9.339618E+05, 1.096255E+04, 4.974543E-15, 2.686428E+04, 4.889974E+06, 2.805445E+04, 1.361868E+03, 1.347389E+03),
    (1.375488E+14, 0.000000E+00, 2.049687E+19, 5.498695E+18, 2.451733E+17, 1.261066E-03, 0.000000E+00, 0.000000E+00, 0.000000E+00, 1.027318E+03, 2.814648E+02),
    (4.427443E+13, 0.000000E+00, 6.597567E+18, 1.769929E+18, 7.891680E+16, 4.059139E-04, 0.000000E+00, 0.000000E+00, 0.000000E+00, 1.027318E+03, 2.274180E+02),
    (2.127829E+12, 0.000000E+00, 3.170791E+17, 8.506280E+16, 3.792741E+15, 1.950822E-05, 0.000000E+00, 0.000000E+00, 0.000000E+00, 1.027318E+03, 2.374389E+02),
    (1.412184E+11, 0.000000E+00, 2.104370E+16, 5.645392E+15, 2.517142E+14, 1.294709E-06, 0.000000E+00, 0.000000E+00, 0.000000E+00, 1.027318E+03, 2.795551E+02),
    (1.254884E+10, 0.000000E+00, 1.874533E+15, 4.923051E+14, 2.239685E+13, 1.147668E-07, 0.000000E+00, 0.000000E+00, 0.000000E+00, 1.027318E+03, 2.190732E+02),
    (5.196477E+05, 1.274494E+08, 4.850450E+07, 1.720838E+06, 2.354487E+04, 5.881940E-15, 2.500078E+04, 6.279210E+06, 2.667273E+04, 1.426412E+03, 1.408608E+03),
    (4.260860E+07, 1.241342E+11, 4.929562E+12, 1.048407E+12, 4.993465E+10, 2.914304E-10, 8.831229E+06, 2.252516E+05, 2.415246E-42, 1.027318E+03, 1.934071E+02),
]


def _reference_inputs():
    """The inputs of the C release's test_gtd7(), one dict per case."""
    cases = [dict(doy=172, sec=29000.0, alt=400.0, g_lat=60.0, g_long=-70.0, lst=16.0,
                  f107A=150.0, f107=150.0, ap=4.0, storm=False) for _ in range(17)]
    cases[1]["doy"] = 81
    cases[2]["sec"] = 75000.0
    cases[2]["alt"] = 1000.0
    cases[3]["alt"] = 100.0
    for i, alt in ((10, 0.0), (11, 10.0), (12, 30.0), (13, 50.0), (14, 70.0), (16, 100.0)):
        cases[i]["alt"] = alt
    cases[4]["g_lat"] = 0.0
    cases[5]["g_long"] = 0.0
    cases[6]["lst"] = 4.0
    cases[7]["f107A"] = 70.0
    cases[8]["f107"] = 180.0
    cases[9]["ap"] = 40.0
    cases[15]["storm"] = cases[16]["storm"] = True      # switch 9 = -1 with ap array all 100
    return cases


class TestNRLMSISE00(unittest.TestCase):

    def test_published_reference_cases(self):
        from astroflyer.backend import nrlmsise00 as M
        for case, expected in zip(_reference_inputs(), REFERENCE):
            switches = np.ones(24)
            switches[0] = 0.0                            # CGS output, as in the C test
            ap_array = np.zeros(7)
            if case["storm"]:
                switches[9] = -1.0
                ap_array[:] = 100.0
            d, t = M.gtd7(case["doy"], case["sec"], case["alt"], case["g_lat"], case["g_long"],
                          case["lst"], case["f107A"], case["f107"], case["ap"], ap_array, switches)
            got = np.concatenate([d, t])
            np.testing.assert_allclose(got, np.array(expected), rtol=2e-6, atol=0.0, err_msg=str(case))

    def test_density_is_smooth_in_altitude(self):
        """No single-precision jitter: log density is smooth at 5 mm steps (away from the model's
        own altitude switches, see test_drag_boundaries_mark_density_jumps)."""
        h = 251e3 + 0.005 * np.arange(41)
        rho = np.array([forces.atmospheric_density(8.2e8, 0.3, 1.0, x, 150.0, 150.0, 15.0) for x in h])
        self.assertTrue(np.all(np.diff(rho) < 0.0))
        second = np.diff(np.log(rho), 2)
        self.assertLess(np.abs(second).max(), 1e-12)

    def test_agrees_with_pymsis(self):
        import pymsis
        rng = np.random.default_rng(7)
        tt0 = 8.2e8
        for _ in range(40):
            t = tt0 + rng.uniform(0, 86400 * 30)
            lat, lon = rng.uniform(-1.5, 1.5), rng.uniform(-math.pi, math.pi)
            alt = rng.uniform(150e3, 1200e3)
            ours = forces.atmospheric_density(t, lat, lon, alt, 150.0, 150.0, 15.0)
            utc = np.datetime64("2000-01-01T11:58:50.816", "ms") + np.timedelta64(int(round(t * 1000.0)), "ms")
            ref = float(np.asarray(pymsis.calculate(utc, math.degrees(lon), math.degrees(lat), alt / 1e3,
                                                    f107s=150.0, f107as=150.0, aps=[[15.0] * 7],
                                                    version=0)).reshape(-1)[0])
            self.assertLess(abs(ours / ref - 1.0), 1e-4, (t, lat, lon, alt))


class TestDragPropagation(unittest.TestCase):

    def test_drag_boundaries_mark_density_jumps(self):
        """
        NRLMSISE-00 itself switches terms on at fixed altitudes (e.g. 160, 300, 450 km) and its
        day of year steps at UTC midnight, so the density jumps there (up to ~0.7% at midnight).
        The propagator restarts at each one; the event functions must change sign exactly there.
        """
        from astroflyer.backend.eclipse import drag_boundary_events
        from astroflyer.backend.nrlmsise00 import DISCONTINUITY_ALTITUDES_KM
        self.assertIn(300.0, DISCONTINUITY_ALTITUDES_KM)
        self.assertIn(160.0, DISCONTINUITY_ALTITUDES_KM)
        epoch_tt = 8.2e8
        identity = lambda t: np.eye(3)
        events = drag_boundary_events(epoch_tt, identity)
        # Altitude events: a point on the equator (geodetic = geocentric there) just below and above
        for h_km in DISCONTINUITY_ALTITUDES_KM:
            r = forces.R_EARTH_EQ + h_km * 1e3
            below = np.array([r - 1e-3, 0.0, 0.0, 0.0, 0.0, 0.0])
            above = np.array([r + 1e-3, 0.0, 0.0, 0.0, 0.0, 0.0])
            signs = [np.sign(g(0.0, below)) != np.sign(g(0.0, above)) for g in events]
            self.assertEqual(sum(signs), 1, h_km)
        # Midnight event: changes sign across the UTC day boundary, where the day of year steps
        doy, sec = forces._utc_day_of_year_and_seconds(epoch_tt)
        t_mid = 86400.0 - sec
        y = np.array([forces.R_EARTH_EQ + 400e3, 0.0, 0.0, 0.0, 0.0, 0.0])
        flips = [np.sign(g(t_mid - 0.01, y)) != np.sign(g(t_mid + 0.01, y)) for g in events]
        self.assertEqual(sum(flips), 1)
        self.assertNotEqual(forces._utc_day_of_year_and_seconds(epoch_tt + t_mid - 0.01)[0],
                            forces._utc_day_of_year_and_seconds(epoch_tt + t_mid + 0.01)[0])

    def test_gto_drag_converges(self):
        """Default and tight tolerances agree once the density is smooth (was 1.7 m)."""
        from astroflyer.backend.astro_engine import ThirdReviewEngine, keplerian_to_cartesian
        from astroflyer.backend.epoch import Epoch
        r, v = keplerian_to_cartesian(24396.137e3, 0.72832, math.radians(28.5), math.radians(45.0),
                                      math.radians(30.0), 0.0)
        state = np.concatenate([r, v])
        epoch = Epoch.from_iso("2026-01-01T00:00:00", scale="TT")

        def run(rtol, atol):
            sol = ThirdReviewEngine(state, epoch=epoch).propagate(
                (0.0, 86400.0), num_points=145, model="coupled", method="DOP853", rtol=rtol, atol=atol,
                enable_drag=True, enable_third_body=False, enable_srp=False, enable_relativity=False,
                enable_albedo=False, gravity_degree=8, gravity_order=8, b_star=0.01, cr_area_over_m=0.02)
            return sol["position_m"]

        self.assertLess(np.linalg.norm(run(1e-12, 1e-6) - run(1e-13, 1e-9), axis=1).max(), 0.05)


if __name__ == "__main__":
    unittest.main()
