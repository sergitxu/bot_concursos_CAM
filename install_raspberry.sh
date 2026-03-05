#!/bin/bash
echo "Configurando bot_concursos_CAM para Raspberry Pi..."
cd /home/pi/bot_concursos_CAM || exit
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
echo "Entorno virtual creado y dependencias instaladas."
