@echo off
setlocal enableextensions

cd /d "%~dp0"

echo ============================================
echo  AUDITORIA PDF - INSTALAR Y EJECUTAR
echo ============================================
echo.

if not exist "main.py" (
  echo ERROR: No se encontro main.py en esta carpeta.
  pause
  exit /b 1
)

if not exist "requirements.txt" (
  echo ERROR: No se encontro requirements.txt en esta carpeta.
  pause
  exit /b 1
)

echo [1/5] Buscando Python...
set "PYTHON_CMD="

where py >nul 2>&1
if not errorlevel 1 (
  py -3.11 -c "import sys" >nul 2>&1
  if not errorlevel 1 (
    set "PYTHON_CMD=py -3.11"
  ) else (
    py -3 -c "import sys" >nul 2>&1
    if not errorlevel 1 (
      set "PYTHON_CMD=py -3"
    )
  )
)

if not defined PYTHON_CMD (
  where python >nul 2>&1
  if not errorlevel 1 (
    set "PYTHON_CMD=python"
  )
)

if not defined PYTHON_CMD (
  echo ERROR: No se encontro Python 3.
  echo Instala Python 3.11+ y vuelve a ejecutar este archivo.
  pause
  exit /b 1
)

echo [2/5] Creando entorno virtual (.venv) si no existe...
if not exist ".venv\Scripts\python.exe" (
  %PYTHON_CMD% -m venv .venv
  if errorlevel 1 (
    echo ERROR: No se pudo crear el entorno virtual.
    pause
    exit /b 1
  )
)

echo [3/5] Activando entorno virtual...
call ".venv\Scripts\activate.bat"
if errorlevel 1 (
  echo ERROR: No se pudo activar .venv.
  pause
  exit /b 1
)

echo [4/5] Instalando dependencias...
python -m pip install --upgrade pip
if errorlevel 1 (
  echo ERROR: Fallo al actualizar pip.
  pause
  exit /b 1
)

pip install -r requirements.txt
if errorlevel 1 (
  echo ERROR: Fallo al instalar requirements.txt.
  pause
  exit /b 1
)

echo [5/5] Ejecutando auditoria...
echo.
echo Puedes pasar argumentos al .bat, por ejemplo:
echo   instalar_y_ejecutar_auditoria.bat --root-dir "D:\Casos"
echo   instalar_y_ejecutar_auditoria.bat --pdf-dir "D:\Casos\Caso001"
echo.
echo Si no envias argumentos, main.py te pedira la ruta de carpeta principal.
echo.

python main.py %*
set "EXIT_CODE=%ERRORLEVEL%"

echo.
echo Proceso finalizado con codigo %EXIT_CODE%.
echo Nota: Si usas OCR, recuerda tener Tesseract instalado.
pause
exit /b %EXIT_CODE%
