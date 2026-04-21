@echo off
echo.
echo ====================================
echo   REINSTALANDO DEPENDENCIAS
echo ====================================
echo.

REM Borra la carpeta anterior
echo 🗑️  Eliminando instalación anterior...
rmdir /s /q node_modules 2>nul

REM Borra el lock file
del package-lock.json 2>nul

REM Instala las nuevas dependencias
echo.
echo 📦 Instalando versiones nuevas...
call npm install

echo.
echo ✅ ¡Instalación completada!
echo.
pause
