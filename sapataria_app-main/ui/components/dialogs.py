import tkinter as tk
from tkinter import ttk, simpledialog


class AddOptionDialog(simpledialog.Dialog):
    """Dialog para adicionar nova opção a um domínio"""

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
