import bcrypt
from db import DB


class ProductService:
    """Serviço com regras de negócio para produtos"""
    
    def __init__(self, db: DB):
        self.db = db

    def create_or_update_product(self, gtin, nome_modelo, brand_id, category_id, 
                                 subcategory_id, supplier_id, color_id, size_id, 
                                 warehouse_id, stock, ref_keyinvoice=None, ref_woocommerce=None):
        """
        Cria produto (model + variant) ou atualiza stock se já existir.
        Retorna (success: bool, message: str, variant_id: int)
        """
        existing = self.db.find_variant_by_gtin(gtin)

        if existing:
            # GTIN já existe: só atualiza/insere stock para o armazém
            variant_id = existing["variant_id"]
            self.db.upsert_stock(variant_id, warehouse_id, stock)
            return True, "GTIN já existia. Stock atualizado para o armazém selecionado.", variant_id

        # GTIN não existe: cria model (ou reutiliza), cria variant, cria stock
        model_id = self.db.get_or_create_model(
            nome_modelo=nome_modelo,
            marca_id=brand_id,
            categoria_id=category_id,
            subcategoria_id=subcategory_id,
            fornecedor_id=supplier_id
        )

        variant_id = self.db.create_variant(
            model_id=model_id,
            gtin=gtin,
            cor_id=color_id,
            tamanho_id=size_id,
            ref_keyinvoice=ref_keyinvoice,
            ref_woocommerce=ref_woocommerce
        )

        self.db.upsert_stock(variant_id, warehouse_id, stock)

        return True, "Produto cadastrado (model + variant) e stock criado.", variant_id

    def update_product_details(self, gtin, model_fields, variant_fields):
        """
        Atualiza detalhes de um produto.
        model_fields: {nome_modelo, marca_id, categoria_id, subcategoria_id, fornecedor_id}
        variant_fields: {cor_id, tamanho_id, ref_keyinvoice}
        Retorna (success: bool, message: str)
        """
        row = self.db.find_variant_by_gtin(gtin)
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
        self.db.update_model(model_id, model_data)

        # update variant
        variant_data = {
            'cor_id': variant_fields["cor_id"],
            'tamanho_id': variant_fields["tamanho_id"],
            'ref_keyinvoice': variant_fields.get("ref_keyinvoice")
        }
        if "ref_woocomerce" in variant_fields:
            variant_data["ref_woocomerce"] = variant_fields.get("ref_woocomerce")
        self.db.update_variant(variant_id, variant_data)

        return True, "Atualizado com sucesso."

    def update_stock(self, variant_id, warehouse_id, stock):
        """Atualiza stock de uma variante num armazém"""
        self.db.upsert_stock(variant_id, warehouse_id, stock)
        return True, "Stock atualizado."

    def add_to_stock(self, variant_id, warehouse_id, quantity):
        """Adiciona quantidade ao stock existente"""
        # Buscar stock atual
        current_stock = self._get_current_stock(variant_id, warehouse_id)
        new_stock = current_stock + quantity
        self.db.upsert_stock(variant_id, warehouse_id, new_stock)
        return True, f"Adicionado {quantity}. Stock atual: {new_stock}"

    def remove_from_stock(self, variant_id, warehouse_id, quantity):
        """Remove quantidade do stock existente"""
        current_stock = self._get_current_stock(variant_id, warehouse_id)
        new_stock = current_stock - quantity
        if new_stock < 0:
            return False, f"Stock insuficiente! Stock atual: {current_stock}"
        self.db.upsert_stock(variant_id, warehouse_id, new_stock)
        return True, f"Retirado {quantity}. Stock atual: {new_stock}"

    def _get_current_stock(self, variant_id, warehouse_id):
        """Obtém stock atual de uma variante num armazém"""
        response = self.db.supabase.table('warehouse_stock').select('stock').eq('variant_id', variant_id).eq('warehouse_id', warehouse_id).execute()
        if response.data:
            return response.data[0]['stock']
        return 0

    def delete_stock(self, variant_id, warehouse_id):
        """
        Remove stock de um armazém e apaga a variante se não tiver mais stock em nenhum lugar.
        Retorna (success: bool, message: str, variant_deleted: bool)
        """
        self.db.delete_stock_row(variant_id, warehouse_id)
        
        deleted_variant = self.delete_variant_if_orphan(variant_id)
        
        msg = "Stock removido."
        if deleted_variant:
            msg += " Variação apagada (não havia stock em nenhum armazém)."
        
        return True, msg, deleted_variant

    def delete_variant_if_orphan(self, variant_id):
        """
        Apaga a variação se ela não tiver stock em nenhum armazém.
        Retorna True se apagou, False caso contrário.
        """
        if self.db.variant_has_any_stock_rows(variant_id):
            return False
        self.db.delete_variant(variant_id)
        return True

    def sell_from_woocommerce(self, gtin, quantity, warehouse_id=1):
        """
        Baixa stock quando venda vem do WooCommerce.
        warehouse_id padrão = 1 (ajustar conforme necessário)
        Retorna (success: bool, message: str)
        """
        # Verificar se produto existe
        row = self.db.find_variant_by_gtin(gtin)
        if not row:
            return False, f"Produto com GTIN {gtin} não encontrado no sistema"
        
        variant_id = row["variant_id"]
        
        # Verificar stock atual
        current_stock = self._get_current_stock(variant_id, warehouse_id)
        
        if current_stock < quantity:
            return False, f"Stock insuficiente para GTIN {gtin}. Disponível: {current_stock}, Solicitado: {quantity}"
        
        # Baixar stock
        new_stock = current_stock - quantity
        self.db.upsert_stock(variant_id, warehouse_id, new_stock)
        
        return True, f"Stock baixado com sucesso. GTIN: {gtin}, Qtd: {quantity}, Stock restante: {new_stock}"


class AuthService:
    """Serviço de autenticação"""
    
    def __init__(self, db: DB):
        self.db = db

    def create_user(self, username, nome_usuario, setor, password):
        """
        Cria novo utilizador com senha hasheada.
        Retorna user_id
        """
        pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        user_id = self.db.create_user(username, nome_usuario, setor, pw_hash)
        return user_id

    def authenticate(self, username, password):
        """
        Autentica utilizador.
        Retorna None se credenciais inválidas, "inactive" se inativo, ou dict com dados do user
        """
        user = self.db.get_user_by_username(username)
        if not user:
            return None
        
        if not user.get("is_active", True):
            return "inactive"
        
        if bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8")):
            return {
                "user_id": user["user_id"],
                "username": user["username"],
                "nome_usuario": user["nome_usuario"],
                "setor": user.get("setor"),
                "role": user.get("role", "operator"),
            }
        return None


class DomainService:
    """Serviço para gestão de domínios (marcas, categorias, etc.)"""
    
    def __init__(self, db: DB):
        self.db = db

    def get_domain_list(self, table):
        """Retorna lista de domínios"""
        return self.db.list_domain(table)

    def get_subcategories_by_category(self, category_id):
        """Retorna subcategorias de uma categoria"""
        return self.db.list_subcategories_by_category(category_id)

    def add_domain_value(self, table, value):
        """Adiciona valor a um domínio"""
        return self.db.get_or_create_simple_domain(table, value)

    def add_subcategory(self, category_id, name):
        """Adiciona subcategoria"""
        return self.db.get_or_create_subcategory(category_id, name)
