@echo off
cd /d "%~dp0silice"
call run.bat %*
exit /b %ERRORLEVEL%
