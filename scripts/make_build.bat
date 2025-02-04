@echo off
set CURRENT_DIR=%cd%
cd /d "%~dp0"
python make_build.py %*
cd /d "%CURRENT_DIR%"
