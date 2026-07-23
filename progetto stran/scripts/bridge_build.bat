@echo off
cd /d "%~dp0"
echo [1/3] spine codegen...
python scripts\spine_codegen.py
if %ERRORLEVEL% NEQ 0 exit /b 1
echo [2/3] spine build + bridge modules...
python scripts\spine_build.py
if %ERRORLEVEL% NEQ 0 exit /b 1
echo [3/3] done.
exit /b 0
