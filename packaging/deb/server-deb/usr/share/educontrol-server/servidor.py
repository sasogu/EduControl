#!/usr/bin/env python3
import argparse
from educontrol_net import enviar_comando, parse_targets

def main() -> None:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument(
        "--targets",
        help="IPs destino para unicast (separadas por coma o espacio). Ej: --targets 192.168.122.144,192.168.122.145",
        default="",
    )
    args = parser.parse_args()
    targets = parse_targets(args.targets) if args.targets else []

    print("Servidor iniciado. Enviando comandos a los clientes.")
    while True:
        print("Opciones:")
        print("1. Bloquear pantallas de los clientes")
        print("2. Desbloquear pantallas de los clientes")
        print("3. Abrir URL en los navegadores de los clientes")
        print("4. Ejecutar comando remoto en los clientes")
        print("5. Salir")
        opcion = input("Selecciona una opción: ")

        if opcion == '1':
            enviar_comando('lock', targets=targets)
            print("Comando 'lock' enviado.")
        elif opcion == '2':
            enviar_comando('unlock', targets=targets)
            print("Comando 'unlock' enviado.")
        elif opcion == '3':
            url = input("URL a abrir (ej: https://example.org): ").strip()
            if not url:
                print("URL vacía; cancelado.")
            else:
                enviar_comando(f'open {url}', targets=targets)
                print(f"Comando 'open {url}' enviado.")
        elif opcion == '4':
            cmd = input("Comando a ejecutar en clientes (ej: gcompris-qt): ").strip()
            if not cmd:
                print("Comando vacío; cancelado.")
            else:
                enviar_comando(f'exec {cmd}', targets=targets)
                print(f"Comando 'exec {cmd}' enviado.")
        elif opcion == '5':
            print("Saliendo del servidor.")
            break
        else:
            print("Opción no válida. Intenta de nuevo.")

if __name__ == "__main__":
    main()