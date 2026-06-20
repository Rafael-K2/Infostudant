"""
Aba "Editar Cardápio" do Painel Administrativo.

Extraído de abrir_painel_admin_ctk (Servidor.py) sem alterar a lógica.
A única mudança em relação ao código original é que as variáveis que antes
vinham do escopo da função-mãe (CTk, cores, helpers de dados) agora chegam
como parâmetros explícitos.
"""
import customtkinter as ctk


def criar_pagina_cardapio(_scroll_inner, cores, ler_json, salvar_json,
                           _sync_nuvem, CARDAPIO_FILE, CARDAPIO_PADRAO):
    """Cria e retorna o frame da página "Editar Cardápio".

    Parâmetros
    ----------
    _scroll_inner : CTkFrame
        Frame pai (área rolável) onde a página é desenhada.
    cores : dict
        Constantes de cor usadas no painel (CINZA_BG, TEXTO_ESCURO,
        TEXTO_CINZA, VERDE_VIBRANTE, VERDE_ESCURO, BRANCO).
    ler_json, salvar_json : callables
        Mesmas funções utilitárias do Servidor.py (leitura/escrita de JSON).
    _sync_nuvem : callable
        Mesma função de sincronização com a API na nuvem.
    CARDAPIO_FILE : str
        Caminho do arquivo cardapio.json.
    CARDAPIO_PADRAO : dict
        Estrutura padrão usada quando o arquivo não existe ainda.
    """
    CINZA_BG       = cores["CINZA_BG"]
    BRANCO         = cores["BRANCO"]
    TEXTO_CINZA    = cores["TEXTO_CINZA"]
    TEXTO_ESCURO   = cores["TEXTO_ESCURO"]
    VERDE_VIBRANTE = cores["VERDE_VIBRANTE"]
    VERDE_ESCURO   = cores["VERDE_ESCURO"]

    page = ctk.CTkFrame(_scroll_inner, fg_color=CINZA_BG)
    page.grid_columnconfigure(0, weight=1)

    # ── Cabeçalho ─────────────────────────────────────────────────────────
    cab = ctk.CTkFrame(page, fg_color="transparent")
    cab.grid(row=0, column=0, sticky="ew", pady=(4, 8))
    ctk.CTkLabel(cab, text="Editar Cardápio 🍽️",
                  font=("Segoe UI", 22, "bold"), text_color=TEXTO_ESCURO).pack(anchor="w")
    ctk.CTkLabel(cab, text="Edite as refeições de cada dia e clique em Salvar.",
                  font=("Segoe UI", 12), text_color=TEXTO_CINZA).pack(anchor="w")

    # ── Botão Salvar (topo) ───────────────────────────────────────────────
    btn_bar = ctk.CTkFrame(page, fg_color="transparent")
    btn_bar.grid(row=1, column=0, sticky="ew", pady=(0, 16))

    lbl_status = ctk.CTkLabel(btn_bar, text="", font=("Segoe UI", 11),
                               text_color=VERDE_VIBRANTE)
    lbl_status.pack(side="right", padx=(12, 0))

    # Constantes dos dias
    DIAS = ["SEGUNDA", "TERCA", "QUARTA", "QUINTA", "SEXTA"]
    DIAS_LABEL = {
        "SEGUNDA": "Segunda-feira",
        "TERCA":   "Terça-feira",
        "QUARTA":  "Quarta-feira",
        "QUINTA":  "Quinta-feira",
        "SEXTA":   "Sexta-feira",
    }
    REFEICOES = ["Merenda Manhã", "Almoço", "Merenda Tarde"]
    CORES_DIA = {
        "SEGUNDA": VERDE_VIBRANTE,
        "TERCA":   "#1565C0",
        "QUARTA":  "#6A1B9A",
        "QUINTA":  "#E65100",
        "SEXTA":   "#C62828",
    }

    # Carrega cardápio atual
    ca = ler_json(CARDAPIO_FILE, CARDAPIO_PADRAO)
    ents = {}  # dia -> [Entry, Entry, Entry]

    # ── Grade de cards ─────────────────────────────────────────────────────
    grade = ctk.CTkFrame(page, fg_color="transparent")
    grade.grid(row=2, column=0, sticky="ew")
    grade.grid_columnconfigure(0, weight=1, uniform="col")
    grade.grid_columnconfigure(1, weight=1, uniform="col")

    def _criar_card_dia(parent, dia, row, col, colspan=1):
        cor = CORES_DIA[dia]
        card = ctk.CTkFrame(parent, fg_color=BRANCO, corner_radius=12)
        if colspan == 2:
            card.grid(row=row, column=col, columnspan=2, sticky="ew",
                      padx=6, pady=6)
        else:
            card.grid(row=row, column=col, sticky="nsew", padx=6, pady=6)

        # Cabeçalho colorido
        hd = ctk.CTkFrame(card, fg_color=cor, corner_radius=8,
                           height=44)
        hd.pack(fill="x", padx=8, pady=(8, 0))
        hd.pack_propagate(False)
        ctk.CTkLabel(hd, text=f"  {DIAS_LABEL[dia]}",
                      font=("Segoe UI", 13, "bold"),
                      text_color="white").place(relx=0, rely=0.5, anchor="w", x=8)

        # Campos de refeição
        ents[dia] = []
        valores_dia = ca.get(dia, ["", "", ""])
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=(10, 14))

        if colspan == 2:
            # Sexta: 3 campos lado a lado
            for j, nome_ref in enumerate(REFEICOES):
                col_frame = ctk.CTkFrame(inner, fg_color="transparent")
                col_frame.pack(side="left", expand=True, fill="both",
                               padx=(0, 12 if j < 2 else 0))
                ctk.CTkLabel(col_frame, text=nome_ref,
                              font=("Segoe UI", 10, "bold"),
                              text_color=TEXTO_CINZA).pack(anchor="w", pady=(0, 4))
                e = ctk.CTkEntry(col_frame, font=("Segoe UI", 11),
                                  height=38, border_color=cor,
                                  border_width=2)
                e.insert(0, valores_dia[j] if j < len(valores_dia) else "")
                e.pack(fill="x")
                ents[dia].append(e)
        else:
            # Seg–Qui: 3 campos empilhados
            for j, nome_ref in enumerate(REFEICOES):
                ctk.CTkLabel(inner, text=nome_ref,
                              font=("Segoe UI", 10, "bold"),
                              text_color=TEXTO_CINZA).pack(anchor="w",
                                                           pady=(6 if j > 0 else 0, 4))
                e = ctk.CTkEntry(inner, font=("Segoe UI", 11),
                                  height=38, border_color=cor,
                                  border_width=2)
                e.insert(0, valores_dia[j] if j < len(valores_dia) else "")
                e.pack(fill="x")
                ents[dia].append(e)

    # Seg / Ter  (linha 0)
    _criar_card_dia(grade, "SEGUNDA", row=0, col=0)
    _criar_card_dia(grade, "TERCA",   row=0, col=1)
    # Qua / Qui  (linha 1)
    _criar_card_dia(grade, "QUARTA",  row=1, col=0)
    _criar_card_dia(grade, "QUINTA",  row=1, col=1)
    # Sexta em linha cheia (linha 2)
    _criar_card_dia(grade, "SEXTA",   row=2, col=0, colspan=2)

    # ── Salvar ────────────────────────────────────────────────────────────
    def salvar():
        novo = {dia: [e.get() for e in ents[dia]] for dia in DIAS}
        salvar_json(CARDAPIO_FILE, novo)
        try:
            _sync_nuvem("/admin/cardapio", "PUT", novo)
        except Exception:
            pass
        lbl_status.configure(text="✔  Cardápio salvo com sucesso!")
        page.after(3000, lambda: lbl_status.configure(text=""))

    ctk.CTkButton(btn_bar, text="💾  Salvar Alterações",
                   fg_color=VERDE_VIBRANTE, hover_color=VERDE_ESCURO,
                   font=("Segoe UI", 12, "bold"), height=40, width=200,
                   command=salvar).pack(side="left")
    return page
