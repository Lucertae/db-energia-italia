@echo off
cd /d "%~dp0.."
start "globe-bridge" /MIN cmd /c "python scripts\globe_bridge.py"
timeout /t 1 /nobreak >nul
cd globe
if not exist node_modules (
  echo npm install...
  call npm install
)
start "globe-vite" /MIN cmd /c "npm run dev -- --host 127.0.0.1 --port 5174"
timeout /t 3 /nobreak >nul
cd ..
python scripts\globe_host.py --url http://127.0.0.1:5174/ %*
