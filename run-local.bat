@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 > nul

set "ROOT=%~dp0"
set "WORKSPACE_DIR=%ROOT%.."
set "BACKEND_DIR=%ROOT%backend"
set "FRONTEND_DIR=%ROOT%frontend"
set "PNLS_DIR=%WORKSPACE_DIR%\ProfitsNLosses"
set "PNLS_BACKEND_DIR=%PNLS_DIR%\backend"
set "FNUP_DIR=%WORKSPACE_DIR%\FoldersNUsersParser"
set "PYTHON_EXE=%BACKEND_DIR%\.venv\Scripts\python.exe"
set "PNLS_PYTHON_EXE=%PNLS_BACKEND_DIR%\.venv\Scripts\python.exe"
set "FNUP_PYTHON_EXE=%FNUP_DIR%\.venv\Scripts\python.exe"
set "FRONTEND_PUBLIC=%FRONTEND_DIR%\public"
set "LOGIN_ART_SOURCE=%ROOT%login-art.jpg"
set "LOGIN_ART_TARGET=%FRONTEND_PUBLIC%\login-art.jpg"
set "BACKEND_PORT="
set "FRONTEND_PORT="
set "BACKEND_PID="
set "FRONTEND_PID="
set "PNLS_BACKEND_PORT=8001"
set "PNLS_BACKEND_PID="
set "FNUP_BACKEND_PORT=8002"
set "FNUP_BACKEND_PID="

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

if not exist "%FNUP_DIR%\package.json" (
  call :log ERROR "FoldersNUsersParser project was not found at %FNUP_DIR%."
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

if not exist "%FNUP_PYTHON_EXE%" (
  call :log INFO "Creating FoldersNUsersParser virtualenv..."
  python -m venv "%FNUP_DIR%\.venv"
  if errorlevel 1 exit /b 1
)

call :log INFO "Checking FoldersNUsersParser backend dependencies..."
call "%FNUP_PYTHON_EXE%" -m pip install --disable-pip-version-check -r "%FNUP_DIR%\backend\requirements.txt"
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

if not exist "%FNUP_DIR%\node_modules" (
  call :log INFO "Installing FoldersNUsersParser frontend dependencies..."
  call npm install --prefix "%FNUP_DIR%"
  if errorlevel 1 exit /b 1
)

call :log INFO "Building ProfitsNLosses frontend for /pnl/..."
call npm run build --prefix "%PNLS_DIR%"
if errorlevel 1 exit /b 1

call :log INFO "Building FoldersNUsersParser frontend for /fnup/..."
set "VITE_BASE_PATH=/fnup/"
set "VITE_API_BASE_URL=/fnup"
call npm run build --prefix "%FNUP_DIR%"
set "VITE_BASE_PATH="
set "VITE_API_BASE_URL="
if errorlevel 1 exit /b 1

if exist "%LOGIN_ART_SOURCE%" (
  if not exist "%FRONTEND_PUBLIC%" mkdir "%FRONTEND_PUBLIC%"
  copy /Y "%LOGIN_ART_SOURCE%" "%LOGIN_ART_TARGET%" > nul
  call :log OK "Login image copied: login-art.jpg"
) else (
  call :log WARN "Login image not found. Put login-art.jpg in project root to replace the fallback panel."
)

call :pick_port BACKEND_PORT 8000 8003 8004
if not defined BACKEND_PORT (
  call :log ERROR "No free portal backend port found in 8000, 8003, 8004."
  exit /b 1
)
call :require_var BACKEND_PORT "Portal backend port was not selected."
if errorlevel 1 exit /b 1

call :pick_port FRONTEND_PORT 5173 5174 5175
if not defined FRONTEND_PORT (
  call :log ERROR "No free frontend port found in 5173, 5174, 5175."
  exit /b 1
)
call :require_var FRONTEND_PORT "Frontend port was not selected."
if errorlevel 1 exit /b 1

echo [OK] Backend:  http://127.0.0.1:%BACKEND_PORT%
echo [OK] Frontend: http://127.0.0.1:%FRONTEND_PORT%
echo [OK] PnLs:     http://127.0.0.1:%FRONTEND_PORT%/pnl/
echo [OK] FNUP:     http://127.0.0.1:%FRONTEND_PORT%/fnup/

powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Get-NetTCPConnection -LocalPort %PNLS_BACKEND_PORT% -State Listen -ErrorAction SilentlyContinue) { exit 1 } else { exit 0 }"
if errorlevel 1 (
  call :log WARN "Port %PNLS_BACKEND_PORT% is busy. Assuming ProfitsNLosses backend is already running."
) else (
  call :log INFO "Starting ProfitsNLosses backend on %PNLS_BACKEND_PORT%..."
  start "PNLS_BACKEND" /B "%PNLS_PYTHON_EXE%" -m uvicorn app.main:app --host 127.0.0.1 --port %PNLS_BACKEND_PORT% --app-dir "%PNLS_BACKEND_DIR%" --no-access-log --log-level warning
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

powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Get-NetTCPConnection -LocalPort %FNUP_BACKEND_PORT% -State Listen -ErrorAction SilentlyContinue) { exit 1 } else { exit 0 }"
if errorlevel 1 (
  call :log WARN "Port %FNUP_BACKEND_PORT% is busy. Assuming FoldersNUsersParser backend is already running."
) else (
  call :log INFO "Starting FoldersNUsersParser backend on %FNUP_BACKEND_PORT%..."
  set "APP_ENV=production"
  start "FNUP_BACKEND" /B "%FNUP_PYTHON_EXE%" -m uvicorn backend.app.main:app --host 127.0.0.1 --port %FNUP_BACKEND_PORT% --app-dir "%FNUP_DIR%" --no-access-log --log-level warning
  set "APP_ENV="
  call :find_pid FNUP_BACKEND_PID "%FNUP_PYTHON_EXE%" "%FNUP_BACKEND_PORT%"
)

call :log INFO "Waiting for FoldersNUsersParser backend health..."
set "FNUP_READY="
for /l %%I in (1,1,45) do (
  "%PYTHON_EXE%" -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:%FNUP_BACKEND_PORT%/api/v1/health', timeout=1).status == 200 else 1)" > nul 2> nul
  if not errorlevel 1 (
    set "FNUP_READY=1"
    goto fnup_ready
  )
  timeout /t 1 /nobreak > nul
)

:fnup_ready
if not defined FNUP_READY (
  call :log ERROR "FoldersNUsersParser backend did not become healthy on http://127.0.0.1:%FNUP_BACKEND_PORT%/api/v1/health."
  call :cleanup
  exit /b 1
)

call :log OK "FoldersNUsersParser backend is ready."

call :log INFO "Starting backend in this window..."
set "PORTAL_PNL_API_URL=http://127.0.0.1:%PNLS_BACKEND_PORT%"
set "PORTAL_PNL_WS_URL=ws://127.0.0.1:%PNLS_BACKEND_PORT%"
set "PORTAL_PNL_DIST_PATH=%PNLS_DIR%\dist"
set "PORTAL_FNUP_API_URL=http://127.0.0.1:%FNUP_BACKEND_PORT%"
set "PORTAL_FNUP_DIST_PATH=%FNUP_DIR%\dist"
start "PORTAL_BACKEND" /B "%PYTHON_EXE%" -m uvicorn app.main:app --host 127.0.0.1 --port %BACKEND_PORT% --app-dir "%BACKEND_DIR%" --no-access-log --log-level warning
set "PORTAL_PNL_API_URL="
set "PORTAL_PNL_WS_URL="
set "PORTAL_PNL_DIST_PATH="
set "PORTAL_FNUP_API_URL="
set "PORTAL_FNUP_DIST_PATH="

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

call :log INFO "Waiting for frontend health..."
set "FRONTEND_READY="
for /l %%I in (1,1,30) do (
  "%PYTHON_EXE%" -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:%FRONTEND_PORT%', timeout=1).status < 500 else 1)" > nul 2> nul
  if not errorlevel 1 (
    set "FRONTEND_READY=1"
    goto frontend_ready
  )
  timeout /t 1 /nobreak > nul
)

:frontend_ready
if not defined FRONTEND_READY (
  call :log ERROR "Frontend did not become healthy on http://127.0.0.1:%FRONTEND_PORT%."
  call :cleanup
  exit /b 1
)

call :find_pid FRONTEND_PID "vite.js" "%FRONTEND_PORT%"

echo [OK] Frontend is ready.
echo [INFO] Portal: http://127.0.0.1:%FRONTEND_PORT%
echo [INFO] PnLs:   http://127.0.0.1:%FRONTEND_PORT%/pnl/
echo [INFO] FNUP:   http://127.0.0.1:%FRONTEND_PORT%/fnup/
echo [INFO] Keep this window open. Type stop and press Enter to stop the site.

:wait_for_stop
set "STOP_COMMAND="
set /p STOP_COMMAND=Type stop to stop local site: 
if /I not "%STOP_COMMAND%"=="stop" goto wait_for_stop

call :cleanup
endlocal
exit /b 0

:pick_port
set "PORT_VAR_NAME=%~1"
for %%P in (%~2 %~3 %~4) do (
  netstat -ano | findstr /R /C:":%%P .*LISTENING" > nul 2> nul
  if errorlevel 1 (
    set "!PORT_VAR_NAME!=%%P"
    call :log OK "Port %%P is available."
    exit /b 0
  ) else (
    call :log WARN "Port %%P is busy."
  )
)
exit /b 1

:require_var
if not defined %~1 (
  call :log ERROR "%~2"
  exit /b 1
)
exit /b 0

:find_pid
set "%~1="
for /f "usebackq delims=" %%P in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$needle='%~2'; $port='%~3'; Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like ('*' + $needle + '*') -and $_.CommandLine -like ('*' + $port + '*') } | Select-Object -First 1 -ExpandProperty ProcessId"`) do (
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
if defined FNUP_BACKEND_PID (
  taskkill /F /PID %FNUP_BACKEND_PID% > nul 2> nul
)
if defined BACKEND_PORT (
  for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":%BACKEND_PORT%" ^| findstr "LISTENING"') do (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$p=Get-CimInstance Win32_Process -Filter 'ProcessId=%%P'; if ($p.CommandLine -like '*SoftPortal*') { Stop-Process -Id %%P -Force }" > nul 2> nul
  )
)
if defined FRONTEND_PORT (
  for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":%FRONTEND_PORT%" ^| findstr "LISTENING"') do (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$p=Get-CimInstance Win32_Process -Filter 'ProcessId=%%P'; if ($p.CommandLine -like '*SoftPortal*') { Stop-Process -Id %%P -Force }" > nul 2> nul
  )
)
if defined PNLS_BACKEND_PORT (
  for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":%PNLS_BACKEND_PORT%" ^| findstr "LISTENING"') do (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$p=Get-CimInstance Win32_Process -Filter 'ProcessId=%%P'; if ($p.CommandLine -like '*ProfitsNLosses*') { Stop-Process -Id %%P -Force }" > nul 2> nul
  )
)
if defined FNUP_BACKEND_PORT (
  for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":%FNUP_BACKEND_PORT%" ^| findstr "LISTENING"') do (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$p=Get-CimInstance Win32_Process -Filter 'ProcessId=%%P'; if ($p.CommandLine -like '*FoldersNUsersParser*') { Stop-Process -Id %%P -Force }" > nul 2> nul
  )
)
call :log OK "Stopped."
exit /b 0

:log
echo [%~1] %~2
exit /b 0
