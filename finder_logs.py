import os
import shutil
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

historico = []

# ======================= Funções Utilitárias ========================

def detectar_tipo_log(conteudo, nome_arquivo):
    if nome_arquivo.lower().endswith(('.csv', '.dcl')):
        linhas = [l.strip() for l in conteudo.splitlines() if l.strip()]
        if linhas and linhas[0].count(",") >= 4:
            return "TRI"
    return "AGILENT"

def tentar_ler_arquivo(filepath):
    for enc in ['utf-8', 'utf-16', 'latin1']:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                return f.read()
        except Exception:
            continue
    return None

def extrair_info_arquivo(filepath):
    nome_arquivo = os.path.basename(filepath)
    conteudo = tentar_ler_arquivo(filepath)
    if not conteudo:
        return ("", "", "", "")
    linhas = [l.strip() for l in conteudo.splitlines() if l.strip()]
    if not linhas:
        return ("", "", "", "")
    if "," in linhas[0]:
        colunas = linhas[0].split(",")
    else:
        colunas = linhas[0].split()
    serial = colunas[3].strip() if len(colunas) > 3 else ""
    data = colunas[4].strip() if len(colunas) > 4 else ""
    hora = colunas[5].strip() if len(colunas) > 5 else ""
    erro = ""
    if len(linhas) > 1:
        erro = linhas[1]
    elif len(colunas) > 6:
        erro = colunas[-1]
    return (serial, data, hora, erro)

def buscar_logs(event=None):
    termo = entry_busca.get().strip()
    if len(termo) != 10:
        messagebox.showinfo("Atenção", "Digite o serial de 10 caracteres.")
        return
    arquivos = []
    for diretorio in diretorios:
        for root, dirs, files in os.walk(diretorio):
            for file in files:
                if (file.lower().endswith(".csv") or file.lower().endswith(".dcl") or file.lower().endswith(".txt")) and termo in file:
                    arquivos.append(os.path.join(root, file))
    listbox_logs.delete(0, tk.END)
    listbox_logs.file_paths = {}
    for arquivo in arquivos:
        listbox_logs.insert(tk.END, os.path.basename(arquivo))
        listbox_logs.file_paths[os.path.basename(arquivo)] = arquivo
    if not arquivos:
        messagebox.showinfo("Resultado", "Nenhum arquivo encontrado.")

def limpar_busca():
    entry_busca.delete(0, ctk.END)
    listbox_logs.delete(0, tk.END)
    text_area.configure(state="normal")
    text_area.delete("1.0", tk.END)
    text_area.configure(state="disabled")
    atualizar_painel_destaque("", "", "", "")

def exibir_log(event=None):
    index = listbox_logs.curselection()
    if not index:
        return
    nome_arquivo = listbox_logs.get(index)
    arquivo = listbox_logs.file_paths[nome_arquivo]
    conteudo = tentar_ler_arquivo(arquivo)
    if not conteudo:
        return
    tipo = detectar_tipo_log(conteudo, nome_arquivo)
    # Esconde ambos os painéis antes de mostrar
    tabela_frame.pack_forget()
    painel_agilent.pack_forget()

    if tipo == "TRI":
        serial, data, hora, erro = extrair_info_arquivo(arquivo)
        atualizar_painel_destaque(serial, data, hora, erro)
        for row in tree.get_children():
            tree.delete(row)
        linhas = conteudo.splitlines()
        for linha in linhas[1:]:
            if not linha.strip():
                continue
            dados = [v.strip() for v in linha.split(",")]
            while len(dados) < 13:
                dados.append("")
            tree.insert("", "end", values=dados)
        tabela_frame.pack(pady=6, fill="x")
    else:
        text_agilent.config(state="normal")
        text_agilent.delete("1.0", tk.END)
        blocos = []
        linhas = conteudo.splitlines()
        for idx, linha in enumerate(linhas):
            if "HAS FAILED" in linha:
                blocos.append(("FALHA", linha))
                for i in range(1, 5):
                    if idx + i < len(linhas) and ":" in linhas[idx + i]:
                        blocos.append(("DETALHE", linhas[idx + i]))
            if linha.startswith("Failed Open #"):
                bloco = linha + "\n"
                j = 1
                while idx + j < len(linhas) and linhas[idx + j].strip():
                    bloco += linhas[idx + j] + "\n"
                    j += 1
                blocos.append(("OPEN", bloco))
        serial = ""
        datahora = ""
        for linha in linhas:
            if linha.strip().startswith("Serial #:"):
                serial = linha.strip().split(":")[-1].strip()
            if any(mes in linha for mes in ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]):
                datahora = linha.strip()
        text_agilent.insert(tk.END, f"Serial: {serial}\nData/Hora: {datahora}\n\n")
        for tipo, bloco in blocos:
            if tipo == "FALHA":
                text_agilent.insert(tk.END, bloco + "\n", "falha")
            elif tipo == "DETALHE":
                text_agilent.insert(tk.END, "   " + bloco + "\n", "detalhe")
            elif tipo == "OPEN":
                text_agilent.insert(tk.END, "\n" + bloco + "\n", "open")
        text_agilent.tag_config("falha", foreground="red", font=("Consolas", 11, "bold"))
        text_agilent.tag_config("detalhe", foreground="blue")
        text_agilent.tag_config("open", foreground="purple")
        text_agilent.config(state="disabled")
        painel_agilent.pack(pady=6, fill="both", expand=True)
        atualizar_painel_destaque(serial, "", "", "")

def copiar_log():
    index = listbox_logs.curselection()
    if not index:
        return
    nome_arquivo = listbox_logs.get(index)
    arquivo = listbox_logs.file_paths[nome_arquivo]
    destino = filedialog.asksaveasfilename(
        title="Salvar LOG como",
        initialfile=nome_arquivo,
        defaultextension=".csv",
        filetypes=[("Arquivos de Log", "*.csv *.dcl"), ("Todos", "*.*")]
    )
    if destino:
        shutil.copy2(arquivo, destino)
        messagebox.showinfo("Sucesso", f"Log copiado para {destino}")

# ==================== Visualização Painel Superior ======================

def atualizar_painel_destaque(serial, data, hora, erro):
    var_serial.set(serial or "—")
    var_data.set(formatar_data(data) or "—")
    var_hora.set(formatar_hora(hora) or "—")
    var_erro.set(erro or "—")
    # Ícone/status de resultado:
    erro_min = (erro or "").lower()
    if "fail" in erro_min or "f" in erro_min:
        var_status.set("❌ Falha")
    elif "pass" in erro_min or "p" in erro_min:
        var_status.set("✅ OK")
    elif erro_min.strip() == "":
        var_status.set("⏺️ Indefinido")
    else:
        var_status.set("⚠️ Alerta")

def formatar_data(data_raw):
    # Espera 'YYYYMMDD'
    if len(data_raw) == 8 and data_raw.isdigit():
        return f"{data_raw[6:8]}/{data_raw[4:6]}/{data_raw[0:4]}"
    return data_raw

def formatar_hora(hora_raw):
    # Espera 'HHMMSS'
    if len(hora_raw) == 6 and hora_raw.isdigit():
        return f"{hora_raw[0:2]}:{hora_raw[2:4]}:{hora_raw[4:6]}"
    return hora_raw

# ========================== Histórico Visual ============================

def atualizar_historico_visual():
    hist_list.delete(0, tk.END)
    ultimos = historico[-6:] if historico else []
    for item in reversed(ultimos):
        icone = "✅" if item["status"] == "ok" else "❌"
        dt = f"{item['data']} {item['hora']}"
        hist_list.insert(tk.END, f"{icone} {item['serial']} | {dt} | {item['nome_arquivo']}")

def abrir_do_hist(event=None):
    idx = hist_list.curselection()
    if not idx:
        return
    item = list(reversed(historico[-6:]))[idx[0]]
    termo = item['serial']
    entry_busca.delete(0, tk.END)
    entry_busca.insert(0, termo)
    buscar_logs()
    for i in range(listbox_logs.size()):
        if termo in listbox_logs.get(i):
            listbox_logs.selection_clear(0, tk.END)
            listbox_logs.selection_set(i)
            exibir_log()
            break

# ==================== Busca Interna no Log ==============================

def buscar_no_log(event=None):
    termo = entry_searchlog.get().strip().lower()
    conteudo = text_area.get("1.0", tk.END).lower()
    text_area.tag_remove("highlight", "1.0", tk.END)
    if termo:
        idx = "1.0"
        while True:
            idx = text_area.search(termo, idx, nocase=1, stopindex=tk.END)
            if not idx:
                break
            lastidx = f"{idx}+{len(termo)}c"
            text_area.tag_add("highlight", idx, lastidx)
            idx = lastidx
        text_area.tag_config("highlight", background="yellow", foreground="black")

# =================== Copiar Seleção e Aumentar Fonte ====================

def copiar_selecao():
    try:
        selecionado = text_area.get(tk.SEL_FIRST, tk.SEL_LAST)
        root.clipboard_clear()
        root.clipboard_append(selecionado)
        messagebox.showinfo("Copiado", "Trecho copiado para a área de transferência.")
    except tk.TclError:
        messagebox.showinfo("Copiar", "Nenhum texto selecionado.")

def aumentar_fonte():
    global fonte_log
    fonte_log += 1
    text_area.configure(font=("Consolas", fonte_log))

def diminuir_fonte():
    global fonte_log
    if fonte_log > 7:
        fonte_log -= 1
        text_area.configure(font=("Consolas", fonte_log))

# =========================== Diretórios =============================

diretorios = [
    r"\\147.1.0.95\teste_ict\ict02\defeitos_tri",
    r"\\147.1.0.95\teste_ict\ict01\defeitos"
]

# ======================== Interface Gráfica =========================

root = ctk.CTk()
root.title("Busca de Logs ICT")
root.geometry("1050x750")

frame = ctk.CTkFrame(master=root)
frame.pack(padx=20, pady=20, fill="both", expand=True)

from tkinter import ttk

# ... após o frame principal:
colunas = [
    "Step", "Part name", "Actual", "Standard", "High lim", "Low lim",
    "Mode", "Type", "High pin", "Low pin", "Location", "Measure", "Result"
]
tabela_frame = ctk.CTkFrame(master=frame)
tabela_frame.pack(pady=6, fill="x")
tree = ttk.Treeview(tabela_frame, columns=colunas, show='headings', height=7)
tree.pack(side="left", fill="x", expand=True)
for col in colunas:
    tree.heading(col, text=col)
    tree.column(col, width=80, anchor="center")
scroll_x = tk.Scrollbar(tabela_frame, orient="horizontal", command=tree.xview)
tree.configure(xscrollcommand=scroll_x.set)
scroll_x.pack(side="bottom", fill="x")
tabela_frame.pack_forget()  # Esconde por padrão

painel_agilent = ctk.CTkFrame(master=frame)
painel_agilent.pack(pady=6, fill="both", expand=True)
text_agilent = tk.Text(painel_agilent, width=110, height=12, font=("Consolas", 11), wrap="word", bg="#eaf0fa")
text_agilent.pack(fill="both", expand=True)
painel_agilent.pack_forget()  # Esconde por padrão


# ---------- Painel de Destaque (Serial, Data, Hora, Erro, Status) ----------
painel = ctk.CTkFrame(master=frame)
painel.pack(pady=8, fill="x")
var_serial = tk.StringVar(value="—")
var_data = tk.StringVar(value="—")
var_hora = tk.StringVar(value="—")
var_erro = tk.StringVar(value="—")
var_status = tk.StringVar(value="—")
ctk.CTkLabel(painel, text="Serial:", font=("Arial", 16, "bold")).grid(row=0, column=0, padx=8, pady=4)
ctk.CTkLabel(painel, textvariable=var_serial, font=("Consolas", 16)).grid(row=0, column=1, padx=8)
ctk.CTkLabel(painel, text="Data:", font=("Arial", 14, "bold")).grid(row=0, column=2, padx=8)
ctk.CTkLabel(painel, textvariable=var_data, font=("Consolas", 14)).grid(row=0, column=3, padx=8)
ctk.CTkLabel(painel, text="Hora:", font=("Arial", 14, "bold")).grid(row=0, column=4, padx=8)
ctk.CTkLabel(painel, textvariable=var_hora, font=("Consolas", 14)).grid(row=0, column=5, padx=8)
ctk.CTkLabel(painel, text="Status:", font=("Arial", 14, "bold")).grid(row=0, column=6, padx=8)
ctk.CTkLabel(painel, textvariable=var_status, font=("Consolas", 14)).grid(row=0, column=7, padx=8)
ctk.CTkLabel(painel, text="Erro:", font=("Arial", 14, "bold")).grid(row=1, column=0, padx=8, pady=4)
ctk.CTkLabel(painel, textvariable=var_erro, font=("Consolas", 14)).grid(row=1, column=1, columnspan=7, padx=8, sticky="w")

# ------------- Barra de Busca, Histórico e Log List --------------
busca_frame = ctk.CTkFrame(master=frame, fg_color="transparent")
busca_frame.pack(pady=5, fill="x")
entry_busca = ctk.CTkEntry(master=busca_frame, width=220, placeholder_text="Serial (10 caracteres)...")
entry_busca.pack(side="left", padx=5)
entry_busca.bind("<Return>", buscar_logs)
botao_buscar = ctk.CTkButton(master=busca_frame, text="Buscar", command=buscar_logs)
botao_buscar.pack(side="left", padx=5)
botao_limpar = ctk.CTkButton(master=busca_frame, text="Limpar", command=limpar_busca)
botao_limpar.pack(side="left", padx=5)

hist_frame = ctk.CTkFrame(master=frame)
hist_frame.pack(pady=8)
ctk.CTkLabel(hist_frame, text="Histórico:", font=("Arial", 14, "bold")).pack(side="left")
hist_list = tk.Listbox(hist_frame, width=52, height=3, font=("Consolas", 11))
hist_list.pack(side="left", padx=10)
hist_list.bind("<Double-Button-1>", abrir_do_hist)

logs_frame = ctk.CTkFrame(master=frame)
logs_frame.pack(pady=8)
scroll_logs = tk.Scrollbar(logs_frame)
scroll_logs.pack(side="right", fill="y")
listbox_logs = tk.Listbox(logs_frame, width=60, height=10, yscrollcommand=scroll_logs.set, font=("Consolas", 11))
listbox_logs.pack(side="left", fill="both")
scroll_logs.config(command=listbox_logs.yview)
listbox_logs.bind("<Double-Button-1>", exibir_log)
listbox_logs.bind("<Return>", exibir_log)

botoes_frame = ctk.CTkFrame(master=frame, fg_color="transparent")
botoes_frame.pack(pady=5, fill="x")
botao_exibir = ctk.CTkButton(master=botoes_frame, text="Exibir Log", command=exibir_log)
botao_exibir.pack(side="left", padx=5)
botao_copiar = ctk.CTkButton(master=botoes_frame, text="Copiar LOG para máquina", command=copiar_log)
botao_copiar.pack(side="left", padx=5)

# ----------------- Área de Visualização do Log --------------------
fonte_log = 10
visu_frame = ctk.CTkFrame(master=frame)
visu_frame.pack(pady=8, fill="both", expand=True)
top_visu = ctk.CTkFrame(visu_frame, fg_color="transparent")
top_visu.pack(pady=2, fill="x")
ctk.CTkLabel(top_visu, text="Buscar no log:", font=("Arial", 12)).pack(side="left")
entry_searchlog = ctk.CTkEntry(top_visu, width=150, placeholder_text="Buscar termo…")
entry_searchlog.pack(side="left", padx=5)
entry_searchlog.bind("<Return>", buscar_no_log)
ctk.CTkButton(top_visu, text="Aumentar Fonte", command=aumentar_fonte, width=10).pack(side="right", padx=3)
ctk.CTkButton(top_visu, text="Diminuir Fonte", command=diminuir_fonte, width=10).pack(side="right", padx=3)
ctk.CTkButton(top_visu, text="Copiar Seleção", command=copiar_selecao, width=10).pack(side="right", padx=3)

text_area = ctk.CTkTextbox(visu_frame, width=940, height=270, font=("Consolas", fonte_log))
text_area.pack(pady=4, fill="both", expand=True)
text_area.configure(state="disabled")

root.mainloop()
