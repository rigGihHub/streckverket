@echo off
setlocal
cd /d "%~dp0"
title Streckverket

echo.
echo ==========================================
echo   STRECKVERKET - STARTAR APPEN
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" goto dependencies

where py >nul 2>nul
if %errorlevel%==0 (
  echo Forsta starten: skapar lokal Python-miljo...
  py -3 -m venv .venv
  goto dependencies
)

where python >nul 2>nul
if %errorlevel%==0 (
  echo Forsta starten: skapar lokal Python-miljo...
  python -m venv .venv
  goto dependencies
)

echo.
echo Python hittades inte pa datorn.
echo Installera Python 3.11 eller senare fran python.org och kor sedan filen igen.
echo Markera "Add Python to PATH" under installationen.
echo.
pause
exit /b 1

:dependencies
echo Kontrollerar beroenden...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 (
  echo.
  echo Det gick inte att installera appens beroenden.
  echo Kontrollera internetanslutningen och forsok igen.
  echo.
  pause
  exit /b 1
)

echo.
echo Streckverket oppnas i din webblasare.
echo Stang detta fonster nar du vill stoppa appen.
echo.
".venv\Scripts\python.exe" -m streamlit run app.py --server.headless=false --server.address=localhost --server.port=8501

if errorlevel 1 (
  echo.
  echo Streckverket avslutades med ett fel.
  pause
)
