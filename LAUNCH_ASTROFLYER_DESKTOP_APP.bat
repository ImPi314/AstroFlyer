@echo off
title AstroFlyer HEO - Flight Dynamics & Trajectory Analysis Studio
echo ==============================================================================
echo    ASTROFLYER HEO - OFFLINE STANDALONE DESKTOP FLIGHT DYNAMICS STUDIO
echo    ACS College of Engineering - Aerospace Engineering Major Project
echo ==============================================================================
echo.
echo [*] Launching Desktop Application...
echo.

if exist "%~dp0dist\AstroFlyer_HEO\AstroFlyer.exe" (
    start "" "%~dp0dist\AstroFlyer_HEO\AstroFlyer.exe"
    exit
) else (
    echo [*] Launching via Python Desktop Launcher...
    python "%~dp0main.py"
)
