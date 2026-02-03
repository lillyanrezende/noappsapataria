from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from ui.components.helpers import BaseTab, safe_int
from ui.tabs.bulk_update_window import BulkUpdateWindow


class UpdateTab(BaseTab):
    """Tab para atualizar produtos"""

    def __init__(self, parent, app):
        super().__init__(parent, app)

        self.load_domains()

        ttk.Label(self, text="Alterar Produto", font=("Segoe UI", 14, "bold")).grid(
            row=0, column=0, columnspan=6, sticky="w", pady=(0, 12)
        )

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

        ttk.Label(self, text="Código:").grid(row=2, column=0, sticky="w", pady=(6, 0))
        self.search_value = ttk.Entry(self, width=28)
        self.search_value.grid(row=2, column=1, sticky="w", padx=(0, 8), pady=(6, 0))

        ttk.Button(self, text="Procurar", command=self.search_variants).grid(row=2, column=2, sticky="w", pady=(6, 0))
        ttk.Button(self, text="Carregar selecionado", command=self.load_selected_variant).grid(
            row=2, column=3, sticky="w", pady=(6, 0))
        ttk.Button(self, text="Alteração em Massa", command=self.bulk_update_stock).grid(
            row=2, column=4, sticky="w", padx=(8, 0), pady=(6, 0))

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

        self.tree.bind("<Double-1>", lambda e: self.load_selected_variant())

        ttk.Separator(self).grid(row=4, column=0, columnspan=6, sticky="ew", pady=12)

        self.lbl_gtin = ttk.Label(self, text="Item carregado: -", font=("Segoe UI", 10, "bold"))
        self.lbl_gtin.grid(row=5, column=0, columnspan=6, sticky="w")
        self.form_row0 = 6

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

        r0 = self.form_row0
        ttk.Label(self, text="Gestão de Stock por Armazém", font=("Segoe UI", 10, "bold")).grid(
            row=r0+8, column=0, columnspan=6, sticky="w", pady=(14, 6))

        ttk.Label(self, text="Armazém:").grid(row=r0+9, column=0, sticky="w")
        self.combo_warehouse.grid(row=r0+9, column=1, sticky="w")

        ttk.Label(self, text="Quantidade:").grid(row=r0+9, column=2, sticky="w", padx=(12, 0))
        self.stock = ttk.Entry(self, width=12)
        self.stock.grid(row=r0+9, column=3, sticky="w")

        ttk.Button(self, text="➕ Adicionar", command=self.add_to_stock).grid(row=r0+9, column=4, padx=(8, 0))
        ttk.Button(self, text="➖ Retirar", command=self.remove_from_stock).grid(row=r0+9, column=5, padx=(4, 0))

        ttk.Button(self, text="📊 Ver Stock", command=self.show_current_stock).grid(row=r0+10, column=0, sticky="w", pady=(8, 0))

        ttk.Label(self, text="Stock nos Armazéns:", font=("Segoe UI", 9, "bold")).grid(
            row=r0+11, column=0, columnspan=6, sticky="w", pady=(12, 4))

        self.txt_stock_info = tk.Text(self, height=6, width=80, state="disabled")
        self.txt_stock_info.grid(row=r0+12, column=0, columnspan=6, sticky="ew", pady=(0, 8))

        self.loaded_variant_id = None
        self.loaded_gtin = None

    def search_variants(self):
        value = self.search_value.get().strip()
        search_type = self.var_search_type.get()

        if not value:
            messagebox.showwarning("Atenção", "Informa um código para buscar.")
            return

        try:
            results = self.db.search_variants(value, search_type)

            for iid in self.tree.get_children():
                self.tree.delete(iid)

            if not results:
                messagebox.showinfo("Não encontrado", "Nenhuma variação encontrada para esse código.")
                return

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
            self.loaded_gtin = header.get("gtin")

            self.lbl_gtin.config(
                text=f"Item carregado: GTIN={header.get('gtin')} | variant_id={header['variant_id']}"
            )

            self.nome_modelo.delete(0, tk.END)
            self.nome_modelo.insert(0, header.get("nome_modelo") or "")

            self.ref_keyinvoice.delete(0, tk.END)
            self.ref_keyinvoice.insert(0, header.get("ref_keyinvoice") or "")

            self.var_brand.set(self.brand_id_to_name.get(header["marca_id"], ""))
            self.var_category.set(self.category_id_to_name.get(header["categoria_id"], ""))

            self._refresh_subcategories()
            self.var_subcategory.set(self.sub_id_to_name.get(header["subcategoria_id"], ""))

            self.var_supplier.set(self.supplier_id_to_name.get(header["fornecedor_id"], ""))
            self.var_color.set(self.color_id_to_name.get(header["cor_id"], ""))
            self.var_size.set(self.size_id_to_name.get(header["tamanho_id"], ""))

            self.txt_stock_info.config(state="normal")
            self.txt_stock_info.delete("1.0", tk.END)

            if stocks:
                self.txt_stock_info.insert(tk.END, "Stock disponível nos armazéns:\n\n")
                total_stock = 0
                for s in stocks:
                    self.txt_stock_info.insert(tk.END, f"  • {s['armazem']}: {s['stock']} unidades\n")
                    total_stock += s['stock']
                self.txt_stock_info.insert(tk.END, f"\n📦 Total geral: {total_stock} unidades")

                wh_name = stocks[0]["armazem"]
                if wh_name in self.combo_warehouse["values"]:
                    self.var_warehouse.set(wh_name)
                self.stock.delete(0, tk.END)
                self.stock.insert(0, str(stocks[0]["stock"]))
            else:
                self.txt_stock_info.insert(tk.END, "⚠️ Nenhum stock registado em armazéns.\n\n")
                self.txt_stock_info.insert(tk.END, "Use os botões 'Adicionar' para criar stock.")
                self.stock.delete(0, tk.END)

            self.txt_stock_info.config(state="disabled")

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
        subs = self.domain_service.get_subcategories_by_category(cat_id)
        self.sub_id_to_name = {r[0]: r[1] for r in subs}
        self.sub_name_to_id = {r[1]: r[0] for r in subs}
        self.combo_subcategory["values"] = list(self.sub_name_to_id.keys())
        if self.combo_subcategory["values"]:
            self.var_subcategory.set(self.combo_subcategory["values"][0])
        else:
            self.var_subcategory.set("")

    def _build_edit_fields(self):
        r0 = self.form_row0

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

        ttk.Label(self, text="Cor").grid(row=r0+0, column=2, sticky="w", pady=(8, 0))
        self.combo_color.grid(row=r0+0, column=3, sticky="w", pady=(8, 0))

        ttk.Label(self, text="Tamanho").grid(row=r0+1, column=2, sticky="w", pady=(8, 0))
        self.combo_size.grid(row=r0+1, column=3, sticky="w", pady=(8, 0))

        ttk.Label(self, text="Ref KeyInvoice").grid(row=r0+2, column=2, sticky="w", pady=(8, 0))
        self.ref_keyinvoice.grid(row=r0+2, column=3, sticky="w", pady=(8, 0))

        ttk.Separator(self).grid(row=r0+5, column=0, columnspan=6, sticky="ew", pady=12)

        ttk.Button(self, text="Guardar alterações (item)", command=self.save_item).grid(
            row=r0+6, column=0, sticky="w", pady=(14, 0))
        ttk.Button(self, text="Limpar", command=self.clear).grid(
            row=r0+6, column=1, sticky="w", padx=(8, 0), pady=(14, 0))

    def clear(self):
        self.loaded_variant_id = None
        self.loaded_gtin = None
        self.lbl_gtin.config(text="Item carregado: -")
        self.nome_modelo.delete(0, tk.END)
        self.ref_keyinvoice.delete(0, tk.END)
        self.stock.delete(0, tk.END)

        self.txt_stock_info.config(state="normal")
        self.txt_stock_info.delete("1.0", tk.END)
        self.txt_stock_info.config(state="disabled")

    def save_item(self):
        if not self.loaded_variant_id or not self.loaded_gtin:
            messagebox.showwarning("Atenção", "Carrega um produto primeiro.")
            return

        gtin = self.loaded_gtin
        nome_modelo = self.nome_modelo.get().strip()
        if not nome_modelo:
            messagebox.showwarning("Atenção", "Modelo é obrigatório.")
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

        ok, msg = self.app.product_service.update_product_details(
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

    def add_to_stock(self):
        if not self.loaded_variant_id:
            messagebox.showwarning("Atenção", "Carrega um produto primeiro.")
            return

        quantity = safe_int(self.stock.get(), None)
        if quantity is None or quantity <= 0:
            messagebox.showwarning("Atenção", "Quantidade inválida. Deve ser maior que 0.")
            return

        wh_id = self.warehouse_name_to_id.get(self.var_warehouse.get())
        if not wh_id:
            messagebox.showwarning("Atenção", "Escolhe um armazém.")
            return

        try:
            success, msg = self.app.product_service.add_to_stock(self.loaded_variant_id, wh_id, quantity)
            if success:
                self.app.db.audit(self.app.user, "ADD_STOCK", "warehouse_stock",
                                entity_pk=f"variant_id={self.loaded_variant_id},warehouse_id={wh_id}",
                                details={"quantity_added": quantity})
                messagebox.showinfo("OK", msg)
                self.stock.delete(0, tk.END)
                self._refresh_stock_display()
            else:
                messagebox.showerror("Erro", msg)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao adicionar stock.\n\n{e}")

    def remove_from_stock(self):
        if not self.loaded_variant_id:
            messagebox.showwarning("Atenção", "Carrega um produto primeiro.")
            return

        quantity = safe_int(self.stock.get(), None)
        if quantity is None or quantity <= 0:
            messagebox.showwarning("Atenção", "Quantidade inválida. Deve ser maior que 0.")
            return

        wh_id = self.warehouse_name_to_id.get(self.var_warehouse.get())
        if not wh_id:
            messagebox.showwarning("Atenção", "Escolhe um armazém.")
            return

        try:
            success, msg = self.app.product_service.remove_from_stock(self.loaded_variant_id, wh_id, quantity)
            if success:
                self.app.db.audit(self.app.user, "REMOVE_STOCK", "warehouse_stock",
                                entity_pk=f"variant_id={self.loaded_variant_id},warehouse_id={wh_id}",
                                details={"quantity_removed": quantity})
                messagebox.showinfo("OK", msg)
                self.stock.delete(0, tk.END)
                self._refresh_stock_display()
            else:
                messagebox.showerror("Erro", msg)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao retirar stock.\n\n{e}")

    def show_current_stock(self):
        if not self.loaded_variant_id:
            messagebox.showwarning("Atenção", "Carrega um produto primeiro.")
            return

        wh_id = self.warehouse_name_to_id.get(self.var_warehouse.get())
        if not wh_id:
            messagebox.showwarning("Atenção", "Escolhe um armazém.")
            return

        try:
            response = self.db.supabase.table('warehouse_stock').select('stock').eq('variant_id', self.loaded_variant_id).eq('warehouse_id', wh_id).execute()
            if response.data:
                current = response.data[0]['stock']
                messagebox.showinfo("Stock Atual", f"Armazém: {self.var_warehouse.get()}\nStock atual: {current}")
            else:
                messagebox.showinfo("Stock Atual", f"Armazém: {self.var_warehouse.get()}\nStock atual: 0 (sem registo)")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao consultar stock.\n\n{e}")

    def _refresh_stock_display(self):
        if not self.loaded_variant_id:
            return

        try:
            full = self.db.get_full_view_by_variant_id(self.loaded_variant_id)
            if not full:
                return

            header, stocks = full

            self.txt_stock_info.config(state="normal")
            self.txt_stock_info.delete("1.0", tk.END)

            if stocks:
                self.txt_stock_info.insert(tk.END, "Stock disponível nos armazéns:\n\n")
                total_stock = 0
                for s in stocks:
                    self.txt_stock_info.insert(tk.END, f"  • {s['armazem']}: {s['stock']} unidades\n")
                    total_stock += s['stock']
                self.txt_stock_info.insert(tk.END, f"\n📦 Total geral: {total_stock} unidades")
            else:
                self.txt_stock_info.insert(tk.END, "⚠️ Nenhum stock registado em armazéns.\n\n")
                self.txt_stock_info.insert(tk.END, "Use os botões 'Adicionar' para criar stock.")

            self.txt_stock_info.config(state="disabled")
        except Exception:
            pass

    def bulk_update_stock(self):
        BulkUpdateWindow(self, self.app)
