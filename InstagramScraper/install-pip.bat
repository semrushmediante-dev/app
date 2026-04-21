@echo off
echo.
echo ====================================
echo   INSTALAR PIP EN PYTHON 3.14
echo ====================================
echo.

REM Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python no esta disponible
    pause
    exit /b 1
)

echo ✅ Python detectado
python --version
echo.

REM Ir a la carpeta del proyecto
cd /d "%~dp0"

echo 📥 Instalando pip...
echo.

REM Instalar pip
python -m ensurepip --upgrade

if %errorlevel% neq 0 (
    echo.
    echo ⚠️  Intentando método alternativo...
    echo.
    
    REM Descargar get-pip.py
    echo 📥 Descargando get-pip.py...
    powershell -Command "(New-Object Net.WebClient).DownloadFile('https://bootstrap.pypa.io/get-pip.py', 'get-pip.py')"
    
    echo Ejecutando get-pip.py...
    python get-pip.py
    
    del get-pip.py
)

echo.
echo ✅ pip instalado correctamente
echo.
echo 📦 Ahora instalando dependencias...
echo.

REM Instalar las librerías
python -m pip install --upgrade pip
python -m pip install Flask==3.0.0
python -m pip install Flask-CORS==4.0.0
python -m pip install instaloader==4.13.0
python -m pip install requests==2.31.0

if %errorlevel% neq 0 (
    echo.
    echo ❌ Error en la instalacion
    pause
    exit /b 1
)

echo.
echo ✅ ¡Instalacion completada!
echo.
echo 🚀 Ahora ejecuta:
echo    python app.py
echo.
echo 📊 Luego abre: http://localhost:5000
echo.
pause
