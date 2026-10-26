"""
AstroFlyer HEO - the run's TLE, OPM and mission script are for the run's own epoch and state.

They used to carry a fixed 24 Sep 2026 epoch whatever the run's was, the OPM a placeholder
state vector, and the TLE the run's osculating elements as if they were SGP4 mean elements.
Now the TLE holds SGP4 mean elements fitted so that SGP4 reproduces the run's initial state at
the run's epoch. Written before the implementation.
"""

import math
import re
import unittest

import numpy as np

from astroflyer.backend.analytic import TLEPropagator
from astroflyer.backend.epoch import Epoch
from astroflyer.backend.propagation_run import run
from astroflyer.backend.script_runner import _parse_script_epoch

CASES = {
    "molniya": {"hp": 1000.0, "ha": 39350.0, "inc": 63.4, "raan": 20.0, "aop": 270.0, "ta": 10.0,
                "epoch": "2026-01-01T06:30:15.250Z"},
    "gto": {"hp": 250.0, "ha": 35786.0, "inc": 28.5, "raan": 45.0, "aop": 30.0, "ta": 0.0,
            "epoch": "2027-07-14T18:00:00Z"},
    "near_geo": {"a": 42164.0, "e": 0.0003, "inc": 0.05, "raan": 10.0, "aop": 0.0, "ta": 40.0,
                 "epoch": "2026-11-30T23:59:59Z"},
}
COMMON = {"num_orbits": 1, "num_points": 200, "model": "two_body", "mass": 1234.0, "cd": 2.1,
          "drag_area": 11.0, "cr": 1.3, "srp_area": 17.0}


class ExportsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.reports = {name: run({**COMMON, **case}) for name, case in CASES.items()}

    def initial_state(self, name):
        rep = self.reports[name]
        return np.asarray(rep["position_m"][0]), np.asarray(rep["velocity_ms"][0])

    def test_tle_reproduces_the_run_initial_state_at_its_epoch(self):
        for name, case in CASES.items():
            with self.subTest(case=name):
                lines = self.reports[name]["ccsds_interoperability"]["tle_string"].strip().splitlines()
                self.assertEqual(len(lines[1]), 69)
                self.assertEqual(len(lines[2]), 69)
                tle = TLEPropagator(lines[1], lines[2])
                epoch = Epoch.coerce(case["epoch"])
                self.assertLess(abs(tle.epoch - epoch), 1e-3)
                r, v = tle.states(epoch, [0.0])
                r0, v0 = self.initial_state(name)
                self.assertLess(np.linalg.norm(r[0] - r0), 200.0)
                self.assertLess(np.linalg.norm(v[0] - v0), 0.2)
                fit = self.reports[name]["ccsds_interoperability"]["tle_fit"]
                self.assertAlmostEqual(fit["position_error_m"], np.linalg.norm(r[0] - r0), delta=1.0)

    def test_opm_holds_the_run_epoch_state_and_spacecraft(self):
        for name, case in CASES.items():
            with self.subTest(case=name):
                opm = self.reports[name]["ccsds_interoperability"]["opm_string"]
                fields = dict(re.findall(r"^(\w+)\s*=\s*(\S+)", opm, re.M))
                self.assertEqual(fields["REF_FRAME"], "GCRF")
                self.assertEqual(fields["TIME_SYSTEM"], "UTC")
                self.assertLess(abs(Epoch.coerce(fields["EPOCH"] + "Z") - Epoch.coerce(case["epoch"])), 1e-3)
                r0, v0 = self.initial_state(name)
                got_r = np.array([float(fields[k]) for k in ("X", "Y", "Z")]) * 1000.0
                got_v = np.array([float(fields[k]) for k in ("X_DOT", "Y_DOT", "Z_DOT")]) * 1000.0
                np.testing.assert_allclose(got_r, r0, atol=1e-3)
                np.testing.assert_allclose(got_v, v0, atol=1e-5)
                self.assertEqual(float(fields["MASS"]), 1234.0)
                self.assertEqual(float(fields["DRAG_AREA"]), 11.0)
                self.assertEqual(float(fields["SOLAR_RAD_AREA"]), 17.0)

    def test_script_epoch_is_the_run_epoch(self):
        for name, case in CASES.items():
            with self.subTest(case=name):
                script = self.reports[name]["script_workbench"]["script_content"]
                fmt = re.search(r"\.DateFormat\s*=\s*(\w+);", script).group(1)
                text = re.search(r"\.Epoch\s*=\s*'([^']+)';", script).group(1)
                self.assertLess(abs(_parse_script_epoch(text, fmt) - Epoch.coerce(case["epoch"])), 1e-3)
                self.assertNotIn("24 Sep 2026", script)


if __name__ == "__main__":
    unittest.main()
