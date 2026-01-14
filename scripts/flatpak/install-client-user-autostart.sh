#!/usr/bin/env bash
set -euo pipefail

APP_ID="com.educontrol.Client"
BUNDLE_PATH_DEFAULT="dist/educontrol-client.flatpak"

bundle_path="${1:-$BUNDLE_PATH_DEFAULT}"

if ! command -v flatpak >/dev/null 2>&1; then
  echo "Error: flatpak no está instalado o no está en PATH" >&2
  exit 1
fi

if [[ ! -f "$bundle_path" ]]; then
  echo "Error: no existe el bundle: $bundle_path" >&2
  echo "Uso: $0 [ruta/al/educontrol-client.flatpak]" >&2
  exit 1
fi

echo "Instalando $APP_ID (scope: --user) desde: $bundle_path" >&2

# Idempotente: si ya está instalado, continuamos (y si existe --reinstall, lo usamos).
install_out=""
if install_out=$(flatpak install --user -y --reinstall "$bundle_path" 2>&1); then
  :
else
  if echo "$install_out" | grep -qiE 'unknown option|unrecognized option'; then
    # Flatpak antiguo: reintenta sin --reinstall.
    install_out=$(flatpak install --user -y "$bundle_path" 2>&1) || true
  fi

  if echo "$install_out" | grep -qi 'already installed'; then
    echo "Aviso: $APP_ID ya estaba instalado; continúo configurando autostart." >&2
  elif echo "$install_out" | grep -qi 'Installation complete'; then
    :
  elif [[ -n "$install_out" ]]; then
    echo "$install_out" >&2
    exit 1
  fi
fi

autostart_dir="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"
autostart_file="$autostart_dir/${APP_ID}.desktop"

mkdir -p "$autostart_dir"

cat >"$autostart_file" <<EOF
[Desktop Entry]
Type=Application
Name=EduControl (Cliente)
Comment=Inicia automáticamente el cliente de EduControl al iniciar sesión
Exec=flatpak run --user $APP_ID
Terminal=false
X-GNOME-Autostart-enabled=true
EOF

echo "Autostart creado: $autostart_file" >&2

# Bodhi Linux (Moksha/Enlightenment) a veces no respeta XDG autostart.
# En esos casos, también registramos el .desktop en el directorio de startup de Enlightenment.
is_bodhi_or_enlightenment="0"
if [[ -r /etc/os-release ]]; then
  if grep -Eiq '^(ID|ID_LIKE)=.*\b(bodhi|moksha|enlightenment)\b' /etc/os-release; then
    is_bodhi_or_enlightenment="1"
  fi

  # Bodhi suele tener ID=ubuntu, pero el nombre lo delata.
  if grep -Eiq '^(NAME|PRETTY_NAME)=.*bodhi' /etc/os-release; then
    is_bodhi_or_enlightenment="1"
  fi
fi

if [[ "${XDG_CURRENT_DESKTOP:-}" =~ (Enlightenment|Moksha) ]]; then
  is_bodhi_or_enlightenment="1"
fi

if [[ "${DESKTOP_SESSION:-}" =~ (enlightenment|moksha|bodhi) ]]; then
  is_bodhi_or_enlightenment="1"
fi

# Si el usuario ya tiene estructura ~/.e, asumimos Enlightenment/Moksha aunque no haya env vars.
if [[ -d "$HOME/.e" ]]; then
  is_bodhi_or_enlightenment="1"
fi

if [[ "$is_bodhi_or_enlightenment" == "1" ]]; then
  e_startup_dir="$HOME/.e/e/applications/startup"
  e_desktop_file="$e_startup_dir/${APP_ID}.desktop"
  e_order_file="$e_startup_dir/.order"

  mkdir -p "$e_startup_dir"
  cp -f "$autostart_file" "$e_desktop_file"

  # Algunas versiones de Enlightenment usan un archivo .order para definir el arranque.
  # Si existe (o si queremos crearlo), aseguramos que el .desktop está listado.
  if [[ -f "$e_order_file" ]]; then
    if ! grep -Fxq "${APP_ID}.desktop" "$e_order_file"; then
      printf '%s\n' "${APP_ID}.desktop" >>"$e_order_file"
    fi
  else
    # Crear .order ayuda en entornos donde solo se respetan entradas listadas.
    printf '%s\n' "${APP_ID}.desktop" >"$e_order_file"
  fi

  echo "Autostart adicional (Enlightenment/Moksha) creado: $e_desktop_file" >&2

  # Fallback extra para casos donde el DE no respeta autostart XDG o no propaga bien el entorno.
  # Creamos un servicio systemd --user con DISPLAY/DBUS/XAUTHORITY explícitos.
  systemd_user_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
  unit_file="$systemd_user_dir/educontrol-client.service"

  mkdir -p "$systemd_user_dir"
  cat >"$unit_file" <<EOF
[Unit]
Description=EduControl Client (Flatpak)
After=graphical-session.target
Wants=graphical-session.target

[Service]
Type=simple
ExecStartPre=-/usr/bin/flatpak kill $APP_ID
ExecStart=/usr/bin/flatpak run --user --socket=x11 --env=DISPLAY=:0 --env=XAUTHORITY=%h/.Xauthority --env=HOME=%h --env=XDG_STATE_HOME=%h/.var/app/$APP_ID/state $APP_ID
ExecStop=-/usr/bin/flatpak kill $APP_ID
Restart=on-failure
RestartSec=2

# Nota: flatpak creará su DISPLAY proxy (p.ej. :99) si X11 está disponible.
Environment=XDG_RUNTIME_DIR=/run/user/%U
Environment=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/%U/bus

[Install]
WantedBy=default.target
EOF

if command -v systemctl >/dev/null 2>&1; then
  systemctl --user daemon-reload || true
  systemctl --user enable --now educontrol-client.service || true
  echo "Servicio systemd --user habilitado: educontrol-client.service" >&2
fi
fi

echo "Para desactivar: usa scripts/remove-client-user-autostart.sh" >&2
