@echo off
echo.
echo ====================================
echo   SOCIAL SCRAPER HUB
echo ====================================
echo.

set PLAYWRIGHT_BROWSERS_PATH=D:\playwright-browsers

echo Iniciando Instagram Scraper (puerto 5000)...
start "InstagramScraper" cmd /k "cd /d D:\Descargas\instagram-analyzer\InstagramScraper && set PLAYWRIGHT_BROWSERS_PATH=D:\playwright-browsers && D:\WinPython\WPy64-3.13.12.0\python\python.exe app.py"

timeout /t 2 /nobreak >nul

echo Iniciando Facebook Scraper (puerto 5001)...
start "FacebookScraper" cmd /k "cd /d D:\Descargas\instagram-analyzer\FacebookScraper && set PLAYWRIGHT_BROWSERS_PATH=D:\playwright-browsers && D:\WinPython\WPy64-3.13.12.0\python\python.exe app.py"

timeout /t 3 /nobreak >nul

echo Abriendo portal...
start "" "D:\Descargas\instagram-analyzer\index.html"

echo.
echo Servidores iniciados:
echo   Instagram: http://localhost:5000
echo   Facebook:  http://localhost:5001
echo.
pause
