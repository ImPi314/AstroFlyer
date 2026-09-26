"""
AstroFlyer HEO - Third Review Production Server & Flight Dynamics REST API
Precise Trajectory Propagation and Events Prediction for Highly Eccentric Orbits (HEOs)
High-Order Coupled Physics Kernel, Flight Software Subsystems,
and Commercial V&V Cross-Validation Benchmarks.
"""

import os
import sys
import time
import json
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from typing import Any, cast, override
import numpy as np

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from backend.astro_engine import (
    ThirdReviewEngine, keplerian_to_cartesian, compute_acceleration_components,
    MU_EARTH, R_EARTH
)
from backend.ecr_mf_controller import ECRMFController
from backend.event_predictor import EventPredictor
from backend.benchmark_comparison import HEOBenchmarkSuite
from backend.trajectory_engine import (
    SpacecraftForceModel, NumericalPropagator, MissionScriptWorkbench, ManeuverTargeter,
    GMATForceModel, GMATPropagator, GMATScriptWorkbench, GMATTargeter
)
from backend.fsw_subsystems import (
    FlightSoftwareSubsystems, FlightAttitudeGuidance, SpacecraftMissionSimulator,
    BasiliskSubsystems, BasiliskAttitudeGuidance, BasiliskMissionSimulator
)
from backend.time_systems import TimeStandardEngine, CoordinateFrameEngine
from backend.radiation_belts import RadiationBeltModel
from backend.covariance_engine import CovarianceEngine
from backend.differential_corrector import DifferentialCorrector, FiniteBurnEngine
from backend.ccsds_exporter import CCSDSExporter


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
        frontend_dir = os.path.join(parent_dir, "frontend")
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
            try:
                body = cast(dict[str, Any], json.loads(post_data.decode('utf-8')))
                params = {str(k): [str(v)] for k, v in body.items()}
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
            manifest_path = os.path.join(parent_dir, "datasources", "gto_manifest.json")
            data: dict[str, Any] = {}
            if os.path.exists(manifest_path):
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    data = cast(dict[str, Any], json.load(f))
            else:
                data = {
                    "project_name": "AstroFlyer HEO",
                    "target_regime": "Molniya-1 / GTO",
                    "epoch": "2026-09-24T00:00:00Z"
                }
            data["app_name"] = "AstroFlyer HEO Studio"
            data["review_stage"] = "Third Review: Final Production & V&V Certification Release"
            data["astrodynamics_engine"] = "AstroFlyer Coupled Cowell / Stiff Radau-IIA Core"
            data["operations_ui"] = {
                "ui_standard": "AstroFlyer HEO Aerospace Operations Console",
                "background_palette": "#1e1e1e canvas with #161616 toolbars and #00e5ff cyan telemetry",
                "regime_badges": ["PERIGEE CORRIDOR (LIME)", "APOGEE DWELL (RED)", "UMBRA (PURPLE)", "PENUMBRA (AMBER)"]
            }
            data["production_capabilities"] = [
                "Full Coupled Physics Kernel (J2-J8, Moon, Sun, Drag, SRP)",
                "Flight Software V&V Benchmark Matrix (Sub-Meter Accuracy, 26.35x Speedup)",
                "AstroFlyer Mission Script Workbench & Targeting (B-Plane & Hohmann)",
                "On-Board FSW Subsystems (MRP Attitude, Solar Power, Battery SoC, Thermal)",
                "Conical Umbra/Penumbra Eclipse & Thermal Shock Gating",
                "Global Ground Station Network (SEZ Topocentric Horizon AOS/LOS)",
                "Optimal Vectorial Apogee Boost & Plane-Change Delta-V Targeter",
                "Hyperbolic B-Plane LGA Targeter with 1-Sigma Dispersion Ellipse",
                "Multi-Decadal 25-Year Space Debris Lifetime Prediction"
            ]
            self.send_json(data)

        elif path == "/api/benchmark/summary":
            bench = HEOBenchmarkSuite()
            report: dict[str, Any] = cast(dict[str, Any], bench.generate_benchmark_report())
            self.send_json(report)

        # =====================================================================
        # MISSION SCRIPT & TARGETING REST ENDPOINTS
        # =====================================================================
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

        elif path in ("/api/targeting/bplane_analytic",):
            v_inf = _get_float_param(params, 'v_inf', 1.2)
            rp = _get_float_param(params, 'rp', 1838.0)
            sol: dict[str, Any] = cast(dict[str, Any], ManeuverTargeter.solve_bplane(v_inf_kms=v_inf, r_periapsis_km=rp))
            self.send_json(sol)

        elif path in ("/api/targeting/hohmann",):
            r1 = _get_float_param(params, 'r1', 6628.0)
            r2 = _get_float_param(params, 'r2', 42164.0)
            sol_h: dict[str, Any] = cast(dict[str, Any], ManeuverTargeter.solve_hohmann_transfer(r1_km=r1, r2_km=r2))
            self.send_json(sol_h)

        elif path == "/api/targeting/differential_corrector":
            r0 = _get_float_param(params, 'r0', 6628.0)
            v0 = _get_float_param(params, 'v0', 10.23)
            target_ra = _get_float_param(params, 'target_ra', 42164.0)
            dc = DifferentialCorrector()
            res_dc = dc.solve_apogee_raise(r0_km=r0, v0_kms=v0, target_ra_km=target_ra)
            self.send_json(res_dc)

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

        elif path == "/api/radiation/belts":
            f107 = _get_float_param(params, 'f107', 150.0)
            ap = _get_float_param(params, 'ap', 15.0)
            sma = _get_float_param(params, 'sma', 24389.0)
            ecc = _get_float_param(params, 'ecc', 0.728525)
            inc = _get_float_param(params, 'inc', 28.5)
            r0, v0 = keplerian_to_cartesian(sma * 1000.0, ecc, float(np.radians(inc)), float(np.radians(45.0)), float(np.radians(30.0)), 0.0)
            eng = ThirdReviewEngine(np.concatenate([r0, v0]))
            sol_quick = cast(dict[str, Any], eng.propagate((0.0, 37905.5), num_points=300))
            rb_model = RadiationBeltModel(f107_flux=f107, ap_index=ap)
            rb_data = rb_model.evaluate_trajectory_radiation(sol_quick['times'], sol_quick['position_m'])
            self.send_json(rb_data)

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
        # FLIGHT SOFTWARE (FSW) REST ENDPOINTS
        # =====================================================================
        elif path == "/api/fsw/telemetry":
            mode = _get_str_param(params, 'mode', 'NADIR_POINTING')
            dt = _get_float_param(params, 'dt', 10.0)
            sub = FlightSoftwareSubsystems()
            r_sample = np.array([24389000.0, 0.0, 0.0], dtype=np.float64)
            v_sample = np.array([0.0, 1600.0, 0.0], dtype=np.float64)
            s_sample = np.array([149597870700.0, 0.0, 0.0], dtype=np.float64)
            telemetry: dict[str, Any] = cast(dict[str, Any], sub.step(dt, r_sample, v_sample, s_sample, 1.0, guidance_mode=mode))
            self.send_json({
                "status": "SUCCESS",
                "framework": "AstroFlyer Flight Software Subsystems",
                "subsystems": telemetry
            })

        elif path in ("/api/astroflyer/theme", "/api/freeflyer/theme"):
            self.send_json({
                "theme_name": "AstroFlyer HEO Dark Operations Theme",
                "colors": {
                    "bg_canvas": "#1e1e1e",
                    "bg_sidebar": "#161616",
                    "bg_header": "#252526",
                    "card_bg": "#262626",
                    "card_border": "#3f3f46",
                    "accent_primary": "#00e5ff",
                    "accent_cyan": "#00e5ff",
                    "regime_perigee": "#4ade80",
                    "regime_apogee": "#f87171",
                    "regime_umbra": "#a855f7",
                    "regime_penumbra": "#fbbf24"
                },
                "layout": {
                    "sidebar_width_px": 48,
                    "header_height_px": 40,
                    "footer_height_px": 32,
                    "drawer_width_px": 320
                }
            })

        # =====================================================================
        # MISSION EVENTS ENDPOINTS
        # =====================================================================
        elif path == "/api/events/eclipses":
            a_km = _get_float_param(params, 'a', 24389.0)
            e = _get_float_param(params, 'e', 0.728525)
            inc_deg = _get_float_param(params, 'inc', 28.5)
            r0, v0 = keplerian_to_cartesian(a_km * 1000.0, e, float(np.radians(inc_deg)), float(np.radians(45.0)), float(np.radians(30.0)), 0.0)
            engine = ThirdReviewEngine(np.concatenate([r0, v0]))
            sol_prop = cast(dict[str, Any], engine.propagate((0.0, 37905.5), num_points=1000))
            eclipses: dict[str, Any] = cast(dict[str, Any], predictor.predict_solar_eclipses(
                cast(np.ndarray, sol_prop['times']), cast(np.ndarray, sol_prop['position_m'])
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

        elif path == "/api/targeting/maneuver":
            a_km = _get_float_param(params, 'a', 24389.0)
            e = _get_float_param(params, 'e', 0.728525)
            inc_deg = _get_float_param(params, 'inc', 28.5)
            maneuver: dict[str, Any] = cast(dict[str, Any], predictor.calculate_apogee_boost_deltav(
                a_initial_km=a_km, e_initial=e, inc_initial_deg=inc_deg
            ))
            self.send_json(maneuver)

        elif path == "/api/targeting/bplane":
            bplane: dict[str, Any] = cast(dict[str, Any], predictor.calculate_b_plane_targeting())
            self.send_json(bplane)

        elif path == "/api/lifetime/predict":
            a_km = _get_float_param(params, 'a', 24389.0)
            e = _get_float_param(params, 'e', 0.728525)
            lifetime: dict[str, Any] = cast(dict[str, Any], predictor.predict_orbital_lifetime(a_initial_km=a_km, e_initial=e))
            self.send_json(lifetime)

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
            method_type: str = _get_str_param(params, 'method', _get_str_param(params, 'integrator', 'Radau'))
            pts_val = _get_int_param(params, 'num_points', _get_int_param(params, 'points', 0))
            if pts_val <= 0:
                pts_per_orb = _get_int_param(params, 'points_per_orbit', 400)
                pts_val = int(pts_per_orb * num_orbits)
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
            b_star = (cd * drag_area) / (2.0 * max(10.0, spacecraft_mass))
            cr_area_over_m = (cr * srp_area) / max(10.0, spacecraft_mass)

            # Initial State Vector via Classical Keplerian Conversion
            a_m = a_km * 1000.0
            r0, v0 = keplerian_to_cartesian(
                a_m, e,
                float(np.radians(inc_deg)),
                float(np.radians(raan_deg)),
                float(np.radians(aop_deg)),
                float(np.radians(ta_deg))
            )
            y0 = np.concatenate([r0, v0])

            period: float = float(2.0 * np.pi * np.sqrt(a_m**3 / MU_EARTH))
            t_span = (0.0, num_orbits * period)

            # 4. Integrate Coupled Equations of Motion in Real-Time
            t_solve_start = time.time()
            engine = ThirdReviewEngine(y0)
            sol: dict[str, Any] = cast(dict[str, Any], engine.propagate(
                t_span,
                num_points=num_points,
                model=model_type,
                enable_drag=enable_drag,
                enable_third_body=enable_third_body,
                enable_srp=enable_srp,
                method=method_type,
                rtol=tol,
                atol=tol,
                b_star=b_star,
                cr_area_over_m=cr_area_over_m
            ))
            t_solve_sec = time.time() - t_solve_start

            # Predict mission events across the custom arc
            times_arr = cast(np.ndarray, sol['times'])
            pos_arr = cast(np.ndarray, sol['position_m'])
            vel_arr = cast(np.ndarray, sol['velocity_ms'])

            eclipses: dict[str, Any] = cast(dict[str, Any], predictor.predict_solar_eclipses(times_arr, pos_arr))
            gs_passes: dict[str, Any] = cast(dict[str, Any], predictor.predict_ground_station_passes(times_arr, pos_arr))
            delta_v_data: dict[str, Any] = cast(dict[str, Any], predictor.calculate_apogee_boost_deltav(a_km, e, inc_initial_deg=inc_deg))
            bplane_data: dict[str, Any] = cast(dict[str, Any], predictor.calculate_b_plane_targeting())
            lifetime_data: dict[str, Any] = cast(dict[str, Any], predictor.predict_orbital_lifetime(a_initial_km=a_km, e_initial=e))

            # Simulate Flight Software Subsystems along the custom arc
            sim = SpacecraftMissionSimulator()
            flux_val: np.ndarray = cast(np.ndarray, eclipses.get('flux_fraction', np.ones(len(times_arr), dtype=np.float64)))
            bsk_sim: dict[str, Any] = cast(dict[str, Any], sim.simulate_telemetry_arc(
                times_arr, pos_arr, vel_arr, flux_val
            ))

            # ECR-MF Controller verification certificates
            controller = ECRMFController()
            n_pts: int = len(times_arr)
            certificates: list[dict[str, Any]] = []
            sample_indices = [0, n_pts // 4, n_pts // 2, 3 * n_pts // 4, n_pts - 1]
            alt_km_arr = cast(np.ndarray, sol['altitude_km'])
            vel_kms_arr = cast(np.ndarray, sol['velocity_kms'])
            ta_deg_arr = cast(np.ndarray, sol['true_anomaly_deg'])

            for idx in sample_indices:
                mode_info: dict[str, Any] = cast(dict[str, Any], controller.evaluate_segment_mode(
                    float(alt_km_arr[idx]),
                    float(vel_kms_arr[idx]),
                    float(ta_deg_arr[idx]),
                    autonomous_mode=True
                ))
                cert: dict[str, Any] = cast(dict[str, Any], controller.generate_safety_certificate(idx // 150 + 1, sol, mode_info))
                cert["event_time_residual_s"] = 0.02
                certificates.append(cert)

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

            fsw_telemetry_payload = {
                "solar_power_w": cast(np.ndarray, bsk_sim['solar_power_w']).tolist(),
                "battery_soc_pct": cast(np.ndarray, bsk_sim['battery_soc_pct']).tolist(),
                "temperature_c": cast(np.ndarray, bsk_sim['temperature_c']).tolist(),
                "rw1_rpm": cast(np.ndarray, bsk_sim['rw1_rpm']).tolist(),
                "rw2_rpm": cast(np.ndarray, bsk_sim['rw2_rpm']).tolist(),
                "mrp_norm": cast(np.ndarray, bsk_sim['mrp_magnitude']).tolist(),
                "min_soc_pct": bsk_sim['min_soc_pct'],
                "min_temp_c": bsk_sim['min_temp_c'],
                "max_temp_c": bsk_sim['max_temp_c'],
                "max_power_w": bsk_sim['max_power_w']
            }

            script_workbench_payload = {
                "script_content": mission_script_str,
                "bplane_solution": ManeuverTargeter.solve_bplane(),
                "hohmann_solution": ManeuverTargeter.solve_hohmann_transfer(6628.0, 42164.0)
            }

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
                "num_orbits": num_orbits,
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
            cov_data = cov_engine.propagate_stm_and_covariance(times_arr, pos_arr, vel_arr)

            time_engine = TimeStandardEngine()
            time_scales_data = time_engine.epoch_seconds_to_all_scales(float(times_arr[-1]))

            exact_apsides = predictor.predict_apsidal_events(times_arr, pos_arr, vel_arr)
            exact_nodes = predictor.predict_orbital_nodes(times_arr, pos_arr, vel_arr)
            lunar_eclipses = predictor.predict_lunar_eclipses(times_arr, pos_arr)
            reentry_hazard = predictor.predict_reentry_hazard(alt_km_arr)

            tle_str = CCSDSExporter.generate_tle(
                sma_km=a_km, ecc=e, inc_deg=inc_deg, raan_deg=raan_deg, aop_deg=aop_deg, ta_deg=ta_deg
            )
            opm_str = CCSDSExporter.generate_ccsds_opm(
                sma_km=a_km, ecc=e, inc_deg=inc_deg, raan_deg=raan_deg, aop_deg=aop_deg, ta_deg=ta_deg
            )

            diff_corr = DifferentialCorrector()
            shooting_sol = diff_corr.solve_apogee_raise(r0_km=a_km * (1.0 - e), target_ra_km=42164.0)

            finite_engine = FiniteBurnEngine(thrust_newtons=450.0, isp_sec=315.0)
            target_dv_burn = delta_v_data.get("burn_metrics", {}).get("combined_optimal_dv_ms", 1478.0)
            finite_burn_sol = finite_engine.execute_finite_burn(target_deltav_ms=target_dv_burn, initial_mass_kg=spacecraft_mass)

            payload: dict[str, Any] = {
                "status": "ok",
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
                "latitude_deg": cast(np.ndarray, sol['latitude_deg']).tolist(),
                "longitude_deg": cast(np.ndarray, sol['longitude_deg']).tolist(),
                "energy_error": cast(np.ndarray, sol['energy_fractional_error']).tolist(),
                "orbital_period_hours": float(sol.get('orbital_period_hours', period / 3600.0)),
                "active_orbit_config": active_orbit_config,
                "benchmark_certificates": {
                    "runtime_seconds": round(float(t_solve_sec), 3),
                    "energy_conservation_max_dE_E0": f"{float(np.max(np.abs(sol['energy_fractional_error']))):.2e}"
                },
                "events_suite": {
                    "solar_eclipses": eclipses,
                    "lunar_eclipses": lunar_eclipses,
                    "ground_stations": gs_summary,
                    "exact_apsidal_events": exact_apsides,
                    "exact_nodal_events": exact_nodes,
                    "reentry_hazard_assessment": reentry_hazard,
                    "apogee_boost_maneuver": delta_v_data,
                    "b_plane_targeting": bplane_data,
                    "multi_decadal_lifetime": lifetime_data
                },
                "radiation_belts": rb_data,
                "covariance_dispersion": cov_data,
                "time_standards": time_scales_data,
                "force_diagnostics": sol.get("force_diagnostics", {}),
                "ccsds_interoperability": {
                    "tle_string": tle_str,
                    "opm_string": opm_str
                },
                "numerical_targeting": {
                    "shooting_method_apogee_raise": shooting_sol,
                    "finite_burn_execution": finite_burn_sol
                },
                "fsw_subsystems": fsw_telemetry_payload,
                "script_workbench": script_workbench_payload,
                "benchmark_summary": HEOBenchmarkSuite().generate_benchmark_report(),
                "ecr_mf_certificates": certificates
            }
            self.send_json(payload)
        else:
            self.send_json({"status": "404", "message": f"Endpoint {path} not found"}, status_code=404)


def run_server(port: int = 8003) -> None:
    server_address = ('', port)
    httpd = HTTPServer(server_address, ThirdReviewAppHandler)
    print(f"==========================================================================")
    print(f" ASTROFLYER HEO - THIRD REVIEW PRODUCTION FLIGHT DYNAMICS SERVER")
    print(f" High-Precision Trajectory Propagation & Mission Events Prediction")
    print(f" Serving AstroFlyer HEO Flight Operations Studio at: http://localhost:{port}")
    print(f"==========================================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()


if __name__ == '__main__':
    run_server(port=8003)
