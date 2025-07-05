
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import DateEntry
import datetime
import shutil
from models import incluir_data, salvar_dados_pdf

class PalletApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Preparação de Cargas")
        self.geometry("800x600")

        # Dados de sessão
        self.linhas = []
        self.paletes_quebrados = []

        # Cabeçalho
        hdr_frame = ttk.LabelFrame(self, text="Cabeçalho")
        hdr_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(hdr_frame, text="Sold To:").grid(row=0, column=0, sticky="w")
        self.sold_to = ttk.Entry(hdr_frame, width=30)
        self.sold_to.grid(row=0, column=1)
        ttk.Label(hdr_frame, text="Cliente:").grid(row=0, column=2)
        self.nome_cliente = ttk.Entry(hdr_frame, width=30)
        self.nome_cliente.grid(row=0, column=3)
        ttk.Label(hdr_frame, text="Data:").grid(row=1, column=0)
        self.data = DateEntry(hdr_frame, date_pattern='yyyy-mm-dd')
        self.data.grid(row=1, column=1)
        ttk.Label(hdr_frame, text="Pedido:").grid(row=1, column=2)
        self.numero_pedido = ttk.Entry(hdr_frame, width=30)
        self.numero_pedido.grid(row=1, column=3)

        # Referência
        ref_frame = ttk.LabelFrame(self, text="Incluir Referência")
        ref_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(ref_frame, text="Referência:").grid(row=0, column=0)
        self.referencia = ttk.Entry(ref_frame)
        self.referencia.grid(row=0, column=1)
        ttk.Label(ref_frame, text="Quantidade:").grid(row=0, column=2)
        self.quantidade = ttk.Spinbox(ref_frame, from_=1, to=1000, width=5)
        self.quantidade.grid(row=0, column=3)
        ttk.Button(ref_frame, text="Incluir", command=self.incluir_item).grid(row=0, column=4, padx=5)

        # Árvores de dados
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.tree_complete = ttk.Treeview(tree_frame, columns=("ref","qty","peso"), show="headings")
        for col, txt in [("ref","Referência"),("qty","Qtd Peças"),("peso","Peso Líq")]:
            self.tree_complete.heading(col, text=txt)
        self.tree_complete.pack(side="left", fill="both", expand=True)

        self.tree_broken = ttk.Treeview(tree_frame, columns=("ref","qty","peso"), show="headings")
        self.tree_broken.heading("ref", text="Referência")
        self.tree_broken.heading("qty", text="Qtd Peças")
        self.tree_broken.heading("peso", text="Peso Líq")
        self.tree_broken.pack(side="right", fill="both", expand=True)

        # Botões PDF e totais
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=10, pady=5)
        ttk.Button(btn_frame, text="Gerar PDF", command=self.gerar_pdf).pack(side="left")
        self.lbl_totais = ttk.Label(btn_frame, text="Total Peças: 0 | Total Paletes: 0")
        self.lbl_totais.pack(side="right")

    def incluir_item(self):
        ref = self.referencia.get().strip()
        try:
            qty = int(self.quantidade.get())
        except ValueError:
            messagebox.showerror("Erro", "Quantidade inválida.")
            return
        if not ref or qty <= 0:
            messagebox.showerror("Erro", "Preencha referência e quantidade.")
            return

        resultado = incluir_data(ref, qty)
        if isinstance(resultado, tuple):
            self.linhas, self.paletes_quebrados = resultado
            self.atualizar_telas()
        else:
            messagebox.showerror("Erro", resultado)

    def atualizar_telas(self):
        for tree in (self.tree_complete, self.tree_broken):
            for row in tree.get_children():
                tree.delete(row)

        for item in self.linhas:
            self.tree_complete.insert("", "end", values=(item['referencia'], item['quantidade'], f"{item['peso_liquido']:.2f}"))

        for grp in self.paletes_quebrados:
            if grp.get('mix_group'):
                for it in grp['items']:
                    self.tree_broken.insert("", "end", values=(it['referencia'], it['quantidade'], f"{it['peso_liquido']:.2f}"))
            else:
                self.tree_broken.insert("", "end", values=(grp['referencia'], grp['quantidade'], f"{grp['peso_liquido']:.2f}"))

        total_pecas = sum(i['quantidade'] for i in self.linhas)
        for g in self.paletes_quebrados:
            if g.get('mix_group'):
                total_pecas += sum(it['quantidade'] for it in g['items'])
            else:
                total_pecas += g['quantidade']
        total_paletes = len(self.linhas) + len(self.paletes_quebrados)
        self.lbl_totais.config(text=f"Total Peças: {total_pecas} | Total Paletes: {total_paletes}")

    def gerar_pdf(self):
        cab = {
            'soldTo': self.sold_to.get(),
            'nomeCliente': self.nome_cliente.get(),
            'data': self.data.get_date().isoformat(),
            'numeroPedido': self.numero_pedido.get()
        }
        if not all(cab.values()):
            messagebox.showerror("Erro", "Preencha todas as informações de cabeçalho.")
            return

        default_name = f"PickSlip_{cab['numeroPedido']}_{cab['data']}.pdf"
        save_path = filedialog.asksaveasfilename(
            defaultextension='.pdf',
            filetypes=[('PDF','*.pdf')],
            initialfile=default_name
        )
        if not save_path:
            return
        try:
            # Tenta gerar direto no caminho escolhido
            resultado = salvar_dados_pdf(cab, self.linhas, self.paletes_quebrados, save_path)
            final_path = resultado if isinstance(resultado, str) else save_path
            messagebox.showinfo("Sucesso", f"PDF salvo em: {final_path}")
        except TypeError:
            # Versão antiga: gera em default 'pick_slip.pdf' e depois copia
            original = salvar_dados_pdf(cab, self.linhas, self.paletes_quebrados)
            try:
                shutil.copy(original, save_path)
                messagebox.showinfo("Sucesso", f"PDF copiado para: {save_path}")
            except Exception as e:
                messagebox.showerror("Erro ao copiar", str(e))
        except Exception as e:
            messagebox.showerror("Erro", str(e))

if __name__ == '__main__':
    app = PalletApp()
    app.mainloop()
