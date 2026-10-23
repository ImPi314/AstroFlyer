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


if __name__ == "__main__":
    unittest.main()
