"""
AstroFlyer HEO - Local HTTP server: the console's files and its JSON endpoints, on 127.0.0.1.
Each endpoint adapts HTTP to a backend module (the propagation run is backend/propagation_run.py).
"""

import os
import sys
import math
import json
import socket
import urllib.parse
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from typing import Any, Optional, cast, override
import numpy as np

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)


def resolve_app_path(*subpaths: str) -> str:
    """Resolves file and directory paths across development, PyInstaller, and installed environments."""
    if hasattr(sys, '_MEIPASS'):
        p = os.path.join(sys._MEIPASS, "astroflyer", *subpaths)
        if os.path.exists(p):
            return p
        p_flat = os.path.join(sys._MEIPASS, *subpaths)
        if os.path.exists(p_flat):
            return p_flat
    exe_dir = os.path.dirname(sys.executable)
    for base in [
        os.path.join(exe_dir, "_internal", "astroflyer"),
        os.path.join(exe_dir, "_internal"),
        os.path.join(exe_dir, "astroflyer"),
        exe_dir,
        parent_dir
    ]:
        p = os.path.join(base, *subpaths)
        if os.path.exists(p):
            return p
    return os.path.join(parent_dir, *subpaths)


from backend.astro_engine import ThirdReviewEngine, keplerian_to_cartesian, MU_EARTH, R_EARTH_EQ
from backend.trajectory_engine import MissionScriptWorkbench
from backend.epoch import Epoch
from backend import access as access_analysis
from backend.script_runner import run_script
from backend.differential_corrector import DifferentialCorrector, FiniteBurnEngine
from backend.propagation_run import run as run_propagation, steering_summary


def app_manifest() -> dict[str, Any]:
    """What the app is and does, stated plainly; numbers are computed, never typed in."""
    a_km, ecc = 24389.0, 0.728525          # default mission: the GTO the script editor starts from
    r_eq_km = R_EARTH_EQ / 1000.0
    return {
        "app_name": "AstroFlyer HEO",
        "propagator": "Cowell (Cartesian state) with SciPy DOP853 by default; also Radau, RKF7(8), "
                      "Bulirsch-Stoer, RK4, and analytic Kepler, J2 mean elements and SGP4",
        "force_model": [
            "EGM2008 gravity up to degree and order 70 (8x8 by default)",
            "Sun and Moon from JPL DE440 (1990-2060)",
            "Solar radiation pressure with a conical shadow on the WGS-84 ellipsoid",
            "NRLMSISE-00 drag driven by the bundled CelesTrak daily F10.7/Ap history (150/15 outside it)",
            "IERS relativity correction",
        ],
        "validation": "Cross-checked against Orekit, NASA GMAT and Basilisk on Molniya, Tundra, GTO and a "
                      "high-eccentricity orbit, two-body through the full model, over 1 and 7 days",
        "default_mission": {
            "mission_name": "Geostationary transfer orbit",
            "orbit_parameters": {
                "semi_major_axis_km": a_km,
                "eccentricity": ecc,
                "inclination_deg": 28.5,
                "raan_deg": 45.0,
                "argument_of_perigee_deg": 30.0,
                "true_anomaly_deg": 0.0,
                "perigee_altitude_km": round(a_km * (1.0 - ecc) - r_eq_km, 3),
                "apogee_altitude_km": round(a_km * (1.0 + ecc) - r_eq_km, 3),
                "period_hours": round(2.0 * math.pi * math.sqrt((a_km * 1e3) ** 3 / MU_EARTH) / 3600.0, 4),
            },
        },
    }


class NumpyJSONEncoder(json.JSONEncoder):
    @override
    def default(self, o: Any) -> Any:
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, (np.floating, float)):
            return float(o)
        if isinstance(o, (np.integer, int)):
            return int(o)
        return super().default(o)


def _get_float_param(params: dict[str, list[str]], key: str, default: float) -> float:
    val_list = params.get(key)
    if val_list and len(val_list) > 0:
        try:
            return float(val_list[0])
        except (ValueError, TypeError):
            return default
    return default


def _get_str_param(params: dict[str, list[str]], key: str, default: str) -> str:
    val_list = params.get(key)
    if val_list and len(val_list) > 0:
        return str(val_list[0])
    return default


def _get_bool_param(params: dict[str, list[str]], key: str, default: bool) -> bool:
    val_list = params.get(key)
    if val_list and len(val_list) > 0:
        val = str(val_list[0]).strip().lower()
        if val in ('true', '1', 'yes', 'on'):
            return True
        elif val in ('false', '0', 'no', 'off'):
            return False
    return default


def _get_vector_param(params: dict[str, list[str]], body: dict[str, Any], key: str) -> Optional[np.ndarray]:
    """A 3-vector from a JSON list or from text such as "x, y, z" or "[x, y, z]"; None when absent."""
    raw: Any = body.get(key) if key in body else (params.get(key, [None])[0])
    if raw is None or raw == '':
        return None
    if isinstance(raw, str):
        raw = [p for p in raw.strip().strip('[]').replace(',', ' ').split() if p]
    try:
        vec = np.array([float(x) for x in raw], dtype=float)
    except (TypeError, ValueError):
        raise ValueError(f"{key} must be three numbers") from None
    if vec.shape != (3,) or not np.all(np.isfinite(vec)):
        raise ValueError(f"{key} must be three numbers, got {len(vec)}")
    return vec


def _get_int_param(params: dict[str, list[str]], key: str, default: int) -> int:
    val_list = params.get(key)
    if val_list and len(val_list) > 0:
        try:
            return int(float(val_list[0]))
        except (ValueError, TypeError):
            return default
    return default


class ThirdReviewAppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        frontend_dir = resolve_app_path("frontend")
        super().__init__(*args, directory=frontend_dir, **kwargs)

    @override
    def do_GET(self) -> None:
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        if path.startswith("/api/"):
            raw_query: dict[str, list[str]] = urllib.parse.parse_qs(parsed_path.query)
            self.handle_api(path, raw_query)
        else:
            super().do_GET()

    @override
    def do_POST(self) -> None:
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        if path.startswith("/api/"):
            # Only the console's own JSON requests: a page on another site can send a text/plain
            # POST here without the browser's cross-origin check, but not an application/json one
            if self.headers.get_content_type() != "application/json":
                self.send_json({"error": "POST bodies must be application/json"}, 415)
                return
            content_length = int(self.headers.get('Content-Length', '0'))
            post_data = self.rfile.read(content_length) if content_length > 0 else b'{}'
            params: dict[str, list[str]] = {}
            self.json_body: dict[str, Any] = {}     # the parsed body, for routes that take lists or objects
            try:
                body = cast(dict[str, Any], json.loads(post_data.decode('utf-8')))
                params = {str(k): [str(v)] for k, v in body.items()}
                self.json_body = body
            except Exception:
                params = {}
            self.handle_api(path, params)
        else:
            self.send_error(404, "Endpoint not found")

    def send_json(self, data: Any, status_code: int = 200) -> None:
        resp_bytes = json.dumps(data, indent=2, cls=NumpyJSONEncoder).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(resp_bytes)))
        self.end_headers()
        _ = self.wfile.write(resp_bytes)

    def handle_api(self, path: str, params: dict[str, list[str]]) -> None:
        if path == "/api/manifest":
            self.send_json(app_manifest())

        elif path in ("/api/script/generate", "/api/mission/script"):
            sma = _get_float_param(params, 'sma', 24389.0)
            ecc = _get_float_param(params, 'ecc', 0.728525)
            inc = _get_float_param(params, 'inc', 28.5)
            raan = _get_float_param(params, 'raan', 45.0)
            aop = _get_float_param(params, 'aop', 30.0)
            ta = _get_float_param(params, 'ta', 0.0)
            num_orbits = int(_get_float_param(params, 'num_orbits', 3.0))

            script_text: str = str(MissionScriptWorkbench.generate_mission_script(
                sma_km=sma, ecc=ecc, inc_deg=inc, raan_deg=raan, aop_deg=aop, ta_deg=ta, num_orbits=num_orbits
            ))
            self.send_json({
                "status": "SUCCESS",
                "tool": "AstroFlyer Mission Script Generator",
                "script_content": script_text,
                "script_filename": "AstroFlyer_HEO_Mission.script"
            })

        elif path == "/api/targeting/differential_corrector":
            r0 = _get_float_param(params, 'r0', 6628.0)
            v0 = _get_float_param(params, 'v0', 10.23)
            target_ra = _get_float_param(params, 'target_ra', 42164.0)
            dc = DifferentialCorrector()
            res_dc = dc.solve_apogee_raise(r0_km=r0, v0_kms=v0, target_ra_km=target_ra)
            self.send_json(res_dc)

        elif path == "/api/script/run":
            # Runs a full mission script (Create ... BeginMissionSequence ...) on the AstroFlyer engine
            self.send_json(run_script(_get_str_param(params, 'script_text', '')))

        elif path == "/api/analysis/access":
            # Ground-station passes, eclipses, beta angle and a report for one propagated orbit
            self.send_json(_analysis_access(getattr(self, 'json_body', {}) or {}))

        elif path == "/api/targeting/finite_burn":
            dv_req = _get_float_param(params, 'deltav', 1478.0)
            m0 = _get_float_param(params, 'mass', 1500.0)
            thrust = _get_float_param(params, 'thrust', 450.0)
            isp = _get_float_param(params, 'isp', 315.0)
            fb = FiniteBurnEngine(thrust_newtons=thrust, isp_sec=isp)
            res_fb = fb.execute_finite_burn(target_deltav_ms=dv_req, initial_mass_kg=m0)
            self.send_json(res_fb)

        elif path in ("/api/covariance/steered", "/api/covariance/step_factor"):
            # One covariance-steered orbit of the given elements (see /api/propagate steering=covariance)
            sma = _get_float_param(params, 'sma', 26560.0)
            ecc = _get_float_param(params, 'ecc', 0.72)
            inc = _get_float_param(params, 'inc', 63.4)
            eta = _get_float_param(params, 'eta', 0.02)
            # A closed orbit clear of the Earth, at most ~1e6 km, so the run has a finite period
            if not (0.0 <= ecc < 1.0 and sma * (1.0 - ecc) > R_EARTH_EQ / 1000.0 and sma <= 1.0e6
                    and 1e-4 <= eta <= 1.0):
                self.send_json({"error": "Need 0 <= ecc < 1, perigee above the Earth's surface, "
                                         "sma <= 1e6 km and 1e-4 <= eta <= 1"}, 400)
                return
            r0, v0 = keplerian_to_cartesian(sma * 1000.0, ecc, float(np.radians(inc)), 0.0, float(np.radians(270.0)), 0.0)
            period_s = float(2.0 * np.pi * np.sqrt((sma * 1000.0) ** 3 / MU_EARTH))
            steered = ThirdReviewEngine(np.concatenate([r0, v0])).propagate(
                (0.0, period_s), num_points=50, model='j2', method='RKF78', rtol=1e-10, atol=1e-10,
                steering='covariance', steering_eta=eta)
            self.send_json(steering_summary(steered['steps']))
        elif path in ("/api/propagate", "/api/script/propagate"):
            request = _propagation_request(params, getattr(self, 'json_body', None))
            if path == "/api/script/propagate":
                # The orbit comes from the script; everything else from the request
                parsed = MissionScriptWorkbench.parse_mission_script(str(request.pop('script_text', '')))
                request.update({_REQUEST_ALIASES.get(k, k): v for k, v in parsed.items()})
            try:
                self.send_json(run_propagation(request))
            except ValueError as exc:
                self.send_json({"error": str(exc)}, 400)
        else:
            self.send_json({"status": "404", "message": f"Endpoint {path} not found"}, status_code=404)


class LocalAppServer(ThreadingHTTPServer):
    """Refuses a port another process already holds, so the launcher can fall back to a free one.
    On Windows SO_REUSEADDR lets a second bind succeed on a busy port, so it is off there and
    SO_EXCLUSIVEADDRUSE is set instead."""
    allow_reuse_address = sys.platform != "win32"
    daemon_threads = True

    def server_bind(self) -> None:
        if sys.platform == "win32" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


# Other names the propagate request accepts for the console's fields (the mission-script
# parser and older clients use them); the console's own name wins when both are given
_REQUEST_ALIASES = {
    "hp_km": "hp", "ha_km": "ha", "sma": "a", "sma_km": "a", "ecc": "e", "eccentricity": "e",
    "inc_deg": "inc", "inclination_deg": "inc", "raan_deg": "raan", "aop_deg": "aop",
    "arg_perigee_deg": "aop", "ta_deg": "ta", "true_anomaly_deg": "ta", "gravity_model": "model",
    "integrator": "method", "tol": "tolerance", "points": "num_points", "spacecraft_mass": "mass",
}


def _propagation_request(params: dict[str, list[str]], body: Optional[dict[str, Any]]) -> dict[str, Any]:
    """The propagation_run request from a JSON body (POST) or query parameters (GET)."""
    raw: dict[str, Any] = dict(body) if body else {k: v[0] for k, v in params.items() if v}
    request = {k: v for k, v in raw.items() if k not in _REQUEST_ALIASES}
    for alias, name in _REQUEST_ALIASES.items():
        if alias in raw:
            request.setdefault(name, raw[alias])
    return request


def _analysis_access(body: dict[str, Any]) -> dict[str, Any]:
    """Runs /api/analysis/access: Keplerian elements in, passes/eclipses/beta/report out."""
    try:
        epoch = Epoch.coerce(body.get('epoch') or None)
        r0, v0 = keplerian_to_cartesian(float(body.get('sma_km', 24389.0)) * 1000.0, float(body.get('ecc', 0.0)),
                                        *(float(np.radians(float(body.get(k, 0.0))))
                                          for k in ('inc_deg', 'raan_deg', 'aop_deg', 'ta_deg')))
        duration = float(body.get('duration_s', 86400.0))
        step = max(1.0, float(body.get('step_s', 60.0)))
        sol = ThirdReviewEngine(np.concatenate([r0, v0]), epoch=epoch).propagate(
            (0.0, duration), num_points=int(round(duration / step)) + 1, model=str(body.get('model', 'two_body')),
            method=str(body.get('method', 'RKF78')))
        stations = [access_analysis.GroundStation.from_dict(d) for d in body.get('stations', [])]
        out = access_analysis.analyze(epoch, np.asarray(sol['times']), np.asarray(sol['position_m']),
                                      np.asarray(sol['velocity_ms']), stations,
                                      body.get('parameters') or ['Epoch'])
        out['error'] = None
        return out
    except (KeyError, TypeError, ValueError) as exc:
        return {'error': str(exc), 'passes': {}, 'eclipses': [], 'beta_angle_deg': [], 'report': {}}


def create_server(port: int = 8003, host: str = "127.0.0.1") -> ThreadingHTTPServer:
    """Binds the API/frontend server. Port 0 lets the OS pick a free port (read it from server_address)."""
    return LocalAppServer((host, port), ThirdReviewAppHandler)


def run_server(port: int = 8003, host: str = "127.0.0.1", httpd: Optional[ThreadingHTTPServer] = None) -> None:
    if httpd is None:
        httpd = create_server(port, host)
    port = httpd.server_address[1]
    print(f"==========================================================================")
    print(f" ASTROFLYER HEO - LOCAL ENGINE SERVER")
    print(f" High-Precision Trajectory Propagation & Mission Events Prediction")
    print(f" Serving AstroFlyer HEO Flight Operations Studio at: http://127.0.0.1:{port}")
    print(f"==========================================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()


if __name__ == '__main__':
    run_server(port=8003)
