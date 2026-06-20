"""
Aba "Logs do Sistema" do Painel Administrativo.

Extraído de abrir_painel_admin_ctk (Servidor.py) sem alterar a lógica.
"""
import os
import re as _re
import customtkinter as ctk
from tkinter import messagebox

from paineis.helpers import card_resumo


def criar_pagina_logs(_scroll_inner, cores, logger, _agora_br, LOG_FILE):
    """Cria e retorna o frame da página "Logs do Sistema".

    Parâmetros
    ----------
    _scroll_inner : CTkFrame
        Frame pai (área rolável) onde a página é desenhada.
    cores : dict
        Constantes de cor: CINZA_BG, BRANCO, TEXTO_CINZA, TEXTO_ESCURO,
        VERDE_VIBRANTE, VERDE_ESCURO, AZUL_CLARO, VERDE_CLARO,
        LARANJA_CLARO, VERMELHO_CLARO.
    logger : Logger
        Logger usado para registrar a limpeza manual de logs.
    _agora_br : callable
        Devolve datetime atual no fuso do Brasil.
    LOG_FILE : str
        Caminho do arquivo de log do sistema (marwin.log).
    """
    CINZA_BG       = cores["CINZA_BG"]
    BRANCO         = cores["BRANCO"]
    TEXTO_CINZA    = cores["TEXTO_CINZA"]
    TEXTO_ESCURO   = cores["TEXTO_ESCURO"]
    VERDE_VIBRANTE = cores["VERDE_VIBRANTE"]
    VERDE_ESCURO   = cores["VERDE_ESCURO"]
    AZUL_CLARO     = cores["AZUL_CLARO"]
    VERDE_CLARO    = cores["VERDE_CLARO"]
    LARANJA_CLARO  = cores["LARANJA_CLARO"]
    VERMELHO_CLARO = cores["VERMELHO_CLARO"]

    def _card_resumo(parent, row, col, icone, cor_fundo, cor_icone, titulo, valor, subtitulo):
        return card_resumo(parent, row, col, icone, cor_fundo, cor_icone, titulo, valor,
                            subtitulo, {"BRANCO": BRANCO, "TEXTO_CINZA": TEXTO_CINZA,
                                        "TEXTO_ESCURO": TEXTO_ESCURO})

    page = ctk.CTkFrame(_scroll_inner, fg_color=CINZA_BG)
    page.grid_columnconfigure(0, weight=1)
    page.grid_rowconfigure(3, weight=1)

    CORES_NIVEL = {
        "DEBUG":   "#9E9E9E",
        "INFO":    "#2196F3",
        "WARNING": "#FB8C00",
        "ERROR":   "#F44336",
        "CRITICAL": "#B71C1C",
    }

    # ── Cabeçalho ─────────────────────────────────────────────────────────
    cab = ctk.CTkFrame(page, fg_color="transparent")
    cab.grid(row=0, column=0, sticky="ew", pady=(4, 12))
    ctk.CTkLabel(cab, text="Logs do Sistema 📄",
                  font=("Segoe UI", 22, "bold"), text_color=TEXTO_ESCURO).pack(anchor="w")
    ctk.CTkLabel(cab, text="Acompanhe os eventos registrados pelo servidor.",
                  font=("Segoe UI", 12), text_color=TEXTO_CINZA).pack(anchor="w")

    # ── Card de filtros ───────────────────────────────────────────────────
    filtro_card = ctk.CTkFrame(page, fg_color=BRANCO, corner_radius=12)
    filtro_card.grid(row=1, column=0, sticky="ew", pady=(0, 12))

    linha_f = ctk.CTkFrame(filtro_card, fg_color="transparent")
    linha_f.pack(fill="x", padx=14, pady=14)

    ctk.CTkLabel(linha_f, text="Nível:", font=("Segoe UI", 11, "bold"),
                  text_color=TEXTO_ESCURO).pack(side="left", padx=(0, 6))
    cb_nivel = ctk.CTkOptionMenu(linha_f,
                                  values=["Todos", "INFO", "WARNING", "ERROR", "DEBUG", "CRITICAL"],
                                  width=120, fg_color=VERDE_VIBRANTE,
                                  button_color=VERDE_ESCURO, button_hover_color=VERDE_ESCURO)
    cb_nivel.set("Todos")
    cb_nivel.pack(side="left", padx=(0, 14))

    ctk.CTkLabel(linha_f, text="Buscar:", font=("Segoe UI", 11, "bold"),
                  text_color=TEXTO_ESCURO).pack(side="left", padx=(0, 6))
    ent_busca = ctk.CTkEntry(linha_f, width=260, height=32,
                              placeholder_text="Filtrar por texto na mensagem...")
    ent_busca.pack(side="left", padx=(0, 14))

    ctk.CTkButton(linha_f, text="🔍  Buscar", fg_color=VERDE_VIBRANTE,
                   hover_color=VERDE_ESCURO, font=("Segoe UI", 11, "bold"),
                   height=32, width=100,
                   command=lambda: atualizar_logs()).pack(side="left", padx=(0, 8))
    ctk.CTkButton(linha_f, text="↻  Atualizar", fg_color="#1565C0",
                   hover_color="#0D47A1", font=("Segoe UI", 11, "bold"),
                   height=32, width=110,
                   command=lambda: atualizar_logs()).pack(side="left", padx=(0, 8))
    ctk.CTkButton(linha_f, text="🗑  Limpar logs", fg_color="#C62828",
                   hover_color="#8E1F1F", font=("Segoe UI", 11, "bold"),
                   height=32, width=120,
                   command=lambda: limpar_logs()).pack(side="left")

    # ── Cards de resumo ───────────────────────────────────────────────────
    resumo_row = ctk.CTkFrame(page, fg_color="transparent")
    resumo_row.grid(row=2, column=0, sticky="ew", pady=(0, 12))
    resumo_row.grid_columnconfigure((0, 1, 2, 3), weight=1)

    lbl_total, _ = _card_resumo(resumo_row, 0, 0, "📄", AZUL_CLARO, "#1565C0",
                                "Total exibido", "0", "linhas")
    lbl_info, _ = _card_resumo(resumo_row, 0, 1, "ℹ️", VERDE_CLARO, "#2196F3",
                               "INFO", "0", "")
    lbl_warn, _ = _card_resumo(resumo_row, 0, 2, "⚠️", LARANJA_CLARO, "#FB8C00",
                               "WARNING", "0", "")
    lbl_err, _ = _card_resumo(resumo_row, 0, 3, "🚨", VERMELHO_CLARO, "#F44336",
                              "ERROR / CRITICAL", "0", "")

    # ── Tabela de logs ─────────────────────────────────────────────────────
    tabela_card = ctk.CTkFrame(page, fg_color=BRANCO, corner_radius=12)
    tabela_card.grid(row=3, column=0, sticky="nsew", pady=(0, 4))
    tabela_card.grid_rowconfigure(2, weight=1)
    tabela_card.grid_columnconfigure(0, weight=1)

    topo_tab = ctk.CTkFrame(tabela_card, fg_color="transparent")
    topo_tab.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 6))
    ctk.CTkLabel(topo_tab, text="Eventos recentes (mais novos primeiro)",
                  font=("Segoe UI", 13, "bold"), text_color=TEXTO_ESCURO).pack(side="left")

    header_tab = ctk.CTkFrame(tabela_card, fg_color=VERDE_ESCURO, corner_radius=6)
    header_tab.grid(row=1, column=0, sticky="ew", padx=14)
    COLS = [("DATA/HORA", 150), ("NÍVEL", 100), ("MENSAGEM", 0)]
    for i, (col, w) in enumerate(COLS):
        ctk.CTkLabel(header_tab, text=col, font=("Segoe UI", 10, "bold"),
                      text_color="white", width=w, anchor="w"
                      ).pack(side="left", expand=(i == len(COLS) - 1), fill="x", padx=8, pady=8)

    corpo_tab = ctk.CTkFrame(tabela_card, fg_color="transparent")
    corpo_tab.grid(row=2, column=0, sticky="nsew", padx=14, pady=(4, 14))
    corpo_tab.grid_columnconfigure(0, weight=1)

    lbl_status = ctk.CTkLabel(page, text="", font=("Segoe UI", 10), text_color=TEXTO_CINZA)
    lbl_status.grid(row=4, column=0, sticky="w", pady=(8, 16))

    PADRAO_LOG = _re.compile(r"^(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}) - (\w+) - (.*)$")

    def _ler_linhas_log(max_linhas=500):
        if not os.path.exists(LOG_FILE):
            return []
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                linhas = f.readlines()
        except Exception:
            return []
        return linhas[-max_linhas:]

    def limpar_logs():
        if not messagebox.askyesno("Confirmar", "Limpar todos os logs do sistema?\nEsta ação não pode ser desfeita."):
            return
        try:
            open(LOG_FILE, "w", encoding="utf-8").close()
            logger.info("Logs do sistema limpos via painel administrativo")
            atualizar_logs()
            messagebox.showinfo("Sucesso", "Logs limpos com sucesso.")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao limpar logs:\n{e}")

    def atualizar_logs():
        for w in corpo_tab.winfo_children():
            w.destroy()

        nivel_f = cb_nivel.get()
        busca_f = ent_busca.get().strip().lower()

        linhas_raw = _ler_linhas_log(500)

        registros = []
        for linha in linhas_raw:
            linha = linha.rstrip("\n")
            if not linha:
                continue
            m = PADRAO_LOG.match(linha)
            if m:
                data_hora, nivel, msg = m.group(1), m.group(2), m.group(3)
            else:
                data_hora, nivel, msg = "", "INFO", linha

            if nivel_f != "Todos" and nivel.upper() != nivel_f:
                continue
            if busca_f and busca_f not in linha.lower():
                continue

            registros.append((data_hora, nivel.upper(), msg))

        registros.reverse()  # mais recentes primeiro

        cnt_info = sum(1 for r in registros if r[1] == "INFO")
        cnt_warn = sum(1 for r in registros if r[1] == "WARNING")
        cnt_err = sum(1 for r in registros if r[1] in ("ERROR", "CRITICAL"))

        lbl_total.configure(text=str(len(registros)))
        lbl_info.configure(text=str(cnt_info))
        lbl_warn.configure(text=str(cnt_warn))
        lbl_err.configure(text=str(cnt_err))

        if not registros:
            ctk.CTkLabel(corpo_tab, text="Nenhum log encontrado para o filtro selecionado.",
                          font=("Segoe UI", 11), text_color=TEXTO_CINZA
                          ).grid(row=0, column=0, sticky="w", pady=12, padx=4)
        else:
            for i, (data_hora, nivel, msg) in enumerate(registros):
                cor = CORES_NIVEL.get(nivel, TEXTO_ESCURO)
                linha_frame = ctk.CTkFrame(corpo_tab, fg_color=("#FAFAFA" if i % 2 else "transparent"))
                linha_frame.grid(row=i, column=0, sticky="ew")
                linha_frame.grid_columnconfigure(2, weight=1)

                ctk.CTkLabel(linha_frame, text=data_hora or "—", font=("Segoe UI", 11),
                              text_color="#374151", width=150, anchor="w"
                              ).grid(row=0, column=0, padx=8, pady=6, sticky="w")
                ctk.CTkLabel(linha_frame, text=nivel, font=("Segoe UI", 10, "bold"),
                              text_color=cor, width=100, anchor="w"
                              ).grid(row=0, column=1, padx=8, pady=6, sticky="w")
                ctk.CTkLabel(linha_frame, text=msg, font=("Segoe UI", 11),
                              text_color="#374151", anchor="w", justify="left",
                              wraplength=700
                              ).grid(row=0, column=2, padx=8, pady=6, sticky="ew")

        agora_txt = _agora_br().strftime("%d/%m/%Y %H:%M:%S")
        lbl_status.configure(text=f"Atualizado em {agora_txt}  ·  exibindo até 500 linhas mais recentes do arquivo de log.")

    atualizar_logs()
    return page
