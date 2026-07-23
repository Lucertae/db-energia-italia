@echo off
cd /d "%~dp0"
if not exist world_clocks.exe (
    echo Compilo...
    call build.bat || exit /b 1
)
start "" "%~dp0world_clocks.exe" --data
