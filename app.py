#!/usr/bin/env python3
"""
VoicePlace · Servidor de Voz Multi-Dispositivo con Sincronización en Tiempo Real
Desarrollado para Dhamit Amit Elgueta Ríos
Motor: Edge-TTS (318+ voces, 75 idiomas) + Fallback Piper + Di CLI
Puerto: 8095
"""

import asyncio
import base64
import glob
import io
import json
import os
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from mutagen.mp3 import MP3
from pydantic import BaseModel
import qrcode

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
AUDIO_CACHE_DIR = BASE_DIR / "audio_cache"
DB_PATH = BASE_DIR / "voiceplace.db"

STATIC_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Base de datos SQLite para historial persistente de audios
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS historial_audios (
        id TEXT PRIMARY KEY,
        texto TEXT NOT NULL,
        voz_id TEXT NOT NULL,
        voz_label TEXT NOT NULL,
        velocidad REAL DEFAULT 1.0,
        duracion_segundos REAL NOT NULL,
        duracion_formateada TEXT NOT NULL,
        origen TEXT DEFAULT 'device',
        archivo_mp3 TEXT NOT NULL,
        fecha_hora TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()
    conn.close()

init_db()

app = FastAPI(title="VoicePlace API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PAISES_NOMBRES = {
    'AE': 'Emiratos Árabes Unidos', 'AF': 'Afganistán', 'AL': 'Albania', 'AR': 'Argentina',
    'AT': 'Austria', 'AU': 'Australia', 'AZ': 'Azerbaiyán', 'BA': 'Bosnia y Herzegovina',
    'BD': 'Bangladés', 'BE': 'Bélgica', 'BG': 'Bulgaria', 'BH': 'Baréin', 'BO': 'Bolivia',
    'BR': 'Brasil', 'CA': 'Canadá', 'CH': 'Suiza', 'CL': 'Chile', 'CN': 'China',
    'CO': 'Colombia', 'CR': 'Costa Rica', 'CU': 'Cuba', 'CZ': 'República Checa',
    'DE': 'Alemania', 'DK': 'Dinamarca', 'DO': 'República Dominicana', 'DZ': 'Argelia',
    'EC': 'Ecuador', 'EE': 'Estonia', 'EG': 'Egipto', 'ES': 'España', 'ET': 'Etiopía',
    'FI': 'Finlandia', 'FR': 'Francia', 'GB': 'Reino Unido', 'GE': 'Georgia',
    'GQ': 'Guinea Ecuatorial', 'GR': 'Grecia', 'GT': 'Guatemala', 'HK': 'Hong Kong',
    'HN': 'Honduras', 'HR': 'Croacia', 'HU': 'Hungría', 'ID': 'Indonesia', 'IE': 'Irlanda',
    'IL': 'Israel', 'IN': 'India', 'IQ': 'Irak', 'IR': 'Irán', 'IS': 'Islandia',
    'IT': 'Italia', 'JO': 'Jordania', 'JP': 'Japón', 'KE': 'Kenia', 'KH': 'Camboya',
    'KR': 'Corea del Sur', 'KW': 'Kuwait', 'KZ': 'Kazajistán', 'LA': 'Laos', 'LB': 'Líbano',
    'LK': 'Sri Lanka', 'LT': 'Lituania', 'LV': 'Letonia', 'LY': 'Libia', 'MA': 'Marruecos',
    'MK': 'Macedonia del Norte', 'MM': 'Myanmar', 'MN': 'Mongolia', 'MT': 'Malta',
    'MX': 'México', 'MY': 'Malasia', 'NG': 'Nigeria', 'NI': 'Nicaragua', 'NL': 'Países Bajos',
    'NO': 'Noruega', 'NP': 'Nepal', 'NZ': 'Nueva Zelanda', 'OM': 'Omán', 'PA': 'Panamá',
    'PE': 'Perú', 'PH': 'Filipinas', 'PK': 'Pakistán', 'PL': 'Polonia', 'PR': 'Puerto Rico',
    'PT': 'Portugal', 'PY': 'Paraguay', 'QA': 'Catar', 'RO': 'Rumania', 'RS': 'Serbia',
    'RU': 'Rusia', 'SA': 'Arabia Saudita', 'SE': 'Suecia', 'SG': 'Singapur', 'SI': 'Eslovenia',
    'SK': 'Eslovaquia', 'SO': 'Somalia', 'SV': 'El Salvador', 'SY': 'Siria', 'TH': 'Tailandia',
    'TN': 'Túnez', 'TR': 'Turquía', 'TW': 'Taiwán', 'TZ': 'Tanzania', 'UA': 'Ucrania',
    'US': 'Estados Unidos', 'UY': 'Uruguay', 'UZ': 'Uzbekistán', 'VE': 'Venezuela',
    'VN': 'Vietnam', 'YE': 'Yemen', 'ZA': 'Sudáfrica'
}

def _generar_bandera(c_code: str) -> str:
    if len(c_code) == 2 and c_code.isalpha():
        return "".join(chr(127397 + ord(c.upper())) for c in c_code)
    return "🌐"

def construir_catalogo_voces():
    voces = {}
    favoritas = [
        ("🇨🇴 Colombia (Mujer) - Salomé ⭐ [Predeterminada]", "es-CO-SalomeNeural"),
        ("🇨🇴 Colombia (Hombre) - Gonzalo", "es-CO-GonzaloNeural"),
        ("🇨🇱 Chile (Mujer) - Catalina", "es-CL-CatalinaNeural"),
        ("🇨🇱 Chile (Hombre) - Lorenzo", "es-CL-LorenzoNeural"),
        ("🇲🇽 México (Mujer) - Dalia", "es-MX-DaliaNeural"),
        ("🇲🇽 México (Hombre) - Jorge", "es-MX-JorgeNeural"),
        ("🇪🇸 España (Mujer) - Elvira", "es-ES-ElviraNeural"),
        ("🇪🇸 España (Hombre) - Álvaro", "es-ES-AlvaroNeural"),
        ("🇦🇷 Argentina (Mujer) - Elena", "es-AR-ElenaNeural"),
        ("🇦🇷 Argentina (Hombre) - Tomás", "es-AR-TomasNeural"),
        ("🇺🇸 Estados Unidos (Mujer - Inglés) - Jenny", "en-US-JennyNeural"),
        ("🇺🇸 Estados Unidos (Hombre - Inglés) - Guy", "en-US-GuyNeural"),
        ("🇮🇹 Italia (Mujer - Italiano) - Elsa", "it-IT-ElsaNeural"),
        ("🇨🇳 China (Mujer - Mandarín) - Xiaoxiao", "zh-CN-XiaoxiaoNeural"),
    ]
    ids_agregados = set()
    for label, vid in favoritas:
        voces[label] = vid
        ids_agregados.add(vid)

    edge_bin = shutil.which("edge-tts") or "/home/dhamit/.local/bin/edge-tts"
    if os.path.isfile(edge_bin):
        try:
            res = subprocess.run([edge_bin, "--list-voices"], capture_output=True, text=True, timeout=8, check=False)
            if res.returncode == 0:
                resto_items = []
                for line in res.stdout.strip().split("\n")[2:]:
                    parts = line.split()
                    if len(parts) >= 2:
                        vid = parts[0]
                        gender = parts[1]
                        if vid in ids_agregados:
                            continue
                        m = re.match(r"^([a-z]{2,3})-([A-Za-z]{2,3})-(.+?)(?:Neural)?$", vid)
                        if m:
                            lang, c_code, name = m.groups()
                            c_up = c_code.upper()
                            flag = _generar_bandera(c_up)
                            p_name = PAISES_NOMBRES.get(c_up, c_up)
                            g_lbl = "Mujer" if gender.lower() == "female" else "Hombre"
                            label = f"{flag} {p_name} ({g_lbl}) - {name}"
                            resto_items.append((c_up, label, vid))

                paises_hispanos = {'CO', 'CL', 'MX', 'AR', 'ES', 'PE', 'VE', 'EC', 'BO', 'UY', 'PY', 'CR', 'PA', 'DO', 'GT', 'CU', 'SV', 'HN', 'NI', 'PR'}
                resto_items.sort(key=lambda x: (0 if x[0] in paises_hispanos else 1, x[1]))

                for _, label, vid in resto_items:
                    lbl_final = label
                    if lbl_final in voces:
                        lbl_final = f"{label} [{vid}]"
                    voces[lbl_final] = vid
                    ids_agregados.add(vid)
        except Exception:
            pass

    return voces

CATALOGO_VOCES = construir_catalogo_voces()
VOICE_ID_TO_LABEL = {vid: label for label, vid in CATALOGO_VOCES.items()}

def obtener_ips():
    lan_ip = "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        lan_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    tailscale_ip = ""
    try:
        out = subprocess.check_output(["tailscale", "ip", "-4"], stderr=subprocess.DEVNULL).decode().strip()
        tailscale_ip = out.splitlines()[0].strip() if out else ""
    except Exception:
        pass

    return lan_ip, tailscale_ip

def formatear_duracion(segundos: float) -> str:
    seg_int = int(round(segundos))
    mins = seg_int // 60
    segs = seg_int % 60
    if mins == 0:
        return f"{segs} seg"
    return f"{mins} min {segs} seg"

def estimar_duracion(texto: str, velocidad: float) -> tuple[float, str]:
    palabras = len([p for p in re.split(r"\s+", (texto or "").strip()) if p])
    if palabras == 0:
        return 0.0, "0 seg"
    vel = max(0.5, min(3.0, float(velocidad)))
    segundos = (palabras / 150.0) * 60.0 / vel
    segundos = max(1.5, segundos)
    return round(segundos, 1), formatear_duracion(segundos)

# Gestor de conexiones WebSocket en vivo para celular y laptop
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

class SpeakRequest(BaseModel):
    text: str
    voice: Optional[str] = "es-CO-SalomeNeural"
    speed: Optional[float] = 1.0
    target: Optional[str] = "device"  # "device" (celular/web), "laptop" (parlantes PC), o "both" (ambos)
    client_id: Optional[str] = "web"

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Mantener conexión activa (heartbeat / ping)
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

@app.get("/api/voices")
def get_voices():
    items = []
    for label, vid in CATALOGO_VOCES.items():
        items.append({"label": label, "id": vid})
    return items

@app.get("/api/info")
def get_info():
    lan_ip, ts_ip = obtener_ips()
    port = 8095
    return {
        "app_name": "VoicePlace",
        "lan_ip": lan_ip,
        "tailscale_ip": ts_ip,
        "port": port,
        "lan_url": f"http://{lan_ip}:{port}",
        "tailscale_url": f"http://{ts_ip}:{port}" if ts_ip else None,
        "default_voice": "es-CO-SalomeNeural",
        "default_speed": 1.0,
        "total_voices": len(CATALOGO_VOCES),
        "connected_clients": len(manager.active_connections),
    }

@app.get("/api/qr")
def get_qr(target: str = "lan"):
    lan_ip, ts_ip = obtener_ips()
    port = 8095
    url = f"http://{ts_ip}:{port}" if (target == "tailscale" and ts_ip) else f"http://{lan_ip}:{port}"
    
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0F172A", back_color="#38BDF8")
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return Response(content=buf.getvalue(), media_type="image/png")

@app.get("/api/history")
def get_history(limit: int = 30):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
    SELECT id, texto, voz_id, voz_label, velocidad, duracion_segundos, duracion_formateada,
           origen, archivo_mp3, fecha_hora
    FROM historial_audios
    ORDER BY created_at DESC
    LIMIT ?;
    """, (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    for r in rows:
        r["audio_url"] = f"/api/audio/{r['archivo_mp3']}"
        r["player_url"] = f"/player/{r['id']}"
    return rows

@app.post("/api/speak")
async def speak(req: SpeakRequest):
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="El texto no puede estar vacío.")

    voice = req.voice or "es-CO-SalomeNeural"
    voice_label = VOICE_ID_TO_LABEL.get(voice, voice)
    speed = float(req.speed or 1.0)
    target = req.target or "device"

    # Pre-cálculo estimado
    est_sec, est_fmt = estimar_duracion(text, speed)

    # Sintetizar audio en MP3 (siempre para que quede en el historial y se pueda reproducir en cualquier dispositivo)
    file_id = f"vp_{uuid.uuid4().hex[:10]}"
    output_filename = f"{file_id}.mp3"
    output_mp3 = AUDIO_CACHE_DIR / output_filename

    percent = int(round((speed - 1.0) * 100))
    rate_arg = f"+{percent}%" if percent >= 0 else f"{percent}%"

    try:
        import edge_tts
        communicate = edge_tts.Communicate(text, voice, rate=rate_arg)
        await communicate.save(str(output_mp3))
    except Exception:
        edge_bin = shutil.which("edge-tts") or "/home/dhamit/.local/bin/edge-tts"
        cmd = f'{edge_bin} --voice "{voice}" --rate="{rate_arg}" --text "{text}" --write-media "{output_mp3}"'
        proc = subprocess.run(cmd, shell=True, capture_output=True, timeout=35)
        if proc.returncode != 0 or not output_mp3.exists():
            raise HTTPException(status_code=500, detail=f"Fallo de síntesis: {proc.stderr.decode()}")

    # Duración real exacta
    try:
        audio = MP3(str(output_mp3))
        real_duration_sec = round(audio.info.length, 1)
        real_fmt = formatear_duracion(real_duration_sec)
    except Exception:
        real_duration_sec = est_sec
        real_fmt = est_fmt

    now_str = datetime.now().strftime("%H:%M:%S · %d/%m")

    # Guardar en SQLite Historial
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO historial_audios (id, texto, voz_id, voz_label, velocidad, duracion_segundos, duracion_formateada, origen, archivo_mp3, fecha_hora)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (file_id, text, voice, voice_label, speed, real_duration_sec, real_fmt, target, output_filename, now_str))
    conn.commit()
    conn.close()

    audio_item = {
        "id": file_id,
        "texto": text,
        "voz_id": voice,
        "voz_label": voice_label,
        "velocidad": speed,
        "duracion_segundos": real_duration_sec,
        "duracion_formateada": real_fmt,
        "audio_url": f"/api/audio/{output_filename}",
        "player_url": f"/player/{file_id}",
        "origen": target,
        "fecha_hora": now_str,
    }

    # Si el target es 'laptop' o 'both', también mandar a reproducir localmente en la laptop
    if target in ("laptop", "both"):
        try:
            vel_str = f"{speed:.2f}"
            cmd = ["/home/dhamit/.local/bin/Di", "-v", voice, f"{vel_str} {text}"]
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print("Error enviando a Di en laptop:", e)

    # Transmisión en tiempo real vía WebSocket a todos los clientes (especialmente al celular)
    await manager.broadcast({
        "type": "new_audio",
        "audio": audio_item,
        "auto_play": (target in ("device", "both")),
    })

    return {
        "success": True,
        "target": target,
        "audio": audio_item,
        "message": "Audio generado y transmitido a todos los dispositivos"
    }

@app.get("/api/audio/{filename}")
def get_audio(filename: str):
    file_path = AUDIO_CACHE_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio no encontrado.")
    return FileResponse(file_path, media_type="audio/mpeg", headers={"Accept-Ranges": "bytes"})

# Página del reproductor dedicado e individual para compartir o ver en otra ventana
@app.get("/player/{audio_id}", response_class=HTMLResponse)
def player_page(audio_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM historial_audios WHERE id = ? LIMIT 1;", (audio_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return HTMLResponse("<h1>Audio no encontrado o expirado</h1>", status_code=404)

    item = dict(row)
    audio_url = f"/api/audio/{item['archivo_mp3']}"
    texto_esc = item["texto"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', '&quot;')

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VoicePlace · {item['voz_label']} ({item['duracion_formateada']})</title>
    <meta name="theme-color" content="#090D16">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-base: #090D16;
            --bg-card: rgba(15, 23, 42, 0.9);
            --border-card: rgba(255, 255, 255, 0.09);
            --border-glow: rgba(56, 189, 248, 0.45);
            --text-main: #F8FAFC;
            --text-muted: #94A3B8;
            --accent-sky: #38BDF8;
            --accent-emerald: #10B981;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background: var(--bg-base);
            background-image:
                radial-gradient(circle at 10% 10%, rgba(56, 189, 248, 0.1), transparent 45%),
                radial-gradient(circle at 90% 90%, rgba(16, 185, 129, 0.1), transparent 45%);
            color: var(--text-main);
            font-family: 'Plus Jakarta Sans', sans-serif;
            min-height: 100vh;
            display: grid;
            place-items: center;
            padding: 20px;
        }}
        .player-modal {{
            width: 100%;
            max-width: 540px;
            background: var(--bg-card);
            border: 1px solid var(--border-glow);
            border-radius: 20px;
            padding: 24px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.6);
            display: flex;
            flex-direction: column;
            gap: 16px;
        }}
        .top-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-card);
            padding-bottom: 12px;
        }}
        .tag-pill {{
            background: rgba(56, 189, 248, 0.15);
            color: var(--accent-sky);
            font-size: 0.78rem;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 8px;
            border: 1px solid rgba(56, 189, 248, 0.3);
        }}
        .dur-badge {{
            font-family: 'JetBrains Mono', monospace;
            background: rgba(16, 185, 129, 0.18);
            color: #6EE7B7;
            font-size: 0.82rem;
            font-weight: 800;
            padding: 4px 10px;
            border-radius: 8px;
            border: 1px solid rgba(16, 185, 129, 0.35);
        }}
        .text-box {{
            background: #060911;
            border: 1px solid var(--border-card);
            border-radius: 12px;
            padding: 14px;
            font-size: 0.95rem;
            line-height: 1.5;
            max-height: 220px;
            overflow-y: auto;
            color: #E2E8F0;
        }}
        canvas#wave {{
            width: 100%;
            height: 60px;
            background: #050811;
            border-radius: 10px;
            display: block;
        }}
        audio {{
            width: 100%;
            height: 44px;
            border-radius: 10px;
        }}
        .controls-row {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }}
        button, a.btn-link {{
            font-family: inherit;
            font-size: 0.84rem;
            font-weight: 700;
            border-radius: 10px;
            padding: 11px 14px;
            cursor: pointer;
            border: 1px solid var(--border-card);
            background: #1E293B;
            color: white;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            transition: all 0.16s ease;
        }}
        button:hover, a.btn-link:hover {{
            border-color: var(--border-glow);
            transform: translateY(-1px);
        }}
        .btn-emerald {{
            background: linear-gradient(135deg, #10B981, #059669);
            border-color: rgba(16, 185, 129, 0.5);
        }}
        .btn-sky {{
            background: linear-gradient(135deg, #0284C7, #2563EB);
            border-color: rgba(56, 189, 248, 0.5);
        }}
    </style>
</head>
<body>
<div class="player-modal">
    <div class="top-row">
        <span class="tag-pill">{item['voz_label']} · {item['velocidad']}x</span>
        <span class="dur-badge">⏱️ {item['duracion_formateada']} ({item['duracion_segundos']}s)</span>
    </div>
    <div class="text-box">{texto_esc}</div>
    <canvas id="wave"></canvas>
    <audio id="player" controls autoplay src="{audio_url}"></audio>
    <div class="controls-row">
        <button type="button" class="btn-sky" onclick="replayAudio()">↻ Repetir (Replay)</button>
        <a class="btn-link btn-emerald" href="{audio_url}" download="voiceplace_{item['id']}.mp3">⬇️ Descargar MP3</a>
    </div>
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <a class="btn-link" href="/" style="font-size:0.78rem;">← Volver a VoicePlace</a>
        <button type="button" style="font-size:0.78rem;" onclick="copyShareLink()">🔗 Compartir enlace</button>
    </div>
</div>
<script>
    const audio = document.getElementById('player');
    const canvas = document.getElementById('wave');
    const ctx = canvas.getContext('2d');
    
    function resize() {{
        canvas.width = canvas.clientWidth * window.devicePixelRatio;
        canvas.height = canvas.clientHeight * window.devicePixelRatio;
    }}
    resize();
    window.addEventListener('resize', resize);

    function replayAudio() {{
        audio.currentTime = 0;
        audio.play();
    }}

    function copyShareLink() {{
        navigator.clipboard.writeText(window.location.href);
        alert('Enlace del audio copiado para abrirlo en cualquier dispositivo.');
    }}

    let phase = 0;
    function draw() {{
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        const w = canvas.width, h = canvas.height, mid = h / 2, bars = 40, barW = w / bars;
        const active = !audio.paused && !audio.ended;
        for (let i = 0; i < bars; i++) {{
            const mult = active ? (Math.sin(i * 0.3 + phase) * 0.4 + Math.cos(i * 0.2 - phase) * 0.4) : 0.06;
            const barH = Math.max(4, Math.abs(mult) * (h * 0.8));
            const x = i * barW;
            const y = mid - barH / 2;
            ctx.fillStyle = active ? '#38BDF8' : 'rgba(56, 189, 248, 0.25)';
            ctx.fillRect(x + 1, y, barW - 2, barH);
        }}
        if (active) phase += 0.2;
        requestAnimationFrame(draw);
    }}
    draw();
</script>
</body>
</html>
"""
    return HTMLResponse(html)

@app.get("/manifest.json")
def get_manifest():
    return JSONResponse({
        "name": "VoicePlace",
        "short_name": "VoicePlace",
        "description": "Comando Di y TTS Edge multicadena en tu Celular y Laptop con sincronización en vivo",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#090D16",
        "theme_color": "#0284C7",
        "icons": [
            {"src": "/static/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png"}
        ]
    })

@app.get("/sw.js")
def get_sw():
    js = """
    self.addEventListener('install', (e) => self.skipWaiting());
    self.addEventListener('activate', (e) => e.waitUntil(clients.claim()));
    self.addEventListener('fetch', (e) => {
        e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
    });
    """
    return Response(content=js, media_type="application/javascript")

@app.get("/", response_class=HTMLResponse)
def index():
    html_path = BASE_DIR / "static" / "index.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>VoicePlace cargando...</h1>")

if __name__ == "__main__":
    import uvicorn
    lan_ip, ts_ip = obtener_ips()
    print("=" * 64)
    print("🎙️ VoicePlace v2.0 · Servidor Activo (Sincronización en Vivo)")
    print(f"👉 Celular / Red Local (Wi-Fi): http://{lan_ip}:8095")
    if ts_ip:
        print(f"👉 Celular / Tailscale (Desde cualquier lugar): http://{ts_ip}:8095")
    print("👉 Laptop local: http://localhost:8095")
    print("=" * 64)
    uvicorn.run("app:app", host="0.0.0.0", port=8095, reload=False)
