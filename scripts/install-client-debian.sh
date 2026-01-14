#!/usr/bin/env bash
set -euo pipefail

REPO_URL_DEFAULT="https://repo.edutictac.es"
KEY_URL_DEFAULT="https://repo.edutictac.es/repo.key"
KEYRING_PATH_DEFAULT="/usr/share/keyrings/edutictac-repo.gpg"
LIST_PATH_DEFAULT="/etc/apt/sources.list.d/edutictac.list"

COMPONENT_DEFAULT="main"
ARCH_DEFAULT="amd64"
PACKAGE_NAME_DEFAULT="educontrol.client"

usage() {
  cat <<'EOF'
Uso:
  sudo ./install-client-debian.sh [opciones]

Opciones:
  --repo-url URL        (por defecto: https://repo.edutictac.es)
  --key-url URL         (por defecto: https://repo.edutictac.es/repo.key)
  --suite CODENAME      (por defecto: detectado desde /etc/os-release; fallback: bookworm)
  --component NAME      (por defecto: main)
  --arch ARCH           (por defecto: amd64)
  --package NOMBRE      (por defecto: educontrol.client)
  -h, --help            Ayuda

Ejemplos:
  sudo ./install-client-debian.sh
  sudo ./install-client-debian.sh --suite bookworm
  sudo ./install-client-debian.sh --package educontrol.client
EOF
}

if [[ "${EUID}" -ne 0 ]]; then
  echo "Este script debe ejecutarse con sudo o como root."
  exit 1
fi

REPO_URL="$REPO_URL_DEFAULT"
KEY_URL="$KEY_URL_DEFAULT"
KEYRING_PATH="$KEYRING_PATH_DEFAULT"
LIST_PATH="$LIST_PATH_DEFAULT"
COMPONENT="$COMPONENT_DEFAULT"
ARCH="$ARCH_DEFAULT"
PACKAGE_NAME="$PACKAGE_NAME_DEFAULT"

DETECTED_SUITE="bookworm"
DETECTED_PRETTY="Linux"
if [[ -f /etc/os-release ]]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  DETECTED_PRETTY="${PRETTY_NAME:-Linux}"
  if [[ -n "${VERSION_CODENAME:-}" ]]; then
    DETECTED_SUITE="$VERSION_CODENAME"
  fi
fi
SUITE="$DETECTED_SUITE"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-url)   REPO_URL="$2"; shift 2 ;;
    --key-url)    KEY_URL="$2"; shift 2 ;;
    --suite)      SUITE="$2"; shift 2 ;;
    --component)  COMPONENT="$2"; shift 2 ;;
    --arch)       ARCH="$2"; shift 2 ;;
    --package)    PACKAGE_NAME="$2"; shift 2 ;;
    -h|--help)    usage; exit 0 ;;
    *) echo "Argumento desconocido: $1" >&2; usage; exit 1 ;;
  esac
done

echo "➡ Detectado: $DETECTED_PRETTY (suite=$SUITE)"

echo "➡ Instalando dependencias básicas..."
apt-get update
apt-get install -y --no-install-recommends ca-certificates curl gnupg

echo "➡ Instalando clave GPG del repositorio..."
mkdir -p /usr/share/keyrings
tmp_keyring="$(mktemp)"
curl -fsSL "$KEY_URL" | gpg --dearmor -o "$tmp_keyring"
install -m 0644 "$tmp_keyring" "$KEYRING_PATH"
rm -f "$tmp_keyring"
chmod 0644 "$KEYRING_PATH"

echo "➡ Añadiendo repositorio APT..."
cat > "$LIST_PATH" <<EOF
deb [arch=${ARCH} signed-by=${KEYRING_PATH}] ${REPO_URL} ${SUITE} ${COMPONENT}
EOF
chmod 0644 "$LIST_PATH"

echo "➡ Actualizando índices APT..."
apt-get update

echo "➡ Instalando paquete: $PACKAGE_NAME"
apt-get install -y "$PACKAGE_NAME"

echo "✅ Instalación completada correctamente."
echo "   Paquete instalado: $PACKAGE_NAME"
