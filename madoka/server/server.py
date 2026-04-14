"""
Madoka Scanner - Servidor de produccion
Usa la API Python de Magika directamente (sin subprocess)
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from pathlib import Path
import os
import sys
import logging

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(
            os.path.join(os.path.dirname(__file__), "madoka.log"),
            encoding="utf-8"
        ),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger("madoka")

# ── Magika (API Python directa) ───────────────────────────────────────────────
try:
    from magika import Magika
    _magika = Magika()
    log.info("Magika cargado correctamente via API Python")
except ImportError:
    log.error("Magika no está instalado — ejecuta: pip install magika")
    _magika = None

# ── Flask ─────────────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app, origins=["chrome-extension://*", "moz-extension://*"])

EXTENSION_MAP = {
    "pdf":  ["pdf"],
    "exe":  ["pe", "msi"],
    "zip":  ["zip"],
    "docx": ["docx", "zip"],
    "xlsx": ["xlsx", "zip"],
    "jpg":  ["jpeg"],
    "jpeg": ["jpeg"],
    "png":  ["png"],
    "gif":  ["gif"],
    "mp4":  ["mp4"],
    "mp3":  ["mp3"],
    "py":   ["python"],
    "js":   ["javascript"],
    "html": ["html"],
    "txt":  ["txt"],
}
SUSPICIOUS_TYPES = ["pe", "elf", "msi", "bat", "powershell", "sh"]


def analyze_file(file_path: str) -> dict:
    """Analiza un archivo usando la API Python de Magika."""
    if _magika is None:
        raise RuntimeError("Magika no está instalado")

    result = _magika.identify_path(Path(file_path))

    # Magika devuelve un objeto MagikaResult
    # Intentamos las distintas formas en que puede venir el resultado
    # segun la version instalada
    try:
        label = result.output.ct_label
    except AttributeError:
        try:
            label = result.dl.ct_label
        except AttributeError:
            label = str(result.output) if hasattr(result, "output") else "unknown"

    try:
        score = float(result.output.score)
    except AttributeError:
        try:
            score = float(result.dl.score)
        except AttributeError:
            try:
                score = float(result.score)
            except AttributeError:
                score = 0.0
    # Normalizar: Magika algunas veces devuelve 0.0 aunque hay confianza alta.
    # En ese caso usamos 1.0 si el label no es unknown.
    if score == 0.0 and str(label) not in ("unknown", "txt"):
        score = 1.0

    try:
        mime_type = result.output.mime_type
    except AttributeError:
        mime_type = ""

    try:
        description = result.output.description
    except AttributeError:
        description = ""

    return {
        "label":       str(label),
        "score":       float(score),
        "mime_type":   str(mime_type),
        "description": str(description),
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.route("/ping", methods=["GET"])
def ping():
    return {"status": "ok", "magika": "ready" if _magika else "not installed"}


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    file_path = os.path.normpath(data.get("path", "").strip())

    log.info(f"Analizando: '{file_path}'")

    if not file_path:
        return {"error": "No se proporcionó ruta"}, 400

    if not os.path.exists(file_path):
        log.warning(f"Archivo no encontrado: {file_path}")
        return {"error": f"Archivo no encontrado: {file_path}"}, 404

    log.info(f"Tamaño: {os.path.getsize(file_path):,} bytes")

    try:
        result = analyze_file(file_path)
    except Exception as e:
        log.error(f"Error analizando: {e}")
        return {"error": str(e)}, 500

    label        = result["label"]
    declared_ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
    expected     = EXTENSION_MAP.get(declared_ext, [])
    mismatch     = bool(declared_ext and expected and label not in expected)
    suspicious   = label in SUSPICIOUS_TYPES

    log.info(f"Resultado → label={label}, score={result['score']:.2f}, "
             f"mismatch={mismatch}, suspicious={suspicious}")

    return {
        "label":              label,
        "score":              result["score"],
        "mime_type":          result["mime_type"],
        "description":        result["description"],
        "extension_mismatch": mismatch,
        "suspicious":         suspicious,
        "declared_extension": declared_ext,
    }


@app.route("/debug", methods=["GET"])
def debug_page():
    log_path = os.path.join(os.path.dirname(__file__), "madoka.log")
    try:
        with open(log_path, encoding="utf-8") as f:
            log_content = "".join(f.readlines()[-50:])
    except Exception:
        log_content = "(sin log aún)"

    port = int(os.environ.get("MADOKA_PORT", 5050))
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Madoka Debug</title>
<style>
  body{{font-family:monospace;background:#1a1a1a;color:#e5e5e5;padding:24px;margin:0}}
  h2{{color:#a78bfa;margin-top:0}} h3{{color:#7dd3fc}}
  pre{{background:#2a2a2a;padding:16px;border-radius:8px;font-size:12px;
       white-space:pre-wrap;word-break:break-all;max-height:500px;overflow-y:auto}}
  .ok{{color:#22c55e}} .warn{{color:#f59e0b}}
  .reload{{background:#4f46e5;color:#fff;border:none;padding:8px 16px;
           border-radius:6px;cursor:pointer;font-size:13px;margin-bottom:16px}}
</style></head><body>
<h2>Madoka Scanner — Diagnóstico</h2>
<p class="ok">✔ Servidor activo · Puerto {port} · 
   Magika: {"✔ cargado" if _magika else "✘ no instalado"}</p>
<button class="reload" onclick="location.reload()">↻ Actualizar log</button>
<h3>Log reciente</h3>
<pre>{log_content or "(vacío — descarga un archivo para ver actividad)"}</pre>
</body></html>"""


# ── Servidor de produccion ────────────────────────────────────────────────────
def run_production():
    import platform
    port = int(os.environ.get("MADOKA_PORT", 5050))
    host = "127.0.0.1"
    log.info(f"Iniciando Madoka Scanner en http://{host}:{port}")

    if platform.system() == "Windows":
        try:
            from waitress import serve
            log.info("Motor: waitress")
            serve(app, host=host, port=port, threads=4)
        except ImportError:
            log.warning("waitress no instalado, usando Flask dev server")
            app.run(host=host, port=port)
    else:
        try:
            import gunicorn.app.base

            class StandaloneApp(gunicorn.app.base.BaseApplication):
                def __init__(self, application, options=None):
                    self.options = options or {}
                    self.application = application
                    super().__init__()
                def load_config(self):
                    for k, v in self.options.items():
                        self.cfg.set(k.lower(), v)
                def load(self):
                    return self.application

            opts = {"bind": f"{host}:{port}", "workers": 2, "loglevel": "warning"}
            log.info("Motor: gunicorn")
            StandaloneApp(app, opts).run()
        except ImportError:
            log.warning("gunicorn no instalado, usando Flask dev server")
            app.run(host=host, port=port)


if __name__ == "__main__":
    run_production()
