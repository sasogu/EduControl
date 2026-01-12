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

## Ejecución

En la máquina del profesor (servidor):

```bash
flatpak run com.educontrol.Server
```

En cada máquina del alumnado (cliente):

```bash
flatpak run com.educontrol.Client
```

## Modo aula (overlay)

- Al recibir `lock`, el cliente muestra un overlay **a pantalla completa** con un mensaje.
- El overlay se mantiene hasta recibir `unlock`.

Nota: en escritorios y/o compositores modernos (especialmente Wayland) no siempre es posible “capturar” teclado/ratón como un bloqueo real del sistema. El overlay está pensado como medida práctica de atención en clase, no como un control de seguridad.

## Depuración rápida

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
