from __future__ import annotations

from tkinter import ttk, messagebox, simpledialog
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.main import App


class LoginFrame(ttk.Frame):
    """Frame de login"""

    def __init__(self, app: App):
        super().__init__(app, padding=12)
        self.app = app

        ttk.Label(self, text="Login", font=("Segoe UI", 16, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 12))

        ttk.Label(self, text="Username").grid(row=1, column=0, sticky="w")
        self.username = ttk.Entry(self, width=40)
        self.username.grid(row=2, column=0, sticky="w", pady=(0, 8))

        ttk.Label(self, text="Password").grid(row=3, column=0, sticky="w")
        self.password = ttk.Entry(self, width=40, show="*")
        self.password.grid(row=4, column=0, sticky="w", pady=(0, 12))

        btns = ttk.Frame(self)
        btns.grid(row=5, column=0, sticky="w")

        ttk.Button(btns, text="Entrar", command=self.do_login).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(btns, text="Criar conta", command=self.do_register).grid(row=0, column=1)

        ttk.Separator(self).grid(row=6, column=0, sticky="ew", pady=18)

        info = (
            "Notas:\n"
            "- Utilizadores guardados em public.app_users\n"
            "- Senha guardada com hash (bcrypt)\n"
        )
        ttk.Label(self, text=info).grid(row=7, column=0, sticky="w")

    def do_login(self):
        """Realiza login"""
        u = self.username.get().strip()
        p = self.password.get().strip()
        if not u or not p:
            messagebox.showwarning("Atenção", "Preenche username e password.")
            return

        try:
            res = self.app.auth_service.authenticate(u, p)
            if res == "inactive":
                messagebox.showerror("Bloqueado", "Utilizador inativo. Contacta o administrador.")
                return
            if not res:
                messagebox.showerror("Erro", "Credenciais inválidas.")
                return

            self.app.db.audit(res, "LOGIN", "profiles", entity_pk=f"user_id={res['user_id']}", details={})
            self.app.show_main(res)
        except Exception as e:
            messagebox.showerror(
                "Erro de Conexão",
                "Não foi possível conectar ao Supabase.\n\n"
                "Verifica se o ficheiro .env tem as credenciais corretas:\n"
                "- SUPABASE_URL\n"
                "- SUPABASE_KEY\n\n"
                f"Erro: {str(e)}",
            )

    def do_register(self):
        """Regista novo utilizador"""
        username = simpledialog.askstring("Criar conta", "Username (login):", parent=self)
        if not username:
            return
        nome = simpledialog.askstring("Criar conta", "Nome do utilizador:", parent=self)
        if not nome:
            return
        setor = simpledialog.askstring("Criar conta", "Setor (opcional):", parent=self)
        password = simpledialog.askstring("Criar conta", "Password:", show="*", parent=self)
        if not password:
            return

        try:
            user_id = self.app.auth_service.create_user(username, nome, setor, password)
            self.app.db.audit({"user_id": user_id, "username": username}, "REGISTER", "profiles",
                            entity_pk=f"user_id={user_id}", details={"username": username, "setor": setor})
            messagebox.showinfo("OK", "Conta criada. Agora faz login.")
        except Exception as e:
            messagebox.showerror(
                "Erro de Conexão",
                "Não foi possível criar o utilizador.\n\n"
                "Verifica se o ficheiro .env tem as credenciais corretas.\n\n"
                f"Erro: {str(e)}",
            )
