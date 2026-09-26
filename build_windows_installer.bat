@echo off
title AstroFlyer HEO - Desktop Standalone EXE and Installer Builder
echo ==============================================================================
echo    ASTROFLYER HEO - STANDALONE OFFLINE DESKTOP EXE & INSTALLER BUILDER
echo ==============================================================================
echo.
python "%~dp0installer\build_desktop_package.py"
echo.
pause
