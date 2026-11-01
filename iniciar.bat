@echo off
cd /d "%~dp0"
if exist "python\pythonw.exe" (
  start "" "python\pythonw.exe" "app.py"
  exit /b
)
where py >nul 2>nul && (py app.py) || (python app.py)
if errorlevel 1 (
  echo.
  echo No se pudo abrir el programa. Revisa que Python este instalado.
  pause
)
