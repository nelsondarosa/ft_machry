@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "PYTHON="
if exist ".venv\Scripts\python.exe" goto usevenv
where py >nul 2>&1
if not errorlevel 1 (
  py -3 -c "import sys; assert sys.version_info >= (3,12)" >nul 2>&1
  if not errorlevel 1 set "PYTHON=py -3"
)
if not defined PYTHON (
  where python >nul 2>&1
  if not errorlevel 1 (
    python -c "import sys; assert sys.version_info >= (3,12)" >nul 2>&1
    if not errorlevel 1 set "PYTHON=python"
  )
)
if not defined PYTHON (
  echo [ERRO] Instale o Python 3.12 ou superior e marque Add Python to PATH.
  pause
  exit /b 1
)
echo [1/4] Criando ambiente virtual...
%PYTHON% -m venv .venv || goto error
:usevenv
echo [2/4] Instalando dependencias...
".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto error
if not defined DATABASE_PATH set "DATABASE_PATH=%CD%\data\app.db"
echo [3/4] Verificando banco SQLite...
if /i "%~1"=="--seed" (
  ".venv\Scripts\python.exe" -m flask --app app init-db --seed || goto error
) else (
  ".venv\Scripts\python.exe" -m flask --app app init-db || goto error
)
echo [4/4] Iniciando servidor...
echo.
echo API:     http://127.0.0.1:5000
echo Swagger: http://127.0.0.1:5000/docs
echo Frontend: execute "pnpm dev" dentro da pasta frontend
echo Parar: Ctrl+C
echo.
".venv\Scripts\python.exe" -m flask --app app run --host 127.0.0.1 --port 5000
exit /b %errorlevel%
:error
echo.
echo [ERRO] Verifique a mensagem acima. Nenhum dado foi apagado pelo script.
pause
exit /b 1
