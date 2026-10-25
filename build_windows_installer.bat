@echo off
title AstroFlyer HEO - Desktop Standalone EXE and Installer Builder
echo ==============================================================================
echo    ASTROFLYER HEO - STANDALONE OFFLINE DESKTOP EXE & INSTALLER BUILDER
echo ==============================================================================
echo.
cd /d "%~dp0"
python build_release.py
echo.
pause
