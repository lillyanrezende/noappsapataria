from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from db import DB
from services import ProductService, AuthService, DomainService
from ui.login import LoginFrame
from ui.tabs.create_tab import CreateTab
from ui.tabs.update_tab import UpdateTab
from ui.tabs.delete_tab import DeleteTab
from ui.tabs.view_tab import ViewTab
from ui.tabs.warehouse_tab import WarehouseTab


class App(tk.Tk):
    """Aplicação principal"""

    def __init__(self, db: DB):
        super().__init__()
        self.title("Sistema Sapataria - Cadastro/Stock (Supabase)")
        self.geometry("980x700")
        self.db = db
        self.user = None

        self.product_service = ProductService(db)
        self.auth_service = AuthService(db)
        self.domain_service = DomainService(db)

        self.db.init_app_tables()
        self.show_login()

    def show_login(self):
        for w in self.winfo_children():
            w.destroy()
        LoginFrame(self).pack(fill="both", expand=True)

    def show_main(self, user):
        self.user = user
        for w in self.winfo_children():
            w.destroy()
        MainFrame(self).pack(fill="both", expand=True)


class MainFrame(ttk.Frame):
    """Frame principal com tabs"""

    def __init__(self, app: App):
        super().__init__(app, padding=10)
        self.app = app

        top = ttk.Frame(self)
        top.pack(fill="x")

        ttk.Label(top, text=f"Utilizador: {app.user['nome_usuario']}  |  Setor: {app.user.get('setor') or '-'}",
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        ttk.Button(top, text="Sair", command=self.logout).pack(side="right")

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, pady=(10, 0))

        self.tab_create = CreateTab(nb, app)
        self.tab_update = UpdateTab(nb, app)
        self.tab_delete = DeleteTab(nb, app)
        self.tab_view = ViewTab(nb, app)
        self.tab_warehouse = WarehouseTab(nb, app)

        nb.add(self.tab_create, text="Cadastrar")
        nb.add(self.tab_update, text="Alterar")
        nb.add(self.tab_delete, text="Excluir")
        nb.add(self.tab_view, text="Visualizar")
        nb.add(self.tab_warehouse, text="Armazéns")

    def logout(self):
        self.app.db.audit(self.app.user, "LOGOUT", "profiles",
                         entity_pk=f"user_id={self.app.user['user_id']}", details={})
        self.app.user = None
        self.app.show_login()


def main():
    """Função principal"""
    db = DB()
    app = App(db)
    app.mainloop()


if __name__ == "__main__":
    main()
