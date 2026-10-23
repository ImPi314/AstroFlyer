@echo off
setlocal
echo ==============================================================================
echo   ASTROFLYER HEO - COMPILING C++17 ASTRODYNAMICS CORE (MSVC x64)
echo ==============================================================================

set VCVARS="C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsall.bat"
if not exist %VCVARS% (
    echo [!] vcvarsall.bat not found at default location. Searching...
    for /d %%i in ("C:\Program Files\Microsoft Visual Studio\*") do (
        for /d %%j in ("%%i\*") do (
            if exist "%%j\VC\Auxiliary\Build\vcvarsall.bat" set VCVARS="%%j\VC\Auxiliary\Build\vcvarsall.bat"
        )
    )
)

echo [*] Initializing Visual Studio build environment: %VCVARS%
call %VCVARS% x64

cd /d "%~dp0"
echo [*] Compiling astro_physics.cpp into native 64-bit DLL (C++17, O2 Optimization)...
rem /MT links the C++ runtime statically, so the DLL runs on PCs without the MSVC redistributable
cl /O2 /MT /std:c++17 /LD /EHsc astro_physics.cpp /Fe:astro_physics_kernel.dll

if %ERRORLEVEL% equ 0 (
    echo [SUCCESS] C++17 Astrodynamics Kernel successfully compiled to:
    echo           %~dp0astro_physics_kernel.dll
) else (
    echo [!] Compilation failed with error level %ERRORLEVEL%
)
endlocal
