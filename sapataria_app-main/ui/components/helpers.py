from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import TYPE_CHECKING

from services import DomainService
from ui.components.dialogs import AddOptionDialog

if TYPE_CHECKING:
    from ui.main import App


def safe_int(s, default=None):
    """Converte string para int com segurança"""
    try:
        return int(str(s).strip())
    except Exception:
        return default


def copy_to_clipboard(widget):
    """Copia texto selecionado para clipboard"""
    try:
        text = widget.get("sel.first", "sel.last")
        widget.clipboard_clear()
        widget.clipboard_append(text)
        widget.update()
        messagebox.showinfo("OK", "Texto copiado para clipboard!")
    except tk.TclError:
        messagebox.showwarning("Atenção", "Seleciona o texto que queres copiar.")


def paste_from_clipboard(widget):
    """Cola texto do clipboard"""
    try:
        text = widget.clipboard_get()
        widget.insert(tk.INSERT, text)
    except tk.TclError:
        messagebox.showwarning("Atenção", "Não há texto no clipboard.")


class BaseTab(ttk.Frame):
    """Tab base com funcionalidades comuns"""

    def __init__(self, parent, app: App):
        super().__init__(parent, padding=10)
        self.app = app
        self.db = app.db
        self.domain_service: DomainService = app.domain_service
        self.cache = {}

    def load_domains(self):
        """Carrega todos os domínios"""
        self.cache["brands"] = self.domain_service.get_domain_list("brands")
        self.cache["categories"] = self.domain_service.get_domain_list("categories")
        self.cache["colors"] = self.domain_service.get_domain_list("colors")
        self.cache["sizes"] = self.domain_service.get_domain_list("sizes")
        self.cache["warehouses"] = self.domain_service.get_domain_list("warehouses")
        self.cache["suppliers"] = self.domain_service.get_domain_list("suppliers")

    def tuple_list_to_map(self, rows):
        """Converte lista de tuples em mapas id->name e name->id"""
        id_to_name = {r[0]: r[1] for r in rows}
        name_to_id = {r[1]: r[0] for r in rows}
        return id_to_name, name_to_id

    def ask_add_option(self, table, label):
        """Pergunta ao utilizador para adicionar nova opção"""
        dlg = AddOptionDialog(self, f"Adicionar {label}", f"Novo {label}:")
        if dlg.value:
            if table == "subcategories":
                raise RuntimeError("Use add_subcategory (depende da categoria).")
            new_id = self.domain_service.add_domain_value(table, dlg.value)
            return new_id, dlg.value
        return None, None
