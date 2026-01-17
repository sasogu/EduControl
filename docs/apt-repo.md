# Repo APT (multi-arch) para EduControl

Esto sirve para publicar los `.deb` (cliente/servidor) en un repositorio APT accesible por HTTP(S), para que los scripts:

- `scripts/install-client-debian.sh`
- `scripts/install-server-debian.sh`

puedan instalar con `apt`.

## Qué necesitas publicar

Para soportar **i386** además de **amd64** necesitas que tu repo publique índices para ambas arquitecturas, típicamente:

- `dists/bookworm/main/binary-amd64/Packages.gz`
- `dists/bookworm/main/binary-i386/Packages.gz`

(El servidor suele ser `Architecture: all`, así que también cae en el repo.)

Lo más cómodo es usar `reprepro`, que genera toda la estructura (`dists/`, `pool/`, `Release`, etc.) y firma el repo.

## Opción recomendada: `reprepro` (servidor propio)

En tu servidor (Debian/Ubuntu) que vaya a servir `https://repo.edutictac.es/`:

1. Instala herramientas

```bash
sudo apt-get update
sudo apt-get install -y reprepro nginx gnupg
```

2. Crea el directorio del repo (ejemplo)

```bash
sudo mkdir -p /var/www/repo/conf
sudo chown -R "$USER":"$USER" /var/www/repo
```

3. Crea (o reutiliza) una clave GPG de firma

- Si ya tienes la clave con la que generas `repo.key`, reutilízala.
- Si no tienes una:

```bash
gpg --quick-gen-key "EduControl Repo <noreply@example.org>" rsa4096 sign 2y
```

Obtén el `KEYID`:

```bash
gpg --list-secret-keys --keyid-format LONG
```

4. Configura `reprepro`

Crea `/var/www/repo/conf/distributions` (ejemplo para Bookworm):

```conf
Origin: EduControl
Label: EduControl
Suite: stable
Codename: bookworm
Components: main
Architectures: amd64 i386 all
SignWith: <TU_KEYID>
```

5. Importa los `.deb`

Copia los `.deb` al servidor (por ejemplo con `scp`/`rsync`) y luego:

```bash
reprepro -b /var/www/repo includedeb bookworm educontrol-server-0.1.6.deb
reprepro -b /var/www/repo includedeb bookworm educontrol-client-0.1.6-amd64.deb
reprepro -b /var/www/repo includedeb bookworm educontrol-client-0.1.6-i386.deb
```

Notas:

- El nombre del archivo `.deb` puede ser cualquiera; lo que importa es el campo `Architecture:` dentro del paquete.
- Si vuelves a incluir una versión ya existente, usa `reprepro remove` o incrementa `Version:`.

6. Publica la clave del repo (`repo.key`)

Los scripts descargan `https://repo.edutictac.es/repo.key` y la convierten a keyring con `gpg --dearmor`.

Puedes publicar la **clave pública en ASCII**:

```bash
gpg --armor --export <TU_KEYID> > /var/www/repo/repo.key
```

7. Nginx (ejemplo mínimo)

Sirve `/var/www/repo` como raíz del vhost `repo.edutictac.es`.

Comprueba que existen URLs como:

- `https://repo.edutictac.es/dists/bookworm/Release`
- `https://repo.edutictac.es/pool/main/.../*.deb`

## Dónde “subirlo”

Tienes varias opciones válidas:

- Servidor propio (recomendado): `/var/www/repo` + Nginx/Apache.
- VPS barato (DigitalOcean/Hetzner/etc.) sirviendo estático.
- Un bucket compatible S3 + CDN (funciona, pero gestionar firma/paths requiere más cuidado).

La opción más simple para empezar suele ser: **un VPS + Nginx + reprepro**.
