#!/usr/bin/env bash
set -euo pipefail

APP_ID="com.educontrol.Client"

if ! command -v flatpak >/dev/null 2>&1; then
  echo "Error: flatpak no está instalado o no está en PATH" >&2
  exit 1
fi

if ! command -v systemctl >/dev/null 2>&1; then
  echo "Error: systemctl no está disponible (¿systemd?)" >&2
  exit 1
fi

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

Environment=XDG_RUNTIME_DIR=/run/user/%U
Environment=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/%U/bus

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now educontrol-client.service

echo "Servicio systemd --user habilitado: educontrol-client.service" >&2
echo "Unit instalado en: $unit_file" >&2
