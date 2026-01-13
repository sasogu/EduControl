# EduControl (Flatpak)

Cliente/servidor para un entorno de aula.

- **Servidor**: envía comandos `lock`/`unlock` por red.
- **Cliente**: recibe comandos y activa un “modo aula” mostrando un overlay a pantalla completa (y además intenta bloquear la sesión con DBus cuando es posible).

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

Desde la raíz del proyecto:

```bash
# Cliente
flatpak-builder --repo=repo --force-clean build-dir flatpak-client/educontrol-client.json
flatpak build-bundle repo dist/educontrol-client.flatpak com.educontrol.Client \
  --runtime-repo=https://flathub.org/repo/flathub.flatpakrepo

# Servidor
flatpak-builder --repo=repo --force-clean build-dir flatpak-server/educontrol-server.json
flatpak build-bundle repo dist/educontrol-server.flatpak com.educontrol.Server \
  --runtime-repo=https://flathub.org/repo/flathub.flatpakrepo
```

## Instalación (en una máquina destino)

```bash
flatpak install --user -y ./dist/educontrol-server.flatpak
flatpak install --user -y ./dist/educontrol-client.flatpak
```

## Autoinicio del cliente (al iniciar sesión)

Flatpak no ejecuta scripts “post-install” en el host, así que para que el cliente se lance automáticamente al iniciar sesión hay que crear un `.desktop` de autostart en el usuario.

Nota: en Bodhi Linux (Moksha/Enlightenment) puede que `~/.config/autostart/` no se respete. El script también instala el autostart en el directorio de startup de Enlightenment para cubrir ese caso.

Este repo incluye un script que instala el Flatpak del cliente y configura el autostart:

```bash
./scripts/install-client-user-autostart.sh
```

Si el bundle está en otra ruta:

```bash
./scripts/install-client-user-autostart.sh /ruta/al/educontrol-client.flatpak
```

Para desactivar el autostart:

```bash
./scripts/remove-client-user-autostart.sh
```

### Alternativa: autoinicio con systemd (servicio de usuario)

Si tu escritorio no respeta `~/.config/autostart/` o prefieres gestionarlo con `systemctl`, puedes usar un servicio `systemd --user`.

Instalar y habilitar el servicio:

```bash
./scripts/install-client-user-systemd.sh
systemctl --user status educontrol-client.service
```

Desactivar y eliminar el servicio:

```bash
./scripts/remove-client-user-systemd.sh
```

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

1) Verifica conectividad básica entre máquinas (mismo segmento/VLAN): `ping`/`ssh` entre profesor ↔ alumnado.

2) Prueba **unicast explícito** (suele funcionar aunque el broadcast/multicast esté bloqueado):

```bash
flatpak run com.educontrol.Server --targets 192.168.1.101,192.168.1.102
```

3) Si unicast tampoco funciona, revisa firewall/reglas en los clientes (permitir UDP entrante a `5007`) y consulta al administrador de red si hay aislamiento de clientes en el SSID.

## Modo aula (overlay)

- Al recibir `lock`, el cliente muestra un overlay **a pantalla completa** con un mensaje.
- El overlay se mantiene hasta recibir `unlock`.

Nota: en escritorios y/o compositores modernos (especialmente Wayland) no siempre es posible “capturar” teclado/ratón como un bloqueo real del sistema. El overlay está pensado como medida práctica de atención en clase, no como un control de seguridad.

## Depuración rápida

Ver log persistente del cliente (dentro del almacenamiento de Flatpak):

```bash
tail -f ~/.var/app/com.educontrol.Client/state/educontrol-client.log
```

Ver el log del cliente en tiempo real y guardarlo:

```bash
flatpak run com.educontrol.Client 2>&1 | tee ~/educontrol-cliente.log
```

Verificar que el sandbox tiene acceso a display (debe ejecutarse desde sesión gráfica):

```bash
flatpak run --command=sh com.educontrol.Client -c 'echo "DISPLAY=$DISPLAY WAYLAND_DISPLAY=$WAYLAND_DISPLAY"'
```

## Licencia

MIT. Ver `LICENSE`.
