@echo off
setlocal

set "PROJECT_ROOT=%~dp0"
set "PYTHON_EXE=%PROJECT_ROOT%.venv\Scripts\python.exe"
set "REQ_FILE=%PROJECT_ROOT%boardgame_cafe\requirements.txt"

if not exist "%PYTHON_EXE%" (
  echo Virtual environment not found at .venv
  echo Create it first: py -m venv .venv
  exit /b 1
)

if /I "%~1"=="--install-deps" (
  "%PYTHON_EXE%" -m pip install -r "%REQ_FILE%"
)

"%PYTHON_EXE%" -m flask --app run.py run --debug
