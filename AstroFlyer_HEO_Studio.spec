# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['astroflyer/main.py'],
    pathex=['astroflyer'],
    binaries=[
        ('astroflyer/cpp_engine/astro_physics_kernel.dll', 'cpp_engine'),
        ('astroflyer/cpp_engine/astro_physics_kernel.dll', '.')
    ],
    datas=[
        ('astroflyer/backend', 'backend'),
        ('astroflyer/frontend', 'frontend'),
        ('astroflyer/scripts', 'scripts'),
        ('astroflyer/figures', 'figures'),
        ('astroflyer/THIRD_REVIEW_COMPLETE_PROJECT_GUIDE.pdf', '.')
    ],
    hiddenimports=[
        'webview',
        'numpy',
        'scipy',
        'scipy.integrate',
        'http.server',
        'PIL'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AstroFlyer_HEO_Studio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AstroFlyer_HEO_Studio',
)
