#!/usr/bin/env python3
"""
di-mobile · Cliente CLI para VoicePlace
Permite enviar texto para que suene en el celular o en la laptop,
calculando la duración en minutos y segundos.
"""

import sys
import json
import argparse
import urllib.request
import urllib.error

DEFAULT_URL = "http://localhost:8095"

def main():
    parser = argparse.ArgumentParser(description="di-mobile: TTS Edge para celular y laptop")
    parser.add_argument("text", nargs="*", help="Texto a decir")
    parser.add_argument("-v", "--voice", default="es-CO-SalomeNeural", help="ID de voz (ej: es-CO-SalomeNeural, es-CL-CatalinaNeural)")
    parser.add_argument("-s", "--speed", type=float, default=1.0, help="Velocidad (0.5 a 3.0)")
    parser.add_argument("-t", "--target", choices=["device", "laptop"], default="device", help="Destino: 'device' (celular/local) o 'laptop' (parlantes laptop)")
    parser.add_argument("--server", default=DEFAULT_URL, help="URL del servidor VoicePlace")
    
    args = parser.parse_args()
    
    text = " ".join(args.text).strip()
    if not text:
        if not sys.stdin.isatty():
            text = sys.stdin.read().strip()
        else:
            print("Error: Ingresa el texto a hablar. Ej: di-mobile 'Hola mundo'")
            sys.exit(1)

    payload = json.dumps({
        "text": text,
        "voice": args.voice,
        "speed": args.speed,
        "target": args.target
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{args.server}/api/speak",
        data=payload,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            print(f"🎙️ VoicePlace [{data.get('target', 'device')}]:")
            print(f"   ⏱️ Duración: {data.get('formatted_duration')} ({data.get('duration_seconds', data.get('estimated_seconds'))}s)")
            print(f"   🗣️ Voz: {data.get('voice')} | Velocidad: {data.get('speed')}x")
            if data.get("audio_url"):
                print(f"   🔊 URL Audio: {args.server}{data.get('audio_url')}")
    except urllib.error.URLError as e:
        print(f"Error conectando a VoicePlace ({args.server}): {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

