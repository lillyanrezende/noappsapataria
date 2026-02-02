import os
import json
import bcrypt
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from dotenv import load_dotenv
from supabase import create_client, Client

# Carrega as variáveis do arquivo .env
load_dotenv()

# Acessa as variáveis de ambiente
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

DB_URL = os.getenv("DATABASE_URL")

#CONFIG

#tabelas existentes

DOMAIN_TABLES = {
   "brands": ("id", "name"),
    "categories": ("id", "name"),
    "subcategories": ("id", "name"),   # depende de category_id
    "colors": ("id", "name"),
    "sizes": ("id", "value"),
    "warehouses": ("id", "name"),
    "suppliers": ("id", "name"),
}

#DB Layer

class DB:
    def __init__(self):
        self.supabase = create_client(url, key)

    def init_app_tables(self):
        """
        Cria tabelas da aplicação (utilizadores e logs) se não existirem.
        Não mexe nas tuas tabelas principais (products/stock).
        Assume que as tabelas já existem no Supabase.
        """
        pass

    #AUTH

    def create_user(self, username, nome_usuario, setor, password):
            pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            data = {
                'username': username.strip(),
                'nome_usuario': nome_usuario.strip(),
                'setor': (setor or "").strip() or None,
                'password_hash': pw_hash
            }
            response = self.supabase.table('profiles').insert(data).execute()
            user_id = response.data[0]['user_id']
            return user_id


    def authenticate(self, username, password):
            response = self.supabase.table('profiles').select('*').eq('username', username.strip()).execute()
            if not response.data:
                return None
            row = response.data[0]
            if not row.get("is_active", True):
                return "inactive"
            if bcrypt.checkpw(password.encode("utf-8"), row["password_hash"].encode("utf-8")):
                return {
                    "user_id": row["user_id"],
                    "username": row["username"],
                    "nome_usuario": row["nome_usuario"],
                    "setor": row.get("setor"),
                    "role": row.get("role", "operator"),
                }
            return None

    #audit

    def audit(self, user, action, entity, entity_pk=None, details=None):
            data = {
                'user_id': user.get("user_id") if user else None,
                'username': user.get("username") if user else None,
                'action': action,
                'entity': entity,
                'entity_pk': entity_pk,
                'details': json.dumps(details or {})
            }
            self.supabase.table('audit_logs').insert(data).execute()

    #Domain Loaders

    def list_domain(self, table):
            id_col, name_col = DOMAIN_TABLES[table]
            response = self.supabase.table(table).select(f'{id_col}, {name_col}').order(name_col).execute()
            return [(r[id_col], r[name_col]) for r in response.data]

    def list_subcategories_by_category(self, category_id):
            response = self.supabase.table('subcategories').select('id, name').eq('category_id', category_id).order('name').execute()
            return [(r['id'], r['name']) for r in response.data]

    def get_or_create_simple_domain(self, table, value):
            """
            Para brands/categories/colors/warehouses/suppliers/sizes.
            """
            value = value.strip()
            id_col, name_col = DOMAIN_TABLES[table]
            response = self.supabase.table(table).select(id_col).eq(name_col, value).execute()
            if response.data:
                return response.data[0][id_col]
            response = self.supabase.table(table).insert({name_col: value}).execute()
            return response.data[0][id_col]

    def get_or_create_subcategory(self, category_id, name):
            name = name.strip()
            response = self.supabase.table('subcategories').select('id').eq('category_id', category_id).eq('name', name).execute()
            if response.data:
                return response.data[0]['id']
            response = self.supabase.table('subcategories').insert({'category_id': category_id, 'name': name}).execute()
            return response.data[0]['id']

    # Core Product operations

    def find_variant_by_gtin(self, gtin):
            gtin = gtin.strip()
            response = self.supabase.table('product_variant').select('*, product_model(*)').eq('gtin', gtin).execute()
            if response.data:
                row = response.data[0]
                model = row['product_model']
                return {
                    'variant_id': row['id'],
                    'gtin': row['gtin'],
                    'model_id': row['model_id'],
                    'cor_id': row['cor_id'],
                    'tamanho_id': row['tamanho_id'],
                    'ref_keyinvoice': row['ref_keyinvoice'],
                    'nome_modelo': model['nome_modelo'],
                    'marca_id': model['marca_id'],
                    'categoria_id': model['categoria_id'],
                    'subcategoria_id': model['subcategoria_id'],
                    'fornecedor_id': model['fornecedor_id']
                }
            return None

    def get_or_create_model(self, nome_modelo, marca_id, categoria_id, subcategoria_id, fornecedor_id, ref=None):
            """
            Reutiliza modelo se já existir com as mesmas dimensões principais.
            """
            response = self.supabase.table('product_model').select('id').eq('nome_modelo', nome_modelo.strip()).eq('marca_id', marca_id).eq('categoria_id', categoria_id).eq('subcategoria_id', subcategoria_id).eq('fornecedor_id', fornecedor_id).execute()
            if response.data:
                return response.data[0]['id']
            data = {
                'ref': ref,
                'nome_modelo': nome_modelo.strip(),
                'marca_id': marca_id,
                'categoria_id': categoria_id,
                'subcategoria_id': subcategoria_id,
                'fornecedor_id': fornecedor_id
            }
            response = self.supabase.table('product_model').insert(data).execute()
            return response.data[0]['id']

    def create_variant(self, model_id, gtin, cor_id, tamanho_id, ref_keyinvoice=None):
            data = {
                'model_id': model_id,
                'gtin': gtin.strip(),
                'cor_id': cor_id,
                'tamanho_id': tamanho_id,
                'ref_keyinvoice': ref_keyinvoice
            }
            response = self.supabase.table('product_variant').insert(data).execute()
            return response.data[0]['id']

    def upsert_stock(self, variant_id, warehouse_id, stock):
            data = {
                'variant_id': variant_id,
                'warehouse_id': warehouse_id,
                'stock': int(stock)
            }
            self.supabase.table('warehouse_stock').upsert(data).execute()

    def delete_stock_row(self, variant_id, warehouse_id):
            self.supabase.table('warehouse_stock').delete().eq('variant_id', variant_id).eq('warehouse_id', warehouse_id).execute()

    def variant_has_any_stock_rows(self, variant_id):
            response = self.supabase.table('warehouse_stock').select('variant_id').eq('variant_id', variant_id).limit(1).execute()
            return len(response.data) > 0

    def delete_variant_if_orphan(self, variant_id):
            """
            Apaga a variação se ela não tiver stock em nenhum armazém.
            """
            if self.variant_has_any_stock_rows(variant_id):
                return False
            self.supabase.table('product_variant').delete().eq('id', variant_id).execute()
            return True

    def update_variant_and_model(self, gtin, model_fields, variant_fields):
            """
            gtin não muda.
            model_fields: {nome_modelo, marca_id, categoria_id, subcategoria_id, fornecedor_id}
            variant_fields: {cor_id, tamanho_id, ref_keyinvoice}
            """
            row = self.find_variant_by_gtin(gtin)
            if not row:
                return False, "GTIN não encontrado."

            variant_id = row["variant_id"]
            model_id = row["model_id"]

            # update model
            model_data = {
                'nome_modelo': model_fields["nome_modelo"].strip(),
                'marca_id': model_fields["marca_id"],
                'categoria_id': model_fields["categoria_id"],
                'subcategoria_id': model_fields["subcategoria_id"],
                'fornecedor_id': model_fields["fornecedor_id"]
            }
            self.supabase.table('product_model').update(model_data).eq('id', model_id).execute()

            # update variant
            variant_data = {
                'cor_id': variant_fields["cor_id"],
                'tamanho_id': variant_fields["tamanho_id"],
                'ref_keyinvoice': variant_fields.get("ref_keyinvoice")
            }
            self.supabase.table('product_variant').update(variant_data).eq('id', variant_id).execute()

            return True, "Atualizado com sucesso."

#METODO DE PESQUISA QUE VOLTA UMA LISTA DE VARIANTES

    def search_variants(self, search_value, search_type='gtin'):
        search_value = str(search_value).strip()

        if search_type == 'gtin':
            field = 'gtin'
        elif search_type == 'ref_keyinvoice':
            field = 'ref_keyinvoice'
        elif search_type == 'ref_woocommerce':
            field = 'ref_woocomerce'  # OU 'ref_woocommerce' se for esse o nome real no DB
        else:
            raise ValueError("search_type inválido")

        resp = self.supabase.table('product_variant').select(
            'id, gtin, ref_keyinvoice, ref_woocomerce, '
            'model_id, product_model(nome_modelo), '
            'colors(name), sizes(value)'
        ).eq(field, search_value).execute()

        results = []
        for r in (resp.data or []):
            results.append({
                "variant_id": r["id"],
                "gtin": r.get("gtin"),
                "ref_keyinvoice": r.get("ref_keyinvoice"),
                "ref_woocomerce": r.get("ref_woocomerce"),
                "nome_modelo": (r.get("product_model") or {}).get("nome_modelo"),
                "cor": (r.get("colors") or {}).get("name"),
                "tamanho": (r.get("sizes") or {}).get("value"),
            })
        return results

#CARREGAR UMA VARIANTE ESPECIFICA 
    def get_full_view_by_variant_id(self, variant_id):
        resp = self.supabase.table('product_variant').select(
            '*, product_model(*, brands(*), categories(*), subcategories(*), suppliers(*)), colors(*), sizes(*)'
        ).eq('id', variant_id).execute()

        if not resp.data:
            return None

        row = resp.data[0]

        header = {
            'variant_id': row['id'],
            'gtin': row.get('gtin'),
            'ref_keyinvoice': row.get('ref_keyinvoice'),
            'ref_woocomerce': row.get('ref_woocomerce'),

            # IDs da variant
            'model_id': row.get('model_id'),
            'cor_id': row.get('cor_id'),
            'tamanho_id': row.get('tamanho_id'),

            # IDs do model (o que a UI precisa!)
            'marca_id': row['product_model'].get('marca_id'),
            'categoria_id': row['product_model'].get('categoria_id'),
            'subcategoria_id': row['product_model'].get('subcategoria_id'),
            'fornecedor_id': row['product_model'].get('fornecedor_id'),

            # Campos para mostrar
            'nome_modelo': row['product_model']['nome_modelo'],
            'marca': row['product_model']['brands']['name'] if row['product_model'].get('brands') else None,
            'categoria': row['product_model']['categories']['name'] if row['product_model'].get('categories') else None,
            'subcategoria': row['product_model']['subcategories']['name'] if row['product_model'].get('subcategories') else None,
            'fornecedor': row['product_model']['suppliers']['name'] if row['product_model'].get('suppliers') else None,
            'cor': row['colors']['name'] if row.get('colors') else None,
            'tamanho': row['sizes']['value'] if row.get('sizes') else None,
        }

        stocks_resp = self.supabase.table('warehouse_stock').select(
            'stock, warehouses(name)'
        ).eq('variant_id', row['id']).execute()

        stocks = [{'armazem': s['warehouses']['name'], 'stock': s['stock']} for s in (stocks_resp.data or [])]
        return header, stocks



    def get_full_view_by_gtin(self, search_value, search_type='gtin'):
        search_value = str(search_value).strip()

        # Determinar o campo de busca
        if search_type == 'gtin':
            field = 'gtin'
        elif search_type == 'ref_keyinvoice':
            field = 'ref_keyinvoice'
        elif search_type == 'ref_woocommerce':
            field = 'ref_woocomerce'  # mantém se no DB está assim
        else:
            return None

        response = self.supabase.table('product_variant').select(
            '*, product_model(*, brands(*), categories(*), subcategories(*), suppliers(*)), colors(*), sizes(*)'
        ).eq(field, search_value).execute()

        if not response.data:
            return None

        row = response.data[0]
        header = {
            'variant_id': row['id'],
            'gtin': row.get('gtin'),
            'ref_keyinvoice': row.get('ref_keyinvoice'),
            'ref_woocomerce': row.get('ref_woocomerce'),

            # IDs da variant
            'model_id': row.get('model_id'),
            'cor_id': row.get('cor_id'),
            'tamanho_id': row.get('tamanho_id'),

            # IDs do model (CRÍTICO para preencher combobox)
            'marca_id': row['product_model'].get('marca_id'),
            'categoria_id': row['product_model'].get('categoria_id'),
            'subcategoria_id': row['product_model'].get('subcategoria_id'),
            'fornecedor_id': row['product_model'].get('fornecedor_id'),

            # Campos “humanos” (pra exibir)
            'nome_modelo': row['product_model']['nome_modelo'],
            'marca': row['product_model']['brands']['name'] if row['product_model'].get('brands') else None,
            'categoria': row['product_model']['categories']['name'] if row['product_model'].get('categories') else None,
            'subcategoria': row['product_model']['subcategories']['name'] if row['product_model'].get('subcategories') else None,
            'fornecedor': row['product_model']['suppliers']['name'] if row['product_model'].get('suppliers') else None,
            'cor': row['colors']['name'] if row.get('colors') else None,
            'tamanho': row['sizes']['value'] if row.get('sizes') else None,
        }

        stocks_response = self.supabase.table('warehouse_stock').select(
            'stock, warehouses(name)'
        ).eq('variant_id', row['id']).execute()

        stocks = [
            {'armazem': s['warehouses']['name'], 'stock': s['stock']}
            for s in (stocks_response.data or [])
        ]

        return header, stocks


#UI Helpers

def safe_int(s, default=None):
    try:
        return int(str(s).strip())
    except Exception:
        return default

class AddOptionDialog(simpledialog.Dialog):
    def __init__(self, parent, title, label):
        self.label = label
        self.value = None
        super().__init__(parent, title)

    def body(self, master):
        ttk.Label(master, text=self.label).grid(row=0, column=0, sticky="w", padx=6, pady=6)
        self.entry = ttk.Entry(master, width=40)
        self.entry.grid(row=1, column=0, padx=6, pady=6)
        return self.entry

    def apply(self):
        self.value = self.entry.get().strip()

#main app

class App(tk.Tk):
    def __init__(self, db: DB):
        super().__init__()
        self.title("Sistema Sapataria - Cadastro/Stock (Supabase)")
        self.geometry("980x700")
        self.db = db
        self.user = None

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


class LoginFrame(ttk.Frame):
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
        u = self.username.get().strip()
        p = self.password.get().strip()
        if not u or not p:
            messagebox.showwarning("Atenção", "Preenche username e password.")
            return

        res = self.app.db.authenticate(u, p)
        if res == "inactive":
            messagebox.showerror("Bloqueado", "Utilizador inativo. Contacta o administrador.")
            return
        if not res:
            messagebox.showerror("Erro", "Credenciais inválidas.")
            return

        self.app.db.audit(res, "LOGIN", "profiles", entity_pk=f"user_id={res['user_id']}", details={})
        self.app.show_main(res)

    def do_register(self):
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
            user_id = self.app.db.create_user(username, nome, setor, password)
            self.app.db.audit({"user_id": user_id, "username": username}, "REGISTER", "profiles", entity_pk=f"user_id={user_id}", details={"username": username, "setor": setor})
            messagebox.showinfo("OK", "Conta criada. Agora faz login.")
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível criar o utilizador.\n\n{e}")

class MainFrame(ttk.Frame):
    def __init__(self, app: App):
        super().__init__(app, padding=10)
        self.app = app

        top = ttk.Frame(self)
        top.pack(fill="x")

        ttk.Label(top, text=f"Utilizador: {app.user['nome_usuario']}  |  Setor: {app.user.get('setor') or '-'}", font=("Segoe UI", 10, "bold")).pack(side="left")
        ttk.Button(top, text="Sair", command=self.logout).pack(side="right")

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, pady=(10, 0))

        self.tab_create = CreateTab(nb, app)
        self.tab_update = UpdateTab(nb, app)
        self.tab_delete = DeleteTab(nb, app)
        self.tab_view = ViewTab(nb, app)

        nb.add(self.tab_create, text="Cadastrar")
        nb.add(self.tab_update, text="Alterar")
        nb.add(self.tab_delete, text="Excluir")
        nb.add(self.tab_view, text="Visualizar")

    def logout(self):
        self.app.db.audit(self.app.user, "LOGOUT", "profiles", entity_pk=f"user_id={self.app.user['user_id']}", details={})
        self.app.user = None
        self.app.show_login()

# tab base

class BaseTab(ttk.Frame):
    def __init__(self, parent, app: App):
        super().__init__(parent, padding=10)
        self.app = app
        self.db = app.db

        self.cache = {}

    def load_domains(self):
        self.cache["brands"] = self.db.list_domain("brands")
        self.cache["categories"] = self.db.list_domain("categories")
        self.cache["colors"] = self.db.list_domain("colors")
        self.cache["sizes"] = self.db.list_domain("sizes")
        self.cache["warehouses"] = self.db.list_domain("warehouses")
        self.cache["suppliers"] = self.db.list_domain("suppliers")

    def tuple_list_to_map(self, rows):
        # rows: [(id, name), ...]
        id_to_name = {r[0]: r[1] for r in rows}
        name_to_id = {r[1]: r[0] for r in rows}
        return id_to_name, name_to_id

    def ask_add_option(self, table, label):
        dlg = AddOptionDialog(self, f"Adicionar {label}", f"Novo {label}:")
        if dlg.value:
            if table == "subcategories":
                raise RuntimeError("Use add_subcategory (depende da categoria).")
            new_id = self.db.get_or_create_simple_domain(table, dlg.value)
            return new_id, dlg.value
        return None, None

#CREATE TAB

class CreateTab(BaseTab):
    def __init__(self, parent, app: App):
        super().__init__(parent, app)

        self.load_domains()

        ttk.Label(self, text="Cadastrar Produto", font=("Segoe UI", 14, "bold")).grid(row=0, column=0, columnspan=6, sticky="w", pady=(0, 12))

        # Fields
        self.gtin = ttk.Entry(self, width=28)
        self.ref_keyinvoice = ttk.Entry(self, width=28)
        self.nome_modelo = ttk.Entry(self, width=28)
        self.stock = ttk.Entry(self, width=10)

        # Dropdown variables
        self.var_brand = tk.StringVar()
        self.var_category = tk.StringVar()
        self.var_subcategory = tk.StringVar()
        self.var_color = tk.StringVar()
        self.var_size = tk.StringVar()
        self.var_warehouse = tk.StringVar()
        self.var_supplier = tk.StringVar()

        self._build_form()
        self._refresh_dropdowns()

    def _build_form(self):
        r = 1

        ttk.Label(self, text="GTIN").grid(row=r, column=0, sticky="w")
        self.gtin.grid(row=r, column=1, sticky="w", padx=(0, 12))
        ttk.Label(self, text="Ref KeyInvoice (opcional)").grid(row=r, column=2, sticky="w")
        self.ref_keyinvoice.grid(row=r, column=3, sticky="w")
        r += 1

        ttk.Label(self, text="Modelo (nome_modelo)").grid(row=r, column=0, sticky="w", pady=(8, 0))
        self.nome_modelo.grid(row=r, column=1, sticky="w", padx=(0, 12), pady=(8, 0))
        r += 1

        # Brand / Supplier
        ttk.Label(self, text="Marca").grid(row=r, column=0, sticky="w", pady=(8, 0))
        self.combo_brand = ttk.Combobox(self, textvariable=self.var_brand, width=25, state="readonly")
        self.combo_brand.grid(row=r, column=1, sticky="w", padx=(0, 6), pady=(8, 0))
        ttk.Button(self, text="+", width=3, command=self.add_brand).grid(row=r, column=1, sticky="e", pady=(8, 0))

        ttk.Label(self, text="Fornecedor").grid(row=r, column=2, sticky="w", pady=(8, 0))
        self.combo_supplier = ttk.Combobox(self, textvariable=self.var_supplier, width=25, state="readonly")
        self.combo_supplier.grid(row=r, column=3, sticky="w", padx=(0, 6), pady=(8, 0))
        ttk.Button(self, text="+", width=3, command=self.add_supplier).grid(row=r, column=3, sticky="e", pady=(8, 0))
        r += 1

        # Category / Subcategory
        ttk.Label(self, text="Categoria").grid(row=r, column=0, sticky="w", pady=(8, 0))
        self.combo_category = ttk.Combobox(self, textvariable=self.var_category, width=25, state="readonly")
        self.combo_category.grid(row=r, column=1, sticky="w", padx=(0, 6), pady=(8, 0))
        ttk.Button(self, text="+", width=3, command=self.add_category).grid(row=r, column=1, sticky="e", pady=(8, 0))

        ttk.Label(self, text="Subcategoria").grid(row=r, column=2, sticky="w", pady=(8, 0))
        self.combo_subcategory = ttk.Combobox(self, textvariable=self.var_subcategory, width=25, state="readonly")
        self.combo_subcategory.grid(row=r, column=3, sticky="w", padx=(0, 6), pady=(8, 0))
        ttk.Button(self, text="+", width=3, command=self.add_subcategory).grid(row=r, column=3, sticky="e", pady=(8, 0))
        r += 1

        # Color / Size / Warehouse / Stock
        ttk.Label(self, text="Cor").grid(row=r, column=0, sticky="w", pady=(8, 0))
        self.combo_color = ttk.Combobox(self, textvariable=self.var_color, width=25, state="readonly")
        self.combo_color.grid(row=r, column=1, sticky="w", padx=(0, 6), pady=(8, 0))
        ttk.Button(self, text="+", width=3, command=self.add_color).grid(row=r, column=1, sticky="e", pady=(8, 0))

        ttk.Label(self, text="Tamanho").grid(row=r, column=2, sticky="w", pady=(8, 0))
        self.combo_size = ttk.Combobox(self, textvariable=self.var_size, width=25, state="readonly")
        self.combo_size.grid(row=r, column=3, sticky="w", padx=(0, 6), pady=(8, 0))
        ttk.Button(self, text="+", width=3, command=self.add_size).grid(row=r, column=3, sticky="e", pady=(8, 0))
        r += 1

        ttk.Label(self, text="Armazém").grid(row=r, column=0, sticky="w", pady=(8, 0))
        self.combo_warehouse = ttk.Combobox(self, textvariable=self.var_warehouse, width=25, state="readonly")
        self.combo_warehouse.grid(row=r, column=1, sticky="w", padx=(0, 6), pady=(8, 0))
        ttk.Button(self, text="+", width=3, command=self.add_warehouse).grid(row=r, column=1, sticky="e", pady=(8, 0))

        ttk.Label(self, text="Stock").grid(row=r, column=2, sticky="w", pady=(8, 0))
        self.stock.grid(row=r, column=3, sticky="w", pady=(8, 0))
        r += 1

        ttk.Separator(self).grid(row=r, column=0, columnspan=6, sticky="ew", pady=14)
        r += 1

        ttk.Button(self, text="Cadastrar / Atualizar Stock", command=self.save).grid(row=r, column=0, sticky="w")
        ttk.Button(self, text="Limpar", command=self.clear).grid(row=r, column=1, sticky="w", padx=(8, 0))

        # events
        self.combo_category.bind("<<ComboboxSelected>>", lambda e: self._refresh_subcategories())

    def _refresh_dropdowns(self):
        self.load_domains()

        # Map domains
        self.brand_rows = self.cache["brands"]
        self.category_rows = self.cache["categories"]
        self.color_rows = self.cache["colors"]
        self.size_rows = self.cache["sizes"]
        self.warehouse_rows = self.cache["warehouses"]
        self.supplier_rows = self.cache["suppliers"]

        self.brand_id_to_name, self.brand_name_to_id = self.tuple_list_to_map(self.brand_rows)
        self.category_id_to_name, self.category_name_to_id = self.tuple_list_to_map(self.category_rows)
        self.color_id_to_name, self.color_name_to_id = self.tuple_list_to_map(self.color_rows)
        self.size_id_to_name, self.size_name_to_id = self.tuple_list_to_map(self.size_rows)
        self.warehouse_id_to_name, self.warehouse_name_to_id = self.tuple_list_to_map(self.warehouse_rows)
        self.supplier_id_to_name, self.supplier_name_to_id = self.tuple_list_to_map(self.supplier_rows)

        self.combo_brand["values"] = list(self.brand_name_to_id.keys())
        self.combo_category["values"] = list(self.category_name_to_id.keys())
        self.combo_color["values"] = list(self.color_name_to_id.keys())
        self.combo_size["values"] = list(self.size_name_to_id.keys())
        self.combo_warehouse["values"] = list(self.warehouse_name_to_id.keys())
        self.combo_supplier["values"] = list(self.supplier_name_to_id.keys())

        # default selections if empty
        if not self.var_brand.get() and self.combo_brand["values"]:
            self.var_brand.set(self.combo_brand["values"][0])
        if not self.var_category.get() and self.combo_category["values"]:
            self.var_category.set(self.combo_category["values"][0])
            self._refresh_subcategories()
        if not self.var_color.get() and self.combo_color["values"]:
            self.var_color.set(self.combo_color["values"][0])
        if not self.var_size.get() and self.combo_size["values"]:
            self.var_size.set(self.combo_size["values"][0])
        if not self.var_warehouse.get() and self.combo_warehouse["values"]:
            self.var_warehouse.set(self.combo_warehouse["values"][0])
        if not self.var_supplier.get() and self.combo_supplier["values"]:
            self.var_supplier.set(self.combo_supplier["values"][0])

    def _refresh_subcategories(self):
        cat_name = self.var_category.get().strip()
        cat_id = self.category_name_to_id.get(cat_name)
        if not cat_id:
            self.combo_subcategory["values"] = []
            self.var_subcategory.set("")
            return
        subs = self.db.list_subcategories_by_category(cat_id)
        self.sub_id_to_name = {r[0]: r[1] for r in subs}
        self.sub_name_to_id = {r[1]: r[0] for r in subs}
        self.combo_subcategory["values"] = list(self.sub_name_to_id.keys())
        if self.combo_subcategory["values"]:
            self.var_subcategory.set(self.combo_subcategory["values"][0])
        else:
            self.var_subcategory.set("")

    # Add domain handlers
    def add_brand(self):
        new_id, new_val = self.ask_add_option("brands", "Marca")
        if new_id:
            self._refresh_dropdowns()
            self.var_brand.set(new_val)

    def add_supplier(self):
        new_id, new_val = self.ask_add_option("suppliers", "Fornecedor")
        if new_id:
            self._refresh_dropdowns()
            self.var_supplier.set(new_val)

    def add_category(self):
        new_id, new_val = self.ask_add_option("categories", "Categoria")
        if new_id:
            self._refresh_dropdowns()
            self.var_category.set(new_val)
            self._refresh_subcategories()

    def add_subcategory(self):
        cat_name = self.var_category.get().strip()
        cat_id = self.category_name_to_id.get(cat_name)
        if not cat_id:
            messagebox.showwarning("Atenção", "Escolhe uma categoria primeiro.")
            return
        dlg = AddOptionDialog(self, "Adicionar Subcategoria", "Nova Subcategoria:")
        if dlg.value:
            sub_id = self.db.get_or_create_subcategory(cat_id, dlg.value)
            self._refresh_subcategories()
            self.var_subcategory.set(dlg.value)

    def add_color(self):
        new_id, new_val = self.ask_add_option("colors", "Cor")
        if new_id:
            self._refresh_dropdowns()
            self.var_color.set(new_val)

    def add_size(self):
        dlg = AddOptionDialog(self, "Adicionar Tamanho", "Novo Tamanho (ex: 40):")
        if dlg.value:
            new_id = self.db.get_or_create_simple_domain("sizes", dlg.value)
            self._refresh_dropdowns()
            self.var_size.set(dlg.value)

    def add_warehouse(self):
        new_id, new_val = self.ask_add_option("warehouses", "Armazém")
        if new_id:
            self._refresh_dropdowns()
            self.var_warehouse.set(new_val)

    def clear(self):
        self.gtin.delete(0, tk.END)
        self.ref_keyinvoice.delete(0, tk.END)
        self.nome_modelo.delete(0, tk.END)
        self.stock.delete(0, tk.END)

    def save(self):
        gtin = self.gtin.get().strip()
        if not gtin:
            messagebox.showwarning("Atenção", "GTIN é obrigatório.")
            return

        stock_val = safe_int(self.stock.get(), None)
        if stock_val is None or stock_val < 0:
            messagebox.showwarning("Atenção", "Stock inválido (precisa ser número inteiro >= 0).")
            return

        # dropdown selections
        brand_id = self.brand_name_to_id.get(self.var_brand.get())
        cat_id = self.category_name_to_id.get(self.var_category.get())
        sub_id = self.sub_name_to_id.get(self.var_subcategory.get()) if hasattr(self, "sub_name_to_id") else None
        color_id = self.color_name_to_id.get(self.var_color.get())
        size_id = self.size_name_to_id.get(self.var_size.get())
        wh_id = self.warehouse_name_to_id.get(self.var_warehouse.get())
        supplier_id = self.supplier_name_to_id.get(self.var_supplier.get())

        nome_modelo = self.nome_modelo.get().strip()
        if not nome_modelo:
            messagebox.showwarning("Atenção", "Modelo (nome_modelo) é obrigatório.")
            return
        if not (brand_id and cat_id and sub_id and color_id and size_id and wh_id and supplier_id):
            messagebox.showwarning("Atenção", "Preenche todas as opções (marca/categoria/subcategoria/cor/tamanho/armazém/fornecedor).")
            return

        ref_keyinvoice = self.ref_keyinvoice.get().strip() or None

        try:
            existing = self.db.find_variant_by_gtin(gtin)

            if existing:
                # GTIN já existe: só atualiza/insere stock para o armazém
                variant_id = existing["variant_id"]
                self.db.upsert_stock(variant_id, wh_id, stock_val)

                self.db.audit(self.app.user, "UPSERT_STOCK", "warehouse_stock",
                              entity_pk=f"variant_id={variant_id},warehouse_id={wh_id}",
                              details={"gtin": gtin, "stock": stock_val, "warehouse": self.var_warehouse.get()})

                messagebox.showinfo("OK", "GTIN já existia. Stock atualizado para o armazém selecionado.")
                return

            # GTIN não existe: cria model (ou reutiliza), cria variant, cria stock
            model_id = self.db.get_or_create_model(
                nome_modelo=nome_modelo,
                marca_id=brand_id,
                categoria_id=cat_id,
                subcategoria_id=sub_id,
                fornecedor_id=supplier_id
            )

            variant_id = self.db.create_variant(
                model_id=model_id,
                gtin=gtin,
                cor_id=color_id,
                tamanho_id=size_id,
                ref_keyinvoice=ref_keyinvoice
            )

            self.db.upsert_stock(variant_id, wh_id, stock_val)

            self.db.audit(self.app.user, "CREATE_VARIANT", "product_variant",
                          entity_pk=f"id={variant_id}",
                          details={"gtin": gtin, "model_id": model_id})

            self.db.audit(self.app.user, "CREATE_STOCK", "warehouse_stock",
                          entity_pk=f"variant_id={variant_id},warehouse_id={wh_id}",
                          details={"gtin": gtin, "stock": stock_val, "warehouse": self.var_warehouse.get()})

            messagebox.showinfo("OK", "Produto cadastrado (model + variant) e stock criado.")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao cadastrar.\n\n{e}")

#update tab

class UpdateTab(BaseTab):
    def __init__(self, parent, app: App):
        super().__init__(parent, app)

        self.load_domains()

        ttk.Label(self, text="Alterar Produto", font=("Segoe UI", 14, "bold")).grid(
            row=0, column=0, columnspan=6, sticky="w", pady=(0, 12)
        )

        ttk.Label(self, text="Buscar por:").grid(row=1, column=0, sticky="w")

        self.var_search_type = tk.StringVar(value="gtin")
        search_frame = ttk.Frame(self)
        search_frame.grid(row=1, column=1, columnspan=3, sticky="w")

        ttk.Radiobutton(search_frame, text="GTIN", variable=self.var_search_type, value="gtin").pack(side="left", padx=(0, 10))
        ttk.Radiobutton(search_frame, text="Ref KeyInvoice", variable=self.var_search_type, value="ref_keyinvoice").pack(side="left", padx=(0, 10))
        ttk.Radiobutton(search_frame, text="Ref WooCommerce", variable=self.var_search_type, value="ref_woocommerce").pack(side="left")

        ttk.Label(self, text="Código:").grid(row=2, column=0, sticky="w", pady=(6, 0))
        self.search_value = ttk.Entry(self, width=28)
        self.search_value.grid(row=2, column=1, sticky="w", padx=(0, 8), pady=(6, 0))

        ttk.Button(self, text="Procurar", command=self.search_variants).grid(row=2, column=2, sticky="w", pady=(6, 0))
        ttk.Button(self, text="Carregar selecionado", command=self.load_selected_variant).grid(row=2, column=3, sticky="w", pady=(6, 0))

        # Treeview (lista de variações encontradas)
        cols = ("variant_id", "gtin", "modelo", "cor", "tamanho", "ref_keyinvoice", "ref_woocomerce")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=6)
        self.tree.grid(row=3, column=0, columnspan=6, sticky="ew", pady=(10, 0))

        self.tree.heading("variant_id", text="Variant ID")
        self.tree.heading("gtin", text="GTIN")
        self.tree.heading("modelo", text="Modelo")
        self.tree.heading("cor", text="Cor")
        self.tree.heading("tamanho", text="Tamanho")
        self.tree.heading("ref_keyinvoice", text="Ref KeyInvoice")
        self.tree.heading("ref_woocomerce", text="Ref WooCommerce")

        self.tree.column("variant_id", width=90, anchor="w")
        self.tree.column("gtin", width=120, anchor="w")
        self.tree.column("modelo", width=180, anchor="w")
        self.tree.column("cor", width=120, anchor="w")
        self.tree.column("tamanho", width=80, anchor="w")
        self.tree.column("ref_keyinvoice", width=120, anchor="w")
        self.tree.column("ref_woocomerce", width=130, anchor="w")

        # duplo clique carrega
        self.tree.bind("<Double-1>", lambda e: self.load_selected_variant())

        ttk.Separator(self).grid(row=4, column=0, columnspan=6, sticky="ew", pady=12)

        # label que mostra o que foi carregado
        self.lbl_gtin = ttk.Label(self, text="Item carregado: -", font=("Segoe UI", 10, "bold"))
        self.lbl_gtin.grid(row=5, column=0, columnspan=6, sticky="w")
        self.form_row0 = 6 

        # ---------------------------
        # A PARTIR DAQUI, mantém o formulário normal
        # ---------------------------
        self.nome_modelo = ttk.Entry(self, width=28)
        self.ref_keyinvoice = ttk.Entry(self, width=28)

        self.var_brand = tk.StringVar()
        self.var_category = tk.StringVar()
        self.var_subcategory = tk.StringVar()
        self.var_supplier = tk.StringVar()
        self.var_color = tk.StringVar()
        self.var_size = tk.StringVar()
        self.var_warehouse = tk.StringVar()

        self.combo_brand = ttk.Combobox(self, textvariable=self.var_brand, width=25, state="readonly")
        self.combo_category = ttk.Combobox(self, textvariable=self.var_category, width=25, state="readonly")
        self.combo_subcategory = ttk.Combobox(self, textvariable=self.var_subcategory, width=25, state="readonly")
        self.combo_supplier = ttk.Combobox(self, textvariable=self.var_supplier, width=25, state="readonly")
        self.combo_color = ttk.Combobox(self, textvariable=self.var_color, width=25, state="readonly")
        self.combo_size = ttk.Combobox(self, textvariable=self.var_size, width=25, state="readonly")
        self.combo_warehouse = ttk.Combobox(self, textvariable=self.var_warehouse, width=25, state="readonly")

        self._refresh_dropdowns()
        self._build_edit_fields()

        self.combo_category.bind("<<ComboboxSelected>>", lambda e: self._refresh_subcategories())

        # Stock section (mantém)
        r0 = self.form_row0

        ttk.Label(self, text="Stock por armazém (seleciona e atualiza)", font=("Segoe UI", 10, "bold")).grid(
        row=r0+8, column=0, columnspan=4, sticky="w", pady=(14, 6)
        )
        self.combo_warehouse.grid(row=r0+9, column=0, sticky="w")
        self.stock = ttk.Entry(self, width=10)
        self.stock.grid(row=r0+9, column=1, sticky="w", padx=(8, 0))
        ttk.Button(self, text="Atualizar stock", command=self.update_stock).grid(row=r0+9, column=2, sticky="w", padx=(8, 0))

        self.loaded_variant_id = None

    # ---------------------------
    # NOVAS FUNÇÕES
    # ---------------------------
    def search_variants(self):
        value = self.search_value.get().strip()
        search_type = self.var_search_type.get()

        if not value:
            messagebox.showwarning("Atenção", "Informa um código para buscar.")
            return

        try:
            results = self.db.search_variants(value, search_type)

            # limpa a lista
            for iid in self.tree.get_children():
                self.tree.delete(iid)

            if not results:
                messagebox.showinfo("Não encontrado", "Nenhuma variação encontrada para esse código.")
                return

            # preenche a lista
            for r in results:
                self.tree.insert(
                    "", "end",
                    values=(
                        r["variant_id"],
                        r.get("gtin") or "",
                        r.get("nome_modelo") or "",
                        r.get("cor") or "",
                        r.get("tamanho") or "",
                        r.get("ref_keyinvoice") or "",
                        r.get("ref_woocomerce") or "",
                    )
                )

            # se só tiver 1, carrega logo (menos cliques)
            if len(results) == 1:
                self.tree.selection_set(self.tree.get_children()[0])
                self.load_selected_variant()

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao buscar.\n\n{e}")

    def load_selected_variant(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Atenção", "Seleciona uma variação na lista.")
            return

        values = self.tree.item(sel[0], "values")
        variant_id = values[0]

        try:
            full = self.db.get_full_view_by_variant_id(variant_id)
            if not full:
                messagebox.showinfo("Não encontrado", "Essa variação não existe mais.")
                return

            header, stocks = full
            self.loaded_variant_id = header["variant_id"]

            self.lbl_gtin.config(
                text=f"Item carregado: GTIN={header.get('gtin')} | variant_id={header['variant_id']}"
            )

            # preencher campos texto
            self.nome_modelo.delete(0, tk.END)
            self.nome_modelo.insert(0, header.get("nome_modelo") or "")

            self.ref_keyinvoice.delete(0, tk.END)
            self.ref_keyinvoice.insert(0, header.get("ref_keyinvoice") or "")

            # dropdowns por ID (usa teus mapas já existentes)
            self.var_brand.set(self.brand_id_to_name.get(header["marca_id"], ""))
            self.var_category.set(self.category_id_to_name.get(header["categoria_id"], ""))

            self._refresh_subcategories()
            self.var_subcategory.set(self.sub_id_to_name.get(header["subcategoria_id"], ""))

            self.var_supplier.set(self.supplier_id_to_name.get(header["fornecedor_id"], ""))
            self.var_color.set(self.color_id_to_name.get(header["cor_id"], ""))
            self.var_size.set(self.size_id_to_name.get(header["tamanho_id"], ""))

            # (opcional) stock: mostra do primeiro armazém encontrado
            if stocks:
                # tenta casar com o nome do armazém no combo
                wh_name = stocks[0]["armazem"]
                if wh_name in self.combo_warehouse["values"]:
                    self.var_warehouse.set(wh_name)
                self.stock.delete(0, tk.END)
                self.stock.insert(0, str(stocks[0]["stock"]))
            else:
                self.stock.delete(0, tk.END)

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao carregar.\n\n{e}")

    def _refresh_dropdowns(self):
        self.load_domains()

        self.brand_rows = self.cache["brands"]
        self.category_rows = self.cache["categories"]
        self.color_rows = self.cache["colors"]
        self.size_rows = self.cache["sizes"]
        self.warehouse_rows = self.cache["warehouses"]
        self.supplier_rows = self.cache["suppliers"]

        self.brand_id_to_name, self.brand_name_to_id = self.tuple_list_to_map(self.brand_rows)
        self.category_id_to_name, self.category_name_to_id = self.tuple_list_to_map(self.category_rows)
        self.color_id_to_name, self.color_name_to_id = self.tuple_list_to_map(self.color_rows)
        self.size_id_to_name, self.size_name_to_id = self.tuple_list_to_map(self.size_rows)
        self.warehouse_id_to_name, self.warehouse_name_to_id = self.tuple_list_to_map(self.warehouse_rows)
        self.supplier_id_to_name, self.supplier_name_to_id = self.tuple_list_to_map(self.supplier_rows)

        self.combo_brand["values"] = list(self.brand_name_to_id.keys())
        self.combo_category["values"] = list(self.category_name_to_id.keys())
        self.combo_color["values"] = list(self.color_name_to_id.keys())
        self.combo_size["values"] = list(self.size_name_to_id.keys())
        self.combo_warehouse["values"] = list(self.warehouse_name_to_id.keys())
        self.combo_supplier["values"] = list(self.supplier_name_to_id.keys())

        if self.combo_warehouse["values"] and not self.var_warehouse.get():
            self.var_warehouse.set(self.combo_warehouse["values"][0])

    def _refresh_subcategories(self):
        cat_name = self.var_category.get().strip()
        cat_id = self.category_name_to_id.get(cat_name)
        if not cat_id:
            self.combo_subcategory["values"] = []
            self.var_subcategory.set("")
            return
        subs = self.db.list_subcategories_by_category(cat_id)
        self.sub_id_to_name = {r[0]: r[1] for r in subs}
        self.sub_name_to_id = {r[1]: r[0] for r in subs}
        self.combo_subcategory["values"] = list(self.sub_name_to_id.keys())
        if self.combo_subcategory["values"]:
            self.var_subcategory.set(self.combo_subcategory["values"][0])
        else:
            self.var_subcategory.set("")

    def _build_edit_fields(self):
        r0 = self.form_row0
        # model fields
        ttk.Label(self, text="Modelo").grid(row=r0+0, column=0, sticky="w", pady=(8, 0))
        self.nome_modelo.grid(row=r0+0, column=1, sticky="w", pady=(8, 0))

        ttk.Label(self, text="Marca").grid(row=r0+1, column=0, sticky="w", pady=(8, 0))
        self.combo_brand.grid(row=r0+1, column=1, sticky="w", pady=(8, 0))

        ttk.Label(self, text="Fornecedor").grid(row=r0+2, column=0, sticky="w", pady=(8, 0))
        self.combo_supplier.grid(row=r0+2, column=1, sticky="w", pady=(8, 0))

        ttk.Label(self, text="Categoria").grid(row=r0+3, column=0, sticky="w", pady=(8, 0))
        self.combo_category.grid(row=r0+3, column=1, sticky="w", pady=(8, 0))

        ttk.Label(self, text="Subcategoria").grid(row=r0+4, column=0, sticky="w", pady=(8, 0))
        self.combo_subcategory.grid(row=r0+4, column=1, sticky="w", pady=(8, 0))

        # variant fields
        ttk.Label(self, text="Cor").grid(row=r0+0, column=2, sticky="w", pady=(8, 0))
        self.combo_color.grid(row=r0+0, column=3, sticky="w", pady=(8, 0))

        ttk.Label(self, text="Tamanho").grid(row=r0+1, column=2, sticky="w", pady=(8, 0))
        self.combo_size.grid(row=r0+1, column=3, sticky="w", pady=(8, 0))

        ttk.Label(self, text="Ref KeyInvoice").grid(row=r0+2, column=2, sticky="w", pady=(8, 0))
        self.ref_keyinvoice.grid(row=r0+2, column=3, sticky="w", pady=(8, 0))

        ttk.Separator(self).grid(row=r0+5, column=0, columnspan=6, sticky="ew", pady=12)

        ttk.Button(self, text="Guardar alterações (item)", command=self.save_item).grid(row=r0+6, column=0, sticky="w", pady=(14, 0))
        ttk.Button(self, text="Limpar", command=self.clear).grid(row=r0+6, column=1, sticky="w", padx=(8, 0), pady=(14, 0))
    
    def clear(self):
        self.loaded_variant_id = None
        self.lbl_gtin.config(text="GTIN: -")
        self.nome_modelo.delete(0, tk.END)
        self.ref_keyinvoice.delete(0, tk.END)
        self.stock.delete(0, tk.END)

    def load_by_gtin(self):
        gtin = self.gtin.get().strip()
        if not gtin:
            messagebox.showwarning("Atenção", "Informa um GTIN.")
            return
        try:
            row = self.db.find_variant_by_gtin(gtin)
            if not row:
                messagebox.showinfo("Não encontrado", "GTIN não existe.")
                return

            self.loaded_variant_id = row["variant_id"]
            self.lbl_gtin.config(text=f"GTIN: {row['gtin']}  |  variant_id: {row['variant_id']}")

            # set form values
            self.nome_modelo.delete(0, tk.END)
            self.nome_modelo.insert(0, row["nome_modelo"] or "")

            # fill dropdowns by ids
            self.var_brand.set(self.brand_id_to_name.get(row["marca_id"], ""))
            self.var_category.set(self.category_id_to_name.get(row["categoria_id"], ""))
            self._refresh_subcategories()
            self.var_subcategory.set(self.sub_id_to_name.get(row["subcategoria_id"], ""))

            self.var_supplier.set(self.supplier_id_to_name.get(row["fornecedor_id"], ""))
            self.var_color.set(self.color_id_to_name.get(row["cor_id"], ""))
            self.var_size.set(self.size_id_to_name.get(row["tamanho_id"], ""))

            self.ref_keyinvoice.delete(0, tk.END)
            self.ref_keyinvoice.insert(0, row["ref_keyinvoice"] or "")

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao carregar.\n\n{e}")

    def save_item(self):
        if not self.loaded_variant_id:
            messagebox.showwarning("Atenção", "Carrega um GTIN primeiro.")
            return

        gtin = self.gtin.get().strip()
        nome_modelo = self.nome_modelo.get().strip()
        if not gtin or not nome_modelo:
            messagebox.showwarning("Atenção", "GTIN e Modelo são obrigatórios.")
            return

        marca_id = self.brand_name_to_id.get(self.var_brand.get())
        categoria_id = self.category_name_to_id.get(self.var_category.get())
        subcategoria_id = self.sub_name_to_id.get(self.var_subcategory.get()) if hasattr(self, "sub_name_to_id") else None
        fornecedor_id = self.supplier_name_to_id.get(self.var_supplier.get())

        cor_id = self.color_name_to_id.get(self.var_color.get())
        tamanho_id = self.size_name_to_id.get(self.var_size.get())
        ref_keyinvoice = self.ref_keyinvoice.get().strip() or None

        if not all([marca_id, categoria_id, subcategoria_id, fornecedor_id, cor_id, tamanho_id]):
            messagebox.showwarning("Atenção", "Preenche marca/categoria/subcategoria/fornecedor/cor/tamanho.")
            return

        ok, msg = self.db.update_variant_and_model(
            gtin=gtin,
            model_fields={
                "nome_modelo": nome_modelo,
                "marca_id": marca_id,
                "categoria_id": categoria_id,
                "subcategoria_id": subcategoria_id,
                "fornecedor_id": fornecedor_id
            },
            variant_fields={
                "cor_id": cor_id,
                "tamanho_id": tamanho_id,
                "ref_keyinvoice": ref_keyinvoice
            }
        )

        if ok:
            self.app.db.audit(self.app.user, "UPDATE_ITEM", "product_variant",
                              entity_pk=f"gtin={gtin}",
                              details={"fields": ["model", "variant"]})
            messagebox.showinfo("OK", msg)
        else:
            messagebox.showerror("Erro", msg)

    def update_stock(self):
        if not self.loaded_variant_id:
            messagebox.showwarning("Atenção", "Carrega um GTIN primeiro.")
            return

        stock_val = safe_int(self.stock.get(), None)
        if stock_val is None or stock_val < 0:
            messagebox.showwarning("Atenção", "Stock inválido.")
            return

        wh_id = self.warehouse_name_to_id.get(self.var_warehouse.get())
        if not wh_id:
            messagebox.showwarning("Atenção", "Escolhe um armazém.")
            return

        try:
            self.db.upsert_stock(self.loaded_variant_id, wh_id, stock_val)
            self.app.db.audit(self.app.user, "UPSERT_STOCK", "warehouse_stock",
                              entity_pk=f"variant_id={self.loaded_variant_id},warehouse_id={wh_id}",
                              details={"stock": stock_val})
            messagebox.showinfo("OK", "Stock atualizado.")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao atualizar stock.\n\n{e}")

#DELETE TAB

class DeleteTab(BaseTab):
    def __init__(self, parent, app: App):
        super().__init__(parent, app)
        self.load_domains()

        ttk.Label(self, text="Excluir Produto (por Código + Armazém)", font=("Segoe UI", 14, "bold")).grid(
            row=0, column=0, columnspan=6, sticky="w", pady=(0, 12)
        )

        # Tipo de busca
        ttk.Label(self, text="Buscar por:").grid(row=1, column=0, sticky="w")
        self.var_search_type = tk.StringVar(value="gtin")
        
        search_frame = ttk.Frame(self)
        search_frame.grid(row=1, column=1, columnspan=3, sticky="w")
        
        ttk.Radiobutton(search_frame, text="GTIN", variable=self.var_search_type, 
                       value="gtin").pack(side="left", padx=(0, 10))
        ttk.Radiobutton(search_frame, text="Ref KeyInvoice", variable=self.var_search_type, 
                       value="ref_keyinvoice").pack(side="left", padx=(0, 10))
        ttk.Radiobutton(search_frame, text="Ref WooCommerce", variable=self.var_search_type, 
                       value="ref_woocommerce").pack(side="left")

        ttk.Label(self, text="Código:").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.search_value = ttk.Entry(self, width=28)
        self.search_value.grid(row=2, column=1, sticky="w", padx=(0, 12), pady=(8, 0))

        ttk.Label(self, text="Armazém:").grid(row=2, column=2, sticky="w", pady=(8, 0))
        self.var_warehouse = tk.StringVar()
        self.combo_warehouse = ttk.Combobox(self, textvariable=self.var_warehouse, width=25, state="readonly")
        self.combo_warehouse.grid(row=2, column=3, sticky="w", pady=(8, 0))

        self._refresh_warehouses()

        ttk.Button(self, text="Carregar", command=self.preview).grid(row=2, column=4, padx=(8, 0), pady=(8, 0))
        ttk.Separator(self).grid(row=3, column=0, columnspan=6, sticky="ew", pady=12)

        self.txt = tk.Text(self, height=18, width=110)
        self.txt.grid(row=4, column=0, columnspan=6, sticky="nsew")

        btns = ttk.Frame(self)
        btns.grid(row=5, column=0, columnspan=6, sticky="w", pady=(10, 0))
        ttk.Button(btns, text="Excluir stock deste armazém", command=self.delete_stock).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(btns, text="Cancelar / Limpar", command=self.clear).grid(row=0, column=1)

        self.loaded = None
        self.grid_rowconfigure(4, weight=1)
        self.grid_columnconfigure(5, weight=1)

    def _refresh_warehouses(self):
        whs = self.db.list_domain("warehouses")
        self.wh_id_to_name = {r[0]: r[1] for r in whs}
        self.wh_name_to_id = {r[1]: r[0] for r in whs}
        self.combo_warehouse["values"] = list(self.wh_name_to_id.keys())
        if self.combo_warehouse["values"]:
            self.var_warehouse.set(self.combo_warehouse["values"][0])

    def clear(self):
        self.loaded = None
        self.txt.delete("1.0", tk.END)
        self.search_value.delete(0, tk.END)

    def preview(self):
        value = self.search_value.get().strip()
        search_type = self.var_search_type.get()
        
        if not value:
            messagebox.showwarning("Atenção", "Informa o código.")
            return
        
        try:
            full = self.db.get_full_view_by_gtin(value, search_type)
            self.txt.delete("1.0", tk.END)
            
            if not full:
                self.txt.insert(tk.END, "Código não encontrado.\n")
                self.loaded = None
                return

            header, stocks = full
            self.loaded = header

            self.txt.insert(tk.END, f"GTIN: {header['gtin']}\n")
            self.txt.insert(tk.END, f"Ref KeyInvoice: {header['ref_keyinvoice']}\n")
            self.txt.insert(tk.END, f"Ref WooCommerce: {header['ref_woocomerce']}\n")
            self.txt.insert(tk.END, f"Modelo: {header['nome_modelo']}\n")
            self.txt.insert(tk.END, f"Marca: {header['marca']}\n")
            self.txt.insert(tk.END, f"Categoria/Subcategoria: {header['categoria']} / {header['subcategoria']}\n")
            self.txt.insert(tk.END, f"Fornecedor: {header['fornecedor']}\n")
            self.txt.insert(tk.END, f"Cor/Tamanho: {header['cor']} / {header['tamanho']}\n\n")

            self.txt.insert(tk.END, "Stock por armazém:\n")
            for s in stocks:
                self.txt.insert(tk.END, f" - {s['armazem']}: {s['stock']}\n")

        except Exception as e:
            messagebox.showerror("Erro", f"Falha.\n\n{e}")

    def delete_stock(self):
        if not self.loaded:
            messagebox.showwarning("Atenção", "Carrega um produto primeiro.")
            return
            
        wh_name = self.var_warehouse.get()
        wh_id = self.wh_name_to_id.get(wh_name)
        if not wh_id:
            messagebox.showwarning("Atenção", "Escolhe armazém.")
            return

        variant_id = self.loaded["variant_id"]
        gtin = self.loaded["gtin"]

        if not messagebox.askyesno("Confirmar", f"Excluir o stock do GTIN {gtin} no armazém '{wh_name}'?"):
            return

        try:
            self.db.delete_stock_row(variant_id, wh_id)
            self.app.db.audit(self.app.user, "DELETE_STOCK", "warehouse_stock",
                              entity_pk=f"variant_id={variant_id},warehouse_id={wh_id}",
                              details={"gtin": gtin, "warehouse": wh_name})

            deleted_variant = self.db.delete_variant_if_orphan(variant_id)
            if deleted_variant:
                self.app.db.audit(self.app.user, "DELETE_VARIANT", "product_variant",
                                  entity_pk=f"id={variant_id}",
                                  details={"gtin": gtin, "reason": "no_stock_rows"})

            msg = "Stock removido."
            if deleted_variant:
                msg += " Variação apagada (não havia stock em nenhum armazém)."
            messagebox.showinfo("OK", msg)
            self.preview()
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao excluir.\n\n{e}")

#VIEW TAB

class ViewTab(BaseTab):
    def __init__(self, parent, app: App):
        super().__init__(parent, app)

        ttk.Label(self, text="Visualizar Produto", font=("Segoe UI", 14, "bold")).grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, 12)
        )

        # Tipo de busca
        ttk.Label(self, text="Buscar por:").grid(row=1, column=0, sticky="w")
        self.var_search_type = tk.StringVar(value="gtin")
        
        search_frame = ttk.Frame(self)
        search_frame.grid(row=1, column=1, columnspan=3, sticky="w")
        
        ttk.Radiobutton(search_frame, text="GTIN", variable=self.var_search_type, 
                       value="gtin").pack(side="left", padx=(0, 10))
        ttk.Radiobutton(search_frame, text="Ref KeyInvoice", variable=self.var_search_type, 
                       value="ref_keyinvoice").pack(side="left", padx=(0, 10))
        ttk.Radiobutton(search_frame, text="Ref WooCommerce", variable=self.var_search_type, 
                       value="ref_woocommerce").pack(side="left")

        # Campo de busca
        ttk.Label(self, text="Código:").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.search_value = ttk.Entry(self, width=40)
        self.search_value.grid(row=2, column=1, sticky="w", padx=(0, 8), pady=(8, 0))

        ttk.Button(self, text="Buscar", command=self.search).grid(row=2, column=2, sticky="w", pady=(8, 0))
        ttk.Button(self, text="Limpar", command=self.clear).grid(row=2, column=3, sticky="w", pady=(8, 0))

        ttk.Separator(self).grid(row=3, column=0, columnspan=6, sticky="ew", pady=12)

        self.txt = tk.Text(self, height=26, width=110)
        self.txt.grid(row=4, column=0, columnspan=6, sticky="nsew")

        self.grid_rowconfigure(4, weight=1)

    def clear(self):
        self.search_value.delete(0, tk.END)
        self.txt.delete("1.0", tk.END)

    def search(self):
        value = self.search_value.get().strip()
        search_type = self.var_search_type.get()
        
        if not value:
            messagebox.showwarning("Atenção", "Informa o código de busca.")
            return
        
        try:
            full = self.db.get_full_view_by_gtin(value, search_type)
            self.txt.delete("1.0", tk.END)
            
            if not full:
                tipo_busca = {
                    'gtin': 'GTIN',
                    'ref_keyinvoice': 'Ref KeyInvoice',
                    'ref_woocommerce': 'Ref WooCommerce'
                }
                self.txt.insert(tk.END, f"{tipo_busca[search_type]} não encontrado.\n")
                return

            header, stocks = full

            self.txt.insert(tk.END, f"GTIN: {header['gtin']}\n")
            self.txt.insert(tk.END, f"Ref KeyInvoice: {header['ref_keyinvoice']}\n")
            self.txt.insert(tk.END, f"Ref WooCommerce: {header['ref_woocomerce']}\n")
            self.txt.insert(tk.END, f"Modelo: {header['nome_modelo']}\n")
            self.txt.insert(tk.END, f"Marca: {header['marca']}\n")
            self.txt.insert(tk.END, f"Categoria/Subcategoria: {header['categoria']} / {header['subcategoria']}\n")
            self.txt.insert(tk.END, f"Fornecedor: {header['fornecedor']}\n")
            self.txt.insert(tk.END, f"Cor/Tamanho: {header['cor']} / {header['tamanho']}\n\n")

            self.txt.insert(tk.END, "Stock por armazém:\n")
            for s in stocks:
                self.txt.insert(tk.END, f" - {s['armazem']}: {s['stock']}\n")

            self.app.db.audit(
                self.app.user, 
                "VIEW", 
                "product_variant", 
                entity_pk=f"{search_type}={value}", 
                details={"search_type": search_type}
            )
        except Exception as e:
            messagebox.showerror("Erro", f"Falha.\n\n{e}")
#RUN

def main():
    db = DB()
    app = App(db)
    app.mainloop()

if __name__ == "__main__":
    main()
