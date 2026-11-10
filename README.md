# 🎙️ VoicePlace v2.0 · El Comando Di en tu Celular & Laptop (Sincronizado)

**VoicePlace** es una aplicación web y PWA con sincronización bidireccional en tiempo real (**WebSockets**) diseñada para que puedas escribir desde tu laptop o celular y hacer que el audio suene en cualquiera de los dos dispositivos al instante, con reproductor minimizado flotante, historial interactivo y ventanas dedicadas para repetir o descargar.

---

## 🌟 Novedades de la Versión 2.0 (Sincronización en Vivo)

1. **⚡ Transmisión en Tiempo Real entre Dispositivos:**
   - Si tienes **VoicePlace abierto en tu celular** y estás escribiendo en tu **laptop**: al presionar *"Hacer sonar en el Celular"*, el audio se sintetiza y se envía de inmediato al teléfono vía WebSockets.
   - En la pantalla de tu celular aparece automáticamente el **Reproductor Flotante Minimizado** en la parte inferior y comienza a reproducirse por los altavoces de tu teléfono.

2. **📱 Reproductor Flotante Minimizado (Bottom Mini-Player):**
   - Barra flotante oscura con bordes iluminados fija en la parte inferior.
   - Controles inmediatos:
     - **`↻ Repetir`**: Vuelve a reproducir el audio actual desde el segundo cero con un solo toque.
     - **`⏯️ Play / Pausa`**
     - Contador de tiempo transcurrido / total (ej.: *`⏱️ 0:15 / 1:24`*).
     - **`🔍 Expandir`**: Abre la ventana dedicada del audio.

3. **📜 Historial Persistente de Audios en Vivo (SQLite):**
   - Cada audio generado queda guardado en la base de datos local [`voiceplace.db`](file:///home/dhamit/Documentos/MYCreIAtedAPPs/VoicePlace/voiceplace.db).
   - Puedes revisar el texto completo, la voz con su bandera (ej.: 🇨🇴 Salomé), la velocidad y la duración exacta en minutos y segundos.
   - Acciones directas por cada tarjeta:
     - `▶️ Reproducir aquí`
     - `🔍 Ventana dedicada`
     - `⬇️ Descargar MP3`

4. **🪟 Ventana Dedicada del Reproductor (`/player/{id}`):**
   - Si pulsas *"Ventana dedicada"*, se abre en una pestaña o ventana independiente enfocada únicamente en ese audio.
   - Ideal para guardarlo como marcador, descargarlo, inspeccionar su duración o compartir el enlace directo para escucharlo en cualquier otro dispositivo.

5. **⏱️ Cálculo de Duración en Minutos y Segundos:**
   - **En vivo:** Estima en tiempo real según el texto y la velocidad (ej.: *`⏱️ Estimado: 1 min 15 seg (a 1.25x)`*).
   - **Real:** Lee los metadatos precisos del archivo MP3 generado con `mutagen` (ej.: *`⏱️ 1 min 24 seg (84.3s)`*).

---

## 🚀 Cómo Conectarte desde tu Celular

1. **Abre VoicePlace en tu celular:**
   - Por red Wi-Fi local: 👉 **`http://10.155.27.82:8095`**
   - Por Tailscale (desde cualquier lugar): 👉 **`http://100.97.169.86:8095`**
   - O escanea el código QR desde tu laptop en **`http://localhost:8095`**.
2. **Toca la barra superior una vez:**
   - Verás el mensaje *"Toca aquí una vez para activar audio en este celular"*.
   - Los navegadores móviles exigen este primer toque para autorizar el audio.
   - Una vez tocado, cambiará a **`🟢 Celular listo y conectado`**.
3. **¡Listo!** Ahora cualquier texto que envíes desde tu laptop sonará inmediatamente en los altavoces de tu celular.
