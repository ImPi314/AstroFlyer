"""
AstroFlyer HEO - Third Review Production Server & Flight Dynamics REST API
Precise Trajectory Propagation and Events Prediction for Highly Eccentric Orbits (HEOs)
High-Order Coupled Physics Kernel, Flight Software Subsystems,
and Commercial V&V Cross-Validation Benchmarks.
"""

import os
import sys
import math
import time
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


from backend.astro_engine import ThirdReviewEngine, keplerian_to_cartesian, MU_EARTH, R_EARTH, R_EARTH_EQ
from backend.event_predictor import EventPredictor
from backend.trajectory_engine import MissionScriptWorkbench
from backend.epoch import Epoch
from backend import access as access_analysis
from backend import mission as mission_targeting
from backend.script_runner import run_script
from backend.radiation_belts import RadiationBeltModel
from backend.covariance_engine import CovarianceEngine
from backend.differential_corrector import DifferentialCorrector, FiniteBurnEngine
from backend.ccsds_exporter import CCSDSExporter


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
            "NRLMSISE-00 drag with bundled space weather",
            "IERS relativity correction",
        ],
        "validation": "Cross-checked against Orekit on Molniya, Tundra, GTO and a high-eccentricity "
                      "orbit, two-body through the full model, over 1 and 7 days",
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
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        _ = self.wfile.write(resp_bytes)

    def handle_api(self, path: str, params: dict[str, list[str]]) -> None:
        predictor = EventPredictor()

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

        elif path == "/api/mission/target":
            # General vary/achieve targeter (backend/mission.py) on a propagated trajectory
            scenario = _get_str_param(params, 'scenario', 'gto_to_geo')
            try:
                epoch = Epoch.coerce(_get_str_param(params, 'epoch', '') or None)
                if scenario == 'gto_to_geo':
                    res_t = mission_targeting.target_gto_to_geo(
                        epoch,
                        perigee_alt_km=_get_float_param(params, 'hp_km', 250.0),
                        apogee_alt_km=_get_float_param(params, 'ha_km', 35786.0),
                        inc_deg=_get_float_param(params, 'inc_deg', 28.5),
                        raan_deg=_get_float_param(params, 'raan_deg', 0.0),
                        dry_mass_kg=_get_float_param(params, 'dry_mass_kg', 1500.0),
                        fuel_mass_kg=_get_float_param(params, 'fuel_mass_kg', 2000.0),
                        isp_s=_get_float_param(params, 'isp_s', 320.0),
                        model=_get_str_param(params, 'model', 'j2'))
                elif scenario == 'perigee_raise':
                    res_t = mission_targeting.target_perigee_raise(
                        epoch,
                        sma_km=_get_float_param(params, 'sma_km', 26560.0),
                        perigee_alt_km=_get_float_param(params, 'hp_km', 450.0),
                        inc_deg=_get_float_param(params, 'inc_deg', 63.4),
                        raan_deg=_get_float_param(params, 'raan_deg', 30.0),
                        argp_deg=_get_float_param(params, 'aop_deg', 270.0),
                        target_perigee_alt_km=_get_float_param(params, 'target_hp_km', 600.0),
                        dry_mass_kg=_get_float_param(params, 'dry_mass_kg', 1000.0),
                        fuel_mass_kg=_get_float_param(params, 'fuel_mass_kg', 200.0),
                        isp_s=_get_float_param(params, 'isp_s', 300.0),
                        model=_get_str_param(params, 'model', 'j2_j3_j4'))
                else:
                    self.send_json({"error": f"Unknown scenario {scenario!r}; use gto_to_geo or perigee_raise"}, 400)
                    return
            except (ValueError, RuntimeError) as exc:
                self.send_json({"error": str(exc)}, 400)
                return
            self.send_json(res_t)

        elif path == "/api/targeting/finite_burn":
            dv_req = _get_float_param(params, 'deltav', 1478.0)
            m0 = _get_float_param(params, 'mass', 1500.0)
            thrust = _get_float_param(params, 'thrust', 450.0)
            isp = _get_float_param(params, 'isp', 315.0)
            fb = FiniteBurnEngine(thrust_newtons=thrust, isp_sec=isp)
            res_fb = fb.execute_finite_burn(target_deltav_ms=dv_req, initial_mass_kg=m0)
            self.send_json(res_fb)

        elif path in ("/api/ccsds/tle", "/api/ccsds/generate_tle"):
            sma = _get_float_param(params, 'sma', 24389.0)
            ecc = _get_float_param(params, 'ecc', 0.728525)
            inc = _get_float_param(params, 'inc', 28.5)
            raan = _get_float_param(params, 'raan', 45.0)
            aop = _get_float_param(params, 'aop', 30.0)
            ta = _get_float_param(params, 'ta', 0.0)
            tle_str = CCSDSExporter.generate_tle(sma_km=sma, ecc=ecc, inc_deg=inc, raan_deg=raan, aop_deg=aop, ta_deg=ta)
            self.send_json({
                "status": "SUCCESS",
                "standard": "NORAD Two-Line Element (TLE) Format",
                "tle_content": tle_str,
                "filename": "AstroFlyer_HEO.tle"
            })

        elif path in ("/api/ccsds/opm", "/api/ccsds/generate_opm"):
            sma = _get_float_param(params, 'sma', 24389.0)
            ecc = _get_float_param(params, 'ecc', 0.728525)
            inc = _get_float_param(params, 'inc', 28.5)
            raan = _get_float_param(params, 'raan', 45.0)
            aop = _get_float_param(params, 'aop', 30.0)
            ta = _get_float_param(params, 'ta', 0.0)
            opm_str = CCSDSExporter.generate_ccsds_opm(sma_km=sma, ecc=ecc, inc_deg=inc, raan_deg=raan, aop_deg=aop, ta_deg=ta)
            self.send_json({
                "status": "SUCCESS",
                "standard": "CCSDS 502.0-B-2 Orbit Parameter Message (OPM)",
                "opm_content": opm_str,
                "filename": "AstroFlyer_HEO.opm"
            })

        elif path in ("/api/ccsds/oem", "/api/ccsds/generate_oem"):
            sma = _get_float_param(params, 'sma', 24389.0)
            ecc = _get_float_param(params, 'ecc', 0.728525)
            inc = _get_float_param(params, 'inc', 28.5)
            r0, v0 = keplerian_to_cartesian(sma * 1000.0, ecc, float(np.radians(inc)), float(np.radians(45.0)), float(np.radians(30.0)), 0.0)
            eng = ThirdReviewEngine(np.concatenate([r0, v0]))
            sol_quick = cast(dict[str, Any], eng.propagate((0.0, 37905.5), num_points=200))
            oem_str = CCSDSExporter.generate_ccsds_oem(
                sol_quick['times'], sol_quick['position_m'], sol_quick['velocity_ms'], step_interval_s=120.0
            )
            self.send_json({
                "status": "SUCCESS",
                "standard": "CCSDS 502.0-B-2 Orbit Ephemeris Message (OEM)",
                "oem_content": oem_str,
                "filename": "AstroFlyer_HEO.oem"
            })

        elif path == "/api/covariance/propagate":
            sigma_pos = _get_float_param(params, 'sigma_pos', 10.0)
            sigma_vel = _get_float_param(params, 'sigma_vel', 0.01)
            sma = _get_float_param(params, 'sma', 24389.0)
            ecc = _get_float_param(params, 'ecc', 0.728525)
            inc = _get_float_param(params, 'inc', 28.5)
            r0, v0 = keplerian_to_cartesian(sma * 1000.0, ecc, float(np.radians(inc)), float(np.radians(45.0)), float(np.radians(30.0)), 0.0)
            eng = ThirdReviewEngine(np.concatenate([r0, v0]))
            sol_quick = cast(dict[str, Any], eng.propagate((0.0, 37905.5), num_points=300))
            cov_eng = CovarianceEngine(default_sigma_pos_m=sigma_pos, default_sigma_vel_ms=sigma_vel)
            cov_data = cov_eng.propagate_stm_and_covariance(sol_quick['times'], sol_quick['position_m'], sol_quick['velocity_ms'])
            self.send_json(cov_data)

        # =====================================================================
        # INNOVATION 1-5 ADVANCED ASTRODYNAMICS REST ENDPOINTS
        # =====================================================================
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
            self.send_json(_steering_summary(steered['steps']))


        # =====================================================================
        # EVENT ENDPOINTS
        # =====================================================================
        elif path == "/api/events/eclipses":
            a_km = _get_float_param(params, 'a', 24389.0)
            e = _get_float_param(params, 'e', 0.728525)
            inc_deg = _get_float_param(params, 'inc', 28.5)
            r0, v0 = keplerian_to_cartesian(a_km * 1000.0, e, float(np.radians(inc_deg)), float(np.radians(45.0)), float(np.radians(30.0)), 0.0)
            engine = ThirdReviewEngine(np.concatenate([r0, v0]))
            sol_prop = cast(dict[str, Any], engine.propagate((0.0, 37905.5), num_points=1000))
            eclipses: dict[str, Any] = cast(dict[str, Any], predictor.predict_solar_eclipses(
                cast(np.ndarray, sol_prop['times']), cast(np.ndarray, sol_prop['position_m']),
                sol_prop.get('sun_direction_eci')
            ))
            self.send_json(eclipses)

        elif path == "/api/events/ground_stations":
            a_km = _get_float_param(params, 'a', 24389.0)
            e = _get_float_param(params, 'e', 0.728525)
            inc_deg = _get_float_param(params, 'inc', 28.5)
            r0, v0 = keplerian_to_cartesian(a_km * 1000.0, e, float(np.radians(inc_deg)), float(np.radians(45.0)), float(np.radians(30.0)), 0.0)
            engine = ThirdReviewEngine(np.concatenate([r0, v0]))
            sol_prop = cast(dict[str, Any], engine.propagate((0.0, 2 * 37905.5), num_points=1000))
            gs_passes: dict[str, Any] = cast(dict[str, Any], predictor.predict_ground_station_passes(
                cast(np.ndarray, sol_prop['times']), cast(np.ndarray, sol_prop['position_m'])
            ))
            summary: dict[str, Any] = {
                name: {
                    "metadata": d["station_metadata"],
                    "passes": d["passes"],
                    "total_passes_count": d["total_passes_count"],
                    "total_contact_min": d["total_contact_min"]
                }
                for name, d in gs_passes.items()
            }
            self.send_json(summary)

        elif path in ("/api/telemetry", "/api/propagate", "/api/script/propagate"):
            if path == "/api/script/propagate":
                script_text = _get_str_param(params, 'script_text', '')
                parsed = MissionScriptWorkbench.parse_mission_script(script_text)
                for k, v in parsed.items():
                    params[k] = [str(v)]

            # 1. Classical Orbital Elements & Geometry
            hp_km = _get_float_param(params, 'hp', _get_float_param(params, 'hp_km', -1.0))
            ha_km = _get_float_param(params, 'ha', _get_float_param(params, 'ha_km', -1.0))
            r_earth_km = R_EARTH / 1000.0

            if hp_km > 0 and ha_km > hp_km:
                rp = r_earth_km + hp_km
                ra = r_earth_km + ha_km
                a_km = (rp + ra) / 2.0
                e = (ra - rp) / (ra + rp)
            else:
                a_km = _get_float_param(params, 'a', _get_float_param(params, 'sma', _get_float_param(params, 'sma_km', 24389.0)))
                e = _get_float_param(params, 'e', _get_float_param(params, 'ecc', _get_float_param(params, 'eccentricity', 0.728525)))

            # Clamp e to valid elliptic range [0.0, 0.99]
            e = max(0.000001, min(0.99, e))
            a_km = max(r_earth_km + 100.0, a_km)

            inc_deg = _get_float_param(params, 'inc', _get_float_param(params, 'inc_deg', _get_float_param(params, 'inclination_deg', 28.5)))
            raan_deg = _get_float_param(params, 'raan', _get_float_param(params, 'raan_deg', 45.0))
            aop_deg = _get_float_param(params, 'aop', _get_float_param(params, 'aop_deg', _get_float_param(params, 'arg_perigee_deg', 30.0)))
            ta_deg = _get_float_param(params, 'ta', _get_float_param(params, 'ta_deg', _get_float_param(params, 'true_anomaly_deg', 0.0)))

            num_orbits = max(0.5, min(20.0, _get_float_param(params, 'num_orbits', 3.0)))
            model_type: str = _get_str_param(params, 'model', _get_str_param(params, 'gravity_model', 'coupled'))
            method_type: str = _get_str_param(params, 'method', _get_str_param(params, 'integrator', 'DOP853'))
            # Initial-state epoch (ISO 8601, UTC unless tagged TAI/TT/TDB/UT1/GPS); default J2000.0
            epoch_text: str = _get_str_param(params, 'epoch', '')
            try:
                initial_epoch = Epoch.coerce(epoch_text or None)
            except ValueError as exc:
                self.send_json({"error": str(exc)}, 400)
                return
            # Run length: duration_s (seconds, up to 30 days) wins over num_orbits when given
            duration_s: Optional[float] = None
            if _get_str_param(params, 'duration_s', ''):
                duration_s = _get_float_param(params, 'duration_s', 0.0)
                if not (0.0 < duration_s <= 30 * 86400.0):
                    self.send_json({"error": "duration_s must be between 0 and 2592000 s (30 days)"}, 400)
                    return
            try:
                r_cart = _get_vector_param(params, getattr(self, 'json_body', {}) or {}, 'position_km')
                v_cart = _get_vector_param(params, getattr(self, 'json_body', {}) or {}, 'velocity_kms')
            except ValueError as exc:
                self.send_json({"error": str(exc)}, 400)
                return
            if (r_cart is None) != (v_cart is None):
                self.send_json({"error": "Give both position_km and velocity_kms for a Cartesian initial state"}, 400)
                return
            pts_val = _get_int_param(params, 'num_points', _get_int_param(params, 'points', 0))
            if pts_val <= 0:
                pts_per_orb = _get_int_param(params, 'points_per_orbit', 400)
                if duration_s is None:
                    pts_val = int(pts_per_orb * num_orbits)
                elif r_cart is not None:
                    pts_val = int(duration_s / 60.0)      # one point a minute; the state may not be a closed orbit
                else:
                    pts_val = int(pts_per_orb * duration_s / (2.0 * np.pi * np.sqrt((a_km * 1000.0) ** 3 / MU_EARTH)))
            num_points: int = max(200, min(3600, pts_val))
            tol: float = _get_float_param(params, 'tolerance', _get_float_param(params, 'tol', 1e-10))

            # 2. Environmental Force Model Perturbations
            enable_drag = _get_bool_param(params, 'enable_drag', True)
            enable_third_body = _get_bool_param(params, 'enable_third_body', True)
            enable_srp = _get_bool_param(params, 'enable_srp', True)

            # 3. Spacecraft Physical Parameters
            spacecraft_mass = _get_float_param(params, 'mass', _get_float_param(params, 'spacecraft_mass', 1500.0))
            dry_mass = _get_float_param(params, 'dry_mass', 1000.0)
            fuel_mass = _get_float_param(params, 'fuel_mass', 500.0)
            cd = _get_float_param(params, 'cd', 2.2)
            drag_area = _get_float_param(params, 'drag_area', 15.0)
            cr = _get_float_param(params, 'cr', 1.2)
            srp_area = _get_float_param(params, 'srp_area', 15.0)

            # Atmospheric B* parameter and SRP area-to-mass
            b_star = (cd * drag_area) / max(10.0, spacecraft_mass)  # Cd*A/m; the EOM applies the 1/2
            cr_area_over_m = (cr * srp_area) / max(10.0, spacecraft_mass)

            # Initial state: a Cartesian GCRF state (position_km, velocity_kms) when given, else Keplerian
            initial_state_kind = 'keplerian'
            if r_cart is not None:
                initial_state_kind = 'cartesian'
                r0, v0 = r_cart * 1000.0, v_cart * 1000.0
                kep0 = mission_targeting.keplerian_from_state(r0, v0, MU_EARTH)
                a_m = float(kep0['a'])        # plain floats: downstream reports go straight to JSON
                a_km, e = a_m / 1000.0, float(kep0['e'])
                inc_deg, raan_deg, aop_deg, ta_deg = (float(np.degrees(kep0[k])) for k in ('inc', 'raan', 'argp', 'ta'))
            else:
                a_m = a_km * 1000.0
                r0, v0 = keplerian_to_cartesian(
                    a_m, e,
                    float(np.radians(inc_deg)),
                    float(np.radians(raan_deg)),
                    float(np.radians(aop_deg)),
                    float(np.radians(ta_deg))
                )
            y0 = np.concatenate([r0, v0])

            closed_orbit = bool(a_m > 0 and e < 1.0)
            if not closed_orbit and duration_s is None:
                self.send_json({"error": "The initial state is an escape trajectory (e >= 1), which has no "
                                         "period, so give the run length as duration_s"}, 400)
                return
            period: float = float(2.0 * np.pi * np.sqrt(a_m**3 / MU_EARTH)) if closed_orbit else float('inf')
            run_duration_s: float = duration_s if duration_s is not None else num_orbits * period
            t_span = (0.0, run_duration_s)

            # 4. Integrate Coupled Equations of Motion in Real-Time
            t_solve_start = time.time()
            engine = ThirdReviewEngine(y0, epoch=initial_epoch)
            # Innovations that change the run itself: covariance-steered steps (RKF78/BS) and ECR-MF tiers
            steering: Optional[str] = _get_str_param(params, 'steering', '') or None
            fidelity: str = _get_str_param(params, 'fidelity', 'full')
            if fidelity not in ('full', 'ecr_mf'):
                self.send_json({"error": "fidelity must be 'full' or 'ecr_mf'"}, 400)
                return
            try:
                sol: dict[str, Any] = cast(dict[str, Any], engine.propagate(
                    t_span,
                    num_points=num_points,
                    sampling='anomaly',     # points follow the orbit, so perigees aren't jagged
                    model=model_type,
                    enable_drag=enable_drag,
                    enable_third_body=enable_third_body,
                    enable_srp=enable_srp,
                    method=method_type,
                    rtol=tol,
                    atol=tol,
                    b_star=b_star,
                    cr_area_over_m=cr_area_over_m,
                    fixed_step=_get_float_param(params, 'step_s', 0.0) or None,
                    steering=steering,
                    fidelity=fidelity,
                ))
            except ValueError as exc:
                self.send_json({"error": str(exc)}, 400)
                return
            t_solve_sec = time.time() - t_solve_start

            # Predict mission events across the custom arc
            times_arr = cast(np.ndarray, sol['times'])
            pos_arr = cast(np.ndarray, sol['position_m'])
            vel_arr = cast(np.ndarray, sol['velocity_ms'])

            if not closed_orbit:
                # Escape trajectory: the trajectory and its own fields only. The lifetime, apsis,
                # targeting, script and mission-plan reports below all assume a closed orbit.
                self.send_json(_escape_payload(sol, run_duration_s, initial_state_kind, model_type, method_type,
                                               num_points, t_solve_sec,
                                               _get_str_param(params, 'preset', 'Custom trajectory')))
                return

            eclipses: dict[str, Any] = cast(dict[str, Any], predictor.predict_solar_eclipses(times_arr, pos_arr, sol.get('sun_direction_eci')))
            gs_passes: dict[str, Any] = cast(dict[str, Any], predictor.predict_ground_station_passes(times_arr, pos_arr))

            alt_km_arr = cast(np.ndarray, sol['altitude_km'])
            vel_kms_arr = cast(np.ndarray, sol['velocity_kms'])
            ta_deg_arr = cast(np.ndarray, sol['true_anomaly_deg'])

            gs_summary: dict[str, Any] = {
                name: {
                    "metadata": d["station_metadata"],
                    "passes": d["passes"],
                    "total_passes_count": d["total_passes_count"],
                    "total_contact_min": d["total_contact_min"]
                }
                for name, d in gs_passes.items()
            }

            # Generate compliant mission script with custom parameters
            mission_script_str: str = str(MissionScriptWorkbench.generate_mission_script(
                sma_km=a_km,
                ecc=e,
                inc_deg=inc_deg,
                raan_deg=raan_deg,
                aop_deg=aop_deg,
                ta_deg=ta_deg,
                dry_mass_kg=dry_mass,
                fuel_mass_kg=fuel_mass,
                drag_area_m2=drag_area,
                srp_area_m2=srp_area,
                cd=cd,
                cr=cr,
                num_orbits=int(num_orbits)
            ))

            script_workbench_payload = {"script_content": mission_script_str}

            active_orbit_config = {
                "preset_name": _get_str_param(params, 'preset', 'Custom HEO'),
                "semi_major_axis_km": round(float(a_km), 3),
                "eccentricity": round(float(e), 6),
                "inclination_deg": round(float(inc_deg), 3),
                "raan_deg": round(float(raan_deg), 3),
                "arg_perigee_deg": round(float(aop_deg), 3),
                "true_anomaly_deg": round(float(ta_deg), 3),
                "perigee_alt_km": round(float(a_km * (1.0 - e) - r_earth_km), 2),
                "apogee_alt_km": round(float(a_km * (1.0 + e) - r_earth_km), 2),
                "orbital_period_hours": round(float(period / 3600.0), 3),
                "num_orbits": num_orbits if duration_s is None else round(float(run_duration_s / period), 6),
                "duration_s": float(run_duration_s),
                "initial_state": initial_state_kind,
                "model": model_type,
                "integrator": method_type,
                "num_points": num_points,
                "enable_drag": enable_drag,
                "enable_third_body": enable_third_body,
                "enable_srp": enable_srp,
                "spacecraft_mass_kg": float(spacecraft_mass),
                "drag_area_m2": float(drag_area),
                "cd": float(cd),
                "srp_area_m2": float(srp_area),
                "cr": float(cr),
                "solve_time_sec": round(float(t_solve_sec), 3)
            }

            # Compute new high-precision industrial modules
            rb_model = RadiationBeltModel()
            rb_data = rb_model.evaluate_trajectory_radiation(times_arr, pos_arr)

            cov_engine = CovarianceEngine()
            if sol.get('stm') is not None:
                # The run's own variational equations, integrated with the orbit
                cov_data = cov_engine.dispersion_from_stm(pos_arr, vel_arr, cast(np.ndarray, sol['stm']))
            else:
                cov_data = cov_engine.propagate_stm_and_covariance(times_arr, pos_arr, vel_arr)

            exact_apsides = predictor.predict_apsidal_events(times_arr, pos_arr, vel_arr)
            exact_nodes = predictor.predict_orbital_nodes(times_arr, pos_arr, vel_arr)

            tle_str = CCSDSExporter.generate_tle(
                sma_km=a_km, ecc=e, inc_deg=inc_deg, raan_deg=raan_deg, aop_deg=aop_deg, ta_deg=ta_deg
            )
            opm_str = CCSDSExporter.generate_ccsds_opm(
                sma_km=a_km, ecc=e, inc_deg=inc_deg, raan_deg=raan_deg, aop_deg=aop_deg, ta_deg=ta_deg
            )

            payload: dict[str, Any] = {
                "status": "ok",
                "closed_orbit": True,
                "duration_s": float(run_duration_s),
                "total_points": len(times_arr),
                "times": times_arr.tolist(),
                "times_sec": times_arr.tolist(),
                "time_hours": (times_arr / 3600.0).tolist(),
                "position_m": pos_arr.tolist(),
                "positions_m": pos_arr.tolist(),
                "velocity_ms": vel_arr.tolist(),
                "velocities_ms": vel_arr.tolist(),
                "altitude_km": alt_km_arr.tolist(),
                "velocity_kms": vel_kms_arr.tolist(),
                "semi_major_axis_km": cast(np.ndarray, sol['semi_major_axis_km']).tolist(),
                "eccentricity": cast(np.ndarray, sol['eccentricity']).tolist(),
                "inclination_deg": cast(np.ndarray, sol['inclination_deg']).tolist(),
                "raan_deg": cast(np.ndarray, sol['raan_deg']).tolist(),
                "arg_perigee_deg": cast(np.ndarray, sol['arg_perigee_deg']).tolist(),
                "true_anomaly_deg": ta_deg_arr.tolist(),
                "epoch_utc": sol['epoch_utc'],
                "utc_iso": sol['utc_iso'],
                "frame": sol['frame'],
                "eop_in_range": sol['eop_in_range'],
                "epoch": sol['epoch'],
                "events": sol['events'],
                "position_itrf_m": cast(np.ndarray, sol['position_itrf_m']).tolist(),
                "velocity_itrf_ms": cast(np.ndarray, sol['velocity_itrf_ms']).tolist(),
                "latitude_deg": cast(np.ndarray, sol['latitude_deg']).tolist(),
                "longitude_deg": cast(np.ndarray, sol['longitude_deg']).tolist(),
                "energy_error": cast(np.ndarray, sol['energy_fractional_error']).tolist(),
                "orbital_period_hours": float(sol.get('orbital_period_hours', period / 3600.0)),
                "active_orbit_config": active_orbit_config,
                "events_suite": {
                    "solar_eclipses": eclipses,
                    "ground_stations": gs_summary,
                    "exact_apsidal_events": exact_apsides,
                    "exact_nodal_events": exact_nodes
                },
                "radiation_belts": rb_data,
                "covariance_dispersion": cov_data,
                "force_diagnostics": sol.get("force_diagnostics", {}),
                "ccsds_interoperability": {
                    "tle_string": tle_str,
                    "opm_string": opm_str
                },
                "innovations_suite": {
                    "ecr_mf": sol.get('ecr_mf'),
                    "covariance_steered_stepping": _steering_summary(sol.get('steps'))
                },
                "script_workbench": script_workbench_payload,
            }
            # Unit Sun vector in the frame of position_m; absent outside the bundled DE440 years
            if sol.get('sun_direction_eci') is not None:
                payload["sun_direction_eci"] = cast(np.ndarray, sol['sun_direction_eci']).tolist()
            self.send_json(payload)
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


def _escape_payload(sol: dict[str, Any], duration_s: float, initial_state: str, model: str, method: str,
                    num_points: int, solve_time_s: float, preset: str) -> dict[str, Any]:
    """/api/propagate response for an escape (e >= 1) trajectory: the propagated arc and its own fields."""
    def arr(key: str) -> list[Any]:
        return cast(np.ndarray, sol[key]).tolist()
    times = cast(np.ndarray, sol['times'])
    pos = cast(np.ndarray, sol['position_m'])
    vel = cast(np.ndarray, sol['velocity_ms'])
    kep0 = mission_targeting.keplerian_from_state(pos[0], vel[0], MU_EARTH)
    r_earth_km = R_EARTH / 1000.0
    sun = sol.get('sun_direction_eci')
    return {
        "status": "ok",
        "closed_orbit": False,
        "duration_s": float(duration_s),
        "total_points": len(times),
        "times": times.tolist(), "times_sec": times.tolist(), "time_hours": (times / 3600.0).tolist(),
        "position_m": pos.tolist(), "positions_m": pos.tolist(),
        "velocity_ms": vel.tolist(), "velocities_ms": vel.tolist(),
        "altitude_km": arr('altitude_km'), "velocity_kms": arr('velocity_kms'),
        "semi_major_axis_km": arr('semi_major_axis_km'), "eccentricity": arr('eccentricity'),
        "inclination_deg": arr('inclination_deg'), "raan_deg": arr('raan_deg'),
        "arg_perigee_deg": arr('arg_perigee_deg'), "true_anomaly_deg": arr('true_anomaly_deg'),
        "latitude_deg": arr('latitude_deg'), "longitude_deg": arr('longitude_deg'),
        "position_itrf_m": arr('position_itrf_m'), "velocity_itrf_ms": arr('velocity_itrf_ms'),
        "energy_error": arr('energy_fractional_error'),
        "epoch_utc": sol['epoch_utc'], "utc_iso": sol['utc_iso'], "frame": sol['frame'],
        "eop_in_range": sol['eop_in_range'], "epoch": sol['epoch'], "events": sol['events'],
        "sun_direction_eci": None if sun is None else np.asarray(sun).tolist(),
        "orbital_period_hours": None,
        "active_orbit_config": {
            "preset_name": preset,
            "semi_major_axis_km": round(float(kep0['a']) / 1000.0, 3),
            "eccentricity": round(float(kep0['e']), 6),
            "inclination_deg": round(float(np.degrees(kep0['inc'])), 3),
            "raan_deg": round(float(np.degrees(kep0['raan'])), 3),
            "arg_perigee_deg": round(float(np.degrees(kep0['argp'])), 3),
            "true_anomaly_deg": round(float(np.degrees(kep0['ta'])), 3),
            "perigee_alt_km": round(float(kep0['rp']) / 1000.0 - r_earth_km, 2),
            "apogee_alt_km": None, "orbital_period_hours": None, "num_orbits": None,
            "duration_s": float(duration_s), "initial_state": initial_state,
            "model": model, "integrator": method, "num_points": num_points,
            "solve_time_sec": round(float(solve_time_s), 3),
        },
        "notes": ["Escape trajectory (e >= 1): closed-orbit reports (lifetime, apsis targeting, "
                  "mission script, TLE/OPM export) are not produced."],
    }


def _steering_summary(steps: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """What covariance steering did to the run's steps, or None when the run was not steered."""
    if steps is None:
        return None
    h = np.asarray(steps['h_s'][1:])
    sigma = np.asarray(steps['sigma_pos_m'])
    return {
        "eta": steps['eta'],
        "accepted_steps": int(len(h)),
        "limited_steps": int(sum(steps['limited'][1:])),
        "min_step_s": float(h.min()) if len(h) else None,
        "max_step_s": float(h.max()) if len(h) else None,
        "max_step_sigma_growth": float(np.max(np.abs(np.diff(sigma)) / sigma[:-1])) if len(sigma) > 1 else 0.0,
        "initial_1sigma_pos_m": float(sigma[0]),
        "final_1sigma_pos_m": float(sigma[-1]),
    }


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
    print(f" ASTROFLYER HEO - THIRD REVIEW PRODUCTION FLIGHT DYNAMICS SERVER")
    print(f" High-Precision Trajectory Propagation & Mission Events Prediction")
    print(f" Serving AstroFlyer HEO Flight Operations Studio at: http://127.0.0.1:{port}")
    print(f"==========================================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()


if __name__ == '__main__':
    run_server(port=8003)
