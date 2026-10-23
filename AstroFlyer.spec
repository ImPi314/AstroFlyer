# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for the AstroFlyer HEO offline desktop app (the only spec; build with build_release.py).

Onedir build -> dist/AstroFlyer_HEO/AstroFlyer.exe with runtime files under _internal/astroflyer/.
Ships only what the running app needs: frontend, offline data and the icon. The C++ kernel is retired
(cpp_engine/ sources stay in the repo for reference) and is not bundled.
Dev-only libraries (PDF/report generation, plotting) are excluded; see requirements-dev.txt.
"""

import os
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_dynamic_libs, collect_submodules

project_root = os.path.abspath(os.getcwd())
pkg = os.path.join(project_root, 'astroflyer')

datas = [
    (os.path.join(pkg, 'frontend'), os.path.join('astroflyer', 'frontend')),
    (os.path.join(pkg, 'resources'), os.path.join('astroflyer', 'resources')),
    (os.path.join(pkg, 'datasources'), os.path.join('astroflyer', 'datasources')),
    (os.path.join(pkg, 'data', 'AstroFlyer_HEO_Mission_Plan.MissionPlan'), os.path.join('astroflyer', 'data')),
    (os.path.join(pkg, 'icon.ico'), 'astroflyer'),
]
datas = [d for d in datas if os.path.exists(d[0])]

binaries = []

# pyerfa (leap seconds, EOP interpolation in backend/eop.py) ships a compiled extension
try:
    binaries += collect_dynamic_libs('erfa')
    datas += collect_data_files('erfa')
    erfa_imports = collect_submodules('erfa')
except Exception:
    erfa_imports = []

# pymsis (NRLMSIS drag density) ships a compiled Fortran extension plus .parm data files
try:
    msis_datas, msis_binaries, msis_imports = collect_all('pymsis')
    datas += msis_datas
    binaries += msis_binaries
    erfa_imports += msis_imports
except Exception:
    print('[!] pymsis not installed; drag will use the fallback atmosphere.')

# Backend modules are imported both as 'backend.*' (astroflyer/ on sys.path) and 'astroflyer.backend.*'
backend_modules = sorted(
    f[:-3] for f in os.listdir(os.path.join(pkg, 'backend')) if f.endswith('.py') and f != '__init__.py'
)
hiddenimports = (
    ['webview', 'webview.platforms.winforms', 'webview.platforms.edgechromium', 'clr_loader', 'pythonnet',
     'scipy.integrate', 'scipy.spatial.transform', 'astroflyer', 'astroflyer.resource_paths',
     'astroflyer.offline_data', 'resource_paths', 'offline_data', 'jplephem', 'jplephem.spk']
    + [f'backend.{m}' for m in backend_modules]
    + [f'astroflyer.backend.{m}' for m in backend_modules]
    + erfa_imports
)

a = Analysis(
    ['main.py'],
    pathex=[project_root, pkg],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'pytest', 'matplotlib', 'reportlab', 'pandas', 'lxml', 'IPython',
              'PyQt5', 'PyQt6', 'PySide2', 'PySide6'],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AstroFlyer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(pkg, 'icon.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='AstroFlyer_HEO',
)
