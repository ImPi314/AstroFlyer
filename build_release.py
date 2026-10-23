"""
AstroFlyer HEO - Release Build & Installer Packaging Pipeline
Department of Aerospace Engineering, ACS College of Engineering

Orchestrates:
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


def main():
    print("=" * 80)
    print("      ASTROFLYER HEO - STANDALONE EXE & INSTALLER BUILD PIPELINE")
    print("      Department of Aerospace Engineering | ACS College of Engineering")
    print("=" * 80)
    start_time = time.time()

    # Step 1: Ensure PDF is generated and up to date
    pdf_path = os.path.join(PROJECT_ROOT, "THIRD_REVIEW_COMPLETE_PROJECT_GUIDE.pdf")
    if not os.path.exists(pdf_path):
        print("\n[*] [1/3] Generating publication-grade Technical Handbook PDF...")
        subprocess.run([sys.executable, "main.py", "--pdf"], cwd=PROJECT_ROOT, check=True)
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
