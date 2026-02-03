from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from ui.components.helpers import BaseTab, safe_int


class CreateTab(BaseTab):
    """Tab para criar produtos"""

    def __init__(self, parent, app):
        super().__init__(parent, app)

        self.load_domains()

        ttk.Label(self, text="Cadastrar Produto", font=("Segoe UI", 14, "bold")).grid(
            row=0, column=0, columnspan=6, sticky="w", pady=(0, 12))

        # Fields
        self.gtin = ttk.Entry(self, width=28)
        self.ref_keyinvoice = ttk.Entry(self, width=28)
        self.ref_woocommerce = ttk.Entry(self, width=28)
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
        """Constrói formulário"""
        r = 1

        ttk.Label(self, text="GTIN").grid(row=r, column=0, sticky="w")
        self.gtin.grid(row=r, column=1, sticky="w", padx=(0, 12))
        ttk.Label(self, text="Ref KeyInvoice (opcional)").grid(row=r, column=2, sticky="w")
        self.ref_keyinvoice.grid(row=r, column=3, sticky="w")
        r += 1

        ttk.Label(self, text="Ref WooCommerce (opcional)").grid(row=r, column=0, sticky="w", pady=(8, 0))
        self.ref_woocommerce.grid(row=r, column=1, sticky="w", padx=(0, 12), pady=(8, 0))
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
        """Atualiza dropdowns"""
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

        # default selections
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
        """Atualiza subcategorias"""
        cat_name = self.var_category.get().strip()
        cat_id = self.category_name_to_id.get(cat_name)
        if not cat_id:
            self.combo_subcategory["values"] = []
            self.var_subcategory.set("")
            return
        subs = self.domain_service.get_subcategories_by_category(cat_id)
        self.sub_id_to_name = {r[0]: r[1] for r in subs}
        self.sub_name_to_id = {r[1]: r[0] for r in subs}
        self.combo_subcategory["values"] = list(self.sub_name_to_id.keys())
        if self.combo_subcategory["values"]:
            self.var_subcategory.set(self.combo_subcategory["values"][0])
        else:
            self.var_subcategory.set("")

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
        from ui.components.dialogs import AddOptionDialog
        dlg = AddOptionDialog(self, "Adicionar Subcategoria", "Nova Subcategoria:")
        if dlg.value:
            self.domain_service.add_subcategory(cat_id, dlg.value)
            self._refresh_subcategories()
            self.var_subcategory.set(dlg.value)

    def add_color(self):
        new_id, new_val = self.ask_add_option("colors", "Cor")
        if new_id:
            self._refresh_dropdowns()
            self.var_color.set(new_val)

    def add_size(self):
        dlg = self.ask_add_option("sizes", "Tamanho")
        if dlg[0]:
            self._refresh_dropdowns()
            self.var_size.set(dlg[1])

    def add_warehouse(self):
        new_id, new_val = self.ask_add_option("warehouses", "Armazém")
        if new_id:
            self._refresh_dropdowns()
            self.var_warehouse.set(new_val)

    def clear(self):
        """Limpa formulário"""
        self.gtin.delete(0, tk.END)
        self.ref_keyinvoice.delete(0, tk.END)
        self.ref_woocommerce.delete(0, tk.END)
        self.nome_modelo.delete(0, tk.END)
        self.stock.delete(0, tk.END)

    def save(self):
        """Grava produto"""
        gtin = self.gtin.get().strip()
        if not gtin:
            messagebox.showwarning("Atenção", "GTIN é obrigatório.")
            return

        stock_val = safe_int(self.stock.get(), None)
        if stock_val is None or stock_val < 0:
            messagebox.showwarning("Atenção", "Stock inválido (precisa ser número inteiro >= 0).")
            return

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
        ref_woocommerce = self.ref_woocommerce.get().strip() or None

        try:
            success, message, variant_id = self.app.product_service.create_or_update_product(
                gtin=gtin,
                nome_modelo=nome_modelo,
                brand_id=brand_id,
                category_id=cat_id,
                subcategory_id=sub_id,
                supplier_id=supplier_id,
                color_id=color_id,
                size_id=size_id,
                warehouse_id=wh_id,
                stock=stock_val,
                ref_keyinvoice=ref_keyinvoice,
                ref_woocommerce=ref_woocommerce
            )

            if success:
                self.app.db.audit(self.app.user, "CREATE_OR_UPDATE_PRODUCT", "product_variant",
                                entity_pk=f"id={variant_id}",
                                details={"gtin": gtin, "stock": stock_val, "warehouse": self.var_warehouse.get()})
                messagebox.showinfo("OK", message)
            else:
                messagebox.showerror("Erro", message)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao cadastrar.\n\n{e}")
