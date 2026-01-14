#!/usr/bin/env python3
import fcntl
import json
import getpass
import socket
import subprocess
import sys
import threading
import time
import os
from typing import Optional


MULTICAST_GROUP = '224.1.1.1'
PORT = 5007

OVERLAY_TITLE = "EduControl"
OVERLAY_MESSAGE = (
    "ATENCIÓN\n\n"
    "Pantalla bloqueada por el profesor.\n\n"
    "Sigue las instrucciones en clase."
)

_overlay_lock = threading.Lock()
_overlay_enabled = False
_overlay_thread: Optional[threading.Thread] = None
_overlay_proc: Optional[subprocess.Popen] = None


_instance_lock_fh = None


def _acquire_single_instance_lock() -> None:
    global _instance_lock_fh
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    if runtime_dir:
        lock_path = os.path.join(runtime_dir, "educontrol-client.lock")
    else:
        lock_path = f"/tmp/educontrol-client-{os.getuid()}.lock"

    os.makedirs(os.path.dirname(lock_path), exist_ok=True)
    fh = open(lock_path, "w", encoding="utf-8")
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        _log("Ya hay otra instancia de educontrol-client ejecutándose; saliendo.")
        raise SystemExit(0)

    fh.write(str(os.getpid()))
    fh.flush()
    _instance_lock_fh = fh


def _log(message: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {message}"
    print(line, flush=True)
    try:
        state_home = os.environ.get("XDG_STATE_HOME")
        if not state_home:
            # En Flatpak, la ruta persistente típica es ~/.var/app/<APP_ID>/state
            # (visible también desde el host). Si existe, la preferimos.
            flatpak_id = os.environ.get("FLATPAK_ID")
            if flatpak_id:
                candidate = os.path.join(
                    os.path.expanduser("~"), ".var", "app", flatpak_id, "state"
                )
                state_home = candidate
            else:
                state_home = os.path.join(os.path.expanduser("~"), ".local", "state")
        os.makedirs(state_home, exist_ok=True)
        log_path = os.path.join(state_home, "educontrol-client.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        # Logging nunca debe tumbar el cliente
        pass


def _resolve_gui_env() -> dict[str, str]:
    """Devuelve un entorno para procesos GUI (overlay/zenity) intentando corregir DISPLAY/WAYLAND.

    En algunos escritorios (p.ej. Bodhi/Moksha) el autostart puede lanzar la app con
    DISPLAY incorrecto (ej. :99) aunque la sesión real sea :0. Esto haría que el overlay
    no aparezca. Aquí intentamos detectar un socket válido y usarlo.
    """
    env = os.environ.copy()

    # Wayland: el socket suele estar en $XDG_RUNTIME_DIR/$WAYLAND_DISPLAY
    wayland_display = env.get("WAYLAND_DISPLAY", "")
    xdg_runtime = env.get("XDG_RUNTIME_DIR", "")
    if wayland_display and xdg_runtime:
        wayland_path = os.path.join(xdg_runtime, wayland_display)
        if not os.path.exists(wayland_path):
            env.pop("WAYLAND_DISPLAY", None)

    # X11: valida /tmp/.X11-unix/XN
    display = env.get("DISPLAY", "")

    def x_socket_exists(disp: str) -> bool:
        # Acepta formatos ':0', ':0.0'
        if not disp.startswith(":"):
            return False
        try:
            num_str = disp[1:].split(".", 1)[0]
            num = int(num_str)
        except Exception:
            return False
        return os.path.exists(f"/tmp/.X11-unix/X{num}")

    if display:
        if not x_socket_exists(display):
            # Fallback típico
            if x_socket_exists(":0"):
                env["DISPLAY"] = ":0"
            else:
                env.pop("DISPLAY", None)
    else:
        if x_socket_exists(":0"):
            env["DISPLAY"] = ":0"

    return env

def _gdbus_call(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["gdbus", "call", *args],
        capture_output=True,
        text=True,
    )


def _start_overlay() -> None:
    global _overlay_enabled, _overlay_thread
    with _overlay_lock:
        if _overlay_enabled:
            return
        _overlay_enabled = True

        t = threading.Thread(target=_overlay_loop, name="overlay", daemon=True)
        _overlay_thread = t
        t.start()


def _stop_overlay() -> None:
    global _overlay_enabled
    with _overlay_lock:
        _overlay_enabled = False
        proc = _overlay_proc

    if proc and proc.poll() is None:
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


def _overlay_loop() -> None:
    # Mantiene un diálogo grande "encima" reabriéndolo si se cierra.
    # No es un bloqueo de seguridad, pero sí un modo "aula" práctico.
    global _overlay_proc
    while True:
        with _overlay_lock:
            enabled = _overlay_enabled
        if not enabled:
            return

        gui_env = _resolve_gui_env()
        display = gui_env.get("DISPLAY", "")
        wayland_display = gui_env.get("WAYLAND_DISPLAY", "")
        if not display and not wayland_display:
            _log(
                "Overlay: no hay DISPLAY/WAYLAND_DISPLAY. "
                "Ejecuta el cliente desde la sesión gráfica (no por SSH/servicio)."
            )
            time.sleep(2)
            continue

        try:
            # Preferimos overlay propio fullscreen (sin botón).
            # Buscamos el binario en varias rutas para soportar la instalación nativa.
            overlay_candidates = (
                "/app/bin/educontrol-overlay",
                "/usr/bin/educontrol-overlay",
                "/usr/share/educontrol/educontrol-overlay",
                "/opt/educontrol/educontrol-overlay",
            )
            overlay_bin = None
            for p in overlay_candidates:
                if os.path.exists(p) and os.access(p, os.X_OK):
                    overlay_bin = p
                    break

            if overlay_bin:
                proc = subprocess.Popen(
                    [overlay_bin, OVERLAY_MESSAGE],
                    env=gui_env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
            else:
                # Fallback a zenity cuando no exista binario propio.
                proc = subprocess.Popen(
                    [
                        "zenity",
                        "--info",
                        "--title",
                        OVERLAY_TITLE,
                        "--no-wrap",
                        "--text",
                        OVERLAY_MESSAGE,
                        "--ok-label",
                        "Aceptar",
                    ],
                    env=gui_env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
            with _overlay_lock:
                _overlay_proc = proc

            # Espera a que el usuario lo cierre; si sigue bloqueado, se reabre.
            out, err = proc.communicate()
            if out:
                _log(f"overlay stdout: {out.strip()}")
            if err:
                _log(f"overlay stderr: {err.strip()}")
        except FileNotFoundError:
            _log("zenity no está disponible; no se puede mostrar el mensaje de bloqueo.")
            time.sleep(2)
        except Exception as exc:
            _log(f"Error mostrando overlay: {exc}")
            time.sleep(1)

def _print_gdbus_error(prefix: str, result: subprocess.CompletedProcess) -> None:
    if result.returncode == 0:
        return
    stderr = (result.stderr or "").strip()
    stdout = (result.stdout or "").strip()
    if stderr:
        print(f"{prefix}: {stderr}", flush=True)
    elif stdout:
        # gdbus a veces devuelve el error por stdout.
        print(f"{prefix}: {stdout}", flush=True)
    else:
        print(f"{prefix}: fallo (rc={result.returncode})", flush=True)


def _try_lock_screensaver(dest: str) -> bool:
    # Muchos DE exponen un servicio *ScreenSaver* propio (GNOME/MATE/Cinnamon, etc).
    # El método suele ser <dest>.Lock en /ScreenSaver.
    if dest == "org.freedesktop.ScreenSaver":
        method = "org.freedesktop.ScreenSaver.Lock"
    else:
        method = f"{dest}.Lock"

    result = _gdbus_call(
        [
            "--session",
            "--dest",
            dest,
            "--object-path",
            "/ScreenSaver",
            "--method",
            method,
        ]
    )
    if result.returncode == 0:
        _log(f"Bloqueo OK via {dest}.")
        return True

    _print_gdbus_error(f"Bloqueo via {dest} falló", result)
    return False

def _try_lock_login1() -> bool:
    # logind (system bus) suele estar disponible en Ubuntu y no depende del DE.
    result = _gdbus_call(
        [
            "--system",
            "--dest",
            "org.freedesktop.login1",
            "--object-path",
            "/org/freedesktop/login1",
            "--method",
            "org.freedesktop.login1.Manager.LockSessions",
        ]
    )
    if result.returncode == 0:
        _log("Bloqueo OK via org.freedesktop.login1 (LockSessions).")
        return True
    _print_gdbus_error("Bloqueo via org.freedesktop.login1 falló", result)
    return False

def bloquear_pantalla():
    # Modo aula: mostramos un mensaje llamativo que se mantiene hasta 'unlock'.
    _start_overlay()

    # Además intentamos el bloqueo nativo del sistema (si existe).
    # Algunos entornos (p.ej. GNOME en Ubuntu) no exponen org.freedesktop.ScreenSaver.
    # Probamos varios backends antes de rendirnos.
    for dest in (
        "org.freedesktop.ScreenSaver",
        "org.gnome.ScreenSaver",
        "org.mate.ScreenSaver",
        "org.cinnamon.ScreenSaver",
    ):
        if _try_lock_screensaver(dest):
            return
    if _try_lock_login1():
        return

    print(
        "No se pudo bloquear la pantalla via DBus (ScreenSaver/login1). "
        "Revisa que el sistema tenga un locker activo y que el Flatpak tenga permisos DBus."
    )

def desbloquear_pantalla():
    _stop_overlay()

    # Desbloquear de forma programática suele estar bloqueado por seguridad.
    # Intentamos desactivar el salvapantallas; si está bloqueado, seguirá requiriendo contraseña.
    for dest, method in (
        ("org.freedesktop.ScreenSaver", "org.freedesktop.ScreenSaver.SetActive"),
        ("org.gnome.ScreenSaver", "org.freedesktop.ScreenSaver.SetActive"),
    ):
        result = _gdbus_call(
            [
                "--session",
                "--dest",
                dest,
                "--object-path",
                "/ScreenSaver",
                "--method",
                method,
                "false",
            ]
        )
        if result.returncode == 0:
            return

    print("Desbloqueo manual necesario (si aplica).")


def abrir_url_en_navegador(url: str) -> None:
    """Intenta abrir la URL en el navegador por defecto del usuario usando xdg-open.

    Solo acepta esquemas http/https/file para evitar abusos.
    """
    url = url.strip()
    if not url:
        _log("open: URL vacía; ignorando.")
        return

    lower = url.lower()
    if not (lower.startswith("http://") or lower.startswith("https://") or lower.startswith("file://")):
        _log(f"open: esquema no soportado en URL: {url}")
        return

    gui_env = _resolve_gui_env()
    display = gui_env.get("DISPLAY", "")
    wayland_display = gui_env.get("WAYLAND_DISPLAY", "")
    if not display and not wayland_display:
        _log("open: no hay DISPLAY/WAYLAND_DISPLAY; no se puede abrir navegador desde contexto actual.")
        return

    try:
        _log(f"Abriendo URL en navegador: {url}")
        subprocess.Popen(["xdg-open", url], env=gui_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        _log("xdg-open no está disponible en este sistema.")
    except Exception as exc:
        _log(f"Error al abrir URL: {exc}")

def main():
    # Evita buffering cuando se ejecuta desde Flatpak (útil para logs y depuración).
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass

    _acquire_single_instance_lock()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', PORT))

    # Unirse al grupo multicast es opcional: si falla, seguiremos recibiendo broadcast/unicast.
    try:
        mreq = socket.inet_aton(MULTICAST_GROUP) + socket.inet_aton('0.0.0.0')
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    except OSError as exc:
        print(f"Aviso: no se pudo unir al grupo multicast ({exc}).", flush=True)

    _log("Cliente iniciado. Escuchando comandos...")
    while True:
        data, addr = sock.recvfrom(1024)
        comando = data.decode('utf-8', errors='replace').strip()
        if comando == 'who':
            try:
                gui_env = _resolve_gui_env()
                payload = {
                    "type": "educontrol-client",
                    "v": 1,
                    "hostname": socket.gethostname(),
                    "user": getpass.getuser(),
                    "pid": os.getpid(),
                    "display": gui_env.get("DISPLAY") or "",
                    "wayland": gui_env.get("WAYLAND_DISPLAY") or "",
                    "ts": int(time.time()),
                }
                msg = "iam " + json.dumps(payload, ensure_ascii=False)
                sock.sendto(msg.encode("utf-8"), addr)
                _log(f"who: respondido a {addr[0]}:{addr[1]}")
            except Exception as exc:
                _log(f"who: error respondiendo: {exc}")
            continue
        if comando == 'lock':
            _log("Recibido comando para bloquear pantalla.")
            bloquear_pantalla()
        elif comando == 'unlock':
            _log("Recibido comando para desbloquear pantalla.")
            desbloquear_pantalla()
        elif comando.startswith('open '):
            url = comando[len('open '):].strip()
            _log(f"Recibido comando para abrir URL: {url}")
            abrir_url_en_navegador(url)
        elif comando.startswith('exec '):
            cmd = comando[len('exec '):].strip()
            if not cmd:
                _log('exec: comando vacío; ignorando.')
            else:
                _log(f"Recibido comando exec: {cmd}")
                try:
                    gui_env = _resolve_gui_env()
                    subprocess.Popen(cmd, shell=True, env=gui_env)
                    _log(f"exec: comando lanzado: {cmd}")
                except Exception as exc:
                    _log(f"exec: fallo al lanzar comando: {exc}")

if __name__ == "__main__":
    main()