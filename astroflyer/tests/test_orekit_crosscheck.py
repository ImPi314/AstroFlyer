"""
Independent cross-check against Orekit (skipped when orekit-jpype or Java is unavailable).
Full ladder and report: python -m astroflyer.validation.orekit_crosscheck
"""

import unittest

try:
    import orekit_jpype  # noqa: F401
    HAVE_OREKIT = True
except ImportError:
    HAVE_OREKIT = False


@unittest.skipUnless(HAVE_OREKIT, "orekit-jpype not installed")
class TestOrekitCrossCheck(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from astroflyer.validation import orekit_crosscheck as X
        cls.X = X
        cls.ctx = X.OrekitContext(None)  # bundled IERS data only: L0-L3

    @classmethod
    def tearDownClass(cls):
        cls.ctx.close()

    def test_molniya_8x8_quarter_day(self):
        from astroflyer.validation.cases import LEVELS
        res = self.X.compare_case(self.ctx, "molniya", LEVELS["L3"], 0.25)
        self.assertLess(res["max_pos_err_m"], 0.1, res)

    def test_gto_zonal_quarter_day(self):
        from astroflyer.validation.cases import LEVELS
        res = self.X.compare_case(self.ctx, "gto", LEVELS["L2"], 0.25)
        self.assertLess(res["max_pos_err_m"], 0.1, res)

    def test_msis_density_matches_pymsis(self):
        """
        Orekit's NRLMSISE-00, fed the mean Sun, gives AstroFlyer's (pymsis) density.
        The two codes (Java port vs the single-precision Fortran) agree to about 2e-4;
        with Orekit's default true-Sun local time they differ by about 3e-3.
        """
        from org.hipparchus.geometry.euclidean.threed import Vector3D
        from astroflyer.backend import forces
        from astroflyer.backend.epoch import Epoch
        atmosphere = self.ctx.atmosphere()
        epoch = Epoch.from_iso("2026-01-01T00:00:00", scale="TT")
        for hours, r in ((0.0, (6628e3, 0.0, 0.0)), (5.3, (0.0, 4800e3, 4900e3)),
                         (17.9, (-5000e3, -3000e3, 3500e3)), (11.0, (1000e3, -7100e3, -900e3))):
            date = self.ctx.date(epoch).shiftedBy(hours * 3600.0)
            pos = Vector3D(*r)
            rho_orekit = atmosphere.getDensity(date, pos, self.ctx.gcrf)
            gp = self.ctx.earth.transform(pos, self.ctx.gcrf, date)
            rho_af = forces.atmospheric_density(float(epoch - Epoch.j2000()) + hours * 3600.0,
                                                gp.getLatitude(), gp.getLongitude(), gp.getAltitude(),
                                                150.0, 150.0, 15.0)
            self.assertLess(abs(rho_orekit / rho_af - 1.0), 5e-4, (hours, rho_orekit, rho_af))

    def test_gto_drag_quarter_day(self):
        """Drag alone (no ephemerides needed), with the 250 km perigee pass."""
        from astroflyer.validation.cases import Level
        level = Level("L3D", "8x8 + NRLMSISE-00 drag", 8, 8, drag=True)
        self.assertFalse(level.needs_ephemeris)
        res = self.X.compare_case(self.ctx, "gto", level, 0.25)
        self.assertLess(res["max_pos_err_m"], 0.5, res)


if __name__ == "__main__":
    unittest.main()
