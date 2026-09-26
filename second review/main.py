"""
AstroFlyer HEO - Second Review Standalone Offline Desktop Application Launcher
Part of Major Project: Precise Trajectory Propagation and Events Prediction for Highly Eccentric Orbits
ACS College of Engineering - Aerospace Engineering Department
"""

import os
import sys
import threading
import time
import argparse
import webbrowser

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from backend.app_server import run_server


def start_desktop_application(port=8002):
    print("=" * 80)
    print("      ASTROFLYER HEO - SECOND REVIEW OFFLINE DESKTOP STUDIO")
    print("      ACS College of Engineering | Aerospace Engineering Major Project")
    print("=" * 80)
    print(f"[*] Initializing local astrodynamics micro-kernel daemon on port {port}...")
    
    server_thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    server_thread.start()
    time.sleep(0.6)
    
    try:
        import webview
        print("[*] Launching native Windows desktop application window (WebView2 engine)...")
        window = webview.create_window(
            title="AstroFlyer HEO - Flight Dynamics Studio (Second Review: Event Certification)",
            url=f"http://localhost:{port}",
            width=1440,
            height=920,
            min_size=(1024, 700),
            text_select=True,
            confirm_close=False
        )
        webview.start(debug=False)
    except Exception as e:
        print(f"[!] Desktop window manager notice: {e}")
        print("[*] Falling back to default desktop view...")
        webbrowser.open(f"http://localhost:{port}")
        server_thread.join()


def main():
    parser = argparse.ArgumentParser(description="AstroFlyer HEO Second Review Desktop Launcher")
    parser.add_argument('--port', type=int, default=8002, help="Internal port for offline daemon")
    parser.add_argument('--pdf', action='store_true', help="Re-generate Technical Handbook PDF")
    parser.add_argument('--browser', action='store_true', help="Open in browser instead of desktop window")
    args = parser.parse_args()
    
    if args.pdf:
        from scripts.generate_review_pdf import build_pdf
        build_pdf()
    elif args.browser:
        server_thread = threading.Thread(target=run_server, args=(args.port,), daemon=True)
        server_thread.start()
        time.sleep(0.5)
        webbrowser.open(f"http://localhost:{args.port}")
        server_thread.join()
    else:
        start_desktop_application(port=args.port)


if __name__ == '__main__':
    main()
