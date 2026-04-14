# Madoka Scanner

> Analiza cada archivo que descargas usando inteligencia artificial, antes de que lo abras.

Madoka Scanner es una extensión para navegador que se conecta a un servidor local en tu PC y usa **Google Magika** - el mismo motor de IA que usa Google internamente en Gmail, Drive y VirusTotal - para detectar el tipo real de cada archivo descargado, independientemente de su extensión declarada.

Si descargas un archivo `.jpg` que en realidad es un ejecutable, Madoka te avisa antes de que lo abras.

---

## Cómo funciona

```
Tu navegador          Servidor local (tu PC)         Motor de IA
─────────────         ──────────────────────         ───────────
Descarga completa  →  Recibe la ruta del archivo  →  Google Magika analiza
                      Verifica que el archivo           el contenido real
                      existe en disco             ←  Devuelve tipo + confianza
                   ←  Envía resultado a la
Muestra notificación  extensión
```

Todo ocurre **localmente en tu PC**. Ningún archivo se sube a internet.

---

## Requisitos

- **Python 3.8 o superior** - [python.org/downloads](https://www.python.org/downloads/)
- **Windows, macOS o Linux**
- **Edge, Chrome o Firefox**

---

## Instalación

### Paso 1 - Descargar

Descarga el archivo `madoka.zip` desde [Releases](../../releases) y descomprímelo en una carpeta permanente, por ejemplo:

- Windows: `C:\Users\TuUsuario\madoka\`
- macOS/Linux: `~/madoka/`

> ⚠️ No lo descomprimas en la carpeta de Descargas - si la limpias, dejarás de tener el servidor.

---

### Paso 2 - Instalar el servidor

Abre una terminal en la carpeta donde descomprimiste el ZIP y ejecuta:

**Windows (PowerShell)**
```powershell
python madoka.py
```

**macOS / Linux**
```bash
python3 madoka.py
```

El instalador hace lo siguiente automáticamente:
1. Instala las dependencias Python (`magika`, `flask`, `waitress`, etc.)
2. Registra el servidor para que arranque automáticamente con tu sesión
3. Inicia el servidor inmediatamente
4. Verifica que todo responde correctamente

Al terminar verás algo así:
```
✔  Dependencias instaladas
✔  Agregado al inicio de sesión del usuario
✔  Servidor activo en http://localhost:5050
```

> **Sin permisos de administrador en Windows:** El instalador usa automáticamente el registro de inicio de sesión del usuario - funciona igual, sin necesidad de ejecutar como administrador.

> **Con permisos de administrador en Windows:** El servidor se instala como servicio de Windows real y aparece en `services.msc` como "Madoka Scanner". Arranca incluso antes de que inicies sesión.

---

### Paso 3 - Verificar el servidor

Abre tu navegador y ve a:
```
http://localhost:5050/ping
```

Debes ver:
```json
{"status": "ok", "magika": "ready"}
```

Si no carga, el servidor no está corriendo. Inícialo manualmente:
```powershell
python madoka.py start
```

---

### Paso 4 - Instalar la extensión

#### Edge y Chrome

1. Abre `edge://extensions/` o `chrome://extensions/`
2. Activa **Modo desarrollador** (toggle en la esquina superior derecha)
3. Haz clic en **Cargar sin empaquetar** (Edge) o **Cargar descomprimida** (Chrome)
4. Selecciona la carpeta **`extension/`** dentro del ZIP descomprimido

#### Firefox

1. Abre `about:debugging`
2. Haz clic en **Este Firefox**
3. Haz clic en **Cargar complemento temporal**
4. Selecciona el archivo **`extension-firefox/manifest.json`**

> **Nota Firefox:** La instalación temporal se pierde al cerrar Firefox. Para instalación permanente necesitas firmar la extensión en [addons.mozilla.org](https://addons.mozilla.org/developers/) o usar Firefox Developer Edition con `xpinstall.signatures.required = false` en `about:config`.

#### Safari

Safari requiere conversión con Xcode en macOS:
```bash
xcrun safari-web-extension-converter extension/ --project-location ~/Desktop --app-name "MadokaScanner"
```
Abre el proyecto generado en Xcode y ejecútalo. Solo disponible en Mac con Xcode instalado.

---

### Paso 5 - Activar notificaciones

Al hacer clic en el ícono de Madoka en la barra del navegador, se abre el popup. Haz clic en el botón **⚙** (ajustes) y activa **Notificaciones**. Si es la primera vez, el navegador te pedirá permiso - acéptalo.

---

## Uso

Una vez instalado, Madoka funciona en segundo plano sin que tengas que hacer nada.

Cuando termina una descarga, aparece una notificación en la esquina de tu pantalla:

| Resultado | Notificación |
|---|---|
| Archivo normal | ✅ **Madoka - Archivo verificado** · `runner.pdf` · Tipo: PDF Document (99% confianza) |
| Extensión sospechosa | ⚠️ **Madoka - Extensión no coincide** · `foto.jpg` · Extensión .jpg pero contenido: PE executable |
| Ejecutable detectado | ⚠️ **Madoka - Tipo ejecutable detectado** · `instalador.zip` · Tipo real: PE executable |

---

## El popup

Haz clic en el ícono de Madoka en la barra del navegador para ver:

- **Toggle ON/OFF** - Activa o desactiva el escáner sin desinstalar la extensión
- **Estado del servidor** - Punto verde si el servidor local responde, rojo si no
- **Historial** - Las últimas 12 descargas analizadas con su resultado
- **⚙ Ajustes** - Panel con opciones adicionales

### Ajustes disponibles

| Ajuste | Descripción |
|---|---|
| **Notificaciones** | Activa/desactiva las alertas del sistema. Si no hay permiso, lo solicita automáticamente |
| **Analizar descargas** | Activa/desactiva el análisis automático al completar cada descarga |
| **Solo alertar si hay riesgo** | Silencia las notificaciones de archivos normales (✅). Solo muestra alertas ⚠️ |

---

## Comandos del instalador

Desde la carpeta donde está `madoka.py`:

```bash
python madoka.py              # Instalar y registrar como servicio
python madoka.py start        # Iniciar el servidor manualmente
python madoka.py stop         # Detener el servidor
python madoka.py status       # Ver si el servidor está corriendo
python madoka.py remove       # Desinstalar completamente
```

### Puerto personalizado

Si el puerto 5050 está ocupado por otra aplicación:
```bash
MADOKA_PORT=5051 python madoka.py
```

---

## Diagnóstico

Si algo no funciona, revisa el log del servidor. Mientras `server.py` está corriendo, abre:
```
http://localhost:5050/debug
```

Verás los últimos registros de actividad, incluyendo qué archivos se analizaron y si hubo errores.

También puedes ver los logs de la extensión en el navegador:
1. Ve a `edge://extensions/` o `chrome://extensions/`
2. Busca **Madoka Scanner**
3. Haz clic en **Service Worker** o **Inspeccionar vistas**
4. Pestaña **Console** - verás mensajes `[Madoka]` en tiempo real

---

## Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| No aparecen notificaciones | Permisos no concedidos | Abre el popup → ⚙ → activa Notificaciones |
| Notificaciones bloqueadas | Windows tiene Edge silenciado | `Win+I` → Sistema → Notificaciones → activar Microsoft Edge |
| Servidor offline (punto rojo) | El servidor no está corriendo | `python madoka.py start` |
| Error 500 al analizar | Magika no está instalado | `pip install magika` |
| `python` no se reconoce | Python no está en el PATH | Reinstala Python marcando "Add to PATH" |
| El servidor se detuvo al reiniciar | Instalación sin admin no persistió | Vuelve a correr `python madoka.py` |

---

## Desinstalar

```bash
python madoka.py remove
```

Luego en el navegador ve a `edge://extensions/` y elimina **Madoka Scanner**.

---

## Tecnologías

| Componente | Tecnología |
|---|---|
| Motor de detección | [Google Magika](https://github.com/google/magika) - deep learning, ~99% precisión |
| Servidor local | Python + Flask + Waitress (Windows) / Gunicorn (macOS/Linux) |
| Extensión | Manifest V3 (Chrome/Edge), Manifest V2 (Firefox) |
| Comunicación | HTTP local en `127.0.0.1:5050` - nunca sale de tu PC |

---

## Privacidad

- Los archivos **nunca salen de tu PC**
- El servidor escucha únicamente en `127.0.0.1` (no accesible desde la red)
- No se recopilan datos, no hay telemetría, no hay cuenta de usuario
- El historial de análisis se guarda localmente en el almacenamiento de la extensión

---

## Licencia

MIT - úsalo, modifícalo y distribúyelo libremente.

---

*Madoka Scanner usa Google Magika internamente. Madoka no está afiliado a Google.*
