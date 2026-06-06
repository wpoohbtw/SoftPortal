@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 > nul

set "ROOT=%~dp0"
set "WORKSPACE_DIR=%ROOT%.."
set "BACKEND_DIR=%ROOT%backend"
set "FRONTEND_DIR=%ROOT%frontend"
set "PNLS_DIR=%WORKSPACE_DIR%\ProfitsNLosses"
set "PNLS_BACKEND_DIR=%PNLS_DIR%\backend"
set "PYTHON_EXE=%BACKEND_DIR%\.venv\Scripts\python.exe"
set "PNLS_PYTHON_EXE=%PNLS_BACKEND_DIR%\.venv\Scripts\python.exe"
set "FRONTEND_PUBLIC=%FRONTEND_DIR%\public"
set "LOGIN_ART_SOURCE=%ROOT%login-art.jpg"
set "LOGIN_ART_TARGET=%FRONTEND_PUBLIC%\login-art.jpg"
set "BACKEND_PORT="
set "FRONTEND_PORT="
set "BACKEND_PID="
set "FRONTEND_PID="
set "PNLS_BACKEND_PORT=8001"
set "PNLS_BACKEND_PID="

call :log INFO "Workspace: %ROOT%"

where python > nul 2> nul
if errorlevel 1 (
  call :log ERROR "Python was not found in PATH."
  exit /b 1
)

where npm > nul 2> nul
if errorlevel 1 (
  call :log ERROR "npm was not found in PATH."
  exit /b 1
)

if not exist "%PYTHON_EXE%" (
  call :log INFO "Creating backend virtualenv..."
  python -m venv "%BACKEND_DIR%\.venv"
  if errorlevel 1 exit /b 1
)

call :log INFO "Checking backend dependencies..."
call "%PYTHON_EXE%" -m pip install --disable-pip-version-check -r "%BACKEND_DIR%\requirements.txt"
if errorlevel 1 exit /b 1

if not exist "%PNLS_DIR%\package.json" (
  call :log ERROR "ProfitsNLosses project was not found at %PNLS_DIR%."
  exit /b 1
)

if not exist "%PNLS_PYTHON_EXE%" (
  call :log INFO "Creating ProfitsNLosses backend virtualenv..."
  python -m venv "%PNLS_BACKEND_DIR%\.venv"
  if errorlevel 1 exit /b 1
)

call :log INFO "Checking ProfitsNLosses backend dependencies..."
call "%PNLS_PYTHON_EXE%" -m pip install --disable-pip-version-check -r "%PNLS_BACKEND_DIR%\requirements.txt"
if errorlevel 1 exit /b 1

if not exist "%FRONTEND_DIR%\node_modules" (
  call :log INFO "Installing frontend dependencies..."
  call npm install --prefix "%FRONTEND_DIR%"
  if errorlevel 1 exit /b 1
)

if not exist "%PNLS_DIR%\node_modules" (
  call :log INFO "Installing ProfitsNLosses frontend dependencies..."
  call npm install --prefix "%PNLS_DIR%"
  if errorlevel 1 exit /b 1
)

call :log INFO "Building ProfitsNLosses frontend for /pnl/..."
call npm run build --prefix "%PNLS_DIR%"
if errorlevel 1 exit /b 1

if exist "%LOGIN_ART_SOURCE%" (
  if not exist "%FRONTEND_PUBLIC%" mkdir "%FRONTEND_PUBLIC%"
  copy /Y "%LOGIN_ART_SOURCE%" "%LOGIN_ART_TARGET%" > nul
  call :log OK "Login image copied: login-art.jpg"
) else (
  call :log WARN "Login image not found. Put login-art.jpg in project root to replace the fallback panel."
)

call :pick_port BACKEND_PORT 8000 8002 8003
if not defined BACKEND_PORT (
  call :log ERROR "No free portal backend port found in 8000, 8002, 8003."
  exit /b 1
)

call :pick_port FRONTEND_PORT 5173 5174 5175
if not defined FRONTEND_PORT (
  call :log ERROR "No free frontend port found in 5173, 5174, 5175."
  exit /b 1
)

call :log OK "Backend:  http://127.0.0.1:%BACKEND_PORT%"
call :log OK "Frontend: http://127.0.0.1:%FRONTEND_PORT%"
call :log OK "PnLs:     http://127.0.0.1:%FRONTEND_PORT%/pnl/"

powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Get-NetTCPConnection -LocalPort %PNLS_BACKEND_PORT% -State Listen -ErrorAction SilentlyContinue) { exit 1 } else { exit 0 }"
if errorlevel 1 (
  call :log WARN "Port %PNLS_BACKEND_PORT% is busy. Assuming ProfitsNLosses backend is already running."
) else (
  call :log INFO "Starting ProfitsNLosses backend on %PNLS_BACKEND_PORT%..."
  start "PNLS_BACKEND" /B "%PNLS_PYTHON_EXE%" -m uvicorn app.main:app --host 127.0.0.1 --port %PNLS_BACKEND_PORT% --app-dir "%PNLS_BACKEND_DIR%"
  call :find_pid PNLS_BACKEND_PID "%PNLS_PYTHON_EXE%" "%PNLS_BACKEND_PORT%"
)

call :log INFO "Waiting for ProfitsNLosses backend health..."
set "PNLS_READY="
for /l %%I in (1,1,45) do (
  "%PYTHON_EXE%" -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:%PNLS_BACKEND_PORT%/api/v1/health', timeout=1).status == 200 else 1)" > nul 2> nul
  if not errorlevel 1 (
    set "PNLS_READY=1"
    goto pnls_ready
  )
  timeout /t 1 /nobreak > nul
)

:pnls_ready
if not defined PNLS_READY (
  call :log ERROR "ProfitsNLosses backend did not become healthy on http://127.0.0.1:%PNLS_BACKEND_PORT%/api/v1/health."
  call :cleanup
  exit /b 1
)

call :log OK "ProfitsNLosses backend is ready."

call :log INFO "Starting backend in this window..."
start "PORTAL_BACKEND" /B cmd /c set PORTAL_PNL_API_URL=http://127.0.0.1:%PNLS_BACKEND_PORT% ^&^& set PORTAL_PNL_WS_URL=ws://127.0.0.1:%PNLS_BACKEND_PORT% ^&^& set PORTAL_PNL_DIST_PATH=%PNLS_DIR%\dist ^&^& "%PYTHON_EXE%" -m uvicorn app.main:app --host 127.0.0.1 --port %BACKEND_PORT% --app-dir "%BACKEND_DIR%"

call :find_pid BACKEND_PID "%PYTHON_EXE%" "%BACKEND_PORT%"

call :log INFO "Waiting for backend health..."
set "BACKEND_READY="
for /l %%I in (1,1,45) do (
  "%PYTHON_EXE%" -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:%BACKEND_PORT%/api/health', timeout=1).status == 200 else 1)" > nul 2> nul
  if not errorlevel 1 (
    set "BACKEND_READY=1"
    goto backend_ready
  )
  timeout /t 1 /nobreak > nul
)

:backend_ready
if not defined BACKEND_READY (
  call :log ERROR "Backend did not become healthy on http://127.0.0.1:%BACKEND_PORT%/api/health."
  call :cleanup
  exit /b 1
)

call :log OK "Backend health is ready."
call :log INFO "Starting frontend..."
start "PORTAL_FRONTEND" /B cmd /c cd /d "%FRONTEND_DIR%" ^&^& set PORTAL_API_PORT=%BACKEND_PORT% ^&^& npm run dev -- --host 127.0.0.1 --port %FRONTEND_PORT% --strictPort --logLevel warn

timeout /t 2 /nobreak > nul
call :find_pid FRONTEND_PID "vite.js" "%FRONTEND_PORT%"

call :log INFO "Open http://127.0.0.1:%FRONTEND_PORT%"
call :log INFO "Open PnLs through Portal: http://127.0.0.1:%FRONTEND_PORT%/pnl/"
call :log INFO "Close this window to stop the site, or press any key for cleanup."
pause > nul

call :cleanup
endlocal
exit /b 0

:pick_port
set "PORT_VAR=%~1"
for %%P in (%~2 %~3 %~4) do (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Get-NetTCPConnection -LocalPort %%P -State Listen -ErrorAction SilentlyContinue) { exit 1 } else { exit 0 }"
  if errorlevel 1 (
    call :log WARN "Port %%P is busy."
  ) else (
    set "%PORT_VAR%=%%P"
    call :log OK "Port %%P is available."
    exit /b 0
  )
)
exit /b 1

:find_pid
set "%~1="
for /f "usebackq delims=" %%P in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$needle='%~2'; $port='%~3'; Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like ('*' + $needle + '*') -and $_.CommandLine -like ('*' + $port + '*') -and $_.CommandLine -like '*SoftPortal*' } | Select-Object -First 1 -ExpandProperty ProcessId"`) do (
  set "%~1=%%P"
)
exit /b 0

:cleanup
call :log INFO "Stopping local site..."
if defined FRONTEND_PID (
  taskkill /F /PID %FRONTEND_PID% > nul 2> nul
)
if defined BACKEND_PID (
  taskkill /F /PID %BACKEND_PID% > nul 2> nul
)
if defined PNLS_BACKEND_PID (
  taskkill /F /PID %PNLS_BACKEND_PID% > nul 2> nul
)
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":%BACKEND_PORT%" ^| findstr "LISTENING"') do (
  taskkill /F /PID %%P > nul 2> nul
)
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":%FRONTEND_PORT%" ^| findstr "LISTENING"') do (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$p=Get-CimInstance Win32_Process -Filter 'ProcessId=%%P'; if ($p.CommandLine -like '*SoftPortal*') { Stop-Process -Id %%P -Force }" > nul 2> nul
)
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":%PNLS_BACKEND_PORT%" ^| findstr "LISTENING"') do (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$p=Get-CimInstance Win32_Process -Filter 'ProcessId=%%P'; if ($p.CommandLine -like '*ProfitsNLosses*') { Stop-Process -Id %%P -Force }" > nul 2> nul
)
call :log OK "Stopped."
exit /b 0

:log
echo [%~1] %~2
exit /b 0
