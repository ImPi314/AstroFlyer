"""
AstroFlyer HEO - Phase 4: mission script interpreter, batch runs and /api/script/run.
Written before the implementation (tests-first rule, 2026-10-24).

Scripts use the GMAT-style syntax the app's script editor writes
(trajectory_engine.MissionScriptWorkbench), so existing scripts keep working.
"""

import json
import math
import os
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer

import numpy as np

from astroflyer.backend.ephemeris_io import read_oem
from astroflyer.backend.epoch import Epoch
from astroflyer.backend.forces import MU_EARTH
from astroflyer.backend.script_runner import main, run_script
from astroflyer.backend.trajectory_engine import MissionScriptWorkbench

HEADER = """
Create Spacecraft Sat;
Sat.DateFormat = UTCGregorian;
Sat.Epoch = '23 Oct 2026 00:00:00.000';
Sat.CoordinateSystem = EarthMJ2000Eq;
Sat.DisplayStateType = Keplerian;
Sat.SMA = {sma};
Sat.ECC = {ecc};
Sat.INC = 28.5;
Sat.RAAN = 0;
Sat.AOP = 0;
Sat.TA = 0;
Sat.DryMass = 1000;
Sat.Tanks = {{Tank1}};

Create ChemicalTank Tank1;
Tank1.FuelMass = 800;

Create ForceModel PointMass;
PointMass.GravityField.Earth.Degree = 0;
PointMass.GravityField.Earth.Order = 0;
PointMass.PointMasses = {{}};

Create Propagator Prop;
Prop.FM = PointMass;
Prop.Type = RungeKutta89;
Prop.Accuracy = 1e-12;
"""


def header(sma=7000.0, ecc=0.0):
    return HEADER.format(sma=sma, ecc=ecc)


def kepler_period(sma_km):
    return 2.0 * math.pi * math.sqrt((sma_km * 1e3) ** 3 / MU_EARTH)


class TestEditorScriptsStillRun(unittest.TestCase):

    def test_workbench_script_runs_end_to_end(self):
        text = MissionScriptWorkbench.generate_mission_script(num_orbits=1, enable_bplane_target=False)
        out = run_script(text)
        self.assertIsNone(out["error"], out["error"])
        sat = out["spacecraft"]["AstroFlyer_HEO_SC"]
        start = Epoch.from_iso("2026-09-24T00:00:00Z")
        # The editor writes the duration as ElapsedDays rounded to 4 decimals
        expected = round(kepler_period(24389.0) / 86400.0, 4) * 86400.0
        self.assertAlmostEqual(Epoch.from_iso(sat["epoch_utc"]) - start, expected, delta=0.01)
        self.assertGreater(len(out["ephemeris"]["AstroFlyer_HEO_SC"]["epochs_utc"]), 100)
        self.assertIn("AstroFlyer HEO Mission Sequence Completed Successfully.", out["log"])

    def test_default_generated_script_runs(self):
        # The script /api/propagate hands the editor must run as-is: an Earth-orbit HEO never reaches
        # a lunar periapsis, so the generator leaves the lunar B-plane targeter out unless asked
        out = run_script(MissionScriptWorkbench.generate_mission_script(num_orbits=1))
        self.assertIsNone(out["error"], out["error"])

    def test_propagate_endpoint_script_runs(self):
        from astroflyer.backend.app_server import create_server
        server = create_server(port=0)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        body = json.dumps({"hp": 500, "ha": 39800, "inc": 63.4, "num_orbits": 1}).encode()
        req = urllib.request.Request(f"http://127.0.0.1:{server.server_address[1]}/api/propagate", body,
                                     {"Content-Type": "application/json"})
        payload = json.load(urllib.request.urlopen(req, timeout=600))
        out = run_script(payload["script_workbench"]["script_content"])
        self.assertIsNone(out["error"], out["error"])

    def test_unsupported_bplane_goal_is_a_clear_error(self):
        text = MissionScriptWorkbench.generate_mission_script(num_orbits=1, enable_bplane_target=True)
        out = run_script(text)
        self.assertIsNotNone(out["error"])
        self.assertIsInstance(out["error"]["line"], int)
        self.assertIn("Luna", out["error"]["message"])     # Moon-centred stops and B-plane goals are not modelled


class TestSequence(unittest.TestCase):

    def test_propagate_to_apoapsis_and_by_time(self):
        out = run_script(header(sma=24000.0, ecc=0.7) + """
BeginMissionSequence;
Propagate Prop(Sat) {Sat.Apoapsis};
Propagate Prop(Sat) {Sat.ElapsedSecs = 600};
""")
        self.assertIsNone(out["error"], out["error"])
        start = Epoch.from_iso("2026-10-23T00:00:00Z")
        end = Epoch.from_iso(out["spacecraft"]["Sat"]["epoch_utc"])
        self.assertAlmostEqual(end - start, kepler_period(24000.0) / 2.0 + 600.0, delta=1e-3)

    def test_reports_variables_loops_and_branches(self):
        out = run_script(header() + """
Create ReportFile Rpt;
Create Variable I Total;
BeginMissionSequence;
Report 'start';
Total = 0;
For I = 1:3;
   Propagate Prop(Sat) {Sat.ElapsedSecs = 100};
   Total = Total + I^2;
   Report Rpt Sat.ElapsedSecs Sat.SMA I;
EndFor;
If Total == 14;
   Report 'sum ok';
Else;
   Report 'sum wrong';
EndIf;
""")
        self.assertIsNone(out["error"], out["error"])
        rep = out["reports"]["Rpt"]
        self.assertEqual(rep["columns"], ["Sat.ElapsedSecs", "Sat.SMA", "I"])
        self.assertEqual([round(row[0], 6) for row in rep["rows"]], [100.0, 200.0, 300.0])
        self.assertAlmostEqual(rep["rows"][-1][1], 7000.0, delta=1e-6)
        self.assertEqual(out["log"][:1] + out["log"][-1:], ["start", "sum ok"])

    def test_impulsive_burn_in_vnb(self):
        out = run_script(header() + """
Create ImpulsiveBurn Kick;
Kick.Axes = VNB;
Kick.Element1 = 0.1;
Kick.DecrementMass = true;
Kick.Isp = 300;
BeginMissionSequence;
Maneuver Kick(Sat);
""")
        self.assertIsNone(out["error"], out["error"])
        sat = out["spacecraft"]["Sat"]
        v_circ = math.sqrt(MU_EARTH / 7000e3)
        self.assertAlmostEqual(np.linalg.norm(sat["velocity_ms"]), v_circ + 100.0, delta=1e-6)
        self.assertAlmostEqual(sat["fuel_mass_kg"], 800.0 - 1800.0 * (1.0 - math.exp(-100.0 / (300.0 * 9.80665))),
                               places=6)

    def test_finite_burn_uses_fuel(self):
        out = run_script(header() + """
Create ChemicalThruster Engine;
Engine.Thrust = 400;
Engine.Isp = 320;
Engine.Axes = VNB;
Create FiniteBurn Firing;
Firing.Thrusters = {Engine};
Create ReportFile Rpt;
BeginMissionSequence;
BeginFiniteBurn Firing(Sat);
Propagate Prop(Sat) {Sat.ElapsedSecs = 600};
EndFiniteBurn Firing(Sat);
Propagate Prop(Sat) {Sat.ElapsedSecs = 600};
Report Rpt Sat.TotalMass Tank1.FuelMass;
""")
        self.assertIsNone(out["error"], out["error"])
        used = 400.0 / (320.0 * 9.80665) * 600.0
        mass, fuel = out["reports"]["Rpt"]["rows"][0]
        self.assertAlmostEqual(fuel, 800.0 - used, places=6)
        self.assertAlmostEqual(mass, 1800.0 - used, places=6)
        self.assertGreater(out["spacecraft"]["Sat"]["sma_km"], 7000.0)

    def test_hohmann_transfer_by_targeting(self):
        out = run_script(header() + """
Create ImpulsiveBurn TOI GOI;
TOI.Axes = VNB;
GOI.Axes = VNB;
Create DifferentialCorrector DC;
BeginMissionSequence;
Target DC;
   Vary DC(TOI.Element1 = 1.0, {Perturbation = 0.0001, MaxStep = 0.5, Lower = 0, Upper = 3});
   Maneuver TOI(Sat);
   Propagate Prop(Sat) {Sat.Apoapsis};
   Achieve DC(Sat.RMAG = 42164, {Tolerance = 0.1});
   Vary DC(GOI.Element1 = 1.0, {Perturbation = 0.0001, MaxStep = 0.5, Lower = 0, Upper = 3});
   Maneuver GOI(Sat);
   Achieve DC(Sat.ECC = 0.0005, {Tolerance = 0.0001});
EndTarget;
Propagate Prop(Sat) {Sat.ElapsedDays = 0.5};
""")
        self.assertIsNone(out["error"], out["error"])
        (target,) = out["targets"]
        self.assertTrue(target["converged"], target["message"])
        r1, r2 = 7000.0, 42164.0
        mu = MU_EARTH / 1e9
        dv1 = math.sqrt(mu / r1) * (math.sqrt(2 * r2 / (r1 + r2)) - 1)
        dv2 = math.sqrt(mu / r2) * (1 - math.sqrt(2 * r1 / (r1 + r2)))
        self.assertAlmostEqual(target["variables"]["TOI.Element1"], dv1, delta=1e-3)
        self.assertAlmostEqual(target["variables"]["GOI.Element1"], dv2, delta=2e-3)
        self.assertAlmostEqual(out["spacecraft"]["Sat"]["sma_km"], 42164.0, delta=30.0)
        self.assertLess(out["spacecraft"]["Sat"]["ecc"], 0.001)

    def test_mod_julian_epoch(self):
        text = header().replace("Sat.DateFormat = UTCGregorian;", "Sat.DateFormat = UTCModJulian;").replace(
            "Sat.Epoch = '23 Oct 2026 00:00:00.000';", "Sat.Epoch = 31336.5;")
        out = run_script(text + "BeginMissionSequence;\nPropagate Prop(Sat) {Sat.ElapsedSecs = 60};\n")
        self.assertIsNone(out["error"], out["error"])
        # ModJulian 31336.5 = JD 2461336.5 = 2026-10-23 00:00 UTC
        self.assertEqual(out["spacecraft"]["Sat"]["epoch_utc"], "2026-10-23T00:01:00.000Z")


class TestErrors(unittest.TestCase):

    def test_errors_name_the_line(self):
        cases = {
            "Fly Sat to Mars;": "Unsupported command",
            "Propagate Prop(Sat);": "stopping condition",
            "Maneuver Nope(Sat);": "Unknown object",
            "Report Rpt Sat.Nonsense;": "Unknown spacecraft parameter",
        }
        for bad, phrase in cases.items():
            text = header() + "Create ReportFile Rpt;\nBeginMissionSequence;\n" + bad + "\n"
            out = run_script(text)
            self.assertIsNotNone(out["error"], bad)
            self.assertIn(phrase, out["error"]["message"], bad)
            self.assertEqual(out["error"]["line"], text.count("\n"), bad)

    def test_unclosed_block(self):
        out = run_script(header() + "BeginMissionSequence;\nFor I = 1:2;\n")
        self.assertIn("never closed", out["error"]["message"])


class TestBatchAndApi(unittest.TestCase):
    SCRIPT = header(sma=24000.0, ecc=0.7) + """
Create ReportFile Rpt;
BeginMissionSequence;
Propagate Prop(Sat) {Sat.Periapsis};
Report Rpt Sat.UTCGregorian Sat.Altitude;
"""

    def test_command_line_writes_json_and_oem(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = os.path.join(tmp, "mission.script")
            with open(script, "w") as fh:
                fh.write(self.SCRIPT)
            code = main([script, "--json", os.path.join(tmp, "out.json"), "--oem", tmp])
            self.assertEqual(code, 0)
            with open(os.path.join(tmp, "out.json")) as fh:
                result = json.load(fh)
            self.assertEqual(result["reports"]["Rpt"]["columns"], ["Sat.UTCGregorian", "Sat.Altitude"])
            (table,) = read_oem(os.path.join(tmp, "Sat.oem"))
            self.assertAlmostEqual(table.t[-1], kepler_period(24000.0), delta=1e-3)

    def test_command_line_reports_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = os.path.join(tmp, "bad.script")
            with open(script, "w") as fh:
                fh.write(header() + "BeginMissionSequence;\nFly Sat;\n")
            self.assertEqual(main([script]), 1)

    def test_api_endpoint(self):
        from astroflyer.backend.app_server import ThirdReviewAppHandler

        server = ThreadingHTTPServer(("127.0.0.1", 0), ThirdReviewAppHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_address[1]}/api/script/run"
            req = urllib.request.Request(url, data=json.dumps({"script_text": self.SCRIPT}).encode(),
                                         headers={"Content-Type": "application/json"})
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(req, timeout=60) as resp:
                body = json.load(resp)
        finally:
            server.shutdown()
            server.server_close()
        self.assertIsNone(body["error"])
        self.assertEqual(len(body["reports"]["Rpt"]["rows"]), 1)
        eph = body["ephemeris"]["Sat"]
        self.assertEqual(len(eph["epochs_utc"]), len(eph["position_m"]))


if __name__ == "__main__":
    unittest.main()
