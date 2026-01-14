# Prompt para continuar mañana (EduControl)

Contexto rápido:
- Repo: EduControl (Debian).
- Servidor: `educontrol.server` v0.1.6 (CLI + GUI). Envía UDP comandos en puerto 5007.
- Cliente: `educontrol.client` v0.1.6 (añadido lock de instancia única con `fcntl.flock` + responde a discovery `who` con `iam <json>`).
- Problema: el profesor actualiza cliente/servidor pero el servidor aún no detecta clientes en discovery en el entorno real.

Objetivo:
- Diagnosticar por qué el servidor no recibe respuestas `iam`.
- Proponer cambios mínimos para hacerlo robusto (debug logging, modos unicast, etc.).

Lo que quiero que hagas:
1) Dame una checklist corta para aislar si el fallo es:
   - (A) el servidor no está enviando `who` a la red correcta,
   - (B) el cliente no está recibiendo `who`,
   - (C) el cliente responde pero el servidor no recibe `iam`.
2) Dame comandos concretos (servidor y cliente) para verificarlo con herramientas disponibles en Debian.
3) Si el problema apunta a multicast/broadcast bloqueado (Wi-Fi, VLAN, aislamiento), dame una estrategia de operación:
   - usar `--targets` unicast,
   - mantener lista de IPs descubiertas por ARP/SSH,
   - o cualquier alternativa simple.
4) Si hace falta tocar código, propón un parche mínimo para:
   - imprimir a qué direcciones/IFs se envía `who` y desde qué socket/puerto se escuchan respuestas,
   - añadir un modo `--debug`.

Datos/observaciones previas:
- Un test manual previo funcionó: servidor enviando `who` a `192.168.122.144:5007` y escuchando en `5007` recibió `iam {...}`.
- En algunos clientes hubo múltiples instancias; se añadió lockfile.

Archivos relevantes:
- packaging/deb/server-deb/usr/share/educontrol-server/educontrol_net.py
- packaging/deb/server-deb/usr/share/educontrol-server/servidor.py
- packaging/deb/server-deb/usr/share/educontrol-server/servidor_gui.py
- packaging/deb/client-deb/usr/share/educontrol/educontrol-cliente.py
- scripts/install-client-over-ssh.sh
