@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo INSTAGRAM SCRAPER - INSTALACION PORTABLE
echo Carpeta del proyecto: %CD%
echo.

set PYTHON_DIR=%CD%\python
set PYTHON_EXE=%PYTHON_DIR%\python.exe
set BROWSERS_DIR=%CD%\browsers

REM Variable de entorno para que Playwright descargue en la carpeta del proyecto
set PLAYWRIGHT_BROWSERS_PATH=%BROWSERS_DIR%

if exist "%PYTHON_EXE%" (
    echo Python encontrado en: %PYTHON_DIR%
    goto INSTALAR_DEPENDENCIAS
)

echo Python no encontrado en la carpeta del proyecto
echo Descargando Python...
echo.

set PYTHON_ZIP=%TEMP%\python-embedded.zip
set PYTHON_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip

powershell -Command "& { $ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_ZIP%' -TimeoutSec 300 }" 2>nul

if %errorlevel% neq 0 (
    echo ERROR: No se pudo descargar Python
    pause
    exit /b 1
)

echo Extrayendo Python...
if not exist "%PYTHON_DIR%" mkdir "%PYTHON_DIR%"

powershell -Command "& { Add-Type -AssemblyName System.IO.Compression.FileSystem; [System.IO.Compression.ZipFile]::ExtractToDirectory('%PYTHON_ZIP%', '%PYTHON_DIR%') }" 2>nul

if %errorlevel% neq 0 (
    echo ERROR: No se pudo extraer Python
    pause
    exit /b 1
)

del "%PYTHON_ZIP%"

REM Habilitar site en Python embebido
echo Habilitando site...
set PYD_PTH=%PYTHON_DIR%\python311._pth
powershell -Command "& { (Get-Content '%PYD_PTH%') -replace '#import site', 'import site' | Set-Content '%PYD_PTH%' }" 2>nul

REM Descargar y ejecutar get-pip.py
echo Descargando get-pip.py...
set GET_PIP=%PYTHON_DIR%\get-pip.py
powershell -Command "& { $ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%GET_PIP%' -TimeoutSec 300 }" 2>nul

echo Instalando pip...
"%PYTHON_EXE%" "%GET_PIP%"
del "%GET_PIP%"

echo Python instalado en: %PYTHON_DIR%
echo.

:INSTALAR_DEPENDENCIAS

echo Instalando dependencias...
echo.

echo Paso 1: Flask
"%PYTHON_EXE%" -m pip install Flask==3.0.0 --quiet --disable-pip-version-check
if %errorlevel% neq 0 (
    echo ERROR en Flask
    pause
    exit /b 1
)
echo OK

echo Paso 2: Flask-CORS
"%PYTHON_EXE%" -m pip install Flask-CORS==4.0.0 --quiet --disable-pip-version-check
echo OK

echo Paso 3: Playwright
"%PYTHON_EXE%" -m pip install playwright==1.44.0 --quiet --disable-pip-version-check
echo OK

echo Paso 4: Requests
"%PYTHON_EXE%" -m pip install requests==2.31.0 --quiet --disable-pip-version-check
echo OK

echo Paso 5: Instaloader
"%PYTHON_EXE%" -m pip install instaloader==4.13.0 --quiet --disable-pip-version-check
echo OK

echo Paso 6: Chromium (tarda 10-15 minutos - NO CANCELES)
echo.
set PLAYWRIGHT_BROWSERS_PATH=%BROWSERS_DIR%
"%PYTHON_EXE%" -m playwright install chromium
if %errorlevel% neq 0 (
    echo ERROR en Chromium - intentando de nuevo
    set PLAYWRIGHT_BROWSERS_PATH=%BROWSERS_DIR%
    "%PYTHON_EXE%" -m playwright install chromium
)
echo OK

echo.
echo.
echo ===================================
echo INSTALACION COMPLETADA
echo ===================================
echo.
echo Usuario: amanda
echo Contrasena: contraseña2
echo URL: http://localhost:7860
echo.
echo Iniciando servidor en 5 segundos...
echo Se abrira el navegador automaticamente
echo.

REM Esperar 5 segundos
timeout /t 5 /nobreak

REM Abrir navegador
start http://localhost:7860

REM Iniciar servidor
set PLAYWRIGHT_BROWSERS_PATH=%BROWSERS_DIR%
"%PYTHON_EXE%" app.py

echo.
echo Servidor detenido.
pause