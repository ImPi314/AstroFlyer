@echo off
title AstroFlyer HEO - Offline Desktop Flight Dynamics Studio
echo ==============================================================================
echo    ASTROFLYER HEO - OFFLINE STANDALONE DESKTOP FLIGHT DYNAMICS STUDIO
echo    ACS College of Engineering - Aerospace Engineering Major Project
echo ==============================================================================
echo.
echo [*] Launching 100%% Offline Standalone Desktop Executable...
echo.

if exist "%~dp0dist\AstroFlyer_HEO_Studio\AstroFlyer_HEO_Studio.exe" (
    start "" "%~dp0dist\AstroFlyer_HEO_Studio\AstroFlyer_HEO_Studio.exe"
    exit
) else (
    echo [!] Standalone binary not found in dist. Launching via Python Desktop Launcher...
    python "%~dp0zeroeth review\main.py"
)
