"""
Independent cross-check against Basilisk (AVS Lab, University of Colorado). The end-to-end runs are
skipped when Basilisk's own Python environment is not found (set BSK_PYTHON to its python.exe).
Written before the implementation (tests-first rule).
"""

import math
import os
import tempfile
import unittest

import numpy as np

from astroflyer.backend import forces
from astroflyer.backend.astro_engine import keplerian_to_cartesian
from astroflyer.validation import cases as C


class BasiliskInputsTest(unittest.TestCase):
    """What Basilisk is given must match what AstroFlyer uses: Basilisk itself is not needed here."""

    def _read(self, zonal_only):
        from astroflyer.validation.basilisk_crosscheck import write_gravity_csv
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "egm2008.txt")
            write_gravity_csv(path, 8, zonal_only=zonal_only)
            with open(path) as f:
                rows = [[float(x) for x in line.split(",")] for line in f if line.strip()]
        return rows[0], {(int(r[0]), int(r[1])): (r[2], r[3]) for r in rows[1:]}

    def test_gravity_file_carries_our_egm2008_coefficients(self):
        data = np.load(forces._resource_path("gravity", "EGM2008_70.npz"))
        header, coefs = self._read(zonal_only=False)
        self.assertAlmostEqual(header[0], float(data["radius"]), places=6)
        self.assertAlmostEqual(header[1] / float(data["gm"]), 1.0, places=14)
        self.assertEqual(header[5], 1.0)                                  # fully normalized
        for (n, m) in [(2, 0), (2, 2), (3, 1), (8, 8)]:
            self.assertAlmostEqual(coefs[(n, m)][0], float(data["C"][n, m]), delta=1e-20)
            self.assertAlmostEqual(coefs[(n, m)][1], float(data["S"][n, m]), delta=1e-20)

    def test_zonal_levels_get_a_zonal_only_field(self):
        _, coefs = self._read(zonal_only=True)
        self.assertNotEqual(coefs[(2, 0)][0], 0.0)
        self.assertEqual(coefs[(2, 2)], (0.0, 0.0))
        self.assertEqual(coefs[(8, 8)], (0.0, 0.0))

    def test_levels_are_those_basilisk_models_the_same_way(self):
        from astroflyer.validation.basilisk_crosscheck import LEVELS
        self.assertEqual(list(LEVELS), ["L0", "L1", "L2", "L3", "L4", "L5", "L6"])   # no relativity in Basilisk

    def test_job_matches_astroflyer_forces_and_spacecraft(self):
        from astroflyer.validation.basilisk_crosscheck import job_for, BSK_SOLAR_FLUX, BSK_AU_M
        state = np.array([7000e3, 0.0, 0.0, 0.0, 7.5e3, 1.0e3])
        job = job_for(state, C.LEVELS["L6"], 3600.0, "g.txt", {"spk": "de.bsp"})
        self.assertEqual(job["mu_earth"], float(forces.MU_EARTH))
        self.assertEqual(job["mu_sun"], float(forces.MU_SUN))
        self.assertEqual(job["mu_moon"], float(forces.MU_MOON))
        self.assertTrue(job["third_body"] and job["srp"] and job["drag"])
        self.assertEqual((job["gravity_degree"], job["zonal_only"]), (8, False))
        # SRP acceleration Basilisk computes (Cr*A/m * flux/c * (AU/d)^2) equals AstroFlyer's Cr*A/m * 4.56e-6
        bsk = job["cr"] * job["srp_area_m2"] / job["mass_kg"] * BSK_SOLAR_FLUX / 299792458.0 * BSK_AU_M ** 2
        ours = C.CR_AREA_OVER_M * forces.P_SR_1AU * forces.AU_METERS ** 2
        self.assertAlmostEqual(bsk / ours, 1.0, places=12)
        self.assertAlmostEqual(job["cd"] * job["drag_area_m2"] / job["mass_kg"], C.CD_AREA_OVER_M)
        self.assertEqual((job["f107"], job["f107a"], job["ap"]), (C.F107, C.F107A, C.AP))
        # Basilisk's clock starts at the UTC instant of the TT epoch (TT - UTC = 69.184 s in 2026)
        self.assertEqual(job["epoch_utc"], "2025 DECEMBER 31 23:58:50.816 (UTC)")
        # Air co-rotates at the IERS rate about +z (Basilisk's SPICE-derived rate made GTO drag 9% too strong)
        self.assertEqual(job["wind_omega_n"], [0.0, 0.0, forces.OMEGA_EARTH])
        # Eclipse and atmosphere update once per task step, so SRP and drag levels use a short one
        self.assertLessEqual(job["task_step_s"], 1.0)
        self.assertGreaterEqual(job_for(state, C.LEVELS["L3"], 3600.0, "g.txt", {})["task_step_s"], 10.0)
        zonal = job_for(state, C.LEVELS["L1"], 3600.0, "g.txt", {})
        self.assertEqual((zonal["gravity_degree"], zonal["zonal_only"]), (2, True))


def _bsk():
    from astroflyer.validation.basilisk_crosscheck import find_bsk_python, find_kernels
    return find_bsk_python() if find_kernels() else None


@unittest.skipUnless(_bsk(), "Basilisk environment or SPICE kernels not found (set BSK_PYTHON)")
class BasiliskEndToEndTest(unittest.TestCase):

    def test_molniya_two_body_and_8x8_agree_over_a_quarter_day(self):
        from astroflyer.validation.basilisk_crosscheck import compare_case
        for level in ("L0", "L3"):
            with self.subTest(level=level):
                res = compare_case("molniya", C.LEVELS[level], 0.25)
                self.assertLess(res["max_pos_err_m"], 1.0, res)

    def test_drag_does_not_depend_on_the_task_step(self):
        # Atmosphere, wind and shadow are evaluated once per task step; held at the step's start
        # this cost GTO 24 m/day at 1 s (falling only linearly with the step).
        from astroflyer.validation.basilisk_crosscheck import basilisk_run, find_bsk_python, find_kernels
        a, e, i, raan, argp, nu = C.ORBITS["gto"]
        r0, v0 = keplerian_to_cartesian(a, e, *np.radians([i, raan, argp, nu]), mu=forces.MU_EARTH)
        state = np.concatenate([r0, v0])
        runs = [basilisk_run(state, C.LEVELS["L6"], 43200.0, find_bsk_python(), find_kernels(), step)[1]
                for step in (1.0, 0.25)]
        self.assertLess(np.linalg.norm(runs[0] - runs[1], axis=1).max(), 0.3)


if __name__ == "__main__":
    unittest.main()
