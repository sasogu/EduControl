# EduControl

Cliente/servidor para un entorno de aula. Hay dos formatos disponibles:

- Paquetes Flatpak (originales en este repo).
- Paquetes nativos `.deb` (Debian 12+), convenientemente preparados para desplegar en aulas.

Componentes principales:

- **Servidor**: envía comandos `lock`/`unlock` por red.
- **Cliente**: recibe comandos y activa el “modo aula” mostrando un overlay a pantalla completa y, cuando es posible, intenta bloquear la sesión vía DBus.

## Estructura

- `flatpak-client/`
  - `cliente.py`: cliente (escucha UDP y ejecuta lock/unlock).
  - `overlay.c`: overlay GTK a pantalla completa (sin botón), usado por el cliente.
  - `educontrol-client.json`: manifest Flatpak del cliente.
- `flatpak-server/`
  - `servidor.py`: servidor (envía UDP multicast/broadcast/unicast local).
  - `educontrol-server.json`: manifest Flatpak del servidor.

## Requisitos

En el host donde compilas:

- Flatpak y flatpak-builder.
- Runtime: `org.freedesktop.Platform//21.08` y `org.freedesktop.Sdk//21.08`.

## Instalar Flatpak

### Debian/Ubuntu

```bash
sudo apt update
sudo apt install -y flatpak flatpak-builder
```

Opcional (recomendado): añadir Flathub como repositorio de runtimes/apps:

```bash
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
```

### Fedora

```bash
sudo dnf install -y flatpak flatpak-builder
```

## Construcción (host)

Si quieres usar Flatpak aún puedes construir los bundles del cliente/servidor:

```bash
# Cliente (Flatpak)
flatpak-builder --repo=repo --force-clean build-dir flatpak-client/educontrol-client.json
flatpak build-bundle repo dist/educontrol-client.flatpak com.educontrol.Client \
  --runtime-repo=https://flathub.org/repo/flathub.flatpakrepo

# Servidor (Flatpak)
flatpak-builder --repo=repo --force-clean build-dir flatpak-server/educontrol-server.json
flatpak build-bundle repo dist/educontrol-server.flatpak com.educontrol.Server \
  --runtime-repo=https://flathub.org/repo/flathub.flatpakrepo
```

## Instalación (máquina destino)

Opciones:

- Flatpak: instalar los bundles `dist/*.flatpak` como se indica arriba.
- Nativo `.deb` (recomendado para despliegues en Debian 12+): el repo incluye paquetes nativos de ejemplo en `packaging/deb/`.

Instalar los `.deb` locales:

```bash
# En el equipo profesor (instala servidor)
sudo dpkg -i packaging/deb/educontrol-server-native.deb
sudo apt-get -y -f install

# En cada equipo alumno (instala cliente + overlay + autostart)
sudo dpkg -i packaging/deb/educontrol-client-native.deb
sudo apt-get -y -f install
```

Qué instala el `.deb` nativo (cliente):

- `/usr/bin/educontrol-client` — wrapper para lanzar el cliente Python.
- `/usr/bin/educontrol-overlay` — binario overlay fullscreen.
- `/usr/share/educontrol/educontrol-cliente.py` — código del cliente.
- `/etc/xdg/autostart/com.educontrol.Client.desktop` — autostart system-wide.

Servidor nativo:

- `/usr/bin/educontrol-server` — wrapper que ejecuta `/usr/share/educontrol-server/servidor.py`.

## Autoinicio y notas sobre sesión gráfica

El `.deb` cliente instala una entrada en `/etc/xdg/autostart` para lanzar el wrapper al iniciar sesión gráfica. En escritorios que no respetan `~/.config/autostart/` (p. ej. Moksha/Enlightenment) esta entrada system-wide suele funcionar.

Si prefieres `systemd --user` puedes usar el unit file que hemos probado en desarrollo: `usr/lib/systemd/user/educontrol-client.service` (en la versión empaquetada se puede instalar/activar por usuario). En algunos entornos la opción más fiable para garantizar que el proceso herede `DISPLAY`/`XAUTHORITY` es lanzar el wrapper desde la sesión gráfica (autostart) en lugar de arrancarlo desde un servicio que no herede todas las variables.

## Ejecución

En la máquina del profesor (servidor):

```bash
flatpak run com.educontrol.Server
```

Si tienes clientes en una red donde multicast/broadcast no llega (por ejemplo, máquinas virtuales en la red `default` de libvirt), puedes forzar unicast a IPs concretas:

```bash
flatpak run com.educontrol.Server --targets 192.168.122.144
```

En cada máquina del alumnado (cliente):

```bash
flatpak run com.educontrol.Client
```

### Si el cliente no recibe comandos (problemas de red)

EduControl usa UDP en el puerto `5007` y por defecto intenta multicast y broadcast (además de unicast). En muchos centros educativos, sobre todo en Wi‑Fi, es común que:

- Haya **aislamiento de clientes** (los equipos no pueden hablar entre sí).
- Se **filtre/bloquee multicast o broadcast** para reducir ruido.
- Haya **VLANs** separadas o ACLs/firewall entre subredes.

Comprobaciones rápidas:

1. Verifica conectividad básica entre máquinas (mismo segmento/VLAN): `ping`/`ssh` entre profesor ↔ alumnado.

2. Prueba **unicast explícito** (suele funcionar aunque el broadcast/multicast esté bloqueado):

```bash
flatpak run com.educontrol.Server --targets 192.168.1.101,192.168.1.102
```

3. Si unicast tampoco funciona, revisa firewall/reglas en los clientes (permitir UDP entrante a `5007`) y consulta al administrador de red si hay aislamiento de clientes en el SSID.

## Modo aula (overlay)

- Al recibir `lock`, el cliente muestra un overlay **a pantalla completa** con un mensaje.
- El overlay se mantiene hasta recibir `unlock`.

Nota: en escritorios y/o compositores modernos (especialmente Wayland) no siempre es posible “capturar” teclado/ratón como un bloqueo real del sistema. El overlay está pensado como medida práctica de atención en clase, no como un control de seguridad.

## Depuración rápida

Logs del cliente (instalación nativa):

```bash
tail -f ~/.var/app/com.educontrol.Client/state/educontrol-client.log
# o si se ejecuta nativo y usa XDG_STATE_HOME por defecto:
tail -f ~/.local/state/educontrol-client.log
```

Arrancar manualmente (útil para probar visualmente):

```bash
# En la sesión gráfica del usuario (no por SSH), ejecutar:
/usr/bin/educontrol-client
```

Si la ventana no ocupa toda la pantalla, el cliente intenta usar el binario `educontrol-overlay` instalado en `/usr/bin/educontrol-overlay`. Asegúrate que ese binario está presente y es ejecutable.

Si el cliente registra `Overlay: no hay DISPLAY/WAYLAND_DISPLAY`, significa que el proceso no heredó correctamente la variable de entorno de la sesión gráfica; lo más sencillo es lanzar `/usr/bin/educontrol-client` desde una terminal en la sesión gráfica o confiar en el autostart del escritorio.

## Licencia

MIT. Ver `LICENSE`.
