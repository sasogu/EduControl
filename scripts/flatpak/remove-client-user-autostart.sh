#!/usr/bin/env bash
set -euo pipefail

APP_ID="com.educontrol.Client"
autostart_dir="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"
autostart_file="$autostart_dir/${APP_ID}.desktop"

if [[ -f "$autostart_file" ]]; then
  rm -f "$autostart_file"
  echo "Autostart eliminado: $autostart_file" >&2
else
  echo "No existe autostart: $autostart_file" >&2
fi

e_startup_dir="$HOME/.e/e/applications/startup"
e_desktop_file="$e_startup_dir/${APP_ID}.desktop"
e_order_file="$e_startup_dir/.order"

if [[ -f "$e_desktop_file" ]]; then
  rm -f "$e_desktop_file"
  echo "Autostart eliminado (Enlightenment/Moksha): $e_desktop_file" >&2
fi

if [[ -f "$e_order_file" ]]; then
  # Borra la línea exacta si está presente.
  tmpfile="$(mktemp)"
  grep -Fvx "${APP_ID}.desktop" "$e_order_file" >"$tmpfile" || true
  mv "$tmpfile" "$e_order_file"
fi

systemd_user_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
unit_file="$systemd_user_dir/educontrol-client.service"

if command -v systemctl >/dev/null 2>&1; then
  systemctl --user disable --now educontrol-client.service 2>/dev/null || true
  systemctl --user daemon-reload 2>/dev/null || true
fi

if [[ -f "$unit_file" ]]; then
  rm -f "$unit_file"
  echo "Servicio systemd --user eliminado: $unit_file" >&2
fi
