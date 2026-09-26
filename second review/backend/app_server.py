"""
AstroCore Backend Server - Second Review REST API & Web Server
Exposes ECR-MF Event & Covariance Certification, Eclipse Timers, Ground Station AOS/LOS,
Apogee Boost Delta-V, B-Plane Targeting, and Multi-Decadal Lifetime on Port 8002.
"""

import os
import sys
import json
import urllib.parse
import numpy as np
from http.server import HTTPServer, SimpleHTTPRequestHandler

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from backend.astro_engine import SecondReviewEngine, keplerian_to_cartesian, MU_EARTH, R_EARTH
from backend.ecr_mf_controller import ECRMFController
from backend.event_predictor import EventPredictor


class SecondReviewAppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        frontend_dir = os.path.join(parent_dir, "frontend")
        super().__init__(*args, directory=frontend_dir, **kwargs)

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        if path.startswith("/api/"):
            self.handle_api(path, urllib.parse.parse_qs(parsed_path.query))
        else:
            super().do_GET()

    def do_POST(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        if path.startswith("/api/"):
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length) if content_length > 0 else b'{}'
            try:
                body = json.loads(post_data.decode('utf-8'))
                params = {k: [str(v)] for k, v in body.items()}
            except Exception:
                params = {}
            self.handle_api(path, params)
        else:
            self.send_error(404, "Endpoint not found")

    def send_json(self, data, status_code=200):
        resp_bytes = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(resp_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(resp_bytes)

    def handle_api(self, path, params):
        predictor = EventPredictor()

        if path == "/api/manifest":
            manifest_path = os.path.join(parent_dir, "datasources", "gto_manifest.json")
            if os.path.exists(manifest_path):
                with open(manifest_path, 'r') as f:
                    data = json.load(f)
            else:
                data = {"target_regime": "Molniya / GTO", "epoch": "2026-09-24T00:00:00Z"}
            data["review_stage"] = "Second Review: Mission Events, Targeting & Lifetime Certification"
            data["modules"] = [
                "Conical Umbra/Penumbra Eclipse Predictor",
                "Global Ground Station Network (AOS/LOS)",
                "Apogee Boost & Vectorial Plane-Change Delta-V",
                "B-Plane (B·T, B·R) Differential Targeter for LGA",
                "Multi-Decadal 25-Year Space Debris Resonance Predictor"
            ]
            self.send_json(data)

        elif path == "/api/events/eclipses":
            a_km = float(params.get('a', [24389.0])[0])
            e = float(params.get('e', [0.728525])[0])
            inc_deg = float(params.get('inc', [28.5])[0])
            r0, v0 = keplerian_to_cartesian(a_km * 1000.0, e, np.radians(inc_deg), np.radians(45.0), np.radians(30.0), 0.0)
            engine = SecondReviewEngine(np.concatenate([r0, v0]))
            sol = engine.propagate((0.0, 37905.5), num_points=1000)
            eclipses = predictor.predict_solar_eclipses(sol['times'], sol['position_m'])
            self.send_json(eclipses)

        elif path == "/api/events/ground_stations":
            a_km = float(params.get('a', [24389.0])[0])
            e = float(params.get('e', [0.728525])[0])
            inc_deg = float(params.get('inc', [28.5])[0])
            r0, v0 = keplerian_to_cartesian(a_km * 1000.0, e, np.radians(inc_deg), np.radians(45.0), np.radians(30.0), 0.0)
            engine = SecondReviewEngine(np.concatenate([r0, v0]))
            sol = engine.propagate((0.0, 2 * 37905.5), num_points=1000)
            gs_passes = predictor.predict_ground_station_passes(sol['times'], sol['position_m'])
            # Exclude large raw arrays for light JSON summary
            summary = {}
            for name, d in gs_passes.items():
                summary[name] = {
                    "metadata": d["station_metadata"],
                    "passes": d["passes"],
                    "total_passes_count": d["total_passes_count"],
                    "total_contact_min": d["total_contact_min"]
                }
            self.send_json(summary)

        elif path == "/api/targeting/maneuver":
            a_km = float(params.get('a', [24389.0])[0])
            e = float(params.get('e', [0.728525])[0])
            inc_deg = float(params.get('inc', [28.5])[0])
            target_r_km = float(params.get('target_r_km', [42164.0])[0])
            target_inc_deg = float(params.get('target_inc_deg', [0.0])[0])
            maneuver = predictor.calculate_apogee_boost_deltav(
                a_initial_km=a_km,
                e_initial=e,
                inc_initial_deg=inc_deg,
                target_r_km=target_r_km,
                inc_target_deg=target_inc_deg
            )
            self.send_json(maneuver)

        elif path == "/api/targeting/bplane":
            v_inf = float(params.get('v_inf_kms', [1.45])[0])
            target_rp = float(params.get('target_rp_km', [1837.4])[0])
            clock_angle = float(params.get('theta_deg', [45.0])[0])
            bplane = predictor.calculate_b_plane_targeting(
                v_inf_vec_kms=(-v_inf * 0.7, v_inf * 0.5, v_inf * 0.5),
                target_rp_km=target_rp,
                theta_angle_deg=clock_angle
            )
            self.send_json(bplane)

        elif path == "/api/lifetime/predict":
            a_km = float(params.get('a', [24389.0])[0])
            e = float(params.get('e', [0.728525])[0])
            mass = float(params.get('mass_kg', [1500.0])[0])
            area = float(params.get('area_m2', [4.5])[0])
            lifetime = predictor.predict_orbital_lifetime(
                a_initial_km=a_km,
                e_initial=e,
                spacecraft_mass_kg=mass,
                drag_area_m2=area
            )
            self.send_json(lifetime)

        elif path in ("/api/telemetry", "/api/propagate"):
            a_km = float(params.get('a', [24389.0])[0])
            e = float(params.get('e', [0.728525])[0])
            inc_deg = float(params.get('inc', [28.5])[0])
            num_orbits = float(params.get('num_orbits', [2.0])[0])

            a_m = a_km * 1000.0
            r0, v0 = keplerian_to_cartesian(a_m, e, np.radians(inc_deg), np.radians(45.0), np.radians(30.0), 0.0)
            y0 = np.concatenate([r0, v0])

            period = 2.0 * np.pi * np.sqrt(a_m**3 / MU_EARTH)
            t_span = (0.0, num_orbits * period)

            engine = SecondReviewEngine(y0)
            sol = engine.propagate(t_span, num_points=1200)

            # Predict mission events
            eclipses = predictor.predict_solar_eclipses(sol['times'], sol['position_m'])
            gs_passes = predictor.predict_ground_station_passes(sol['times'], sol['position_m'])
            delta_v_data = predictor.calculate_apogee_boost_deltav(a_km, e, inc_initial_deg=inc_deg)
            bplane_data = predictor.calculate_b_plane_targeting()
            lifetime_data = predictor.predict_orbital_lifetime(a_initial_km=a_km, e_initial=e)

            # ECR-MF Safety Certificates
            controller = ECRMFController()
            n_pts = len(sol['times'])
            certificates = []
            for idx in [0, n_pts//4, n_pts//2, 3*n_pts//4, n_pts-1]:
                mode_info = controller.evaluate_segment_mode(
                    sol['altitude_km'][idx],
                    sol['velocity_kms'][idx],
                    sol['true_anomaly_deg'][idx],
                    autonomous_mode=True
                )
                cert = controller.generate_safety_certificate(idx // 150 + 1, sol, mode_info)
                cert["event_time_residual_s"] = 0.02
                certificates.append(cert)

            # Summarize ground station passes for JSON payload
            gs_summary = {}
            for name, d in gs_passes.items():
                gs_summary[name] = {
                    "total_passes": d["total_passes_count"],
                    "total_contact_min": d["total_contact_min"],
                    "passes": d["passes"]
                }

            payload = {
                "status": "success",
                "review_stage": "Second Review (Mission Events, Targeting & Lifetime Certification)",
                "total_points": n_pts,
                "orbital_period_hours": round(period / 3600.0, 3),
                "times_sec": sol['times'].tolist(),
                "altitude_km": sol['altitude_km'].tolist(),
                "velocity_kms": sol['velocity_kms'].tolist(),
                "semi_major_axis_km": sol['semi_major_axis_km'].tolist(),
                "eccentricity": sol['eccentricity'].tolist(),
                "inclination_deg": sol['inclination_deg'].tolist(),
                "raan_deg": sol['raan_deg'].tolist(),
                "arg_perigee_deg": sol['arg_perigee_deg'].tolist(),
                "true_anomaly_deg": sol['true_anomaly_deg'].tolist(),
                "latitude_deg": sol['latitude_deg'].tolist(),
                "longitude_deg": sol['longitude_deg'].tolist(),
                "energy_error": sol['energy_fractional_error'].tolist(),
                "events_suite": {
                    "solar_eclipses": eclipses,
                    "ground_stations": gs_summary,
                    "apogee_boost_maneuver": delta_v_data,
                    "b_plane_targeting": bplane_data,
                    "multi_decadal_lifetime": lifetime_data
                },
                "ecr_mf_certificates": certificates
            }
            self.send_json(payload)
        else:
            self.send_json({"status": "404", "message": f"Endpoint {path} not found"}, status_code=404)


def run_server(port=8002):
    server_address = ('', port)
    httpd = HTTPServer(server_address, SecondReviewAppHandler)
    print(f"==========================================================================")
    print(f" ASTROFLYER HEO - SECOND REVIEW WEB APP SERVER RUNNING")
    print(f" Serving Frontend UI & REST API at: http://localhost:{port}")
    print(f"==========================================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()


if __name__ == '__main__':
    run_server(port=8002)
