"""
AstroFlyer HEO - Automated Desktop Application & Windows Installer Compiler
Compiles the offline desktop suite into a standalone native .exe binary and packages it into
a Microsoft Office-style Windows Setup Wizard Installer (.exe).
"""

import os
import sys
import shutil
import subprocess

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
inno_compiler = r"C:\Users\Harshith\AppData\Local\Programs\Inno Setup 6\ISCC.exe"
pyinstaller_exe = r"C:\Users\Harshith\AppData\Roaming\Python\Python314\Scripts\pyinstaller.exe"

if not os.path.exists(pyinstaller_exe):
    # Try finding in PATH
    pyinstaller_exe = shutil.which("pyinstaller") or "pyinstaller"

print("=" * 80)
print("   ASTROFLYER HEO - DESKTOP .EXE & WINDOWS SETUP BUILD SYSTEM")
print("=" * 80)

def step_1_build_pyinstaller():
    print("\n[STEP 1/3] Compiling Python Astrodynamics Suite into Standalone Native .EXE...")
    entry_point = os.path.join(root_dir, "zeroeth review", "main.py")
    dist_dir = os.path.join(root_dir, "dist")
    build_dir = os.path.join(root_dir, "build")
    
    frontend_src = os.path.join(root_dir, "zeroeth review", "frontend")
    datasources_src = os.path.join(root_dir, "zeroeth review", "datasources")
    backend_src = os.path.join(root_dir, "zeroeth review", "backend")
    
    spec_file = os.path.join(root_dir, "AstroFlyer_HEO_Studio.spec")
    cmd = [
        pyinstaller_exe,
        "--noconfirm",
        spec_file
    ]
    
    print(f"Executing: {' '.join(cmd)}")
    ret = subprocess.run(cmd, cwd=root_dir)
    if ret.returncode != 0:
        print("[!] PyInstaller compilation failed!")
        return False
    print("[+] PyInstaller standalone desktop binary successfully created in dist/AstroFlyer_HEO_Studio!")
    return True

def step_2_build_inno_setup():
    print("\n[STEP 2/3] Compiling Microsoft Office-Style Windows Setup Installer Wizard...")
    iss_file = os.path.join(root_dir, "installer", "AstroFlyer_Installer.iss")
    
    if not os.path.exists(inno_compiler):
        print(f"[!] Inno Setup compiler not found at: {inno_compiler}")
        return False
        
    cmd = [inno_compiler, iss_file]
    print(f"Executing: {' '.join(cmd)}")
    ret = subprocess.run(cmd, cwd=os.path.join(root_dir, "installer"))
    if ret.returncode != 0:
        print("[!] Inno Setup compilation failed!")
        return False
    
    installer_out = os.path.join(root_dir, "dist_installer", "AstroFlyer_HEO_Studio_Setup_v1.0.exe")
    print(f"[+] SUCCESS: Windows Setup Installer generated at:\n    {installer_out}")
    return True

def main():
    os.makedirs(os.path.join(root_dir, "dist_installer"), exist_ok=True)
    # Check if user passed --installer-only
    if "--installer-only" in sys.argv:
        step_2_build_inno_setup()
    else:
        success = step_1_build_pyinstaller()
        if success:
            step_2_build_inno_setup()

if __name__ == '__main__':
    main()
