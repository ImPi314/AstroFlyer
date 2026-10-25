"""
AstroFlyer HEO - Phase 1 gate: time scales, Earth orientation and frames.

Reference values are the published worked example in Vallado,
"Fundamentals of Astrodynamics and Applications" (4th ed.), Example 3-15:
2004-04-06 07:51:28.386009 UTC, with the EOP given in that example.
GCRF, TIRS (PEF) and TEME use the same models and must agree closely. TOD and MOD
in the book use IAU-1976/FK5 without frame bias, so they agree only to the
size of that convention difference.
"""

import unittest

import numpy as np

from astroflyer.backend import eop
from astroflyer.backend import frames as F
from astroflyer.backend.astro_engine import ThirdReviewEngine, keplerian_to_cartesian
from astroflyer.backend.epoch import Epoch

R_ITRF = np.array([-1033.4793830, 7901.2952754, 6380.3565958]) * 1e3
V_ITRF = np.array([-3.225636520, -2.872451450, 5.531924446]) * 1e3
EPOCH_TEXT = "2004-04-06T07:51:28.386009Z"

# frame: (r km, v km/s, position tol m, velocity tol m/s)
VALLADO_3_15 = {
    "GCRF": ([5102.508959, 6123.011403, 6378.136925], [-4.743220156, 0.790536497, 5.533755728], 0.02, 1e-4),
    "TIRS": ([-1033.4750313, 7901.3055856, 6380.3445327], [-3.225632747, -2.872442511, 5.531931288], 0.001, 1e-5),
    "TEME": ([5094.18016210, 6127.64465950, 6380.34453270], [-4.746131487, 0.785818041, 5.531931288], 0.01, 1e-4),
    "TOD": ([5094.5147804, 6127.3664612, 6380.3445328], [-4.746088385, 0.786078324, 5.531931288], 0.3, 2e-3),
    "MOD": ([5094.0283745, 6127.8708164, 6380.2485164], [-4.746263052, 0.786014074, 5.531790531], 1.5, 2e-3),
}


def vallado_eop():
    """Constant EOP from Example 3-15: xp, yp (arcsec), UT1-TAI (s), dX, dY (mas), LOD (ms)."""
    return eop.EarthOrientationData(
        mjd=[53000.0, 53200.0], xp=[-0.140682] * 2, yp=[0.333309] * 2,
        ut1_tai=[-0.4399619 - 32.0] * 2, dx=[-0.205] * 2, dy=[-0.136] * 2, lod=[1.5563] * 2,
    )


class TestTimeScales(unittest.TestCase):

    def test_vallado_time_scales(self):
        ep = Epoch.from_iso(EPOCH_TEXT)
        self.assertEqual(ep.tai_minus_utc(), 32.0)
        self.assertEqual(ep.iso("TT", 6), "2004-04-06T07:52:32.570009 TT")
        self.assertAlmostEqual(ep.julian_centuries_tt(), 0.0426236319, places=10)
        # TDB - TT is periodic with amplitude 1.66 ms
        self.assertLess(abs(ep.tdb_minus_tt()), 0.0017)

    def test_leap_second_is_counted(self):
        before = Epoch.from_iso("2016-12-31T23:59:59Z")
        after = Epoch.from_iso("2017-01-01T00:00:00Z")
        self.assertAlmostEqual(after - before, 2.0, places=9)
        self.assertEqual(Epoch.from_iso("2016-12-31T23:59:60.5Z").iso("UTC", 1), "2016-12-31T23:59:60.5Z")

    def test_gps_week(self):
        ep = Epoch.from_gps_week(2390, 0.0)
        self.assertEqual(ep.iso("GPS"), "2025-10-26T00:00:00.000 GPS")
        self.assertEqual(ep.iso("UTC"), "2025-10-25T23:59:42.000Z")
        week, sow = ep.gps_week_seconds()
        self.assertEqual(week, 2390)
        self.assertAlmostEqual(sow, 0.0, places=6)

    def test_iso_round_trip_in_every_scale(self):
        for scale in ("UTC", "TAI", "TT", "TDB", "UT1", "GPS"):
            ep = Epoch.from_iso("2026-10-23T19:00:00.123456", scale=scale)
            self.assertEqual(ep.iso(scale, 6).split(" ")[0].rstrip("Z"), "2026-10-23T19:00:00.123456", scale)

    def test_j2000_definition(self):
        self.assertEqual(Epoch.j2000().iso("TT"), "2000-01-01T12:00:00.000 TT")
        self.assertEqual(Epoch.j2000().iso("UTC"), "2000-01-01T11:58:55.816Z")

    def test_ut1_continuous_across_leap_second(self):
        eop.set_eop(None)
        before = Epoch.from_iso("2016-12-31T23:59:59Z")
        after = Epoch.from_iso("2017-01-01T00:00:01Z")
        # UT1 advances by elapsed time (3 s of TAI here) minus the 1 s leap, i.e. ~2 s
        ut1_elapsed = ((after.jd("UT1")[0] - before.jd("UT1")[0]) + (after.jd("UT1")[1] - before.jd("UT1")[1])) * 86400.0
        self.assertAlmostEqual(after - before, 3.0, places=6)
        self.assertAlmostEqual(ut1_elapsed, 3.0, delta=1e-3)
        self.assertAlmostEqual(after.ut1_minus_utc() - before.ut1_minus_utc(), 1.0, delta=1e-3)

    def test_bundled_eop_covers_mission_dates(self):
        eop.set_eop(None)
        table = eop.get_eop()
        self.assertTrue(table.loaded)
        self.assertTrue(table.in_range(Epoch.from_iso("2026-10-23T00:00:00Z").mjd()))


class TestFrames(unittest.TestCase):

    def setUp(self):
        eop.get_eop()               # make sure leap seconds are installed
        eop.set_eop(vallado_eop())
        self.epoch = Epoch.from_iso(EPOCH_TEXT)

    def tearDown(self):
        eop.set_eop(None)

    def test_vallado_example_3_15(self):
        for frame, (r_km, v_kms, r_tol, v_tol) in VALLADO_3_15.items():
            r, v = F.transform_state(R_ITRF, V_ITRF, self.epoch, "ITRF", frame)
            dr = np.abs(r - np.array(r_km) * 1e3).max()
            dv = np.abs(v - np.array(v_kms) * 1e3).max()
            self.assertLess(dr, r_tol, f"{frame} position off by {dr:.4f} m")
            self.assertLess(dv, v_tol, f"{frame} velocity off by {dv:.2e} m/s")

    def test_round_trip_between_all_frames(self):
        r_g, v_g = F.transform_state(R_ITRF, V_ITRF, self.epoch, "ITRF", "GCRF")
        for a in F.FRAMES:
            for b in F.FRAMES:
                ra, va = F.transform_state(r_g, v_g, self.epoch, "GCRF", a)
                rb, vb = F.transform_state(ra, va, self.epoch, a, b)
                r_back, v_back = F.transform_state(rb, vb, self.epoch, b, "GCRF")
                self.assertLess(np.abs(r_back - r_g).max(), 1e-6, f"{a}->{b}")
                self.assertLess(np.abs(v_back - v_g).max(), 1e-9, f"{a}->{b}")

    def test_vectorized_matches_single(self):
        offsets = np.linspace(0.0, 86400.0, 7)
        rs = np.tile(R_ITRF, (7, 1))
        vs = np.tile(V_ITRF, (7, 1))
        r_vec, v_vec = F.transform_state(rs, vs, self.epoch, "ITRF", "GCRF", offsets_s=offsets)
        for i, dt in enumerate(offsets):
            r1, v1 = F.transform_state(R_ITRF, V_ITRF, self.epoch + dt, "ITRF", "GCRF")
            self.assertLess(np.abs(r_vec[i] - r1).max(), 1e-6)
            self.assertLess(np.abs(v_vec[i] - v1).max(), 1e-9)

    def test_aliases(self):
        for alias, name in (("ECEF", "ITRF"), ("J2000", "EME2000"), ("ICRF", "GCRF"), ("PEF", "TIRS")):
            self.assertEqual(F.canonical_frame(alias), name)
        with self.assertRaises(ValueError):
            F.canonical_frame("NOT_A_FRAME")

    def test_geodetic(self):
        lat, lon, h = F.itrf_to_geodetic(np.array([6378137.0 + 500e3, 0.0, 0.0]))
        self.assertAlmostEqual(lat, 0.0, places=9)
        self.assertAlmostEqual(lon, 0.0, places=9)
        self.assertAlmostEqual(h, 500e3, places=3)
        back = F.geodetic_to_itrf(45.0, -120.0, 1000.0)
        lat, lon, h = F.itrf_to_geodetic(back)
        self.assertAlmostEqual(lat, 45.0, places=9)
        self.assertAlmostEqual(lon, -120.0, places=9)
        self.assertAlmostEqual(h, 1000.0, places=4)

    def test_local_frames_are_orthonormal(self):
        r_g, v_g = F.transform_state(R_ITRF, V_ITRF, self.epoch, "ITRF", "GCRF")
        for builder in (F.rtn_matrix, F.vnc_matrix, F.lvlh_matrix):
            m = builder(r_g, v_g)
            self.assertLess(np.abs(m @ m.T - np.eye(3)).max(), 1e-12)
            self.assertAlmostEqual(np.linalg.det(m), 1.0, places=12)


class TestFastEarthRotation(unittest.TestCase):

    def test_matches_full_chain_over_30_days(self):
        eop.set_eop(None)
        ep = Epoch.from_iso("2026-10-23T00:00:00Z")
        fast = F.FastEarthRotation(ep, 0.0, 30 * 86400.0)
        ts = np.linspace(0.0, 30 * 86400.0, 97) + 1234.5
        ts = ts[ts <= 30 * 86400.0]
        full = F.EarthOrientation(ep, ts).gcrf_to("ITRF")
        err = max(np.abs(fast.matrix(t) - full[k]).max() for k, t in enumerate(ts))
        self.assertLess(err, 1e-10)


class TestPropagationEpoch(unittest.TestCase):

    def _state(self):
        r, v = keplerian_to_cartesian(26560e3, 0.72, np.radians(63.4), np.radians(30.0), np.radians(270.0), 0.0)
        return np.concatenate([r, v])

    def test_epoch_drives_ground_track(self):
        y0 = self._state()
        a = ThirdReviewEngine(y0, epoch="2026-10-23T00:00:00Z").propagate((0.0, 3600.0), num_points=5, model="two_body")
        b = ThirdReviewEngine(y0, epoch="2026-10-23T06:00:00Z").propagate((0.0, 3600.0), num_points=5, model="two_body")
        self.assertEqual(a["epoch_utc"], "2026-10-23T00:00:00.000Z")
        self.assertEqual(a["utc_iso"][-1], "2026-10-23T01:00:00.000Z")
        np.testing.assert_allclose(a["position_m"], b["position_m"], atol=1e-6)
        # Same inertial orbit 6 h later: Earth has turned ~90.25 deg, so longitude shifts west
        shift = (a["longitude_deg"][0] - b["longitude_deg"][0]) % 360.0
        self.assertAlmostEqual(shift, 90.2464, delta=0.01)
        np.testing.assert_allclose(a["latitude_deg"], b["latitude_deg"], atol=1e-3)

    def test_altitude_is_wgs84_height(self):
        y0 = self._state()
        sol = ThirdReviewEngine(y0, epoch="2026-10-23T00:00:00Z").propagate((0.0, 60.0), num_points=2, model="two_body")
        lat, lon, h = F.gcrf_to_geodetic(sol["position_m"][0], Epoch.from_iso("2026-10-23T00:00:00Z"))
        self.assertAlmostEqual(sol["altitude_km"][0], h / 1000.0, places=6)


if __name__ == "__main__":
    unittest.main()
