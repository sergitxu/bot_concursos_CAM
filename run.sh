#!/bin/bash
# Script de ejecución para CRON en Raspberry Pi

# Ajusta esta ruta a donde tengas la carpeta en la Raspberry Pi
PROJECT_DIR="/home/pi/bot_concursos_CAM"
VENV_DIR="$PROJECT_DIR/venv"

# Configuración de Telegram
export TELEGRAM_TOKEN="TU_TOKEN_TELEGRAM"
export TELEGRAM_CHAT_ID="TU_CHAT_ID"

# Configuración de reintentos
export MAX_RETRIES=6      # Intentará 6 veces en total
export RETRY_DELAY=1800   # Esperará 30 min (1800 seg) entre cada intento fallido

# Moverse al directorio del proyecto
cd "$PROJECT_DIR" || exit 1

# Ejecutar el script usando el binario de Python dentro del virtual env
# (así evitamos tener que hacer "source venv/bin/activate" que en cron a veces falla)
# Se guarda todo el output en "cron.log"
"$VENV_DIR/bin/python" scraper.py >> cron.log 2>&1
