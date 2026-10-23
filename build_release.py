"""
AstroFlyer HEO - Release Build & Installer Packaging Pipeline
Department of Aerospace Engineering, ACS College of Engineering

Orchestrates:
0. Preflight: offline data present (astroflyer/resources/manifest.json)
1. PyInstaller standalone onedir compilation -> dist/AstroFlyer_HEO/AstroFlyer.exe
2. Inno Setup installer compilation -> dist_installer/AstroFlyer_HEO_v1.0_Setup.exe
3. Integrity and checksum verification
"""

import os
import sys
import subprocess
import hashlib
import time

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
ISCC_CANDIDATE_PATHS = [
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Inno Setup 6", "ISCC.exe"),
    r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    r"C:\Program Files\Inno Setup 6\ISCC.exe",
]
ISCC_PATH = next((p for p in ISCC_CANDIDATE_PATHS if os.path.exists(p)), None)


def compute_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def preflight():
    """Stops the build when a required runtime file is missing; warns about optional ones."""
    ok = True
    if sys.version_info >= (3, 14):
        print("[!] Python 3.14+: check that pythonnet (pywebview's WebView2 backend) installs; 3.12/3.13 are safest.")
    sys.path.insert(0, os.path.join(PROJECT_ROOT, "astroflyer"))
    import offline_data
    for item in offline_data.data_status():
        if item["present"]:
            print(f"      [+] {item['file']} (valid until {item['valid_until']})")
        elif item["required"]:
            print(f"[ERROR] Required offline data missing: astroflyer/resources/{item['file']}")
            ok = False
        else:
            print(f"      [-] Optional {item['file']} not bundled (python tools/fetch_offline_data.py)")
    redist = os.path.join(PROJECT_ROOT, "installer", "redist", "MicrosoftEdgeWebView2RuntimeInstallerX64.exe")
    if not os.path.exists(redist):
        print("      [-] No offline WebView2 installer in installer/redist/; setup will ask users without WebView2 to install it.")
    return ok


def main():
    print("=" * 80)
    print("      ASTROFLYER HEO - STANDALONE EXE & INSTALLER BUILD PIPELINE")
    print("      Department of Aerospace Engineering | ACS College of Engineering")
    print("=" * 80)
    start_time = time.time()

    print("\n[*] [0/3] Preflight checks...")
    if not preflight():
        sys.exit(1)

    # Step 1: Ensure PDF is generated and up to date
    pdf_path = os.path.join(PROJECT_ROOT, "THIRD_REVIEW_COMPLETE_PROJECT_GUIDE.pdf")
    if not os.path.exists(pdf_path):
        print("\n[*] [1/3] Generating publication-grade Technical Handbook PDF...")
        # Needs the dev requirements (reportlab); the handbook ships beside the app, not inside it
        if subprocess.run([sys.executable, "main.py", "--pdf"], cwd=PROJECT_ROOT).returncode != 0:
            print("[!] PDF generation failed (pip install -r requirements-dev.txt); continuing without it.")
    else:
        print("\n[*] [1/3] Technical Handbook PDF verified.")

    # Step 2: Run PyInstaller to build standalone desktop application
    print("\n[*] [2/3] Building Standalone Windows Desktop Application with PyInstaller...")
    spec_path = os.path.join(PROJECT_ROOT, "AstroFlyer.spec")
    pyinstaller_cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", spec_path]
    res = subprocess.run(pyinstaller_cmd, cwd=PROJECT_ROOT)
    if res.returncode != 0:
        print("\n[ERROR] PyInstaller build failed!")
        sys.exit(1)

    exe_path = os.path.join(PROJECT_ROOT, "dist", "AstroFlyer_HEO", "AstroFlyer.exe")
    if not os.path.exists(exe_path):
        print(f"\n[ERROR] Output executable not found at: {exe_path}")
        sys.exit(1)

    exe_size_mb = os.path.getsize(exe_path) / (1024 * 1024)
    print(f"      [+] Standalone Executable generated successfully: {exe_path} ({exe_size_mb:.2f} MB)")

    # Step 3: Run Inno Setup Compiler to create the installer
    print("\n[*] [3/3] Compiling Inno Setup Windows Installer Package...")
    if not ISCC_PATH or not os.path.exists(ISCC_PATH):
        print(f"[!] Warning: ISCC.exe not found at standard locations. Checked: {ISCC_CANDIDATE_PATHS}")
        print("[!] Standalone executable in dist/AstroFlyer_HEO is ready, but installer compilation skipped.")
        return

    iss_path = os.path.join(PROJECT_ROOT, "installer", "AstroFlyer_Installer.iss")
    iscc_cmd = [ISCC_PATH, "/Qp", iss_path]
    res_iscc = subprocess.run(iscc_cmd, cwd=os.path.join(PROJECT_ROOT, "installer"))
    if res_iscc.returncode != 0:
        print("\n[ERROR] Inno Setup compilation failed!")
        sys.exit(1)

    installer_path = os.path.join(PROJECT_ROOT, "dist_installer", "AstroFlyer_HEO_v1.0_Setup.exe")
    if not os.path.exists(installer_path):
        print(f"\n[ERROR] Installer output not found at: {installer_path}")
        sys.exit(1)

    inst_size_mb = os.path.getsize(installer_path) / (1024 * 1024)
    inst_hash = compute_sha256(installer_path)

    elapsed = time.time() - start_time
    print("\n" + "=" * 80)
    print("      BUILD & PACKAGING COMPLETE - ALL TARGETS READY")
    print("=" * 80)
    print(f"  [+] Standalone Executable: {exe_path}")
    print(f"  [+] Windows Installer    : {installer_path}")
    print(f"  [+] Installer Size       : {inst_size_mb:.2f} MB")
    print(f"  [+] SHA-256 Checksum     : {inst_hash}")
    print(f"  [+] Total Build Time     : {elapsed:.1f} seconds")
    print("=" * 80)


if __name__ == "__main__":
    main()
