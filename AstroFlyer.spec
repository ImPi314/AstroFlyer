# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Spec File for AstroFlyer HEO Standalone Desktop Application
Aerospace Engineering Major Project - ACS College of Engineering
"""

import os
import sys

block_cipher = None
project_root = os.path.abspath(os.getcwd())

datas = [
    (os.path.join(project_root, 'astroflyer', 'frontend'), os.path.join('astroflyer', 'frontend')),
    (os.path.join(project_root, 'astroflyer', 'datasources'), os.path.join('astroflyer', 'datasources')),
    (os.path.join(project_root, 'astroflyer', 'data'), os.path.join('astroflyer', 'data')),
    (os.path.join(project_root, 'astroflyer', 'figures'), os.path.join('astroflyer', 'figures')),
    (os.path.join(project_root, 'astroflyer', 'cpp_engine'), os.path.join('astroflyer', 'cpp_engine')),
    (os.path.join(project_root, 'astroflyer', 'icon.ico'), 'astroflyer'),
    (os.path.join(project_root, 'astroflyer', 'THIRD_REVIEW_COMPLETE_PROJECT_GUIDE.pdf'), 'astroflyer'),
]

binaries = [
    (os.path.join(project_root, 'astroflyer', 'cpp_engine', 'astro_physics_kernel.dll'), os.path.join('astroflyer', 'cpp_engine')),
    (os.path.join(project_root, 'astroflyer', 'cpp_engine', 'astro_physics_kernel.dll'), '.'),
]

hiddenimports = [
    'webview',
    'webview.platforms.winforms',
    'ctypes',
    'numpy',
    'scipy',
    'scipy.integrate',
    'scipy.spatial.transform',
    'matplotlib',
    'reportlab',
    'reportlab.lib',
    'reportlab.platypus',
    'reportlab.pdfgen',
    'astroflyer',
    'astroflyer.backend',
    'astroflyer.backend.app_server',
    'astroflyer.backend.astro_engine',
    'astroflyer.backend.ecr_mf_controller',
    'astroflyer.backend.event_predictor',
    'astroflyer.backend.benchmark_comparison',
    'astroflyer.backend.trajectory_engine',
    'astroflyer.backend.fsw_subsystems',
    'astroflyer.backend.time_systems',
    'astroflyer.backend.radiation_belts',
    'astroflyer.backend.covariance_engine',
    'astroflyer.backend.differential_corrector',
    'astroflyer.backend.constellation_engine',
    'astroflyer.backend.ccsds_exporter',
    'astroflyer.backend.mission_plan_io',
    'astroflyer.core',
    'astroflyer.core.mission_plan_io',
]

a = Analysis(
    ['main.py'],
    pathex=[project_root, os.path.join(project_root, 'astroflyer')],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'unittest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

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
    icon=os.path.join(project_root, 'astroflyer', 'icon.ico'),
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
