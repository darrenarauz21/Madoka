#!/usr/bin/env python3
"""
madoka.py — Instalador de Madoka Scanner
Uso:
  python madoka.py            -> instalar
  python madoka.py remove     -> desinstalar
  python madoka.py status     -> ver estado
  python madoka.py start      -> iniciar manualmente
  python madoka.py stop       -> detener
"""

import sys, os, subprocess, platform, time, urllib.request, urllib.error

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
SERVER_PATH  = os.path.join(SCRIPT_DIR, "server", "server.py")
SERVICE_NAME = "MadokaScanner"          # nombre único, no colisiona con nada
DISPLAY_NAME = "Madoka Scanner"
PORT         = int(os.environ.get("MADOKA_PORT", 5050))
SYSTEM       = platform.system()        # Windows / Darwin / Linux

# ── Colores ANSI ─────────────────────────────────────────────────────────────
def ok(msg):   print(f"  \033[32m✔\033[0m  {msg}")
def err(msg):  print(f"  \033[31m✘\033[0m  {msg}")
def info(msg): print(f"  \033[36m→\033[0m  {msg}")
def hdr(msg):  print(f"\n\033[1m{msg}\033[0m")

# ── Helpers ───────────────────────────────────────────────────────────────────
def run(cmd, check=True, shell=False):
    return subprocess.run(cmd, check=check, shell=shell,
                          capture_output=True, text=True)

def python_exe():
    return sys.executable

def pip(*packages):
    info(f"pip install {' '.join(packages)}")
    run([python_exe(), "-m", "pip", "install", "--quiet", *packages])

def ping_server():
    try:
        res = urllib.request.urlopen(f"http://localhost:{PORT}/ping", timeout=3)
        return res.status == 200
    except Exception:
        return False

# ── Dependencias ──────────────────────────────────────────────────────────────
def install_deps():
    hdr("[1/4] Dependencias Python")
    pip("magika", "flask", "flask-cors")
    if SYSTEM == "Windows":
        pip("waitress", "pywin32")
    else:
        pip("gunicorn")
    ok("Dependencias instaladas")

# ── Windows ───────────────────────────────────────────────────────────────────
def install_windows():
    hdr("[2/4] Servicio de Windows")
    svc_path = os.path.join(SCRIPT_DIR, "server", "madoka_service.py")
    with open(svc_path, "w") as f:
        f.write(f"""
import win32serviceutil, win32service, win32event, servicemanager
import subprocess, sys

class MadokaService(win32serviceutil.ServiceFramework):
    _svc_name_         = "{SERVICE_NAME}"
    _svc_display_name_ = "{DISPLAY_NAME}"
    _svc_description_  = "Servidor local para la extension Madoka Scanner (madoka)"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.process   = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        if self.process: self.process.terminate()
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED, (self._svc_name_, ""))
        self.process = subprocess.Popen(
            [r"{python_exe()}", r"{SERVER_PATH}"],
            env={{**__import__("os").environ, "MADOKA_PORT": "{PORT}"}}
        )
        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)

if __name__ == "__main__":
    win32serviceutil.HandleCommandLine(MadokaService)
""")
    try:
        run([python_exe(), svc_path, "--startup=auto", "install"])
        run(["net", "start", SERVICE_NAME], shell=True)
        ok(f"Servicio '{SERVICE_NAME}' registrado (services.msc)")
        ok("Arranca automáticamente con Windows (incluso antes de iniciar sesión)")
    except Exception:
        info("Sin permisos de administrador — usando modo usuario (normal)")
        info("El servidor arrancará automáticamente al iniciar sesión")
        _windows_registry_fallback()

def _windows_registry_fallback():
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE)
        cmd = f'"{python_exe()}" "{SERVER_PATH}"'
        winreg.SetValueEx(key, SERVICE_NAME, 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(key)
        ok("Agregado al inicio de sesión del usuario (HKCU\\Run)")
        # Iniciar ahora mismo en background
        subprocess.Popen([python_exe(), SERVER_PATH],
                         creationflags=subprocess.DETACHED_PROCESS |
                                       subprocess.CREATE_NEW_PROCESS_GROUP)
    except Exception as e:
        err(f"No se pudo agregar al registro: {e}")

def remove_windows():
    hdr("Desinstalando — Windows")
    run(["net", "stop", SERVICE_NAME], check=False, shell=True)
    run(["sc", "delete", SERVICE_NAME], check=False, shell=True)
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, SERVICE_NAME)
        winreg.CloseKey(key)
    except Exception:
        pass
    ok("Eliminado")

def status_windows():
    result = run(["sc", "query", SERVICE_NAME], check=False, shell=True)
    if "RUNNING" in result.stdout:
        ok(f"Servicio '{SERVICE_NAME}' está CORRIENDO")
    elif "STOPPED" in result.stdout:
        err(f"Servicio '{SERVICE_NAME}' está DETENIDO")
    else:
        err(f"Servicio '{SERVICE_NAME}' no encontrado (puede estar en registro de inicio)")

def start_windows():
    run(["net", "start", SERVICE_NAME], check=False, shell=True)

def stop_windows():
    run(["net", "stop", SERVICE_NAME], check=False, shell=True)

# ── macOS ─────────────────────────────────────────────────────────────────────
PLIST_PATH = os.path.expanduser("~/Library/LaunchAgents/com.madoka.scanner.plist")

def install_mac():
    hdr("[2/4] LaunchAgent — macOS")
    os.makedirs(os.path.dirname(PLIST_PATH), exist_ok=True)
    with open(PLIST_PATH, "w") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key>             <string>com.madoka.scanner</string>
  <key>ProgramArguments</key>
  <array>
    <string>{python_exe()}</string>
    <string>{SERVER_PATH}</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict><key>MADOKA_PORT</key><string>{PORT}</string></dict>
  <key>RunAtLoad</key>         <true/>
  <key>KeepAlive</key>         <true/>
  <key>StandardOutPath</key>   <string>/tmp/madoka.log</string>
  <key>StandardErrorPath</key> <string>/tmp/madoka.log</string>
</dict></plist>""")
    run(["launchctl", "unload", PLIST_PATH], check=False)
    run(["launchctl", "load",   PLIST_PATH])
    ok("LaunchAgent registrado")
    ok("Se inicia automáticamente con la sesión")

def remove_mac():
    hdr("Desinstalando — macOS")
    run(["launchctl", "unload", PLIST_PATH], check=False)
    if os.path.exists(PLIST_PATH): os.remove(PLIST_PATH)
    ok("LaunchAgent eliminado")

def status_mac():
    r = run(["launchctl", "list", "com.madoka.scanner"], check=False)
    if r.returncode == 0: ok("LaunchAgent activo")
    else: err("LaunchAgent no encontrado o inactivo")

def start_mac():
    run(["launchctl", "load", PLIST_PATH], check=False)

def stop_mac():
    run(["launchctl", "unload", PLIST_PATH], check=False)

# ── Linux ─────────────────────────────────────────────────────────────────────
UNIT_PATH = os.path.expanduser("~/.config/systemd/user/madoka-scanner.service")

def install_linux():
    hdr("[2/4] Servicio systemd — Linux")
    os.makedirs(os.path.dirname(UNIT_PATH), exist_ok=True)
    with open(UNIT_PATH, "w") as f:
        f.write(f"""[Unit]
Description=Madoka Scanner (madoka) local server
After=network.target

[Service]
ExecStart={python_exe()} {SERVER_PATH}
Environment=MADOKA_PORT={PORT}
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
""")
    run(["systemctl", "--user", "daemon-reload"])
    run(["systemctl", "--user", "enable", "madoka-scanner"])
    run(["systemctl", "--user", "start",  "madoka-scanner"])
    ok("Servicio systemd activo")
    ok("Se inicia automáticamente con la sesión")

def remove_linux():
    hdr("Desinstalando — Linux")
    run(["systemctl", "--user", "stop",    "madoka-scanner"], check=False)
    run(["systemctl", "--user", "disable", "madoka-scanner"], check=False)
    if os.path.exists(UNIT_PATH): os.remove(UNIT_PATH)
    run(["systemctl", "--user", "daemon-reload"], check=False)
    ok("Servicio eliminado")

def status_linux():
    r = run(["systemctl", "--user", "is-active", "madoka-scanner"], check=False)
    if r.stdout.strip() == "active": ok("Servicio activo (systemd)")
    else: err(f"Servicio inactivo: {r.stdout.strip()}")

def start_linux():
    run(["systemctl", "--user", "start", "madoka-scanner"])

def stop_linux():
    run(["systemctl", "--user", "stop",  "madoka-scanner"])

# ── Despacho por SO ───────────────────────────────────────────────────────────
ACTIONS = {
    "Windows": dict(install=install_windows, remove=remove_windows,
                    status=status_windows,   start=start_windows,  stop=stop_windows),
    "Darwin":  dict(install=install_mac,     remove=remove_mac,
                    status=status_mac,       start=start_mac,      stop=stop_mac),
    "Linux":   dict(install=install_linux,   remove=remove_linux,
                    status=status_linux,     start=start_linux,    stop=stop_linux),
}

# ── Verificar servidor ────────────────────────────────────────────────────────
def verify():
    hdr("[3/4] Verificando servidor")
    for i in range(6):
        if ping_server():
            ok(f"Servidor activo en http://localhost:{PORT}")
            return True
        info(f"Esperando... ({i+1}/6)")
        time.sleep(2)
    err("No respondió — revisa el log o ejecuta: python madoka.py start")
    return False

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "install"
    dispatch = ACTIONS.get(SYSTEM, ACTIONS["Linux"])

    print("=" * 54)
    print(f"  madoka — {DISPLAY_NAME}")
    print(f"  Sistema: {SYSTEM}  |  Puerto: {PORT}  |  Acción: {action}")
    print("=" * 54)

    if action not in dispatch:
        err(f"Acción desconocida: {action}")
        info("Opciones: install | remove | status | start | stop")
        sys.exit(1)

    if action == "install":
        install_deps()

    dispatch[action]()

    if action == "install":
        verify()
        hdr("[4/4] Listo")
        ok(f"Servidor en http://localhost:{PORT}/ping")
        info("Carga la extensión:")
        info("  Chrome/Edge → carpeta /extension/")
        info("  Firefox     → carpeta /extension-firefox/")
        info("  Safari      → requiere Xcode en Mac (ver README)")
        info("Para desinstalar: python madoka.py remove")

    elif action in ("status",):
        info(f"Ping servidor: {'OK' if ping_server() else 'sin respuesta'}")

    print()

if __name__ == "__main__":
    main()
