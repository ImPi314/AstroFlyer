"""Checks for the offline packaging helpers: space-weather loading, manifest status, local-only server."""

import datetime
import os
import shutil
import sys
import tempfile
import unittest
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import offline_data  # noqa: E402

SAMPLE_CSV = (
    "DATE,BSRN,ND,KP1,KP2,KP3,KP4,KP5,KP6,KP7,KP8,KP_SUM,AP1,AP2,AP3,AP4,AP5,AP6,AP7,AP8,AP_AVG,"
    "CP,C9,ISN,F10.7_OBS,F10.7_ADJ,F10.7_DATA_TYPE,F10.7_OBS_CENTER81,F10.7_OBS_LAST81,"
    "F10.7_ADJ_CENTER81,F10.7_ADJ_LAST81\n"
    "2026-10-01,2600,1,10,10,10,10,10,10,10,10,80,4,4,4,4,4,4,4,7,5,0.2,1,120,"
    "172.3,170.1,OBS,165.0,160.0,163.0,158.0\n"
)


class OfflineDataTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        shutil.copytree(offline_data.resource_path("resources"), os.path.join(self.tmp, "resources"))
        with open(os.path.join(self.tmp, "resources", "spaceweather", "SW-All.csv"), "w") as f:
            f.write(SAMPLE_CSV)
        self._orig = offline_data.resource_path
        offline_data.resource_path = lambda *p: os.path.join(self.tmp, *p)
        offline_data._load_space_weather.cache_clear()

    def tearDown(self):
        offline_data.resource_path = self._orig
        offline_data._load_space_weather.cache_clear()
        shutil.rmtree(self.tmp)

    def test_reads_bundled_day(self):
        sw = offline_data.space_weather(datetime.date(2026, 10, 1))
        self.assertEqual(sw["source"], "file")
        self.assertAlmostEqual(sw["f107"], 172.3)
        self.assertAlmostEqual(sw["f107a"], 165.0)
        self.assertAlmostEqual(sw["ap"], 5.0)
        self.assertEqual(len(sw["ap_3h"]), 8)

    def test_falls_back_outside_coverage(self):
        sw = offline_data.space_weather(datetime.date(2040, 1, 1))
        self.assertEqual(sw["source"], "fallback")
        self.assertEqual(sw["f107"], offline_data.FALLBACK_F107)

    def test_status_lists_manifest(self):
        status = {s["file"]: s for s in offline_data.data_status()}
        self.assertTrue(status["spaceweather/SW-All.csv"]["present"])
        self.assertEqual(status["spaceweather/SW-All.csv"]["valid_until"], "2026-10-01")
        self.assertIn("iers/finals2000A.all", status)


class LocalServerTest(unittest.TestCase):
    def test_binds_loopback_and_falls_back_when_port_busy(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "astroflyer_launcher", os.path.join(os.path.dirname(offline_data.__file__), "main.py"))
        launcher = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(launcher)
        _, port_a = launcher.start_server_thread(0)
        _, port_b = launcher.start_server_thread(port_a)  # busy -> free port
        self.assertNotEqual(port_a, port_b)
        for port in (port_a, port_b):
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5) as resp:
                self.assertEqual(resp.status, 200)


class NoConsoleTest(unittest.TestCase):
    """A windowed PyInstaller exe (and pythonw) has sys.stdout/sys.stderr set to None."""

    def test_server_answers_without_std_streams(self):
        import subprocess
        astroflyer_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        script = (
            "import sys, urllib.request\n"
            "sys.stdout = None\n"
            "sys.stderr = None\n"
            "import importlib.util, os\n"
            "spec = importlib.util.spec_from_file_location('launcher', os.path.join(sys.argv[1], 'main.py'))\n"
            "launcher = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(launcher)\n"
            "_, port = launcher.start_server_thread(0)\n"
            "try:\n"
            "    code = urllib.request.urlopen(f'http://127.0.0.1:{port}/', timeout=10).status\n"
            "except Exception as exc:\n"
            "    code = repr(exc)\n"
            "open(sys.argv[2], 'w').write(str(code))\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            result_file = os.path.join(tmp, "result.txt")
            subprocess.run([sys.executable, "-c", script, astroflyer_dir, result_file],
                           cwd=astroflyer_dir, timeout=120, check=True)
            with open(result_file) as f:
                self.assertEqual(f.read(), "200")


class BuildPreflightTest(unittest.TestCase):
    def _build_release(self):
        import importlib.util
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        spec = importlib.util.spec_from_file_location("build_release", os.path.join(root, "build_release.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_python_version_gate(self):
        build_release = self._build_release()
        self.assertFalse(build_release.python_supported((3, 11, 9)))  # typing.override needs 3.12
        self.assertTrue(build_release.python_supported((3, 12, 0)))
        self.assertTrue(build_release.python_supported((3, 14, 4)))  # verified Windows build, 2026-10-24


if __name__ == "__main__":
    unittest.main()
