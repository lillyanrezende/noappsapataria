import os
import json
from dotenv import load_dotenv
from supabase import create_client, Client

# Carrega as variáveis do arquivo .env
load_dotenv()

# Acessa as variáveis de ambiente
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

DB_URL = os.getenv("DATABASE_URL")

# Tabelas existentes
DOMAIN_TABLES = {
    "brands": ("id", "name"),
    "categories": ("id", "name"),
    "subcategories": ("id", "name"),
    "colors": ("id", "name"),
    "sizes": ("id", "value"),
    "warehouses": ("id", "name"),
    "suppliers": ("id", "name"),
}


class DB:
    """Camada de acesso ao banco de dados Supabase"""
    
    def __init__(self):
        self.supabase = create_client(url, key)

    def init_app_tables(self):
        """
        Cria tabelas da aplicação (utilizadores e logs) se não existirem.
        Não mexe nas tuas tabelas principais (products/stock).
        Assume que as tabelas já existem no Supabase.
        """
        pass

    # ==========================================
    # AUTH
    # ==========================================
    
    def create_user(self, username, nome_usuario, setor, password_hash):
        """Cria um novo utilizador"""
        data = {
            'username': username.strip(),
            'nome_usuario': nome_usuario.strip(),
            'setor': (setor or "").strip() or None,
            'password_hash': password_hash
        }
        response = self.supabase.table('profiles').insert(data).execute()
        user_id = response.data[0]['user_id']
        return user_id

    def get_user_by_username(self, username):
        """Obtém utilizador por username"""
        response = self.supabase.table('profiles').select('*').eq('username', username.strip()).execute()
        if not response.data:
            return None
        return response.data[0]

    # ==========================================
    # AUDIT
    # ==========================================
    
    def audit(self, user, action, entity, entity_pk=None, details=None):
        """Registra log de auditoria"""
        data = {
            'user_id': user.get("user_id") if user else None,
            'username': user.get("username") if user else None,
            'action': action,
            'entity': entity,
            'entity_pk': entity_pk,
            'details': json.dumps(details or {})
        }
        self.supabase.table('audit_logs').insert(data).execute()

    # ==========================================
    # DOMAIN LOADERS
    # ==========================================
    
    def list_domain(self, table):
        """Lista domínios (brands, categories, colors, etc.)"""
        id_col, name_col = DOMAIN_TABLES[table]
        response = self.supabase.table(table).select(f'{id_col}, {name_col}').order(name_col).execute()
        return [(r[id_col], r[name_col]) for r in response.data]

    def list_subcategories_by_category(self, category_id):
        """Lista subcategorias por categoria"""
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
        """Obtém ou cria uma subcategoria"""
        name = name.strip()
        response = self.supabase.table('subcategories').select('id').eq('category_id', category_id).eq('name', name).execute()
        if response.data:
            return response.data[0]['id']
        response = self.supabase.table('subcategories').insert({'category_id': category_id, 'name': name}).execute()
        return response.data[0]['id']

    # ==========================================
    # PRODUCT MODEL
    # ==========================================
    
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

    def update_model(self, model_id, model_data):
        """Atualiza um modelo existente"""
        self.supabase.table('product_model').update(model_data).eq('id', model_id).execute()

    # ==========================================
    # PRODUCT VARIANT
    # ==========================================
    
    def find_variant_by_gtin(self, gtin):
        """Encontra variante por GTIN"""
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

    def create_variant(self, model_id, gtin, cor_id, tamanho_id, ref_keyinvoice=None, ref_woocommerce=None):
        """Cria uma nova variante"""
        data = {
            'model_id': model_id,
            'gtin': gtin.strip(),
            'cor_id': cor_id,
            'tamanho_id': tamanho_id,
            'ref_keyinvoice': ref_keyinvoice,
            'ref_woocomerce': ref_woocommerce
        }
        response = self.supabase.table('product_variant').insert(data).execute()
        return response.data[0]['id']

    def update_variant(self, variant_id, variant_data):
        """Atualiza uma variante existente"""
        self.supabase.table('product_variant').update(variant_data).eq('id', variant_id).execute()

    def delete_variant(self, variant_id):
        """Apaga uma variante"""
        self.supabase.table('product_variant').delete().eq('id', variant_id).execute()

    def search_variants(self, search_value, search_type='gtin'):
        """Pesquisa variantes por GTIN, ref_keyinvoice ou ref_woocommerce"""
        search_value = str(search_value).strip()

        if search_type == 'gtin':
            field = 'gtin'
        elif search_type == 'ref_keyinvoice':
            field = 'ref_keyinvoice'
        elif search_type == 'ref_woocommerce':
            field = 'ref_woocomerce'
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

    def get_full_view_by_variant_id(self, variant_id):
        """Carrega view completa de uma variante por ID"""
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

            'model_id': row.get('model_id'),
            'cor_id': row.get('cor_id'),
            'tamanho_id': row.get('tamanho_id'),

            'marca_id': row['product_model'].get('marca_id'),
            'categoria_id': row['product_model'].get('categoria_id'),
            'subcategoria_id': row['product_model'].get('subcategoria_id'),
            'fornecedor_id': row['product_model'].get('fornecedor_id'),

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
        """Carrega view completa de uma variante por código"""
        search_value = str(search_value).strip()

        if search_type == 'gtin':
            field = 'gtin'
        elif search_type == 'ref_keyinvoice':
            field = 'ref_keyinvoice'
        elif search_type == 'ref_woocommerce':
            field = 'ref_woocomerce'
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

            'model_id': row.get('model_id'),
            'cor_id': row.get('cor_id'),
            'tamanho_id': row.get('tamanho_id'),

            'marca_id': row['product_model'].get('marca_id'),
            'categoria_id': row['product_model'].get('categoria_id'),
            'subcategoria_id': row['product_model'].get('subcategoria_id'),
            'fornecedor_id': row['product_model'].get('fornecedor_id'),

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

    # ==========================================
    # WAREHOUSE STOCK
    # ==========================================
    
    def upsert_stock(self, variant_id, warehouse_id, stock):
        """Cria ou atualiza stock"""
        data = {
            'variant_id': variant_id,
            'warehouse_id': warehouse_id,
            'stock': int(stock)
        }
        self.supabase.table('warehouse_stock').upsert(data).execute()

    def delete_stock_row(self, variant_id, warehouse_id):
        """Apaga stock de um armazém"""
        self.supabase.table('warehouse_stock').delete().eq('variant_id', variant_id).eq('warehouse_id', warehouse_id).execute()

    def variant_has_any_stock_rows(self, variant_id):
        """Verifica se variante tem stock em algum armazém"""
        response = self.supabase.table('warehouse_stock').select('variant_id').eq('variant_id', variant_id).limit(1).execute()
        return len(response.data) > 0
