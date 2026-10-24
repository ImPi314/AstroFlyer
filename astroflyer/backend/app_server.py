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


from backend.astro_engine import (
    ThirdReviewEngine, keplerian_to_cartesian, cartesian_to_keplerian, compute_acceleration_components,
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
from backend.epoch import Epoch
from backend import mission as mission_targeting
from backend.script_runner import run_script
from backend.radiation_belts import RadiationBeltModel, RadiationParetoOptimizer
from backend.covariance_engine import CovarianceEngine, CovarianceSteeredAdaptiveStepController
from backend.differential_corrector import DifferentialCorrector, FiniteBurnEngine, MultiBurnPerigeePumpingPlanner
from backend.constellation_engine import MolniyaConstellationEngine
from backend.ccsds_exporter import CCSDSExporter
from backend.mission_plan_io import export_to_mission_plan, import_from_mission_plan, validate_mission_plan


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
            manifest_path = resolve_app_path("datasources", "gto_manifest.json")
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

        elif path in ("/api/mission_plan/export", "/api/mission/plan/export"):
            sma = _get_float_param(params, 'sma', 24389.0)
            ecc = _get_float_param(params, 'ecc', 0.728525)
            inc = _get_float_param(params, 'inc', 28.5)
            raan = _get_float_param(params, 'raan', 45.0)
            aop = _get_float_param(params, 'aop', 30.0)
            ta = _get_float_param(params, 'ta', 0.0)
            dur = _get_float_param(params, 'duration_hours', 24.0)
            title = _get_str_param(params, 'title', "AstroFlyer HEO Mission Plan (FreeFlyer XML)")

            out_file = resolve_app_path("data", "AstroFlyer_HEO_Mission_Plan.MissionPlan")
            res_mp = export_to_mission_plan(
                {'sma_km': sma, 'ecc': ecc, 'inc_deg': inc, 'raan_deg': raan, 'aop_deg': aop, 'ta_deg': ta},
                output_path=out_file,
                duration_hours=dur,
                mission_title=title,
                validate_xsd=True
            )
            try:
                with open(out_file, "r", encoding="utf-8") as f:
                    res_mp["xml_content"] = f.read()
            except Exception:
                res_mp["xml_content"] = ""
            res_mp["filename"] = "AstroFlyer_HEO_Mission_Plan.MissionPlan"
            self.send_json(res_mp)

        elif path in ("/api/mission_plan/validate",):
            xml_text = _get_str_param(params, 'xml_text', '')
            if not xml_text:
                test_file = resolve_app_path("data", "AstroFlyer_HEO_Mission_Plan.MissionPlan")
                is_valid, errs = validate_mission_plan(test_file) if os.path.exists(test_file) else (False, ["No XML file provided"])
            else:
                is_valid, errs = validate_mission_plan(xml_text)
            self.send_json({
                "status": "SUCCESS",
                "is_schema_valid": is_valid,
                "validation_errors": errs
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

        elif path == "/api/script/run":
            # Runs a full mission script (Create ... BeginMissionSequence ...) on the AstroFlyer engine
            self.send_json(run_script(_get_str_param(params, 'script_text', '')))

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
        # INNOVATION 1-5 ADVANCED ASTRODYNAMICS REST ENDPOINTS
        # =====================================================================
        elif path in ("/api/constellation/molniya", "/api/constellation/propagate"):
            dur_hr = _get_float_param(params, 'duration_hours', 24.0)
            sma = _get_float_param(params, 'sma', 26560.0)
            ecc = _get_float_param(params, 'ecc', 0.72)
            inc = _get_float_param(params, 'inc', 63.4349)
            const_eng = MolniyaConstellationEngine(semi_major_axis_km=sma, eccentricity=ecc, inclination_deg=inc)
            sol_const = const_eng.propagate_constellation(duration_hours=dur_hr)
            self.send_json(sol_const)

        elif path in ("/api/radiation/pareto", "/api/radiation/trade_study"):
            hp_base = _get_float_param(params, 'hp', 250.0)
            ha_target = _get_float_param(params, 'ha', 35786.0)
            lifetime = _get_float_param(params, 'lifetime_years', 5.0)
            opt = RadiationParetoOptimizer(mission_lifetime_years=lifetime)
            pareto_res = opt.evaluate_pareto_frontier(initial_perigee_km=hp_base, apogee_km=ha_target)
            self.send_json(pareto_res)

        elif path in ("/api/targeting/perigee_pumping", "/api/maneuvers/pumping"):
            rp_km = _get_float_param(params, 'rp', 6628.0)
            ra_start = _get_float_param(params, 'ra_start', 35786.0)
            ra_target = _get_float_param(params, 'ra_target', 384400.0)
            wet_m = _get_float_param(params, 'mass', 1500.0)
            n_burns = int(_get_float_param(params, 'num_burns', 5.0))
            planner = MultiBurnPerigeePumpingPlanner()
            pump_sol = planner.plan_perigee_pumping(
                r_perigee_km=rp_km, initial_apogee_km=ra_start, target_apogee_km=ra_target,
                wet_mass_kg=wet_m, num_burns=n_burns
            )
            self.send_json(pump_sol)

        elif path in ("/api/covariance/steered", "/api/covariance/step_factor"):
            phi_dummy = np.eye(6) * (1.0 + float(np.random.uniform(0.01, 0.05)))
            p_dummy = np.diag([100.0, 100.0, 100.0, 0.01, 0.01, 0.01])
            steered_ctrl = CovarianceSteeredAdaptiveStepController()
            factor_res = steered_ctrl.compute_covariance_steered_step_factor(phi_dummy, p_dummy)
            self.send_json(factor_res)


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

        elif path == "/api/maneuver/what_if":
            hp_km = _get_float_param(params, 'hp', 250.0)
            ha_km = _get_float_param(params, 'ha', 35786.0)
            r_earth_km = R_EARTH / 1000.0
            rp = r_earth_km + hp_km
            ra = r_earth_km + ha_km
            a_km = (rp + ra) / 2.0
            e = (ra - rp) / (ra + rp)

            inc_deg = _get_float_param(params, 'inc', 28.5)
            raan_deg = _get_float_param(params, 'raan', 45.0)
            aop_deg = _get_float_param(params, 'aop', 30.0)

            loc = _get_str_param(params, 'burn_location', 'perigee')
            loc_val = _get_float_param(params, 'burn_location_value', 0.0)
            dv_prograde = _get_float_param(params, 'dv_prograde', 0.0)
            dv_normal = _get_float_param(params, 'dv_normal', 0.0)
            dv_radial = _get_float_param(params, 'dv_radial', 0.0)
            mass_kg = _get_float_param(params, 'mass', 1500.0)
            isp_s = _get_float_param(params, 'isp', 315.0)

            if loc == 'perigee':
                nu_burn = 0.0
            elif loc == 'apogee':
                nu_burn = 180.0
            elif loc == 'true_anomaly':
                nu_burn = loc_val
            elif loc == 'node':
                nu_burn = (360.0 - aop_deg) % 360.0
            else:
                nu_burn = 0.0

            a_m = a_km * 1000.0
            r_burn, v_burn = keplerian_to_cartesian(
                a_m, e,
                math.radians(inc_deg),
                math.radians(raan_deg),
                math.radians(aop_deg),
                math.radians(nu_burn)
            )

            v_mag = float(np.linalg.norm(v_burn))
            r_mag = float(np.linalg.norm(r_burn))
            v_hat = v_burn / max(1e-6, v_mag)

            h_vec = np.cross(r_burn, v_burn)
            h_mag = float(np.linalg.norm(h_vec))
            n_hat = h_vec / max(1e-6, h_mag)
            r_hat = np.cross(v_hat, n_hat)

            dv_total_ms = math.sqrt(dv_prograde**2 + dv_normal**2 + dv_radial**2)
            dv_inertial = dv_prograde * v_hat + dv_normal * n_hat + dv_radial * r_hat

            v_post = v_burn + dv_inertial
            post_elem = cartesian_to_keplerian(r_burn, v_post, mu=MU_EARTH)
            a_post_km = post_elem['a'] / 1000.0
            e_post = post_elem['e']
            inc_post_deg = math.degrees(post_elem['inc'])
            raan_post_deg = math.degrees(post_elem['Omega'])
            aop_post_deg = math.degrees(post_elem['omega'])

            rp_post_km = a_post_km * (1.0 - e_post) if e_post < 1.0 else (r_mag / 1000.0)
            hp_post_km = rp_post_km - r_earth_km
            if e_post < 1.0:
                ra_post_km = a_post_km * (1.0 + e_post)
                ha_post_km = ra_post_km - r_earth_km
                period_post_s = 2.0 * math.pi * math.sqrt((a_post_km * 1000.0)**3 / MU_EARTH)
                period_post_hr = period_post_s / 3600.0
            else:
                ha_post_km = float('inf')
                period_post_hr = float('inf')

            period_init_hr = (2.0 * math.pi * math.sqrt((a_km * 1000.0)**3 / MU_EARTH)) / 3600.0

            g0 = 9.80665
            if dv_total_ms > 0:
                mass_ratio = math.exp(dv_total_ms / (isp_s * g0))
                propellant_burnt_kg = mass_kg * (1.0 - 1.0 / mass_ratio)
            else:
                propellant_burnt_kg = 0.0
            final_mass_kg = mass_kg - propellant_burnt_kg

            method_type = _get_str_param(params, 'method', 'Radau')
            tol_val = _get_float_param(params, 'tolerance', 1e-10)
            engine_post = ThirdReviewEngine(np.hstack([r_burn, v_post]))
            t_span_post = (0.0, min(86400.0 * 2.0, max(7200.0, (period_post_hr if period_post_hr != float('inf') else 12.0) * 3600.0 * 2.0)))
            sol_post = engine_post.propagate(t_span_post, num_points=600, method=method_type, rtol=tol_val, atol=tol_val)

            lat_post, lon_post, alt_post = [], [], []
            omega_e = 7.2921159e-5
            for i in range(len(sol_post['times'])):
                t_i = sol_post['times'][i]
                r_i = sol_post['position_m'][i]
                theta = omega_e * t_i
                x_ecef = math.cos(theta) * r_i[0] + math.sin(theta) * r_i[1]
                y_ecef = -math.sin(theta) * r_i[0] + math.cos(theta) * r_i[1]
                z_ecef = r_i[2]
                r_norm = math.sqrt(x_ecef**2 + y_ecef**2 + z_ecef**2)
                lat = math.degrees(math.asin(z_ecef / max(1.0, r_norm)))
                lon = math.degrees(math.atan2(y_ecef, x_ecef))
                lat_post.append(lat)
                lon_post.append(lon)
                alt_post.append((r_norm - R_EARTH) / 1000.0)

            response = {
                "status": "ok",
                "maneuver_summary": {
                    "burn_location": loc,
                    "burn_true_anomaly_deg": round(nu_burn, 2),
                    "burn_radius_km": round(r_mag / 1000.0, 2),
                    "burn_velocity_pre_kms": round(v_mag / 1000.0, 3),
                    "delta_v_total_ms": round(dv_total_ms, 2),
                    "delta_v_components_ms": {
                        "prograde_in_track": round(dv_prograde, 2),
                        "normal_out_of_plane": round(dv_normal, 2),
                        "radial_altitude": round(dv_radial, 2)
                    },
                    "propellant_consumed_kg": round(propellant_burnt_kg, 2),
                    "initial_mass_kg": round(mass_kg, 2),
                    "final_mass_kg": round(final_mass_kg, 2),
                    "propulsion_isp_s": isp_s
                },
                "orbit_delta": {
                    "baseline": {
                        "perigee_altitude_km": round(hp_km, 2),
                        "apogee_altitude_km": round(ha_km, 2),
                        "semi_major_axis_km": round(a_km, 2),
                        "eccentricity": round(e, 5),
                        "inclination_deg": round(inc_deg, 2),
                        "period_hours": round(period_init_hr, 2)
                    },
                    "post_burn": {
                        "perigee_altitude_km": round(hp_post_km, 2),
                        "apogee_altitude_km": round(ha_post_km, 2) if ha_post_km != float('inf') else "ESCAPE",
                        "semi_major_axis_km": round(a_post_km, 2),
                        "eccentricity": round(e_post, 5),
                        "inclination_deg": round(inc_post_deg, 2),
                        "period_hours": round(period_post_hr, 2) if period_post_hr != float('inf') else "HYPERBOLIC"
                    },
                    "net_change": {
                        "delta_hp_km": round(hp_post_km - hp_km, 2),
                        "delta_ha_km": round(ha_post_km - ha_km, 2) if ha_post_km != float('inf') else "N/A",
                        "delta_inc_deg": round(inc_post_deg - inc_deg, 2),
                        "delta_period_hours": round(period_post_hr - period_init_hr, 2) if period_post_hr != float('inf') else "N/A"
                    }
                },
                "post_burn_trajectory": {
                    "times": sol_post['times'].tolist(),
                    "position_km": (sol_post['position_m'] / 1000.0).tolist(),
                    "velocity_kms": (sol_post['velocity_ms'] / 1000.0).tolist(),
                    "ground_track": {
                        "latitudes": lat_post,
                        "longitudes": lon_post,
                        "altitudes": alt_post
                    }
                }
            }
            self.send_json(response)

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
            # Initial-state epoch (ISO 8601, UTC unless tagged TAI/TT/TDB/UT1/GPS); default J2000.0
            epoch_text: str = _get_str_param(params, 'epoch', '')
            try:
                initial_epoch = Epoch.coerce(epoch_text or None)
            except ValueError as exc:
                self.send_json({"error": str(exc)}, 400)
                return
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
            b_star = (cd * drag_area) / max(10.0, spacecraft_mass)  # Cd*A/m; the EOM applies the 1/2
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
            engine = ThirdReviewEngine(y0, epoch=initial_epoch)
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
                cr_area_over_m=cr_area_over_m,
                fixed_step=_get_float_param(params, 'step_s', 0.0) or None
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
                    autonomous_mode=True,
                    r_vec=pos_arr[idx],
                    v_vec=vel_arr[idx]
                ))
                cert: dict[str, Any] = cast(dict[str, Any], controller.generate_safety_certificate(idx // 150 + 1, sol, mode_info))
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

            time_engine = TimeStandardEngine(epoch=initial_epoch)
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

            # Advanced Innovations Calculations
            rad_opt = RadiationParetoOptimizer()
            pareto_data = rad_opt.evaluate_pareto_frontier(initial_perigee_km=max(150.0, a_km * (1.0 - e) - r_earth_km), apogee_km=max(1000.0, a_km * (1.0 + e) - r_earth_km))

            pumping_planner = MultiBurnPerigeePumpingPlanner(thrust_newtons=450.0, isp_sec=315.0)
            pumping_data = pumping_planner.plan_perigee_pumping(
                r_perigee_km=a_km * (1.0 - e),
                initial_apogee_km=a_km * (1.0 + e),
                target_apogee_km=384400.0,
                wet_mass_kg=spacecraft_mass,
                num_burns=5
            )

            constellation_engine = MolniyaConstellationEngine(semi_major_axis_km=a_km, eccentricity=e, inclination_deg=inc_deg)
            constellation_data = constellation_engine.propagate_constellation(duration_hours=min(24.0, num_orbits * (period / 3600.0)))

            steered_cov_ctrl = CovarianceSteeredAdaptiveStepController(base_tolerance=tol)
            phi_mat = np.eye(6) * (1.0 + float(np.random.uniform(0.01, 0.04)))
            p_mat = np.diag([100.0, 100.0, 100.0, 0.01, 0.01, 0.01])
            cov_steering_data = steered_cov_ctrl.compute_covariance_steered_step_factor(phi_mat, p_mat)

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
                "innovations_suite": {
                    "ecr_mf_certificates": certificates,
                    "radiation_pareto": pareto_data,
                    "multi_burn_perigee_pumping": pumping_data,
                    "molniya_constellation_handover": constellation_data,
                    "covariance_steered_stepping": cov_steering_data
                },
                "fsw_subsystems": fsw_telemetry_payload,
                "script_workbench": script_workbench_payload,
                "benchmark_summary": HEOBenchmarkSuite().generate_benchmark_report(),
                "ecr_mf_certificates": certificates
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
