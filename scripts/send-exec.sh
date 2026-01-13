#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Uso: $0 \"comando a ejecutar\" [targets_coma_o_espacio]"
  echo "Ej: $0 \"gcompris-qt\" 192.168.1.101,192.168.1.102"
  exit 2
fi

CMD="$1"
TARGETS="${2:-}"

python3 - "$CMD" "$TARGETS" <<'PY'
import socket, sys

PORT = 5007
cmd = sys.argv[1]
targets = sys.argv[2] if len(sys.argv) > 2 else ""
payload = ("exec " + cmd).encode('utf-8')

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.sendto(payload, ('255.255.255.255', PORT))
except Exception as e:
    print('Aviso: broadcast falló:', e, file=sys.stderr)

try:
    sock.sendto(payload, ('127.0.0.1', PORT))
except Exception:
    pass

if targets:
    for t in targets.replace(',', ' ').split():
        try:
            sock.sendto(payload, (t, PORT))
            print('Enviado a', t)
        except Exception as e:
            print('Fallo envío a', t, e, file=sys.stderr)

sock.close()
PY

echo "Payload 'exec $CMD' enviado."

# Nota: hacer ejecutable con: chmod +x scripts/send-exec.sh
