# Script PowerShell para instalar en disco D
# Haz clic derecho y selecciona "Ejecutar con PowerShell"

Write-Host ""
Write-Host "====================================" -ForegroundColor Cyan
Write-Host "  INSTALAR EN DISCO D" -ForegroundColor Cyan
Write-Host "  Analizador de Seguidores Instagram" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# Verificar si Node.js está instalado
try {
    $nodeVersion = node --version
    Write-Host "✅ Node.js detectado: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Node.js no está instalado" -ForegroundColor Red
    Write-Host "Descargalo desde: https://nodejs.org/" -ForegroundColor Yellow
    Read-Host "Presiona Enter para salir"
    exit 1
}

Write-Host ""

# Crear carpeta para Puppeteer en D
$puppeteerCachePath = "D:\puppeteer-cache"
$npmCachePath = "D:\npm-cache"

Write-Host "📁 Creando carpetas de cache en D:..." -ForegroundColor Cyan
if (-not (Test-Path $puppeteerCachePath)) {
    New-Item -ItemType Directory -Path $puppeteerCachePath -Force | Out-Null
    Write-Host "✅ Carpeta creada: $puppeteerCachePath" -ForegroundColor Green
}

if (-not (Test-Path $npmCachePath)) {
    New-Item -ItemType Directory -Path $npmCachePath -Force | Out-Null
    Write-Host "✅ Carpeta creada: $npmCachePath" -ForegroundColor Green
}

Write-Host ""
Write-Host "📦 Configurando variables de entorno..." -ForegroundColor Cyan

# Establecer variables de entorno para esta sesión
$env:PUPPETEER_CACHE_DIR = $puppeteerCachePath
$env:npm_config_cache = $npmCachePath
$env:PUPPETEER_DOWNLOAD_HOST = "https://registry.npmmirror.com"

Write-Host "✅ PUPPETEER_CACHE_DIR = $puppeteerCachePath" -ForegroundColor Green
Write-Host "✅ npm_config_cache = $npmCachePath" -ForegroundColor Green

Write-Host ""

# Navegar a la carpeta del proyecto
$projectPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectPath

Write-Host "📍 Carpeta del proyecto: $projectPath" -ForegroundColor Cyan
Write-Host ""

# Limpiar instalación anterior
Write-Host "🗑️  Eliminando instalación anterior..." -ForegroundColor Yellow
if (Test-Path "node_modules") {
    Remove-Item -Path "node_modules" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "✅ Carpeta node_modules eliminada" -ForegroundColor Green
}

if (Test-Path "package-lock.json") {
    Remove-Item -Path "package-lock.json" -Force -ErrorAction SilentlyContinue
    Write-Host "✅ package-lock.json eliminado" -ForegroundColor Green
}

Write-Host ""
Write-Host "📥 Instalando dependencias..." -ForegroundColor Cyan
Write-Host "⏳ Esto puede tardar 3-5 minutos..." -ForegroundColor Yellow
Write-Host ""

# Instalar
npm install

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ ¡Instalación completada en D: exitosamente!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📊 Ahora puedes usar la app:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  1️⃣  Opción A: Ejecuta en PowerShell:" -ForegroundColor White
    Write-Host "      npm start" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  2️⃣  Opción B: Usa el script start-puppeteer.bat" -ForegroundColor White
    Write-Host ""
    Write-Host "  3️⃣  Luego abre en navegador:" -ForegroundColor White
    Write-Host "      http://localhost:3000" -ForegroundColor Yellow
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "❌ Hubo un error en la instalación" -ForegroundColor Red
    Write-Host ""
    Write-Host "Intenta esto en PowerShell:" -ForegroundColor Yellow
    Write-Host "`$env:PUPPETEER_CACHE_DIR = 'D:\puppeteer-cache'" -ForegroundColor Cyan
    Write-Host "npm install --verbose" -ForegroundColor Cyan
    Write-Host ""
}

Write-Host ""
Read-Host "Presiona Enter para salir"
