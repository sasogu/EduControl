#!/usr/bin/env python3
import socket
import time
import fcntl
import struct
from typing import List, Optional

MULTICAST_GROUP = '224.1.1.1'
PORT = 5007


def _iface_ipv4(sock: socket.socket, ifname: str, request: int) -> Optional[str]:
    try:
        ifreq = struct.pack('256s', ifname[:15].encode('utf-8'))
        res = fcntl.ioctl(sock.fileno(), request, ifreq)
        return socket.inet_ntoa(res[20:24])
    except OSError:
        return None


def obtener_broadcasts_ipv4() -> List[str]:
    broadcasts: List[str] = []
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            ifaces = socket.if_nameindex()
        except Exception as exc:
            # En algunos entornos restringidos (o implementaciones antiguas) puede fallar.
            print(f"Aviso: no se pudieron enumerar interfaces de red ({exc}).")
            return ["255.255.255.255"]

        for _, ifname in ifaces:
            if ifname == 'lo':
                continue

            ip = _iface_ipv4(s, ifname, 0x8915)  # SIOCGIFADDR
            mask = _iface_ipv4(s, ifname, 0x891b)  # SIOCGIFNETMASK
            if not ip or not mask:
                continue

            ip_int = struct.unpack('!I', socket.inet_aton(ip))[0]
            mask_int = struct.unpack('!I', socket.inet_aton(mask))[0]
            bcast_int = ip_int | (~mask_int & 0xFFFFFFFF)
            bcast = socket.inet_ntoa(struct.pack('!I', bcast_int))
            broadcasts.append(bcast)

    # Evita duplicados manteniendo orden
    unique: List[str] = []
    for b in broadcasts:
        if b not in unique:
            unique.append(b)

    # Fallback: si no encontramos ninguna interfaz válida, intenta el broadcast global.
    if not unique:
        unique.append("255.255.255.255")
    return unique

def enviar_comando(comando):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as sock:
        payload = comando.encode('utf-8')

        # Multicast (útil si la red lo permite)
        try:
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
            sock.sendto(payload, (MULTICAST_GROUP, PORT))
        except OSError as exc:
            print(f"Aviso: envío multicast falló ({exc}).")

        # Broadcast por cada interfaz (más fiable que 255.255.255.255 en muchas redes)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            for bcast in obtener_broadcasts_ipv4():
                try:
                    sock.sendto(payload, (bcast, PORT))
                except OSError as exc:
                    print(f"Aviso: envío broadcast a {bcast} falló ({exc}).")
        except OSError as exc:
            print(f"Aviso: envío broadcast falló ({exc}).")

        # Unicast a localhost (útil para pruebas en una sola máquina)
        try:
            sock.sendto(payload, ('127.0.0.1', PORT))
        except OSError:
            pass

def main():
    print("Servidor iniciado. Enviando comandos a los clientes.")
    while True:
        print("Opciones:")
        print("1. Bloquear pantallas de los clientes")
        print("2. Desbloquear pantallas de los clientes")
        print("3. Salir")
        opcion = input("Selecciona una opción: ")

        if opcion == '1':
            enviar_comando('lock')
            print("Comando 'lock' enviado.")
        elif opcion == '2':
            enviar_comando('unlock')
            print("Comando 'unlock' enviado.")
        elif opcion == '3':
            print("Saliendo del servidor.")
            break
        else:
            print("Opción no válida. Intenta de nuevo.")

if __name__ == "__main__":
    main()