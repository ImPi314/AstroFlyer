"""
AstroFlyer HEO - the run's station contacts and radiation-belt L-shells use the real Earth
orientation at the run's epoch.

The quick-look contacts used to rotate the Earth by omega*t from zero at the run start (so the
Earth Rotation Angle at the epoch, about 100 deg on 2026-01-01, was missing) and put the
stations on a 6371 km sphere; the dipole of the radiation model rotated the same way. They are
checked against Analysis > Access (access.station_passes: IAU 2006/2000A GCRF to ITRF, WGS-84
stations) and against the run's own Earth-fixed positions. Written before the implementation.
"""

import math
import unittest

import numpy as np

from astroflyer.backend import access
from astroflyer.backend.epoch import Epoch
from astroflyer.backend.event_predictor import EventPredictor
from astroflyer.backend.propagation_run import run
from astroflyer.backend.radiation_belts import DIPOLE_LON_RAD, DIPOLE_TILT_RAD, RadiationBeltModel

EPOCH = "2026-01-01T00:00:00Z"
MOLNIYA = {"hp": 1000.0, "ha": 39350.0, "inc": 63.4, "raan": 0.0, "aop": 270.0, "ta": 0.0,
           "num_orbits": 2, "num_points": 800, "model": "two_body", "epoch": EPOCH}


def _station(st):
    return access.GroundStation(st["name"], st["lat_deg"], st["lon_deg"], st["alt_m"], st["min_el_deg"])


class StationContactsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.report = run(MOLNIYA)
        cls.times = np.asarray(cls.report["times"])
        cls.r = np.asarray(cls.report["position_m"])
        cls.v = np.asarray(cls.report["velocity_ms"])
        cls.epoch = Epoch.coerce(EPOCH)

    def test_run_contacts_match_the_access_analysis(self):
        stations = EventPredictor().ground_stations
        reported = self.report["events_suite"]["ground_stations"]
        total = 0
        for st in stations:
            with self.subTest(station=st["name"]):
                expected = access.station_passes(_station(st), self.epoch, self.times, self.r, self.v)
                got = reported[st["name"]]["passes"]
                self.assertEqual(len(got), len(expected))
                for p, x in zip(got, expected):
                    self.assertAlmostEqual(p["aos_epoch_s"], x["aos"] - self.epoch, delta=1.0)
                    self.assertAlmostEqual(p["los_epoch_s"], x["los"] - self.epoch, delta=1.0)
                    self.assertAlmostEqual(p["max_elevation_deg"], x["max_elevation_deg"], delta=0.05)
                total += len(got)
        self.assertGreater(total, 0)        # the orbit is seen by some station, so the check is not empty

    def test_elevation_series_matches_the_access_look_angles(self):
        st = EventPredictor().ground_stations[0]
        out = EventPredictor([st]).predict_ground_station_passes(self.times, self.r, self.epoch, self.v)
        look = _station(st).look_angles(self.epoch, self.times, self.r)
        np.testing.assert_allclose(out[st["name"]]["elevation_series_deg"], look["elevation_deg"], atol=1e-6)
        np.testing.assert_allclose(out[st["name"]]["slant_range_km"], look["range_m"] / 1000.0, rtol=1e-9)

    def test_contacts_depend_on_the_epoch(self):
        # Half a sidereal day later the Earth has turned 180 deg under the same inertial orbit
        later = self.epoch + 0.5 * 86164.0905
        st = {"name": "Equator 0E", "lat_deg": 0.0, "lon_deg": 0.0, "alt_m": 0.0, "min_el_deg": 0.0}
        a = EventPredictor([st]).predict_ground_station_passes(self.times[:50], self.r[:50], self.epoch)
        b = EventPredictor([st]).predict_ground_station_passes(self.times[:50], self.r[:50], later)
        self.assertGreater(np.max(np.abs(a[st["name"]]["elevation_series_deg"]
                                         - b[st["name"]]["elevation_series_deg"])), 10.0)

    def test_radiation_uses_the_run_earth_fixed_positions(self):
        expected = RadiationBeltModel().evaluate_trajectory_radiation(
            self.times, np.asarray(self.report["position_itrf_m"]))
        np.testing.assert_allclose(self.report["radiation_belts"]["l_shell_series"],
                                   expected["l_shell_series"], rtol=1e-9)


class DipoleTest(unittest.TestCase):

    def test_dipole_axis_is_fixed_in_the_earth(self):
        # The dipole north pole at 78.5 N, 72.6 W in Earth-fixed axes has magnetic latitude 90 deg
        lat = math.pi / 2.0 - DIPOLE_TILT_RAD
        pole = 2.0e7 * np.array([math.cos(lat) * math.cos(DIPOLE_LON_RAD),
                                 math.cos(lat) * math.sin(DIPOLE_LON_RAD), math.sin(lat)])
        out = RadiationBeltModel().compute_magnetic_coordinates(pole)
        self.assertAlmostEqual(out["mag_lat_deg"], 90.0, places=1)
        # and a point on the magnetic equator, perpendicular to the axis, has latitude 0
        equator = np.cross(pole, [0.0, 0.0, 1.0])
        self.assertAlmostEqual(RadiationBeltModel().compute_magnetic_coordinates(equator)["mag_lat_deg"], 0.0,
                               places=6)


if __name__ == "__main__":
    unittest.main()
