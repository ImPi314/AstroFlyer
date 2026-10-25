"""
AstroFlyer HEO - Phase 4: ephemeris files and the ephemeris propagator.
Written before the implementation (tests-first rule, 2026-10-24).
"""

import math
import os
import tempfile
import unittest

import numpy as np

from astroflyer.backend import analytic
from astroflyer.backend import frames as F
from astroflyer.backend.epoch import Epoch
from astroflyer.backend.ephemeris_io import (EphemerisTable, read_oem, read_opm, read_sp3, write_oem,
                                             write_opm)
from astroflyer.backend.mission import state_from_keplerian

EPOCH = Epoch.from_iso("2026-10-23T00:00:00Z")


def molniya_samples(step_s=60.0, span_s=6 * 3600.0):
    r0, v0 = state_from_keplerian(26560e3, 0.72, math.radians(63.4), math.radians(30.0), math.radians(270.0), 0.3)
    t = np.arange(0.0, span_s + 1e-9, step_s)
    r, v = analytic.kepler_states(np.concatenate([r0, v0]), t)
    return t, r, v, np.concatenate([r0, v0])


class TestEphemerisTable(unittest.TestCase):

    def test_lagrange_interpolation_between_samples(self):
        t, r, v, y0 = molniya_samples()
        epochs = [EPOCH + float(x) for x in t]
        mid = t[:-1] + 30.0
        r_ref, v_ref = analytic.kepler_states(y0, mid)
        # Worst case is the e = 0.72 perigee pass (~10 km/s) at 60 s spacing
        for order, r_tol, v_tol in ((8, 5e-3, 5e-5), (10, 1e-3, 5e-6)):
            table = EphemerisTable(epochs, r, v, order=order)
            r_i, v_i = table.state_at(mid)
            self.assertLess(np.abs(r_i - r_ref).max(), r_tol, f"order {order} position")
            self.assertLess(np.abs(v_i - v_ref).max(), v_tol, f"order {order} velocity")

    def test_accepts_epochs_and_hits_nodes_exactly(self):
        t, r, v, _ = molniya_samples(span_s=3600.0)
        table = EphemerisTable([EPOCH + float(x) for x in t], r, v)
        r_i, _ = table.state_at([EPOCH + 600.0, (EPOCH + 1200.0).iso("UTC", 6)])
        np.testing.assert_allclose(r_i, r[[10, 20]], atol=1e-6)

    def test_refuses_to_extrapolate(self):
        t, r, v, _ = molniya_samples(span_s=3600.0)
        table = EphemerisTable([EPOCH + float(x) for x in t], r, v)
        with self.assertRaises(ValueError):
            table.state_at([3700.0])


class TestOEM(unittest.TestCase):

    def test_round_trip_in_gcrf_and_eme2000(self):
        t, r, v, _ = molniya_samples(step_s=300.0, span_s=7200.0)
        epochs = [EPOCH + float(x) for x in t]
        for frame in ("GCRF", "EME2000"):
            text = write_oem(None, epochs, r, v, object_name="MOLNIYA-TEST", ref_frame=frame)
            self.assertIn(f"REF_FRAME = {frame}", text)
            self.assertIn("CCSDS_OEM_VERS = 2.0", text)
            (table,) = read_oem(text)
            self.assertEqual(table.name, "MOLNIYA-TEST")
            r_back, v_back = table.state_at(t)
            self.assertLess(np.abs(r_back - r).max(), 1e-3, frame)      # file precision: 1 mm
            self.assertLess(np.abs(v_back - v).max(), 1e-5, frame)

    def test_reads_comments_covariance_and_several_segments(self):
        text = """CCSDS_OEM_VERS = 2.0
COMMENT made by hand
CREATION_DATE = 2026-10-23T00:00:00
ORIGINATOR = TEST

META_START
OBJECT_NAME = SAT-A
OBJECT_ID = 2026-001A
CENTER_NAME = EARTH
REF_FRAME = GCRF
TIME_SYSTEM = UTC
START_TIME = 2026-10-23T00:00:00
STOP_TIME = 2026-10-23T00:02:00
META_STOP
COMMENT data follows
2026-10-23T00:00:00.000 7000.0 0.0 0.0 0.0 7.5 0.0
2026-10-23T00:01:00.000 6998.4 450.0 0.0 -0.05 7.49 0.0
2026-10-23T00:02:00.000 6993.6 899.5 0.0 -0.10 7.48 0.0
COVARIANCE_START
EPOCH = 2026-10-23T00:00:00
COV_REF_FRAME = RTN
1.0e-3
1.0e-5 1.0e-3
COVARIANCE_STOP

META_START
OBJECT_NAME = SAT-B
OBJECT_ID = 2026-001B
CENTER_NAME = EARTH
REF_FRAME = GCRF
TIME_SYSTEM = UTC
START_TIME = 2026-297T00:00:00
STOP_TIME = 2026-297T00:01:00
META_STOP
2026-297T00:00:00 8000.0 0.0 0.0 0.0 7.0 0.0
2026-297T00:01:00 7997.4 420.0 0.0 -0.05 7.0 0.0
"""
        tables = read_oem(text)
        self.assertEqual([t.name for t in tables], ["SAT-A", "SAT-B"])
        self.assertEqual(len(tables[0].t), 3)
        self.assertEqual(tables[1].start.iso("UTC"), "2026-10-24T00:00:00.000Z")   # day 297 of 2026
        np.testing.assert_allclose(tables[0].r[0], [7000e3, 0.0, 0.0])

    def test_write_to_file(self):
        t, r, v, _ = molniya_samples(step_s=600.0, span_s=3600.0)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "sat.oem")
            write_oem(path, [EPOCH + float(x) for x in t], r, v)
            (table,) = read_oem(path)
        self.assertEqual(len(table.t), len(t))


class TestOPM(unittest.TestCase):

    def test_round_trip_with_spacecraft_parameters(self):
        _, r, v, _ = molniya_samples(span_s=0.0)
        text = write_opm(None, EPOCH, r[0], v[0], object_name="SAT", ref_frame="EME2000", mass_kg=1200.0,
                         drag_area_m2=12.0, cd=2.2, srp_area_m2=15.0, cr=1.3)
        out = read_opm(text)
        self.assertEqual(out["object_name"], "SAT")
        self.assertEqual(out["epoch"], EPOCH)
        self.assertLess(np.abs(out["r_m"] - r[0]).max(), 1e-3)
        self.assertLess(np.abs(out["v_ms"] - v[0]).max(), 1e-5)
        self.assertEqual((out["mass_kg"], out["cd"], out["cr"]), (1200.0, 2.2, 1.3))


class TestSP3(unittest.TestCase):

    def _sp3(self, with_velocity):
        # A GPS-like orbit sampled every 15 min, written in ITRF km as SP3-c records
        r0, v0 = state_from_keplerian(26560e3, 0.01, math.radians(55.0), 0.4, 0.2, 0.0)
        t = np.arange(0.0, 6 * 3600.0 + 1, 900.0)
        r, v = analytic.kepler_states(np.concatenate([r0, v0]), t)
        start = Epoch.from_iso("2026-10-23T00:00:00", scale="GPS")
        lines = ["#cP2026 10 23  0  0  0.00000000      25 ORBIT IGS20 HLM  TEST",
                 "## 2389 432000.00000000   900.00000000 61336 0.0000000000000",
                 "+    1   G01  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0",
                 "%c G  cc GPS ccc cccc cccc cccc cccc ccccc ccccc ccccc ccccc"]
        r_itrf, v_itrf = F.transform_state(r, v, start, "GCRF", "ITRF", offsets_s=t)
        for k, tk in enumerate(t):
            ep = (start + float(tk)).iso("GPS", 6)
            date, clock = ep.split("T")
            y, mo, d = date.split("-")
            hh, mm, ss = clock.split()[0].split(":")
            lines.append(f"*  {y} {int(mo):2d} {int(d):2d} {int(hh):2d} {int(mm):2d} {float(ss):11.8f}")
            lines.append("PG01" + "".join(f"{x / 1e3:14.6f}" for x in r_itrf[k]) + "      0.000000")
            if with_velocity:
                lines.append("VG01" + "".join(f"{x * 10.0:14.6f}" for x in v_itrf[k]) + "      0.000000")
        lines.append("EOF")
        return "\n".join(lines) + "\n", start, t, r, v

    def test_positions_and_velocities_come_back_in_gcrf(self):
        for with_velocity in (True, False):
            text, start, t, r, v = self._sp3(with_velocity)
            table = read_sp3(text)
            self.assertEqual(table.name, "G01")
            self.assertEqual(table.start, start)
            r_back, v_back = table.state_at(t)
            self.assertLess(np.abs(r_back - r).max(), 2e-3)
            # Without V records the velocity comes from the interpolating polynomial
            self.assertLess(np.abs(v_back - v).max(), 1e-3 if with_velocity else 0.05, f"V records: {with_velocity}")


if __name__ == "__main__":
    unittest.main()
