"""Checks for the offline packaging helpers: space-weather loading, manifest status, local-only server."""

import datetime
import os
import shlex
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

    def test_monthly_prediction_covers_its_month(self):
        # After the daily forecast CelesTrak predicts one row per month (dated the 1st, no Ap)
        with open(os.path.join(self.tmp, "resources", "spaceweather", "SW-All.csv"), "a") as f:
            f.write("2027-01-01,2637,14,,,,,,,,,,,,,,,,,,,,,73,118.6,114.7,PRM,115.3,108.3,111.8,105.9\n")
        offline_data._load_space_weather.cache_clear()
        sw = offline_data.space_weather(datetime.date(2027, 1, 17))
        self.assertEqual((sw["source"], sw["kind"]), ("file", "PRM"))
        self.assertAlmostEqual(sw["f107"], 118.6)
        self.assertAlmostEqual(sw["f107a"], 115.3)
        self.assertEqual(offline_data.space_weather(datetime.date(2027, 2, 5))["source"], "fallback")

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

    def test_version_has_one_source(self):
        # astroflyer/__init__.py holds the version; the build passes it to the installer, whose
        # recipe states none of its own (five hand-kept copies had drifted to 3.0.0 vs 1.0.0)
        build_release = self._build_release()
        import astroflyer
        self.assertEqual(build_release.app_version(), astroflyer.__version__)
        self.assertRegex(astroflyer.__version__, r"^\d+\.\d+\.\d+$")
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        with open(os.path.join(root, "installer", "AstroFlyer_Installer.iss"), encoding="utf-8") as f:
            recipe = f.read()
        self.assertNotIn("#define MyAppVersion", recipe)
        for key in ("AppVersion=", "OutputBaseFilename=", "VersionInfoVersion="):
            line = next(l for l in recipe.splitlines() if l.startswith(key))
            self.assertIn("{#MyAppVersion}", line)
        self.assertIn("/DMyAppVersion=2.5.1", build_release.iscc_command("x.iss", "2.5.1"))
        self.assertEqual(build_release.installer_name("2.5.1"), "AstroFlyer_HEO_v2.5.1_Setup.exe")

    def test_publishing_needs_a_pushed_clean_main_and_a_new_tag(self):
        build_release = self._build_release()

        def git(dirty="", head="abc", remote="abc", tags=""):
            answers = {("status", "--porcelain"): dirty, ("rev-parse", "HEAD"): head,
                       ("rev-parse", "origin/main"): remote, ("ls-remote", "--tags", "origin"): tags}
            return lambda *args: answers[args]

        self.assertEqual(build_release.release_blockers("1.0.1", git()), [])
        self.assertIn("uncommitted", " ".join(build_release.release_blockers("1.0.1", git(dirty=" M x.py"))))
        self.assertIn("origin/main", " ".join(build_release.release_blockers("1.0.1", git(head="def"))))
        tags = "abc\trefs/tags/v1.0.1\n"
        self.assertIn("v1.0.1", " ".join(build_release.release_blockers("1.0.1", git(tags=tags))))
        self.assertEqual(build_release.release_blockers("1.0.2", git(tags=tags)), [])


def _load_launcher():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "astroflyer_launcher_warmup", os.path.join(os.path.dirname(offline_data.__file__), "main.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ModelWarmUpTest(unittest.TestCase):
    """The Numba-compiled drag model costs ~9 s on first use; the launcher compiles it in the background."""

    def test_warm_up_runs_in_background_and_completes(self):
        import time
        launcher = _load_launcher()
        started = time.perf_counter()
        thread = launcher.warm_up_models()
        self.assertLess(time.perf_counter() - started, 1.0)  # never blocks the window
        self.assertTrue(thread.daemon)
        thread.join(timeout=300)
        self.assertFalse(thread.is_alive())
        self.assertTrue(thread.ok, getattr(thread, "error", None))


class RuntimeDependenciesTest(unittest.TestCase):
    """pymsis is only a test reference now (drag uses backend/nrlmsise00.py), so the app doesn't ship it."""
    ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def _requirements(self, name):
        with open(os.path.join(self.ROOT, name)) as f:
            return [line.split("#")[0].strip() for line in f if line.split("#")[0].strip()]

    def test_pymsis_is_dev_only(self):
        self.assertFalse(any(r.startswith("pymsis") for r in self._requirements("requirements.txt")))
        self.assertTrue(any(r.startswith("pymsis") for r in self._requirements("requirements-dev.txt")))

    def test_spec_does_not_bundle_pymsis(self):
        with open(os.path.join(self.ROOT, "AstroFlyer.spec")) as f:
            self.assertNotIn("collect_all('pymsis')", f.read())


class QuietWebViewTest(unittest.TestCase):
    """WebView2 phones Microsoft (SmartScreen, component updates, telemetry) unless told not to."""

    def test_launcher_turns_off_webview2_background_networking(self):
        launcher = _load_launcher()
        saved = os.environ.pop("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", None)
        try:
            launcher.configure_offline_webview()
            args = shlex.split(os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"])
        finally:
            os.environ.pop("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", None)
            if saved is not None:
                os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = saved
        for flag in ("--disable-background-networking", "--disable-component-update",
                     "--disable-domain-reliability", "--no-pings"):
            self.assertIn(flag, args)
        # Chromium honours only one --disable-features list, so it must keep pywebview's own entry
        features = [a for a in args if a.startswith("--disable-features=")]
        self.assertEqual(len(features), 1)
        disabled = features[0].split("=", 1)[1].split(",")
        for feature in ("ElasticOverscroll", "msSmartScreenProtection"):
            self.assertIn(feature, disabled)

    def test_window_resolves_no_host_but_localhost(self):
        # Edge services the flags above don't cover (seen: the Office 365 range ~30 s after start) need a
        # host name; the UI is served from 127.0.0.1 and needs none, so name lookups are refused.
        launcher = _load_launcher()
        saved = os.environ.pop("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", None)
        try:
            launcher.configure_offline_webview()
            args = shlex.split(os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"])
        finally:
            os.environ.pop("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", None)
            if saved is not None:
                os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = saved
        # The UI's own address must stay reachable: MAP * also matches the IP literal 127.0.0.1
        self.assertIn("--host-resolver-rules=MAP * ~NOTFOUND , EXCLUDE localhost , EXCLUDE 127.0.0.1", args)


class ManifestTest(unittest.TestCase):
    """/api/manifest states only what the app does; nothing invented, nothing from the old demo."""

    def _manifest(self):
        import json
        launcher = _load_launcher()
        _, port = launcher.start_server_thread(0)
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/manifest", timeout=10) as resp:
            return json.load(resp)

    def test_no_invented_or_stale_claims(self):
        import json
        text = json.dumps(self._manifest())
        for claim in ("26.35", "Sub-Meter", "Radau-IIA Core", "Review", "25-Year", "FSW", "Battery",
                      "#00e5ff", "Certification"):
            self.assertNotIn(claim, text)

    def test_altitudes_follow_from_the_orbit_on_wgs84(self):
        from backend import forces
        orbit = self._manifest()["default_mission"]["orbit_parameters"]
        a, e = orbit["semi_major_axis_km"], orbit["eccentricity"]
        r_eq = forces.R_EARTH_EQ / 1000.0
        self.assertAlmostEqual(orbit["perigee_altitude_km"], a * (1 - e) - r_eq, places=1)
        self.assertAlmostEqual(orbit["apogee_altitude_km"], a * (1 + e) - r_eq, places=1)


class NoDocumentationTest(unittest.TestCase):
    """The app ships no documentation (handbooks, READMEs, notes); only the licence texts the bundled
    font, icons and uPlot require to travel with them."""
    ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    SHIPPED = (("astroflyer", "frontend"), ("astroflyer", "resources"))
    DOC_EXTENSIONS = (".md", ".pdf", ".txt", ".rst", ".doc", ".docx")

    def _read(self, *parts):
        with open(os.path.join(self.ROOT, *parts), encoding="utf-8") as f:
            return f.read()

    def test_shipped_folders_hold_no_documents(self):
        for parts in self.SHIPPED:
            for folder, _, files in os.walk(os.path.join(self.ROOT, *parts)):
                docs = [f for f in files if f.lower().endswith(self.DOC_EXTENSIONS)
                        and not f.upper().startswith(("LICENSE", "OFL"))]
                self.assertEqual(docs, [], folder)

    def test_ui_links_no_document(self):
        self.assertNotIn(".pdf", self._read("astroflyer", "frontend", "index.html"))

    def test_spec_bundles_only_runtime_folders(self):
        spec = self._read("AstroFlyer.spec")
        self.assertNotIn("'datasources'", spec)

    def test_installer_and_build_add_no_document(self):
        self.assertNotIn(".pdf", self._read("installer", "AstroFlyer_Installer.iss"))
        self.assertNotIn("--pdf", self._read("build_release.py"))

if __name__ == "__main__":
    unittest.main()
