@echo off
echo.
echo ====================================
echo   INSTALAR PIP EN PYTHON 3.13
echo ====================================
echo.

cd /d "%~dp0"

echo 📥 Instalando pip...
echo.

REM Opción 1: Usar ensurepip
D:\Python313\python.exe -m ensurepip --upgrade

if %errorlevel% equ 0 (
    echo.
    echo ✅ pip instalado correctamente
    echo.
    echo 📦 Ahora instalando librerías...
    echo.
    
    D:\Python313\python.exe -m pip install Flask Flask-CORS instaloader requests
    
    if %errorlevel% equ 0 (
        echo.
        echo ✅ ¡Librerías instaladas!
        echo.
        echo 🚀 Para ejecutar la app:
        echo    D:\Python313\python.exe app.py
        echo.
        pause
        exit /b 0
    )
)

REM Si ensurepip falla, descargar get-pip.py
echo ⚠️  Intentando método alternativo...
echo.
echo 📥 Descargando get-pip.py...

powershell -Command "(New-Object Net.WebClient).DownloadFile('https://bootstrap.pypa.io/get-pip.py', 'get-pip.py')" 2>nul

if exist "get-pip.py" (
    echo ✅ get-pip.py descargado
    echo.
    echo Ejecutando get-pip.py...
    
    D:\Python313\python.exe get-pip.py
    
    del get-pip.py
    
    echo.
    echo ✅ pip instalado correctamente
    echo.
    echo 📦 Ahora instalando librerías...
    echo.
    
    D:\Python313\python.exe -m pip install Flask Flask-CORS instaloader requests
    
    if %errorlevel% equ 0 (
        echo.
        echo ✅ ¡Librerías instaladas!
        echo.
        echo 🚀 Para ejecutar la app:
        echo    D:\Python313\python.exe app.py
        echo.
        pause
        exit /b 0
    )
) else (
    echo ❌ No se pudo descargar get-pip.py
    echo.
    echo Intenta manualmente en PowerShell:
    echo   D:\Python313\python.exe -m ensurepip --upgrade
    echo.
)

echo.
echo ❌ Hubo un error
pause
