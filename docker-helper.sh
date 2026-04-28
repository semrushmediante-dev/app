#!/bin/bash
# docker-helper.sh
# Script para facilitar comandos de Docker Compose en Linux/Mac

set -e

COMMAND=${1:-help}

show_help() {
    cat << 'EOF'
╔════════════════════════════════════════════════════════════════╗
║  Instagram Scraper - Docker Helper                            ║
╚════════════════════════════════════════════════════════════════╝

Uso: ./docker-helper.sh [comando]

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
  ./docker-helper.sh up
  ./docker-helper.sh logs
  ./docker-helper.sh bash

EOF
}

case "$COMMAND" in
    up)
        echo "▶ Levantando aplicación..."
        docker-compose up -d
        echo "✅ App levantada en http://localhost:7860"
        ;;
    down)
        echo "▶ Parando aplicación..."
        docker-compose down
        echo "✅ App detenida"
        ;;
    restart)
        echo "▶ Reiniciando aplicación..."
        docker-compose restart instagram-scraper
        echo "✅ App reiniciada"
        ;;
    logs)
        docker-compose logs -f instagram-scraper
        ;;
    bash)
        docker-compose exec instagram-scraper bash
        ;;
    build)
        echo "▶ Reconstruyendo imagen..."
        docker-compose up --build
        echo "✅ Imagen reconstruida y app levantada"
        ;;
    status)
        docker-compose ps
        ;;
    clean)
        read -p "⚠️  Esto eliminará todos los datos. ¿Continuar? (s/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Ss]$ ]]; then
            docker-compose down -v
            rm -rf data uploads
            echo "✅ Todo limpiado"
        fi
        ;;
    help)
        show_help
        ;;
    *)
        echo "❌ Comando desconocido: $COMMAND"
        show_help
        exit 1
        ;;
esac
