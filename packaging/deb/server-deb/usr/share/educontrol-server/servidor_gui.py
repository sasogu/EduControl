#!/usr/bin/env python3
import argparse
import json
import os
import sys
import tempfile
from typing import Any, Dict, List, Optional, Tuple

from educontrol_net import discover_clients, enviar_comando, parse_targets


def _config_dir() -> str:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if not xdg:
        xdg = os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(xdg, "educontrol-server")


def _presets_path() -> str:
    return os.path.join(_config_dir(), "presets.json")


def _default_data() -> Dict[str, Any]:
    return {
        "version": 1,
        "last_targets": "",
        "urls": [],
        "commands": [],
    }


def _load_data() -> Dict[str, Any]:
    path = _presets_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return _default_data()
        base = _default_data()
        base.update(data)
        if not isinstance(base.get("urls"), list):
            base["urls"] = []
        if not isinstance(base.get("commands"), list):
            base["commands"] = []
        if not isinstance(base.get("last_targets"), str):
            base["last_targets"] = ""
        return base
    except FileNotFoundError:
        return _default_data()
    except Exception:
        return _default_data()


def _atomic_write_json(path: str, data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="presets-", suffix=".json", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    finally:
        try:
            if os.path.exists(tmp):
                os.unlink(tmp)
        except Exception:
            pass


def _require_tkinter() -> None:
    try:
        import tkinter  # noqa: F401
    except Exception:
        print(
            "No se pudo importar tkinter.\n"
            "Instala el paquete 'python3-tk' y vuelve a intentarlo.\n\n"
            "Ejemplo: sudo apt install -y python3-tk",
            file=sys.stderr,
        )
        raise


def _pick_selected(listbox) -> Optional[int]:
    sel = listbox.curselection()
    if not sel:
        return None
    return int(sel[0])


def main() -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument(
        "--targets",
        help="IPs destino para unicast (separadas por coma o espacio). Ej: --targets 192.168.1.10,192.168.1.11",
        default="",
    )
    args = parser.parse_args()

    _require_tkinter()
    import tkinter as tk
    from tkinter import messagebox, simpledialog, ttk

    data = _load_data()

    root = tk.Tk()
    root.title("EduControl Server")

    # Targets
    targets_frame = ttk.Frame(root, padding=10)
    targets_frame.grid(row=0, column=0, sticky="ew")
    targets_frame.columnconfigure(1, weight=1)

    ttk.Label(targets_frame, text="Targets (unicast, opcional):").grid(row=0, column=0, sticky="w")
    targets_var = tk.StringVar(value=args.targets or data.get("last_targets", ""))
    targets_entry = ttk.Entry(targets_frame, textvariable=targets_var)
    targets_entry.grid(row=0, column=1, sticky="ew", padx=(8, 0))

    def current_targets() -> List[str]:
        t = targets_var.get().strip()
        data["last_targets"] = t
        _atomic_write_json(_presets_path(), data)
        return parse_targets(t) if t else []

    # Quick actions
    actions = ttk.Frame(root, padding=(10, 0, 10, 10))
    actions.grid(row=1, column=0, sticky="ew")

    def send_lock() -> None:
        enviar_comando("lock", targets=current_targets())

    def send_unlock() -> None:
        enviar_comando("unlock", targets=current_targets())

    ttk.Button(actions, text="Lock", command=send_lock).grid(row=0, column=0, padx=(0, 8))
    ttk.Button(actions, text="Unlock", command=send_unlock).grid(row=0, column=1)

    ttk.Separator(actions, orient="vertical").grid(row=0, column=2, sticky="ns", padx=10)

    def do_discover() -> None:
        try:
            items = discover_clients(timeout_s=1.2, targets=current_targets())
        except Exception as exc:
            messagebox.showerror("Discovery", f"Error descubriendo clientes: {exc}")
            return

        # Limpia tabla
        for row in clients_tree.get_children():
            clients_tree.delete(row)

        for it in items:
            ip = it.get("ip", "")
            hostname = it.get("hostname", "")
            user = it.get("user", "")
            disp = it.get("display", "")
            way = it.get("wayland", "")
            session = "wayland" if way else ("x11" if disp else "")
            clients_tree.insert("", "end", values=(ip, hostname, user, session))

        status_var.set(f"Discovery: {len(items)} cliente(s) encontrado(s)")

    ttk.Button(actions, text="Descubrir clientes", command=do_discover).grid(row=0, column=3, padx=(0, 8))

    def use_selected_as_targets() -> None:
        selected = clients_tree.selection()
        ips: List[str] = []
        for iid in selected:
            vals = clients_tree.item(iid, "values")
            if vals and vals[0]:
                ips.append(str(vals[0]))
        if not ips:
            messagebox.showinfo("Targets", "Selecciona uno o más clientes en la tabla.")
            return
        targets_var.set(",".join(ips))
        status_var.set(f"Targets actualizados: {len(ips)} IP(s)")

    ttk.Button(actions, text="Usar seleccionados como targets", command=use_selected_as_targets).grid(row=0, column=4)

    # Main content
    content = ttk.Frame(root, padding=10)
    content.grid(row=2, column=0, sticky="nsew")
    root.columnconfigure(0, weight=1)
    root.rowconfigure(2, weight=1)
    content.columnconfigure(0, weight=1)
    content.columnconfigure(1, weight=1)
    content.rowconfigure(1, weight=1)
    content.rowconfigure(4, weight=1)

    ttk.Label(content, text="Clientes detectados").grid(row=0, column=0, columnspan=2, sticky="w")

    clients_tree = ttk.Treeview(content, columns=("ip", "hostname", "user", "session"), show="headings", height=6)
    clients_tree.heading("ip", text="IP")
    clients_tree.heading("hostname", text="Hostname")
    clients_tree.heading("user", text="Usuario")
    clients_tree.heading("session", text="Sesión")
    clients_tree.column("ip", width=130, anchor="w")
    clients_tree.column("hostname", width=180, anchor="w")
    clients_tree.column("user", width=120, anchor="w")
    clients_tree.column("session", width=80, anchor="w")
    clients_tree.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(0, 10))

    ttk.Label(content, text="URLs guardadas").grid(row=2, column=0, sticky="w")
    ttk.Label(content, text="Comandos guardados").grid(row=2, column=1, sticky="w")

    urls_list = tk.Listbox(content, height=10)
    cmds_list = tk.Listbox(content, height=10)
    urls_list.grid(row=3, column=0, sticky="nsew", padx=(0, 10))
    cmds_list.grid(row=3, column=1, sticky="nsew")

    def refresh_lists() -> None:
        urls_list.delete(0, tk.END)
        for item in data.get("urls", []):
            name = str(item.get("name", ""))
            url = str(item.get("url", ""))
            label = f"{name} — {url}" if name else url
            urls_list.insert(tk.END, label)

        cmds_list.delete(0, tk.END)
        for item in data.get("commands", []):
            name = str(item.get("name", ""))
            cmd = str(item.get("cmd", ""))
            label = f"{name} — {cmd}" if name else cmd
            cmds_list.insert(tk.END, label)

    def save() -> None:
        _atomic_write_json(_presets_path(), data)

    def add_url() -> None:
        name = simpledialog.askstring("Nueva URL", "Nombre (opcional):", parent=root)
        if name is None:
            return
        url = simpledialog.askstring("Nueva URL", "URL (ej: https://example.org):", parent=root)
        if url is None:
            return
        url = url.strip()
        if not url:
            messagebox.showerror("Error", "La URL no puede estar vacía.")
            return
        data["urls"].append({"name": name.strip(), "url": url})
        save()
        refresh_lists()

    def edit_url() -> None:
        idx = _pick_selected(urls_list)
        if idx is None:
            return
        current = data["urls"][idx]
        name = simpledialog.askstring("Editar URL", "Nombre:", initialvalue=str(current.get("name", "")), parent=root)
        if name is None:
            return
        url = simpledialog.askstring("Editar URL", "URL:", initialvalue=str(current.get("url", "")), parent=root)
        if url is None:
            return
        url = url.strip()
        if not url:
            messagebox.showerror("Error", "La URL no puede estar vacía.")
            return
        data["urls"][idx] = {"name": name.strip(), "url": url}
        save()
        refresh_lists()

    def delete_url() -> None:
        idx = _pick_selected(urls_list)
        if idx is None:
            return
        if not messagebox.askyesno("Eliminar", "¿Eliminar la URL seleccionada?"):
            return
        del data["urls"][idx]
        save()
        refresh_lists()

    def send_url() -> None:
        idx = _pick_selected(urls_list)
        if idx is None:
            messagebox.showinfo("Enviar", "Selecciona una URL primero.")
            return
        url = str(data["urls"][idx].get("url", "")).strip()
        if not url:
            return
        enviar_comando(f"open {url}", targets=current_targets())

    def add_cmd() -> None:
        name = simpledialog.askstring("Nuevo comando", "Nombre (opcional):", parent=root)
        if name is None:
            return
        cmd = simpledialog.askstring("Nuevo comando", "Comando (ej: gcompris-qt):", parent=root)
        if cmd is None:
            return
        cmd = cmd.strip()
        if not cmd:
            messagebox.showerror("Error", "El comando no puede estar vacío.")
            return
        data["commands"].append({"name": name.strip(), "cmd": cmd})
        save()
        refresh_lists()

    def edit_cmd() -> None:
        idx = _pick_selected(cmds_list)
        if idx is None:
            return
        current = data["commands"][idx]
        name = simpledialog.askstring("Editar comando", "Nombre:", initialvalue=str(current.get("name", "")), parent=root)
        if name is None:
            return
        cmd = simpledialog.askstring("Editar comando", "Comando:", initialvalue=str(current.get("cmd", "")), parent=root)
        if cmd is None:
            return
        cmd = cmd.strip()
        if not cmd:
            messagebox.showerror("Error", "El comando no puede estar vacío.")
            return
        data["commands"][idx] = {"name": name.strip(), "cmd": cmd}
        save()
        refresh_lists()

    def delete_cmd() -> None:
        idx = _pick_selected(cmds_list)
        if idx is None:
            return
        if not messagebox.askyesno("Eliminar", "¿Eliminar el comando seleccionado?"):
            return
        del data["commands"][idx]
        save()
        refresh_lists()

    def send_cmd() -> None:
        idx = _pick_selected(cmds_list)
        if idx is None:
            messagebox.showinfo("Enviar", "Selecciona un comando primero.")
            return
        cmd = str(data["commands"][idx].get("cmd", "")).strip()
        if not cmd:
            return
        enviar_comando(f"exec {cmd}", targets=current_targets())

    urls_buttons = ttk.Frame(content)
    urls_buttons.grid(row=4, column=0, sticky="ew", pady=(8, 0), padx=(0, 10))
    ttk.Button(urls_buttons, text="Añadir", command=add_url).grid(row=0, column=0, padx=(0, 6))
    ttk.Button(urls_buttons, text="Editar", command=edit_url).grid(row=0, column=1, padx=(0, 6))
    ttk.Button(urls_buttons, text="Borrar", command=delete_url).grid(row=0, column=2, padx=(0, 6))
    ttk.Button(urls_buttons, text="Enviar (open)", command=send_url).grid(row=0, column=3)

    cmds_buttons = ttk.Frame(content)
    cmds_buttons.grid(row=4, column=1, sticky="ew", pady=(8, 0))
    ttk.Button(cmds_buttons, text="Añadir", command=add_cmd).grid(row=0, column=0, padx=(0, 6))
    ttk.Button(cmds_buttons, text="Editar", command=edit_cmd).grid(row=0, column=1, padx=(0, 6))
    ttk.Button(cmds_buttons, text="Borrar", command=delete_cmd).grid(row=0, column=2, padx=(0, 6))
    ttk.Button(cmds_buttons, text="Enviar (exec)", command=send_cmd).grid(row=0, column=3)

    refresh_lists()

    status_var = tk.StringVar(value="")
    status = ttk.Label(root, textvariable=status_var, padding=(10, 0, 10, 10))
    status.grid(row=3, column=0, sticky="ew")

    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
