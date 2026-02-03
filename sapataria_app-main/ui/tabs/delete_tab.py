from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from ui.components.helpers import BaseTab, copy_to_clipboard, paste_from_clipboard


class DeleteTab(BaseTab):
    """Tab para excluir produtos"""

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.load_domains()

        ttk.Label(self, text="Excluir Produto (por Código + Armazém)",
                 font=("Segoe UI", 14, "bold")).grid(row=0, column=0, columnspan=6, sticky="w", pady=(0, 12))

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

        self.txt_menu = tk.Menu(self.txt, tearoff=0)
        self.txt_menu.add_command(label="Copiar", command=lambda: copy_to_clipboard(self.txt))
        self.txt_menu.add_command(label="Colar", command=lambda: paste_from_clipboard(self.txt))
        self.txt.bind("<Button-3>", lambda e: self.txt_menu.post(e.x_root, e.y_root))
        self.txt.bind("<Control-c>", lambda e: copy_to_clipboard(self.txt))

        btns = ttk.Frame(self)
        btns.grid(row=5, column=0, columnspan=6, sticky="w", pady=(10, 0))
        ttk.Button(btns, text="Excluir stock deste armazém", command=self.delete_stock).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(btns, text="Cancelar / Limpar", command=self.clear).grid(row=0, column=1)

        self.loaded = None
        self.grid_rowconfigure(4, weight=1)
        self.grid_columnconfigure(5, weight=1)

    def _refresh_warehouses(self):
        whs = self.domain_service.get_domain_list("warehouses")
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
            success, msg, deleted_variant = self.app.product_service.delete_stock(variant_id, wh_id)

            self.app.db.audit(self.app.user, "DELETE_STOCK", "warehouse_stock",
                            entity_pk=f"variant_id={variant_id},warehouse_id={wh_id}",
                            details={"gtin": gtin, "warehouse": wh_name})

            if deleted_variant:
                self.app.db.audit(self.app.user, "DELETE_VARIANT", "product_variant",
                                entity_pk=f"id={variant_id}",
                                details={"gtin": gtin, "reason": "no_stock_rows"})

            messagebox.showinfo("OK", msg)
            self.preview()
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao excluir.\n\n{e}")
