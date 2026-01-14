#!/usr/bin/env bash
set -euo pipefail

systemd_user_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
unit_file="$systemd_user_dir/educontrol-client.service"

if command -v systemctl >/dev/null 2>&1; then
  systemctl --user disable --now educontrol-client.service 2>/dev/null || true
  systemctl --user daemon-reload 2>/dev/null || true
fi

if [[ -f "$unit_file" ]]; then
  rm -f "$unit_file"
  echo "Servicio systemd --user eliminado: $unit_file" >&2
else
  echo "No existe servicio: $unit_file" >&2
fi
