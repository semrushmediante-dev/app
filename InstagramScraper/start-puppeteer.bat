@echo off
echo.
echo ====================================
echo   ANALIZADOR DE SEGUIDORES INSTAGRAM
echo   Con Puppeteer (Web Scraping avanzado)
echo ====================================
echo.

REM Verificar si Node.js está instalado
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ ERROR: Node.js no está instalado
    echo.
    echo Descargalo desde: https://nodejs.org/
    echo.
    pause
    exit /b 1
)

echo ✅ Node.js detectado
node --version
echo.

REM Ir a la carpeta del proyecto
cd /d "%~dp0"

REM Instalar dependencias
echo.
echo 📦 Instalando dependencias (incluyendo Puppeteer)...
echo ⚠️  Esto puede tardar unos minutos la primera vez...
echo.

call npm install

if %errorlevel% neq 0 (
    echo.
    echo ❌ Error en la instalación de dependencias
    echo.
    pause
    exit /b 1
)

echo.
echo ✅ Dependencias instaladas correctamente
echo.

REM Iniciar el servidor
echo 🚀 Iniciando servidor...
echo.
echo 📊 La app estará disponible en: http://localhost:3000
echo.
echo Presiona Ctrl+C para detener el servidor
echo.

node server.js
