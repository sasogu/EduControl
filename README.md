# EduControl

Cliente/servidor para un entorno de aula. El despliegue recomendado es con paquetes nativos `.deb` (Debian 12+).

Componentes principales:

- **Servidor**: envía comandos `lock`/`unlock` por red.
- **Cliente**: recibe comandos y activa el “modo aula” mostrando un overlay a pantalla completa y, cuando es posible, intenta bloquear la sesión vía DBus.
- **Abrir URL**: el servidor puede enviar una orden `open <url>` para que el cliente abra una URL en el navegador por defecto.
- **Ejecutar aplicaciones/comandos**: el servidor puede enviar `exec <comando>` para que el cliente intente lanzar una aplicación o ejecutar un comando en la sesión gráfica del usuario.

## Estructura

- `packaging/deb/`
  - `client-deb/`: raíz del paquete del **cliente** (para construir el `.deb`).
  - `server-deb/`: raíz del paquete del **servidor** (para construir el `.deb`).
  - `educontrol.client-*.deb`: artefactos del cliente (ya construidos).
  - `educontrol.server-*.deb`: artefactos del servidor (ya construidos).

## Requisitos

### Requisitos mínimos para paquetes .deb (nativo)

Los paquetes `.deb` incluidos en `packaging/deb/` están pensados para sistemas Debian/Ubuntu (se ha probado en Debian 12+). Requisitos mínimos para instalar y ejecutar los paquetes nativos:

- **Sistema operativo**: Debian 12 (Bookworm) o compatible.
- **Puerto de comunicación**: permitir UDP entrante y/o saliente en el puerto `5007` (EduControl usa UDP para discovery y comandos).
- **Paquetes necesarios (dependencias declaradas en los .deb)**:
  - `python3` — requerido por el servidor y por los scripts Python del cliente.
  - `zenity` — usado por el cliente nativo para diálogos simples (presente en el paquete nativo).
  - `libglib2.0-bin` — proviene de utilidades que el paquete nativo puede necesitar.
- **Opcional pero recomendable**:
  - `systemd` (usuario) — para habilitar/gestionar la unidad `educontrol-client.service` en `~/.config/systemd/user/`.

Estas dependencias se reflejan en los archivos `DEBIAN/control` de los paquetes dentro de `packaging/deb/`.

## Instalación (máquina destino)

Opciones:

- Vía repositorio APT (recomendado): instala/actualiza con `apt` usando los scripts de `scripts/`.
- Nativo `.deb` local: instalar a mano los `.deb` ya construidos en `packaging/deb/`.

### Instalación vía repositorio APT (recomendada)

Esta opción añade el repositorio `https://repo.edutictac.es` (con keyring en `/usr/share/keyrings/`) e instala el paquete.

Nota: el script detecta `VERSION_CODENAME` del sistema; si tu repo solo publica para `bookworm`, fuerza `--suite bookworm`.

```bash
# Cliente (en cada equipo alumno)
sudo bash scripts/install-client-debian.sh --suite bookworm

# Servidor (en el equipo profesor)
sudo bash scripts/install-server-debian.sh --suite bookworm
```

Instalar los `.deb` locales:

```bash
# En el equipo profesor (instala servidor)
sudo dpkg -i packaging/deb/educontrol.server-0.1.3.deb
sudo apt-get -y -f install

# En cada equipo alumno (instala cliente + overlay + entrada de menú)
sudo dpkg -i packaging/deb/educontrol.client-0.1.3.deb
sudo apt-get -y -f install
```

### Instalación nativa en Debian — pasos prácticos

Comandos útiles para preparar un equipo Debian/Ubuntu e instalar los `.deb` nativos desde la raíz del repo:

```bash
# Actualizar e instalar dependencias mínimas
sudo apt update
sudo apt install -y python3 zenity libglib2.0-bin

# Instalar paquetes .deb nativos (servidor y cliente)
sudo dpkg -i packaging/deb/educontrol.server-0.1.3.deb
sudo dpkg -i packaging/deb/educontrol.client-0.1.3.deb
sudo apt-get -y -f install

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

Qué instala el `.deb` nativo (cliente):

- `/usr/bin/educontrol-client` — wrapper para lanzar el cliente Python.
- `/usr/bin/educontrol-overlay` — binario overlay fullscreen.
- `/usr/share/educontrol/educontrol-cliente.py` — código del cliente.
- `/usr/share/applications/educontrol-client.desktop` — entrada de menú.

Servidor nativo:

- `/usr/bin/educontrol-server` — wrapper que ejecuta `/usr/share/educontrol-server/servidor.py`.

## Autoinicio y notas sobre sesión gráfica

El `.deb` cliente instala una entrada en `/etc/xdg/autostart` para lanzar el wrapper al iniciar sesión gráfica. En escritorios que no respetan `~/.config/autostart/` (p. ej. Moksha/Enlightenment) esta entrada system-wide suele funcionar.

Si prefieres `systemd --user` puedes usar el unit file que hemos probado en desarrollo: `usr/lib/systemd/user/educontrol-client.service` (en la versión empaquetada se puede instalar/activar por usuario). En algunos entornos la opción más fiable para garantizar que el proceso herede `DISPLAY`/`XAUTHORITY` es lanzar el wrapper desde la sesión gráfica (autostart) en lugar de arrancarlo desde un servicio que no herede todas las variables.

## Ejecución

En la máquina del profesor (servidor):

```bash
/usr/bin/educontrol-server
```

Si tienes clientes en una red donde multicast/broadcast no llega (por ejemplo, máquinas virtuales en la red `default` de libvirt), puedes forzar unicast a IPs concretas:

```bash
/usr/bin/educontrol-server --targets 192.168.122.144
```

Nota: desde el menú interactivo del servidor ahora puedes elegir la opción para enviar una URL a los navegadores de los clientes (entrada textual). El servidor envía el comando `open <url>` y el cliente intentará abrirlo con `xdg-open` si la sesión gráfica está disponible.

Además de `open`, el menú interactivo del servidor permite enviar comandos de ejecución remota: enviar `exec <comando>` hará que el cliente intente ejecutar el comando proporcionado (por ejemplo `exec gcompris-qt`).

En cada máquina del alumnado (cliente):

```bash
/usr/bin/educontrol-client
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
/usr/bin/educontrol-server --targets 192.168.1.101,192.168.1.102
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
