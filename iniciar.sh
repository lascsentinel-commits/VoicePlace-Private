#!/usr/bin/env bash
# Iniciar VoicePlace en puerto 8095
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT=8095

echo "=========================================================="
echo "🎙️  Iniciando VoicePlace · Celular & Laptop"
echo "=========================================================="

python3 "$DIR/app.py"

