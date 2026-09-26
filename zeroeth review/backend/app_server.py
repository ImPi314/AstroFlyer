"""
AstroCore Backend Server - Zeroeth Review REST API & Web Server
Serves static frontend files and exposes high-precision astrodynamics telemetry endpoints.
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

from core.astro_engine import MU_EARTH, R_EARTH, keplerian_to_cartesian, TrajectoryEngine, get_engine_status
from backend.ecr_mf_controller import ECRMFController


class AstroAppHandler(SimpleHTTPRequestHandler):
    """
    Custom HTTP Request Handler serving the Web Frontend and JSON REST API.
    """
    def __init__(self, *args, **kwargs):
        candidate_frontend_dirs = [
            os.path.join(parent_dir, "frontend"),
            os.path.join(os.path.dirname(sys.executable), "frontend"),
            os.path.join(os.path.dirname(sys.executable), "_internal", "frontend"),
            os.path.join(getattr(sys, '_MEIPASS', ''), "frontend")
        ]
        frontend_dir = next((d for d in candidate_frontend_dirs if os.path.exists(d)), candidate_frontend_dirs[0])
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

    def handle_api(self, path, params):
        if path == "/api/manifest" or path == "/api/architecture":
            candidate_manifest_paths = [
                os.path.join(parent_dir, "datasources", "gto_manifest.json"),
                os.path.join(os.path.dirname(sys.executable), "datasources", "gto_manifest.json"),
                os.path.join(os.path.dirname(sys.executable), "_internal", "datasources", "gto_manifest.json"),
                os.path.join(getattr(sys, '_MEIPASS', ''), "datasources", "gto_manifest.json")
            ]
            manifest_path = next((p for p in candidate_manifest_paths if os.path.exists(p)), candidate_manifest_paths[0])
            if os.path.exists(manifest_path):
                with open(manifest_path, 'r') as f:
                    data = json.load(f)
            else:
                data = {"status": "success"}
            
            engine_status = get_engine_status()
            data["architecture"] = {
                "layer_1_math_core": {
                    "layer": "Layer 1 (The Math Core)",
                    "title": "Compiled C++17 SIMD/AVX-2 Astrodynamics Core",
                    "status": "ONLINE_ACCELERATED" if engine_status["c_plus_plus_kernel_loaded"] else "FALLBACK_NUMPY",
                    "binary_loaded": engine_status["c_plus_plus_kernel_loaded"],
                    "binary_path": engine_status["kernel_binary"],
                    "standard": engine_status["standard"],
                    "specifications": [
                        "Deterministic Numerical Integration",
                        "High-Precision Coordinate Conversions (Keplerian <-> Cartesian ECI)",
                        "SIMD/AVX-2 Vector Perturbation Accelerations (Two-Body + J2 Oblateness)",
                        "Secular Drift Rates via Lagrange Planetary Equations"
                    ]
                },
                "layer_2_control_pipeline": {
                    "layer": "Layer 2 (The Control / Telemetry Pipeline)",
                    "title": "Python Stiff Radau-IIA & ECR-MF Controller",
                    "status": "ONLINE_ACTIVE",
                    "specifications": [
                        "Mission Sequencing & Event Invariant Monitoring",
                        "Real-Time Telemetry Serialization & State Validation",
                        "Deterministic Mode with Stiff Implicit Radau-IIA Step-Control",
                        "Adaptive Autonomous Mode with Energy Trust Bounds & Invariant Guardrails",
                        "CERT-ECRMF Machine-Readable Cryptographic Safety Certificates"
                    ]
                },
                "layer_3_operator_console": {
                    "layer": "Layer 3 (The Operator Console)",
                    "title": "Hardware-Accelerated 60 FPS Desktop Flight Studio",
                    "status": "ONLINE_READY",
                    "specifications": [
                        "Native Canvas/WebGL Real-Time Orbit & Ground Track Projection (NASA OpenMCT / SpaceX standard)",
                        "Interactive COE Orbital Parameter Sliders & Time Scrubbing",
                        "100% Offline Standalone Windows Executable (.exe)",
                        "Microsoft Office-Style Windows Setup Installer (Inno Setup 6)"
                    ]
                }
            }
            resp_bytes = json.dumps(data).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(resp_bytes)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(resp_bytes)

        elif path == "/api/telemetry" or path == "/api/propagate":
            # Parse parameters or use default GTO
            a_km = float(params.get('a', [24389.0])[0])
            e = float(params.get('e', [0.728525])[0])
            inc = float(params.get('inc', [28.5])[0])
            raan = float(params.get('raan', [45.0])[0])
            argp = float(params.get('argp', [30.0])[0])
            nu = float(params.get('nu', [0.0])[0])
            orbits = float(params.get('orbits', [5.0])[0])
            autonomous_mode = params.get('autonomous_mode', ['true'])[0].lower() in ['true', '1', 'yes']
            
            a_m = a_km * 1000.0
            inc_rad = np.radians(inc)
            raan_rad = np.radians(raan)
            argp_rad = np.radians(argp)
            nu_rad = np.radians(nu)
            
            r0, v0 = keplerian_to_cartesian(a_m, e, inc_rad, raan_rad, argp_rad, nu_rad)
            y0 = np.concatenate([r0, v0])
            
            engine = TrajectoryEngine(y0)
            period_sec = 2.0 * np.pi * np.sqrt(a_m**3 / MU_EARTH)
            t_span = (0.0, orbits * period_sec)
            
            sol = engine.propagate(t_span, num_points=1500, model='j2', method='Radau')
            
            # Format payload for JSON response
            controller = ECRMFController()
            n_pts = len(sol['times'])
            certificates = []
            
            for idx in [0, n_pts//4, n_pts//2, 3*n_pts//4, n_pts-1]:
                mode_info = controller.evaluate_segment_mode(
                    sol['altitude_km'][idx],
                    sol['velocity_kms'][idx],
                    sol['true_anomaly_deg'][idx],
                    autonomous_mode=autonomous_mode
                )
                cert = controller.generate_safety_certificate(idx // 150 + 1, sol, mode_info)
                certificates.append(cert)
                
            payload = {
                "status": "success",
                "review_stage": "Zeroeth Review",
                "total_points": n_pts,
                "orbital_period_hours": period_sec / 3600.0,
                "math_core_status": get_engine_status(),
                "architecture_summary": {
                    "layer_1": "Compiled C++17 Astrodynamics Kernel (MSVC x64 /O2 SIMD)",
                    "layer_2": "ECR-MF Adaptive Autonomous Controller (Radau-IIA)",
                    "layer_3": "Hardware-Accelerated 60 FPS Desktop Console"
                },
                "times_sec": sol['times'].tolist(),
                "positions_m": sol['position_m'].tolist(),
                "velocities_ms": sol['velocity_ms'].tolist(),
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
                "ecr_mf_certificates": certificates
            }
            
            resp_bytes = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(resp_bytes)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(resp_bytes)
        else:
            err_bytes = json.dumps({"status": "404", "message": "API endpoint not found"}).encode("utf-8")
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(err_bytes)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(err_bytes)


def run_server(port=8000):
    server_address = ('', port)
    httpd = HTTPServer(server_address, AstroAppHandler)
    print(f"==========================================================================")
    print(f" ASTROFLYER HEO - ZEROETH REVIEW WEB APP SERVER RUNNING")
    print(f" Serving Frontend UI & REST API at: http://localhost:{port}")
    print(f"==========================================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()


if __name__ == '__main__':
    run_server(port=8000)
