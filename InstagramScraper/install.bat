@echo off
echo.
echo ====================================
echo   ANALIZADOR CON INSTALOADER
echo   (Python + Instaloader)
echo ====================================
echo.

REM Verificar si Python está instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ ERROR: Python no está instalado
    echo.
    echo Descargalo desde: https://www.python.org/downloads/
    echo.
    echo IMPORTANTE: Marca "Add Python to PATH" durante la instalación
    echo.
    pause
    exit /b 1
)

echo ✅ Python detectado
python --version
echo.

REM Ir a la carpeta del proyecto
cd /d "%~dp0"

REM Crear entorno virtual (opcional pero recomendado)
echo.
echo 📦 Creando entorno virtual de Python...
python -m venv venv

REM Activar entorno virtual
call venv\Scripts\activate.bat

REM Instalar dependencias
echo.
echo 📥 Instalando dependencias (Flask, Instaloader, etc)...
echo ⏳ Esto puede tardar 1-2 minutos...
echo.

pip install --upgrade pip
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo ❌ Error en la instalación de dependencias
    echo.
    pause
    exit /b 1
)

echo.
echo ✅ ¡Instalación completada!
echo.
echo 🚀 Para iniciar la app, ejecuta:
echo    python app.py
echo.
echo 📊 Luego abre: http://localhost:5000
echo.
pause
