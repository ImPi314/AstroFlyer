"""
AstroFlyer HEO - Offline desktop application launcher
Part of Major Project: Precise Trajectory Propagation and Events Prediction for Highly Eccentric Orbits
ACS College of Engineering - Aerospace Engineering Department
"""

import os
import sys
import threading
import argparse
import webbrowser

# A windowed PyInstaller exe has no console, so sys.stdout/sys.stderr are None and any write
# (http.server logs every request to stderr) raises and drops the connection.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from backend.app_server import create_server, run_server


def start_server_thread(port=8003):
    """Binds 127.0.0.1 before returning, so the window never opens on a server that isn't listening.
    Keeps the fixed port when it's free (stable origin, so browser storage persists) and falls back to
    an OS-chosen free port when it's busy."""
    try:
        httpd = create_server(port)
    except OSError:
        print(f"[!] Port {port} is busy; using a free port instead.")
        httpd = create_server(0)
    server_thread = threading.Thread(target=run_server, kwargs={"httpd": httpd}, daemon=True)
    server_thread.start()
    return server_thread, httpd.server_address[1]


def warm_up_models():
    """Compiles the Numba drag model (NRLMSISE-00, ~9 s the first time in a process) on a background
    thread, so the first propagation with drag doesn't stall. Failures are recorded, never raised."""
    def run():
        try:
            from backend import forces
            forces.atmospheric_density(0.0, 0.5, 1.0, 400e3, 150.0, 150.0, 15.0)
            thread.ok = True
        except Exception as exc:
            thread.error = repr(exc)

    thread = threading.Thread(target=run, name="model-warm-up", daemon=True)
    thread.ok = False
    thread.error = None
    thread.start()
    return thread


def configure_offline_webview():
    """Stops WebView2's own background traffic to Microsoft (SmartScreen checks, component updates,
    telemetry), so the window talks only to the local server. WebView2 reads this variable when it
    starts; Chromium honours a single --disable-features list, so pywebview's ElasticOverscroll is kept in it.
    Edge services the flags don't reach still need a host name, and the UI (served from 127.0.0.1) needs
    none, so every name lookup is refused except localhost and 127.0.0.1 (MAP * also matches IP literals)."""
    os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = " ".join([
        "--disable-background-networking",
        "--disable-component-update",
        "--disable-domain-reliability",
        "--disable-sync",
        "--no-pings",
        "--disable-features=ElasticOverscroll,msSmartScreenProtection,OptimizationHints,Translate,"
        "AutofillServerCommunication,MediaRouter",
        '--host-resolver-rules="MAP * ~NOTFOUND , EXCLUDE localhost , EXCLUDE 127.0.0.1"',
    ])


def start_desktop_application(port=8003):
    print("=" * 80)
    print("      ASTROFLYER HEO - FLIGHT DYNAMICS & TRAJECTORY ANALYSIS STUDIO")
    print("      ACS College of Engineering | Aerospace Engineering Major Project")
    print("=" * 80)
    server_thread, port = start_server_thread(port)
    warm_up_models()
    print(f"[*] Local astrodynamics micro-kernel daemon listening on 127.0.0.1:{port}")
    
    try:
        import webview
        configure_offline_webview()
        print("[*] Launching native Windows desktop application window (WebView2 engine)...")
        webview.settings['ALLOW_DOWNLOADS'] = True   # plots save as PNG through the window's download dialog
        window = webview.create_window(
            title="AstroFlyer HEO - Flight Dynamics & Trajectory Operations Studio",
            url=f"http://127.0.0.1:{port}",
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
        webbrowser.open(f"http://127.0.0.1:{port}")
        server_thread.join()


def main():
    parser = argparse.ArgumentParser(description="AstroFlyer HEO desktop launcher")
    parser.add_argument('--port', type=int, default=8003, help="Internal port for offline daemon (falls back to a free port if busy)")
    parser.add_argument('--browser', action='store_true', help="Open in browser instead of desktop window")
    args = parser.parse_args()
    
    if args.browser:
        server_thread, port = start_server_thread(args.port)
        warm_up_models()
        webbrowser.open(f"http://127.0.0.1:{port}")
        server_thread.join()
    else:
        start_desktop_application(port=args.port)


if __name__ == '__main__':
    main()
