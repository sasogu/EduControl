#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Construye un .deb del cliente para i386 (32-bit) usando un contenedor Debian i386.

Requisitos (host):
  - docker o podman

Uso:
  scripts/build-client-deb-i386.sh [--out PATH] [--image IMAGE]

Opciones:
  --out PATH     Ruta del .deb de salida (por defecto: packaging/deb/educontrol.client-<version>-i386.deb)
  --image IMAGE  Imagen i386 Debian (por defecto: i386/debian:bookworm)
  -h, --help     Ayuda

Notas:
  - El script compila el binario /usr/bin/educontrol-overlay para i386.
  - El resto del paquete es Python/desktop/autostart.
EOF
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PKG_ROOT_REL="packaging/deb/client-deb"
CONTROL_FILE="$ROOT_DIR/$PKG_ROOT_REL/DEBIAN/control"

if [[ ! -f "$CONTROL_FILE" ]]; then
  echo "No existe $CONTROL_FILE" >&2
  exit 1
fi

VERSION="$(awk -F': ' '$1=="Version"{print $2}' "$CONTROL_FILE" | head -n1)"
if [[ -z "$VERSION" ]]; then
  echo "No puedo detectar Version: en $CONTROL_FILE" >&2
  exit 1
fi

OUT_REL="packaging/deb/educontrol.client-${VERSION}-i386.deb"
IMAGE="i386/debian:bookworm"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --out) OUT_REL="$2"; shift 2;;
    --image) IMAGE="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    *) echo "Argumento desconocido: $1" >&2; usage; exit 1;;
  esac
done

if command -v docker >/dev/null 2>&1; then
  RUNNER="docker"
elif command -v podman >/dev/null 2>&1; then
  RUNNER="podman"
else
  echo "Necesito docker o podman en el host." >&2
  exit 1
fi

# Normaliza el output a ruta absoluta para que dpkg-deb pueda escribirlo.
OUT_ABS="$ROOT_DIR/$OUT_REL"
mkdir -p "$(dirname "$OUT_ABS")"

echo "➡ Construyendo educontrol.client i386 (version=$VERSION)"
echo "   Runner: $RUNNER"
echo "   Image:  $IMAGE"
echo "   Out:    $OUT_REL"

# En el contenedor:
# - Copia el árbol del paquete
# - Ajusta Architecture: i386
# - Compila overlay.c con GTK3 para i386
# - Construye el .deb
$RUNNER run --rm \
  -v "$ROOT_DIR:/src" \
  -w /src \
  "$IMAGE" \
  bash -lc "
    set -euo pipefail
    export DEBIAN_FRONTEND=noninteractive

    apt-get update
    apt-get install -y --no-install-recommends \
      ca-certificates \
      build-essential \
      pkg-config \
      dpkg \
      libgtk-3-dev

    work=\"\$(mktemp -d)\"
    cp -a \"/src/$PKG_ROOT_REL\" \"\$work/root\"

    # Ajustar arquitectura en control (solo en la copia)
    sed -i -E 's/^Architecture: .*/Architecture: i386/' \"\$work/root/DEBIAN/control\"

    # Compilar overlay i386
    if [[ -f \"\$work/root/usr/share/educontrol/overlay.c\" ]]; then
      mkdir -p \"\$work/root/usr/bin\"
      gcc -O2 -o \"\$work/root/usr/bin/educontrol-overlay\" \
        \"\$work/root/usr/share/educontrol/overlay.c\" \
        \$(pkg-config --cflags --libs gtk+-3.0)
      chmod 0755 \"\$work/root/usr/bin/educontrol-overlay\"
    else
      echo 'No encuentro overlay.c dentro del paquete (usr/share/educontrol/overlay.c)' >&2
      exit 1
    fi

    dpkg-deb --build \"\$work/root\" \"/src/$OUT_REL\"
    echo '✅ .deb generado en /src/$OUT_REL'
  "

echo "✅ Listo: $OUT_REL"
