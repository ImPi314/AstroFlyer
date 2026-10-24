"""
Independent cross-check against NASA GMAT (the end-to-end runs are skipped when GMAT is not installed;
set GMAT_CONSOLE to GmatConsole.exe if it is not found on its own).
Written before the implementation (tests-first rule).
"""

import os
import tempfile
import unittest

import numpy as np

from astroflyer.backend import forces
from astroflyer.validation import cases as C


class GmatInputsTest(unittest.TestCase):
    """What GMAT is given must match what AstroFlyer uses: no GMAT needed for these."""

    def test_gravity_file_carries_our_egm2008_coefficients(self):
        from astroflyer.validation.gmat_crosscheck import write_cof
        data = np.load(forces._resource_path("gravity", "EGM2008_70.npz"))
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "EGM2008_70.cof")
            write_cof(path)
            with open(path) as f:
                lines = f.read().splitlines()
        header = next(line for line in lines if line.startswith("POTFIELD"))
        gm, radius = float(header[17:38]), float(header[38:59])   # layout of GMAT's own EGM96.cof
        self.assertAlmostEqual(gm / float(data["gm"]), 1.0, places=14)
        self.assertAlmostEqual(radius, float(data["radius"]), places=6)
        coefs = {}
        for line in lines:
            if line.startswith("RECOEF"):
                n, m = int(line[6:11]), int(line[11:14])
                c = float(line[17:38])
                s = float(line[38:59]) if len(line) > 38 else 0.0
                coefs[(n, m)] = (c, s)
        for (n, m) in [(2, 0), (2, 2), (3, 1), (8, 8)]:
            self.assertAlmostEqual(coefs[(n, m)][0], float(data["C"][n, m]), delta=1e-20)
            self.assertAlmostEqual(coefs[(n, m)][1], float(data["S"][n, m]), delta=1e-20)

    def test_each_level_switches_on_exactly_its_forces(self):
        from astroflyer.validation.gmat_crosscheck import mission_script
        state = np.array([7000e3, 0.0, 0.0, 0.0, 7.5e3, 1.0e3])

        def script(level):
            return mission_script(state, C.LEVELS[level], 600.0, "g.cof", "de440.bsp", "out.txt")

        two_body = script("L0")
        self.assertIn("FM.GravityField.Earth.Degree = 0;", two_body)
        self.assertIn("FM.SRP = Off;", two_body)
        self.assertNotIn("PointMasses", two_body)
        self.assertNotIn("Drag.AtmosphereModel", two_body)
        # GMAT's built-in EarthICRF (Earth origin, ICRF axes) is GCRF, not mean-of-J2000; it can't be redefined
        self.assertIn("Sat.CoordinateSystem = EarthICRF;", two_body)
        self.assertNotIn("Create CoordinateSystem", two_body)
        self.assertNotIn("np.float64", two_body)
        self.assertIn("Sat.DateFormat = TTGregorian;", two_body)
        self.assertIn("Sat.Epoch = '01 Jan 2026 00:00:00.000';", two_body)

        zonal = script("L2")
        self.assertIn("FM.GravityField.Earth.Degree = 4;", zonal)
        self.assertIn("FM.GravityField.Earth.Order = 0;", zonal)

        third = script("L4")
        self.assertIn("FM.PointMasses = {Sun, Luna};", third)
        self.assertIn("SolarSystem.EphemerisSource = 'SPICE';", third)
        self.assertIn("de440.bsp", third)

        srp = script("L5")
        self.assertIn("FM.SRP = On;", srp)
        # Pressure GMAT derives (Flux / c) equals AstroFlyer's 4.56e-6 N/m^2 at 1 AU
        flux = float(srp.split("FM.SRP.Flux = ")[1].split(";")[0])
        self.assertAlmostEqual(flux / 299792458.0, forces.P_SR_1AU, places=12)

        drag = script("L6")
        self.assertIn("FM.Drag.AtmosphereModel = NRLMSISE00;", drag)
        self.assertIn("FM.Drag.HistoricWeatherSource = 'ConstantFluxAndGeoMag';", drag)
        self.assertIn("FM.Drag.F107 = 150;", drag)
        self.assertIn("FM.Drag.MagneticIndex = 3;", drag)                    # Kp 3 is Ap 15
        self.assertIn("FM.RelativisticCorrection = Off;", drag)
        self.assertIn("FM.RelativisticCorrection = On;", script("L7"))

    def test_report_reader_returns_seconds_metres_and_metres_per_second(self):
        from astroflyer.validation.gmat_crosscheck import read_report
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "out.txt")
            with open(path, "w") as f:
                f.write("31119.500000000000   7000.0   0.0   0.0   0.0   7.5   1.0\n")
                f.write("31119.506944444445   6990.5   450.25   60.0   -0.25   7.49   1.0\n")
            t, r, v = read_report(path)
        np.testing.assert_allclose(t, [0.0, 600.0], atol=1e-4)
        np.testing.assert_allclose(r[1], [6990.5e3, 450.25e3, 60.0e3])
        np.testing.assert_allclose(v[1], [-250.0, 7490.0, 1000.0])


def _gmat():
    from astroflyer.validation.gmat_crosscheck import find_gmat
    return find_gmat()


@unittest.skipUnless(_gmat(), "GMAT not installed (set GMAT_CONSOLE)")
class GmatEndToEndTest(unittest.TestCase):

    def test_molniya_two_body_and_8x8_agree_over_a_quarter_day(self):
        from astroflyer.validation.gmat_crosscheck import compare_case
        for level in ("L0", "L3"):
            with self.subTest(level=level):
                res = compare_case(_gmat(), "molniya", C.LEVELS[level], 0.25)
                self.assertLess(res["max_pos_err_m"], 1.0, res)


if __name__ == "__main__":
    unittest.main()
