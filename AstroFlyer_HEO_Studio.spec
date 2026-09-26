# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['zeroeth review/main.py'],
    pathex=['zeroeth review'],
    binaries=[
        ('zeroeth review/cpp_engine/astro_physics_kernel.dll', 'cpp_engine'),
        ('zeroeth review/cpp_engine/astro_physics_kernel.dll', '.')
    ],
    datas=[
        ('zeroeth review/gui', 'gui'),
        ('zeroeth review/core', 'core'),
        ('zeroeth review/data', 'data'),
        ('zeroeth review/scripts', 'scripts'),
        ('zeroeth review/ZEROETH_REVIEW_COMPLETE_PROJECT_GUIDE.pdf', '.')
    ],
    hiddenimports=[
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtOpenGL',
        'PyQt6.QtOpenGLWidgets',
        'pyqtgraph',
        'pyqtgraph.opengl',
        'OpenGL',
        'OpenGL.GL',
        'OpenGL.GLU',
        'numpy',
        'scipy',
        'scipy.integrate',
        'PIL'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['webview', 'http.server'],
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
