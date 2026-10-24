"""
AstroFlyer HEO - Phase 5: ground-station access, eclipses, beta angle and reports.
Written before the implementation (tests-first rule, 2026-10-24).
"""

import json
import math
import threading
import unittest
import urllib.request

import numpy as np

from astroflyer.backend import analytic
from astroflyer.backend import frames as F
from astroflyer.backend.access import (GroundStation, beta_angle, eclipse_intervals, report, shadow_fraction,
                                       station_passes, write_report_csv)
from astroflyer.backend.ephemeris import get_ephemeris
from astroflyer.backend.epoch import Epoch
from astroflyer.backend.forces import R_EARTH_EQ
from astroflyer.backend.mission import state_from_keplerian

EPOCH = Epoch.from_iso("2026-10-23T00:00:00Z")


def kepler_run(a, e, inc_deg, raan_deg, argp_deg, ta_deg, span_s, step_s):
    r0, v0 = state_from_keplerian(a, e, math.radians(inc_deg), math.radians(raan_deg), math.radians(argp_deg),
                                  math.radians(ta_deg))
    y0 = np.concatenate([r0, v0])
    t = np.arange(0.0, span_s + 1e-9, step_s)
    r, v = analytic.kepler_states(y0, t)
    return y0, t, r, v


def sun_unit(epoch, t_s=0.0):
    s = get_ephemeris().sun_gcrf(float(epoch - Epoch.j2000()) + t_s)
    return s / np.linalg.norm(s)


class TestLookAngles(unittest.TestCase):

    def setUp(self):
        self.station = GroundStation("EQ", 0.0, 0.0, 0.0)
        self.up = np.array([1.0, 0.0, 0.0])        # ITRF zenith at lat 0, lon 0
        self.north = np.array([0.0, 0.0, 1.0])
        self.east = np.array([0.0, 1.0, 0.0])

    def _gcrf(self, r_itrf):
        return F.transform_position(np.atleast_2d(r_itrf), EPOCH, "ITRF", "GCRF")

    def test_zenith_north_and_east(self):
        site = np.array([R_EARTH_EQ, 0.0, 0.0])
        cases = [(site + 1000e3 * self.up, 90.0, None),
                 (site + 1000e3 * self.up + 50e3 * self.north, None, 0.0),
                 (site + 1000e3 * self.up + 50e3 * self.east, None, 90.0)]
        for r_itrf, el, az in cases:
            out = self.station.look_angles(EPOCH, [0.0], self._gcrf(r_itrf))
            if el is not None:
                self.assertAlmostEqual(out["elevation_deg"][0], el, places=6)
                self.assertAlmostEqual(out["range_m"][0], 1000e3, delta=1e-3)
            if az is not None:
                self.assertAlmostEqual(out["azimuth_deg"][0], az, places=6)

    def test_range_rate_matches_numerical_derivative(self):
        _, t, r, v = kepler_run(7078e3, 0.001, 51.6, 10.0, 0.0, 0.0, 600.0, 1.0)
        out = GroundStation("MID", 30.0, 20.0, 100.0).look_angles(EPOCH, t, r, v)
        numeric = np.gradient(out["range_m"], t)
        np.testing.assert_allclose(out["range_rate_ms"][5:-5], numeric[5:-5], atol=0.05)

    def test_mask_interpolates_and_wraps(self):
        st = GroundStation("M", 0.0, 0.0, 0.0, min_elevation_deg=5.0,
                           mask=[(0.0, 10.0), (90.0, 30.0), (180.0, 10.0), (350.0, 20.0)])
        self.assertAlmostEqual(st.min_elevation_at(45.0), 20.0)
        self.assertAlmostEqual(st.min_elevation_at(355.0), 15.0)     # between 350 and 360 (= 0)
        self.assertAlmostEqual(st.min_elevation_at(265.0), 15.0)
        low = GroundStation("L", 0.0, 0.0, 0.0, min_elevation_deg=12.0, mask=[(0.0, 2.0)])
        self.assertAlmostEqual(low.min_elevation_at(123.0), 12.0)    # the flat minimum still applies


class TestStationPasses(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.y0, cls.t, cls.r, cls.v = kepler_run(R_EARTH_EQ + 700e3, 0.001, 98.2, 40.0, 0.0, 0.0, 86400.0, 30.0)

    def _elevation_at(self, station, t_s):
        r, v = analytic.kepler_states(self.y0, [t_s])
        out = station.look_angles(EPOCH, [t_s], r, v)
        return out["elevation_deg"][0], out["azimuth_deg"][0]

    def test_aos_los_and_max_elevation_are_refined(self):
        station = GroundStation("SVALBARD", 78.23, 15.41, 500.0, min_elevation_deg=5.0)
        passes = station_passes(station, EPOCH, self.t, self.r, self.v)
        self.assertGreater(len(passes), 8)            # a polar orbit sees Svalbard on most revolutions
        for p in passes:
            if p["partial"]:
                continue
            for key in ("aos", "los"):
                el, _ = self._elevation_at(station, p[key] - EPOCH)
                self.assertAlmostEqual(el, 5.0, delta=1e-4, msg=key)
            self.assertAlmostEqual(p["duration_s"], p["los"] - p["aos"], places=6)
            self.assertLess(p["aos"], p["tca"])
            self.assertLess(p["tca"], p["los"])
            el_max, _ = self._elevation_at(station, p["tca"] - EPOCH)
            self.assertAlmostEqual(el_max, p["max_elevation_deg"], delta=1e-4)

        # Brute force at 1 s finds the same passes
        t_fine = np.arange(0.0, 86400.0 + 1e-9, 1.0)
        r, v = analytic.kepler_states(self.y0, t_fine)
        el = station.look_angles(EPOCH, t_fine, r, v)["elevation_deg"]
        rises = t_fine[1:][(el[1:] >= 5.0) & (el[:-1] < 5.0)]
        self.assertEqual(len(rises), sum(1 for p in passes if not (p["partial"] and p["aos"] == EPOCH)))
        full = [p for p in passes if not p["partial"]]
        for p, rise in zip(full, rises[-len(full):]):
            self.assertAlmostEqual(p["aos"] - EPOCH, rise, delta=1.0)

    def test_mask_shortens_passes(self):
        open_sky = GroundStation("S", 78.23, 15.41, 500.0, min_elevation_deg=5.0)
        masked = GroundStation("S", 78.23, 15.41, 500.0, min_elevation_deg=5.0, mask=[(0.0, 25.0), (359.0, 25.0)])
        a = sum(p["duration_s"] for p in station_passes(open_sky, EPOCH, self.t, self.r, self.v))
        b = station_passes(masked, EPOCH, self.t, self.r, self.v)
        self.assertLess(sum(p["duration_s"] for p in b), a)
        for p in b:
            if not p["partial"]:
                el, _ = self._elevation_at(masked, p["aos"] - EPOCH)
                self.assertAlmostEqual(el, 25.0, delta=1e-3)

    def test_station_without_visibility(self):
        # An equatorial orbit never rises above 5 deg at the South Pole
        _, t, r, v = kepler_run(R_EARTH_EQ + 700e3, 0.0, 0.0, 0.0, 0.0, 0.0, 6000.0, 30.0)
        self.assertEqual(station_passes(GroundStation("POLE", -90.0, 0.0, 2800.0, 5.0), EPOCH, t, r, v), [])


class TestEclipsesAndBeta(unittest.TestCase):

    def test_geo_equinox_season(self):
        epoch = Epoch.from_iso("2026-03-20T00:00:00Z")
        _, t, r, v = kepler_run(42164.17e3, 0.0, 0.0, 0.0, 0.0, 0.0, 86400.0, 60.0)
        events = eclipse_intervals(epoch, t, r)
        umbra = [ev for ev in events if ev["kind"] == "umbra" and ev["body"] == "EARTH"]
        penumbra = [ev for ev in events if ev["kind"] == "penumbra" and ev["body"] == "EARTH"]
        self.assertEqual(len(umbra), 1)
        self.assertEqual(len(penumbra), 2)                          # entry and exit
        self.assertTrue(66 * 60 < umbra[0]["duration_s"] < 71 * 60, umbra[0]["duration_s"])
        for p in penumbra:
            self.assertTrue(60.0 < p["duration_s"] < 240.0, p["duration_s"])
        self.assertEqual(penumbra[0]["end"], umbra[0]["start"])
        self.assertEqual(umbra[0]["end"], penumbra[1]["start"])
        self.assertLess(abs(beta_angle(epoch, t[:1], r[:1], v[:1])[0]), 1.0)

    def test_geo_solstice_has_no_eclipse(self):
        epoch = Epoch.from_iso("2026-06-21T00:00:00Z")
        _, t, r, v = kepler_run(42164.17e3, 0.0, 0.0, 0.0, 0.0, 0.0, 86400.0, 60.0)
        self.assertEqual([ev for ev in eclipse_intervals(epoch, t, r) if ev["body"] == "EARTH"], [])
        self.assertAlmostEqual(abs(beta_angle(epoch, t[:1], r[:1], v[:1])[0]), 23.44, delta=0.3)

    def test_orbit_facing_the_sun_has_beta_90_and_no_shadow(self):
        s = sun_unit(EPOCH)
        # Orbit normal along the Sun: r and v both perpendicular to s
        x = np.cross(s, [0.0, 0.0, 1.0]); x /= np.linalg.norm(x)
        y = np.cross(s, x)
        rm = R_EARTH_EQ + 700e3
        vm = math.sqrt(3.986004418e14 / rm)
        y0 = np.concatenate([rm * x, vm * y])
        t = np.arange(0.0, 6000.0, 30.0)
        r, v = analytic.kepler_states(y0, t)
        beta = beta_angle(EPOCH, t, r, v)
        self.assertAlmostEqual(beta[0], 90.0, delta=1e-6)
        self.assertEqual(eclipse_intervals(EPOCH, t, r), [])
        np.testing.assert_allclose(shadow_fraction(EPOCH, t, r), 1.0)

    def test_moon_shadow(self):
        eph = get_ephemeris()
        tt = float(EPOCH - Epoch.j2000())
        r_sun, r_moon = eph.sun_moon_gcrf(tt)
        behind = r_moon + 10000e3 * (r_moon - r_sun) / np.linalg.norm(r_moon - r_sun)
        self.assertEqual(shadow_fraction(EPOCH, [0.0], [behind])[0], 0.0)
        self.assertEqual(shadow_fraction(EPOCH, [0.0], [behind], occulters=("EARTH",))[0], 1.0)

    def test_partial_interval_at_the_span_edges(self):
        # Starting inside the shadow: the first interval begins at the first sample and says so
        epoch = Epoch.from_iso("2026-03-20T00:00:00Z")
        s = sun_unit(epoch)
        r0 = -(R_EARTH_EQ + 700e3) * s
        h = np.cross(s, [0.0, 0.0, 1.0]); h /= np.linalg.norm(h)
        v0 = math.sqrt(3.986004418e14 / np.linalg.norm(r0)) * np.cross(h, r0 / np.linalg.norm(r0))
        t = np.arange(0.0, 3000.0, 10.0)
        r, _ = analytic.kepler_states(np.concatenate([r0, v0]), t)
        first = eclipse_intervals(epoch, t, r)[0]
        self.assertEqual((first["kind"], first["start"], first["partial"]), ("umbra", epoch, True))


class TestReports(unittest.TestCase):

    def setUp(self):
        self.y0, self.t, self.r, self.v = kepler_run(R_EARTH_EQ + 700e3, 0.0, 0.0, 0.0, 0.0, 0.0, 3000.0, 60.0)
        self.station = GroundStation("EQ", 0.0, 0.0, 0.0)

    def test_columns(self):
        table = report(EPOCH, self.t, self.r, self.v,
                       ["Epoch", "ElapsedSecs", "Altitude", "Latitude", "Longitude", "SMA", "ECC", "INC",
                        "RMAG", "VMAG", "BetaAngle", "ShadowFraction", "Elevation.EQ", "Range.EQ"],
                       stations=[self.station])
        self.assertEqual(list(table), ["Epoch", "ElapsedSecs", "Altitude", "Latitude", "Longitude", "SMA", "ECC",
                                       "INC", "RMAG", "VMAG", "BetaAngle", "ShadowFraction", "Elevation.EQ",
                                       "Range.EQ"])
        self.assertEqual(table["Epoch"][1], (EPOCH + 60.0).iso("UTC"))
        np.testing.assert_allclose(table["Altitude"], 700.0, atol=1e-6)               # km, on the equator
        np.testing.assert_allclose(table["Latitude"], 0.0, atol=1e-6)
        np.testing.assert_allclose(table["SMA"], (R_EARTH_EQ + 700e3) / 1e3, rtol=1e-9)
        np.testing.assert_allclose(table["RMAG"], (R_EARTH_EQ + 700e3) / 1e3, rtol=1e-9)
        np.testing.assert_allclose(table["INC"], 0.0, atol=1e-9)
        look = self.station.look_angles(EPOCH, self.t, self.r, self.v)
        np.testing.assert_allclose(table["Elevation.EQ"], look["elevation_deg"])
        np.testing.assert_allclose(table["Range.EQ"], look["range_m"] / 1e3)
        self.assertTrue(np.all((table["ShadowFraction"] >= 0.0) & (table["ShadowFraction"] <= 1.0)))

    def test_unknown_parameter_and_station(self):
        with self.assertRaises(ValueError):
            report(EPOCH, self.t, self.r, self.v, ["Altitud"])
        with self.assertRaises(ValueError):
            report(EPOCH, self.t, self.r, self.v, ["Elevation.NOPE"], stations=[self.station])

    def test_csv(self):
        table = report(EPOCH, self.t, self.r, self.v, ["Epoch", "Altitude"])
        lines = write_report_csv(None, table).strip().splitlines()
        self.assertEqual(lines[0], "Epoch,Altitude")
        self.assertEqual(len(lines), len(self.t) + 1)
        self.assertTrue(lines[1].startswith(EPOCH.iso("UTC") + ",700.0"))


class TestAccessEndpoint(unittest.TestCase):

    def test_api_analysis_access(self):
        from astroflyer.backend.app_server import create_server
        server = create_server(port=0)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        body = {"epoch": "2026-03-20T00:00:00Z", "sma_km": 42164.17, "ecc": 0.0, "inc_deg": 0.0,
                "raan_deg": 0.0, "aop_deg": 0.0, "ta_deg": 0.0, "duration_s": 86400.0, "step_s": 60.0,
                "model": "two_body",
                "stations": [{"name": "EQ", "lat_deg": 0.0, "lon_deg": 0.0, "height_m": 0.0,
                              "min_elevation_deg": 5.0}],
                "parameters": ["Epoch", "Altitude", "Elevation.EQ"]}
        req = urllib.request.Request(f"http://127.0.0.1:{server.server_address[1]}/api/analysis/access",
                                     json.dumps(body).encode(), {"Content-Type": "application/json"})
        out = json.load(urllib.request.urlopen(req, timeout=300))
        self.assertIsNone(out["error"])
        self.assertEqual(len(out["passes"]["EQ"]), 1)                 # GEO over the station all day
        self.assertTrue(out["passes"]["EQ"][0]["partial"])
        self.assertEqual(sum(1 for ev in out["eclipses"] if ev["kind"] == "umbra"), 1)
        self.assertEqual(len(out["report"]["Epoch"]), len(out["beta_angle_deg"]))
        self.assertIn("aos_utc", out["passes"]["EQ"][0])


if __name__ == "__main__":
    unittest.main()
