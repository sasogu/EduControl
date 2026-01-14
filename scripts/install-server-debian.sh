#!/usr/bin/env bash
set -euo pipefail

# === CONFIG POR DEFECTO (ajusta si quieres) ===
REPO_URL_DEFAULT="https://repo.edutictac.es"
KEY_URL_DEFAULT="https://repo.edutictac.es/repo.key"
KEYRING_PATH_DEFAULT="/usr/share/keyrings/edutictac-repo.gpg"
LIST_PATH_DEFAULT="/etc/apt/sources.list.d/edutictac.list"
SUITE_DEFAULT="bookworm"
COMPONENT_DEFAULT="main"
ARCH_DEFAULT="amd64"

# Paquete a instalar (debe ser el nombre "Package:" real del .deb)
PKG_DEFAULT="educontrol.server"

usage() {
  cat <<'EOF'
Uso:
  sudo ./instalar_educontrol_server.sh [opciones]

Opciones:
  --repo-url URL        (por defecto: https://repo.edutictac.es)
  --key-url URL         (por defecto: https://repo.edutictac.es/repo.key)
  --suite CODENAME      (por defecto: bookworm)
  --component NAME      (por defecto: main)
  --arch ARCH           (por defecto: amd64)
  --package NOMBRE      (por defecto: educontrol.server)
  --uninstall           Quita repo + keyring (no desinstala el paquete)
  -h, --help            Ayuda

Ejemplos:
  sudo ./instalar_educontrol_server.sh
  sudo ./instalar_educontrol_server.sh --package educontrol.server
  sudo ./instalar_educontrol_server.sh --suite bookworm --package educontrol.server
  sudo ./instalar_educontrol_server.sh --uninstall
EOF
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Falta el comando '$1'. Instálalo e inténtalo de nuevo." >&2
    exit 1
  }
}

require_root_or_sudo() {
  if [[ "${EUID}" -ne 0 ]]; then
    echo "Este script necesita privilegios de administrador. Ejecútalo con sudo." >&2
    exit 1
  fi
}

# Parse args
REPO_URL="$REPO_URL_DEFAULT"
KEY_URL="$KEY_URL_DEFAULT"
KEYRING_PATH="$KEYRING_PATH_DEFAULT"
LIST_PATH="$LIST_PATH_DEFAULT"
SUITE="$SUITE_DEFAULT"
COMPONENT="$COMPONENT_DEFAULT"
ARCH="$ARCH_DEFAULT"
PKG="$PKG_DEFAULT"
UNINSTALL="0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-url)   REPO_URL="$2"; shift 2 ;;
    --key-url)    KEY_URL="$2"; shift 2 ;;
    --suite)      SUITE="$2"; shift 2 ;;
    --component)  COMPONENT="$2"; shift 2 ;;
    --arch)       ARCH="$2"; shift 2 ;;
    --package)    PKG="$2"; shift 2 ;;
    --uninstall)  UNINSTALL="1"; shift ;;
    -h|--help)    usage; exit 0 ;;
    *) echo "Argumento desconocido: $1" >&2; usage; exit 1 ;;
  esac
done

require_root_or_sudo

need_cmd curl
need_cmd gpg
need_cmd apt-get

# Detect distro (informativo)
if [[ -r /etc/os-release ]]; then
  # shellcheck disable=SC1091
  source /etc/os-release
  echo "Detectado: ${PRETTY_NAME:-"Linux"} (ID=${ID:-?}, CODENAME=${VERSION_CODENAME:-?})"
fi

if [[ "$UNINSTALL" == "1" ]]; then
  echo "Desinstalando repo (sources list + keyring)..."
  rm -f "$LIST_PATH"
  rm -f "$KEYRING_PATH"
  apt-get update -y
  echo "Hecho. (No he desinstalado el paquete '$PKG'.)"
  exit 0
fi

echo "1) Instalando keyring del repo..."
mkdir -p "$(dirname "$KEYRING_PATH")"
curl -fsSL "$KEY_URL" | gpg --dearmor -o "$KEYRING_PATH"
chmod 0644 "$KEYRING_PATH"

echo "2) Añadiendo repo APT..."
cat > "$LIST_PATH" <<EOF
deb [arch=${ARCH} signed-by=${KEYRING_PATH}] ${REPO_URL} ${SUITE} ${COMPONENT}
EOF
chmod 0644 "$LIST_PATH"

echo "3) Actualizando índices APT..."
apt-get update -y

echo "4) Instalando servidor: ${PKG}"
apt-get install -y "$PKG"

echo "✅ Listo. Repo instalado y paquete '${PKG}' instalado."
echo "Si 'Unable to locate package' aparece, revisa que --package sea el nombre 'Package:' real,"
echo "y que --suite exista en tu repositorio (ahora mismo suele ser 'bookworm')."