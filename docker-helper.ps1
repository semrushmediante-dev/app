# docker-helper.ps1
# Script para facilitar comandos de Docker Compose en Windows

param(
    [string]$command = "help"
)

function Show-Help {
    Write-Host @"
╔════════════════════════════════════════════════════════════════╗
║  Instagram Scraper - Docker Helper                            ║
╚════════════════════════════════════════════════════════════════╝

Uso: .\docker-helper.ps1 [comando]

COMANDOS:
  up          Levantar la aplicación
  down        Parar la aplicación
  restart     Reiniciar la aplicación
  logs        Ver logs en tiempo real
  bash        Abrir bash en el contenedor
  build       Reconstruir la imagen
  status      Ver estado de los contenedores
  clean       Limpiar todo (borrar datos)
  help        Mostrar esta ayuda

EJEMPLOS:
  .\docker-helper.ps1 up
  .\docker-helper.ps1 logs
  .\docker-helper.ps1 bash

"@
}

function Invoke-Command {
    param([string]$cmd)
    Write-Host "▶ Ejecutando: $cmd" -ForegroundColor Green
    Invoke-Expression $cmd
}

switch ($command.ToLower()) {
    "up" {
        Invoke-Command "docker-compose up -d"
        Write-Host "`n✅ App levantada en http://localhost:7860" -ForegroundColor Green
    }
    "down" {
        Invoke-Command "docker-compose down"
        Write-Host "`n✅ App detenida" -ForegroundColor Green
    }
    "restart" {
        Invoke-Command "docker-compose restart instagram-scraper"
        Write-Host "`n✅ App reiniciada" -ForegroundColor Green
    }
    "logs" {
        Invoke-Command "docker-compose logs -f instagram-scraper"
    }
    "bash" {
        Invoke-Command "docker-compose exec instagram-scraper bash"
    }
    "build" {
        Invoke-Command "docker-compose up --build"
        Write-Host "`n✅ Imagen reconstruida y app levantada" -ForegroundColor Green
    }
    "status" {
        Invoke-Command "docker-compose ps"
    }
    "clean" {
        Write-Host "⚠️  Esto eliminará todos los datos locales" -ForegroundColor Yellow
        $confirm = Read-Host "¿Continuar? (s/n)"
        if ($confirm -eq 's') {
            Invoke-Command "docker-compose down -v"
            Remove-Item -Path "data", "uploads" -Recurse -Force -ErrorAction SilentlyContinue
            Write-Host "`n✅ Todo limpiado" -ForegroundColor Green
        }
    }
    "help" {
        Show-Help
    }
    default {
        Write-Host "❌ Comando desconocido: $command" -ForegroundColor Red
        Show-Help
    }
}
