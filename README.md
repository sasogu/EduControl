# EduControl

Cliente/servidor para un entorno de aula. Hay dos formatos disponibles:

- Paquetes Flatpak (originales en este repo).
- Paquetes nativos `.deb` (Debian 12+), convenientemente preparados para desplegar en aulas.

Componentes principales:

- **Servidor**: envía comandos `lock`/`unlock` por red.
- **Cliente**: recibe comandos y activa el “modo aula” mostrando un overlay a pantalla completa y, cuando es posible, intenta bloquear la sesión vía DBus.
- **Abrir URL**: el servidor puede enviar una orden `open <url>` para que el cliente abra una URL en el navegador por defecto.
- **Ejecutar aplicaciones/comandos**: el servidor puede enviar `exec <comando>` para que el cliente intente lanzar una aplicación o ejecutar un comando en la sesión gráfica del usuario.

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

### Requisitos mínimos para paquetes .deb (nativo)

Los paquetes `.deb` incluidos en `packaging/deb/` están pensados para sistemas Debian/Ubuntu (se ha probado en Debian 12+). Requisitos mínimos para instalar y ejecutar los paquetes nativos:

- **Sistema operativo**: Debian 12 (Bookworm) o compatible.
- **Puerto de comunicación**: permitir UDP entrante y/o saliente en el puerto `5007` (EduControl usa UDP para discovery y comandos).
- **Paquetes necesarios (dependencias declaradas en los .deb)**:
  - `python3` — requerido por el servidor y por los scripts Python del cliente.
  - `flatpak` — requerido por el paquete helper `educontrol-client` que lanza el cliente Flatpak.
  - `zenity` — usado por el cliente nativo para diálogos simples (presente en el paquete nativo).
  - `libglib2.0-bin` — proviene de utilidades que el paquete nativo puede necesitar.
- **Opcional pero recomendable**:
  - `systemd` (usuario) — para habilitar/gestionar la unidad `educontrol-client.service` en `~/.config/systemd/user/`.

Estas dependencias se reflejan en los archivos `DEBIAN/control` de los paquetes dentro de `packaging/deb/`.

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

### Instalación nativa en Debian — pasos prácticos

Comandos útiles para preparar un equipo Debian/Ubuntu e instalar los `.deb` nativos desde la raíz del repo:

```bash
# Actualizar e instalar dependencias mínimas
sudo apt update
sudo apt install -y python3 zenity libglib2.0-bin flatpak

# Instalar paquetes .deb nativos (servidor y cliente)
sudo dpkg -i packaging/deb/educontrol-server-native.deb
sudo dpkg -i packaging/deb/educontrol-client-native.deb
sudo apt-get -y -f install

# Habilitar y comprobar el servicio de usuario (si se instaló la unit)
systemctl --user enable --now educontrol-client.service
systemctl --user status educontrol-client.service

# Permitir el puerto UDP en el firewall (ej. ufw)
sudo ufw allow 5007/udp

# Ejecutar servidor manualmente (para pruebas)
/usr/bin/educontrol-server
# o
python3 /usr/share/educontrol-server/servidor.py
```

Notas rápidas:

- Los paquetes y dependencias declaradas se pueden consultar en los archivos `DEBIAN/control` dentro de `packaging/deb/`.
- Asegúrate de que la red entre profesor y alumnado permite UDP en el puerto `5007`.
- Si prefieres usar Flatpak en los clientes, instala únicamente el paquete helper `educontrol-client` que depende de `flatpak`.

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

Nota: desde el menú interactivo del servidor ahora puedes elegir la opción para enviar una URL a los navegadores de los clientes (entrada textual). El servidor envía el comando `open <url>` y el cliente intentará abrirlo con `xdg-open` si la sesión gráfica está disponible.

Además de `open`, el menú interactivo del servidor permite enviar comandos de ejecución remota: enviar `exec <comando>` hará que el cliente intente ejecutar el comando proporcionado (por ejemplo `exec gcompris-qt`).

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

Seguridad adicional: cuando se usa la funcionalidad `exec <comando>` el cliente intentará ejecutar el comando recibido en la sesión del usuario. Asegúrate de desplegar EduControl únicamente en redes de confianza y con equipos administrados; evitar exponer esta funcionalidad en redes públicas o sin control, ya que permite la ejecución remota de procesos en los equipos cliente.

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
