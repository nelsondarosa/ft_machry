@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "PYTHON="
if exist ".venv\Scripts\python.exe" goto ready
where py >nul 2>&1
if not errorlevel 1 set "PYTHON=py -3"
if not defined PYTHON set "PYTHON=python"
%PYTHON% -c "import sys; assert sys.version_info >= (3,12)" >nul 2>&1
if errorlevel 1 (echo [ERRO] Python 3.12+ necessario.& pause & exit /b 1)
echo [1/5] Preparando Python...
%PYTHON% -m venv .venv || goto error
:ready
echo [2/5] Instalando backend...
".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto error
if not defined DB_CONNECTION set "DB_CONNECTION=sqlite"
if /i not "%DB_CONNECTION%"=="sqlite" (echo [ERRO] run.bat e exclusivo do SQLite local. Use Docker para PostgreSQL.& pause & exit /b 1)
if not defined DATABASE_PATH set "DATABASE_PATH=%CD%\data\app.db"
echo [3/5] Inicializando banco sem apagar dados...
if /i "%~1"=="--seed" (
 ".venv\Scripts\python.exe" -m flask --app app init-db --seed || goto error
) else (
 ".venv\Scripts\python.exe" -m flask --app app init-db || goto error
)
echo [4/5] Preparando frontend...
where npm >nul 2>&1 || (echo [ERRO] Instale Node.js 22+ com npm.& pause & exit /b 1)
pushd frontend
if not exist "node_modules\vite" call npm install --no-audit --no-fund
if errorlevel 1 (popd & goto error)
popd
echo [5/5] Iniciando Flask e React...
start "Cozinha Mais - API" cmd /k "cd /d ""%CD%"" && set ""DB_CONNECTION=sqlite"" && set ""DATABASE_PATH=%DATABASE_PATH%"" && "".venv\Scripts\python.exe"" -m flask --app app run --host 127.0.0.1 --port 5000"
echo.
echo Cozinha Mais: http://localhost:8080
echo Outros computadores: http://IP_DESTA_MAQUINA:8080
ipconfig | findstr /i "IPv4"
echo API: http://localhost:5000/health
pushd frontend
call npm run dev
popd
exit /b %errorlevel%
:error
echo [ERRO] Nao foi possivel iniciar. Dados existentes nao foram apagados.
pause
exit /b 1
