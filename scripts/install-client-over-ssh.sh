#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Uso:
  scripts/install-client-over-ssh.sh --host IP [--user USER] [--port PORT] [--deb PATH]

Ejemplos:
  # Instala usando el .deb más reciente en packaging/deb/
  bash scripts/install-client-over-ssh.sh --host 192.168.122.144 --user lliurex

  # Especificando .deb exacto
  bash scripts/install-client-over-ssh.sh --host 192.168.122.144 --user lliurex --deb packaging/deb/educontrol-client-0.1.6.deb

Notas:
  - Si no tienes clave SSH, pedirá contraseña (SSH y sudo) de forma interactiva.
  - Copia el .deb a /tmp/ en el cliente y ejecuta: sudo dpkg -i ... && sudo apt-get -y -f install
EOF
}

HOST=""
USER="${USER:-lliurex}"
PORT="22"
DEB=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) HOST="$2"; shift 2;;
    --user) USER="$2"; shift 2;;
    --port) PORT="$2"; shift 2;;
    --deb)  DEB="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    *) echo "Argumento desconocido: $1" >&2; usage; exit 1;;
  esac
done

if [[ -z "$HOST" ]]; then
  echo "Falta --host" >&2
  usage
  exit 1
fi

if [[ -z "$DEB" ]]; then
  # Elige el .deb más reciente por orden de versión (sort -V)
  mapfile -t candidates < <(ls -1 packaging/deb/educontrol-client-*.deb 2>/dev/null | sort -V)
  if [[ ${#candidates[@]} -eq 0 ]]; then
    echo "No encuentro packaging/deb/educontrol-client-*.deb (usa --deb)" >&2
    exit 1
  fi
  DEB="${candidates[-1]}"
fi

if [[ ! -f "$DEB" ]]; then
  echo "No existe el .deb: $DEB" >&2
  exit 1
fi

base="$(basename "$DEB")"
remote_tmp="/tmp/$base"

set -x
scp -P "$PORT" "$DEB" "$USER@$HOST:$remote_tmp"
ssh -p "$PORT" -t "$USER@$HOST" "sudo dpkg -i '$remote_tmp' && sudo apt-get -y -f install && dpkg -l | grep -E 'educontrol-client|educontrol-server' || true"
set +x

echo "✅ Instalación remota completada en $USER@$HOST"
