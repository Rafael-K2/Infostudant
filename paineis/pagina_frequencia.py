"""
Aba "Frequência" do Painel Administrativo.

Extraído de abrir_painel_admin_ctk (Servidor.py) sem alterar a lógica.
"""
import os
import json
import csv
import unicodedata as _ud
import threading
import customtkinter as ctk
from tkinter import messagebox

from paineis.helpers import card_resumo
from paineis.helpers import iniciar_polling


def criar_pagina_frequencia(_scroll_inner, cores, _hoje, _agora_br,
                             _registros_freq_hoje, _aula_por_hora,
                             _frequencia_duplicado_db, _inserir_frequencia_db,
                             _escrever_csv, _ler_frequencia_todos_db,
                             _apagar_frequencia_data_db, LISTA_ALUNOS_FILE):
    """Cria e retorna o frame da página "Frequência".

    Parâmetros
    ----------
    _scroll_inner : CTkFrame
        Frame pai (área rolável) onde a página é desenhada.
    cores : dict
        Constantes de cor: CINZA_BG, BRANCO, TEXTO_CINZA, TEXTO_ESCURO,
        VERDE_VIBRANTE, VERDE_ESCURO, VERDE_CLARO, AZUL_CLARO.
    _hoje, _agora_br : callables
        Data/hora atual no fuso do Brasil.
    _registros_freq_hoje : callable
        Lê do banco os registros de frequência de hoje.
    _aula_por_hora : callable
        Deduz a aula/turno a partir do horário de entrada.
    _frequencia_duplicado_db : callable
        Verifica se uma matrícula já tem presença registrada hoje.
    _inserir_frequencia_db : callable
        Insere um novo registro de presença.
    _escrever_csv : callable
        Escreve um arquivo CSV utilitário.
    _ler_frequencia_todos_db : callable
        Lê todos os registros de frequência (usado na exportação CSV).
    _apagar_frequencia_data_db : callable
        Apaga os registros de frequência de uma data específica.
    LISTA_ALUNOS_FILE : str
        Caminho do arquivo JSON com a lista completa de alunos cadastrados.
    """
    CINZA_BG       = cores["CINZA_BG"]
    BRANCO         = cores["BRANCO"]
    TEXTO_CINZA    = cores["TEXTO_CINZA"]
    TEXTO_ESCURO   = cores["TEXTO_ESCURO"]
    VERDE_VIBRANTE = cores["VERDE_VIBRANTE"]
    VERDE_ESCURO   = cores["VERDE_ESCURO"]
    VERDE_CLARO    = cores["VERDE_CLARO"]
    AZUL_CLARO     = cores["AZUL_CLARO"]

    def _card_resumo(parent, row, col, icone, cor_fundo, cor_icone, titulo, valor, subtitulo):
        return card_resumo(parent, row, col, icone, cor_fundo, cor_icone, titulo, valor,
                            subtitulo, {"BRANCO": BRANCO, "TEXTO_CINZA": TEXTO_CINZA,
                                        "TEXTO_ESCURO": TEXTO_ESCURO})

    page = ctk.CTkFrame(_scroll_inner, fg_color=CINZA_BG)
    page.grid_columnconfigure(0, weight=1)
    page.grid_rowconfigure(3, weight=1)

    # ── Mapas de siglas / cursos / normalização ──────────────────────────
    SIGLAS_LABEL = {
        "1DS": "1º DS",  "1HOS": "1º HOS", "1ENF": "1º ENF", "1MOD": "1º MOD",
        "2DS": "2º DS",  "2HOS": "2º HOS", "2ENF": "2º ENF", "2MOD": "2º MOD",
        "3DS": "3º DS",  "3HOS": "3º HOS", "3ENF": "3º ENF", "3MOD": "3º MOD",
    }
    SIGLAS = {
        "1DS":  {"serie": "1 Ano", "curso": "Desenvolvimento de Sistemas"},
        "1HOS": {"serie": "1 Ano", "curso": "Hospedagem"},
        "1ENF": {"serie": "1 Ano", "curso": "Enfermagem"},
        "1MOD": {"serie": "1 Ano", "curso": "Modelagem do Vestuario"},
        "2DS":  {"serie": "2 Ano", "curso": "Desenvolvimento de Sistemas"},
        "2HOS": {"serie": "2 Ano", "curso": "Hospedagem"},
        "2ENF": {"serie": "2 Ano", "curso": "Enfermagem"},
        "2MOD": {"serie": "2 Ano", "curso": "Modelagem do Vestuario"},
        "3DS":  {"serie": "3 Ano", "curso": "Desenvolvimento de Sistemas"},
        "3HOS": {"serie": "3 Ano", "curso": "Hospedagem"},
        "3ENF": {"serie": "3 Ano", "curso": "Enfermagem"},
        "3MOD": {"serie": "3 Ano", "curso": "Modelagem do Vestuario"},
    }
    CORES_ANO = {"1": VERDE_VIBRANTE, "2": "#6A1B9A", "3": "#C62828"}

    def _norm(texto):
        return _ud.normalize("NFD", str(texto).lower()).encode("ascii", "ignore").decode("ascii")

    _GRUPOS_SERIE = {
        "1": ["1º", "1o", "1 ano", "primeiro ano", "primeiro", "1"],
        "2": ["2º", "2o", "2 ano", "segundo ano",  "segundo",  "2"],
        "3": ["3º", "3o", "3 ano", "terceiro ano", "terceiro", "3"],
    }
    _GRUPOS_CURSO = {
        "ds":   ["ds", "desenvolvimento de sistemas", "dev. sistemas", "dev sistemas", "desenv. sistemas"],
        "enf":  ["enf", "enfermagem"],
        "hosp": ["hosp", "hospedagem"],
        "mod":  ["mod", "modelagem do vestuario", "modelagem", "vestuario"],
    }

    def _grupo_serie(texto):
        t = _norm(texto).strip()
        for chave, variantes in _GRUPOS_SERIE.items():
            for v in variantes:
                if t == v or t.startswith(v) or v.startswith(t):
                    return chave
        return None

    def _grupo_curso(texto):
        t = _norm(texto).strip()
        for chave, variantes in _GRUPOS_CURSO.items():
            for v in variantes:
                if t == v or t in v or v in t:
                    return chave
        return None

    def _serie_bate(serie_aluno, filtro_serie):
        if filtro_serie in ("(Todas)", ""):
            return True
        g_a, g_f = _grupo_serie(serie_aluno), _grupo_serie(filtro_serie)
        if g_a is None or g_f is None:
            return _norm(filtro_serie) in _norm(serie_aluno)
        return g_a == g_f

    def _curso_bate(curso_aluno, filtro_curso):
        if filtro_curso in ("(Todos)", ""):
            return True
        g_a, g_f = _grupo_curso(curso_aluno), _grupo_curso(filtro_curso)
        if g_a is None or g_f is None:
            return _norm(filtro_curso) in _norm(curso_aluno)
        return g_a == g_f

    # ── Cabeçalho ─────────────────────────────────────────────────────────
    cab = ctk.CTkFrame(page, fg_color="transparent")
    cab.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 12))
    ctk.CTkLabel(cab, text="Frequência ⏱️",
                  font=("Segoe UI", 22, "bold"), text_color=TEXTO_ESCURO).pack(anchor="w")
    ctk.CTkLabel(cab, text=f"Controle de presença — hoje ({_hoje()})",
                  font=("Segoe UI", 12), text_color=TEXTO_CINZA).pack(anchor="w")

    # ── Filtros ───────────────────────────────────────────────────────────
    filtro_card = ctk.CTkFrame(page, fg_color=BRANCO, corner_radius=12)
    filtro_card.grid(row=1, column=0, sticky="ew", pady=(0, 12))

    filtro_row = ctk.CTkFrame(filtro_card, fg_color="transparent")
    filtro_row.pack(fill="x", padx=14, pady=(12, 8))

    ctk.CTkLabel(filtro_row, text="Série:", font=("Segoe UI", 11, "bold"),
                  text_color=TEXTO_ESCURO).pack(side="left", padx=(0, 6))
    cb_serie = ctk.CTkOptionMenu(filtro_row, values=["(Todas)", "1 Ano", "2 Ano", "3 Ano"],
                                  width=110, fg_color=VERDE_VIBRANTE,
                                  button_color=VERDE_ESCURO, button_hover_color=VERDE_ESCURO)
    cb_serie.set("(Todas)")
    cb_serie.pack(side="left", padx=(0, 14))

    ctk.CTkLabel(filtro_row, text="Curso:", font=("Segoe UI", 11, "bold"),
                  text_color=TEXTO_ESCURO).pack(side="left", padx=(0, 6))
    cb_curso = ctk.CTkOptionMenu(filtro_row,
                                  values=["(Todos)", "Desenvolvimento de Sistemas", "Hospedagem",
                                          "Enfermagem", "Modelagem do Vestuario"],
                                  width=220, fg_color=VERDE_VIBRANTE,
                                  button_color=VERDE_ESCURO, button_hover_color=VERDE_ESCURO)
    cb_curso.set("(Todos)")
    cb_curso.pack(side="left", padx=(0, 14))

    ctk.CTkLabel(filtro_row, text="Nome:", font=("Segoe UI", 11, "bold"),
                  text_color=TEXTO_ESCURO).pack(side="left", padx=(0, 6))
    ent_nome = ctk.CTkEntry(filtro_row, width=180, height=30,
                             placeholder_text="Buscar por nome...")
    ent_nome.pack(side="left", padx=(0, 14))

    # Salas rápidas
    sala_row = ctk.CTkFrame(filtro_card, fg_color="transparent")
    sala_row.pack(fill="x", padx=14, pady=(0, 12))
    ctk.CTkLabel(sala_row, text="Sala rápida:", font=("Segoe UI", 10, "bold"),
                  text_color=TEXTO_CINZA).pack(side="left", padx=(0, 8))

    btn_sala_refs = {}

    # ── Cards de resumo ───────────────────────────────────────────────────
    cards_row = ctk.CTkFrame(page, fg_color="transparent")
    cards_row.grid(row=2, column=0, sticky="ew", pady=(0, 12))
    cards_row.grid_columnconfigure((0, 1, 2), weight=1)

    lbl_total, sub_total = _card_resumo(cards_row, 0, 0, "👥", VERDE_CLARO, VERDE_VIBRANTE,
                                        "Presentes (filtro)", "0", "alunos")
    lbl_cad,   sub_cad   = _card_resumo(cards_row, 0, 1, "📋", AZUL_CLARO, "#1565C0",
                                        "Total Cadastrados", "0", "alunos na lista")
    lbl_aus,   sub_aus   = _card_resumo(cards_row, 0, 2, "🚫", "#FFEBEE", "#C62828",
                                        "Ausentes", "0", "ainda não vieram")

    # ── Tabela de presentes ──────────────────────────────────────────────
    tabela_card = ctk.CTkFrame(page, fg_color=BRANCO, corner_radius=12)
    tabela_card.grid(row=3, column=0, sticky="nsew")
    tabela_card.grid_rowconfigure(2, weight=1)
    tabela_card.grid_columnconfigure(0, weight=1)

    topo_tab = ctk.CTkFrame(tabela_card, fg_color="transparent")
    topo_tab.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 6))
    ctk.CTkLabel(topo_tab, text="Alunos Presentes — hoje",
                  font=("Segoe UI", 13, "bold"), text_color=TEXTO_ESCURO).pack(side="left")
    lbl_filtro_ativo = ctk.CTkLabel(topo_tab, text="", font=("Segoe UI", 9),
                                     text_color=TEXTO_CINZA)
    lbl_filtro_ativo.pack(side="right")

    header_tab = ctk.CTkFrame(tabela_card, fg_color=VERDE_ESCURO, corner_radius=6)
    header_tab.grid(row=1, column=0, sticky="ew", padx=14)
    COLS = [("Aluno", 240), ("Série", 80), ("Curso", 220), ("Hora Entrada", 120), ("Aula", 110)]
    for i, (col, w) in enumerate(COLS):
        ctk.CTkLabel(header_tab, text=col, font=("Segoe UI", 10, "bold"),
                      text_color="white", width=w, anchor="w"
                      ).pack(side="left", expand=(i == len(COLS)-1),
                             fill="x", padx=6, pady=8)

    corpo_tab = ctk.CTkFrame(tabela_card, fg_color="transparent")
    corpo_tab.grid(row=2, column=0, sticky="nsew", padx=14, pady=(0, 14))
    corpo_tab.grid_columnconfigure(0, weight=1)

    # ── Botões de ação ────────────────────────────────────────────────────
    btn_row = ctk.CTkFrame(page, fg_color="transparent")
    btn_row.grid(row=4, column=0, sticky="w", pady=(12, 4))

    lbl_acao_status = ctk.CTkLabel(btn_row, text="", font=("Segoe UI", 10),
                                    text_color=VERDE_VIBRANTE)

    # ── Estado interno ────────────────────────────────────────────────────
    _estado = {"alunos_unicos": {}, "lista_todos": []}

    # ── Atualização principal ────────────────────────────────────────────
    def atualizar_freq():
        f_serie = cb_serie.get()
        f_curso = cb_curso.get()
        f_nome = ent_nome.get().strip().lower()

        def _thread_body():
            registros = _registros_freq_hoje()
            lista_todos = []
            if os.path.exists(LISTA_ALUNOS_FILE):
                try:
                    with open(LISTA_ALUNOS_FILE, "r", encoding="utf-8") as f:
                        lista_todos = json.load(f)
                except Exception:
                    lista_todos = []
            page.after(0, lambda: _renderizar(registros, lista_todos, f_serie, f_curso, f_nome))

        threading.Thread(target=_thread_body, daemon=True).start()

    def _renderizar(registros, lista_todos, f_serie, f_curso, f_nome):
        alunos_unicos = {}
        for r in registros:
            mat   = r[2]
            nome  = r[3]
            serie = r[4] if len(r) > 4 else ""
            curso = r[5] if len(r) > 5 else ""
            hora  = r[1] if len(r) > 1 else ""
            aula  = r[6] if len(r) > 6 else _aula_por_hora(hora)
            if mat not in alunos_unicos:
                alunos_unicos[mat] = {"nome": nome, "serie": serie,
                                       "curso": curso, "hora": hora, "aula": aula}
            else:
                if hora and alunos_unicos[mat].get("hora", "") and hora < alunos_unicos[mat]["hora"]:
                    alunos_unicos[mat]["hora"] = hora
                    alunos_unicos[mat]["aula"] = aula

        _estado["alunos_unicos"] = alunos_unicos
        _estado["lista_todos"] = lista_todos

        exibidos = []
        for info in alunos_unicos.values():
            if not _serie_bate(info["serie"], f_serie): continue
            if not _curso_bate(info["curso"], f_curso): continue
            if f_nome and f_nome not in info["nome"].lower(): continue
            exibidos.append(info)

        presentes_total = len(alunos_unicos)
        cadastrados_total = len(lista_todos)
        ausentes_total = max(0, cadastrados_total - presentes_total) if cadastrados_total else 0

        lbl_total.configure(text=str(len(exibidos)))
        lbl_cad.configure(text=str(cadastrados_total))
        lbl_aus.configure(text=str(ausentes_total))

        partes_filtro = []
        if f_serie not in ("(Todas)", ""): partes_filtro.append(f_serie)
        if f_curso not in ("(Todos)", ""): partes_filtro.append(f_curso)
        if f_nome: partes_filtro.append(f'"{f_nome}"')
        lbl_filtro_ativo.configure(
            text=("Filtro: " + " | ".join(partes_filtro)) if partes_filtro else "")

        for w in corpo_tab.winfo_children():
            w.destroy()

        if not exibidos:
            ctk.CTkLabel(corpo_tab, text="Nenhum registro encontrado.",
                          font=("Segoe UI", 12), text_color=TEXTO_CINZA
                          ).grid(row=0, column=0, pady=24)
            return

        exibidos_ord = sorted(exibidos, key=lambda a: a["nome"].lower())
        _estado_pag_freq = {"pagina": 0, "exibidos": exibidos_ord}
        LIMITE = 10

        def _renderizar_pagina_freq():
            for w in corpo_tab.winfo_children():
                w.destroy()
            pag = _estado_pag_freq["pagina"]
            dados = _estado_pag_freq["exibidos"]
            inicio = pag * LIMITE
            fatia = dados[inicio:inicio + LIMITE]

            for i, info in enumerate(fatia):
                bg = BRANCO if i % 2 == 0 else "#F8F9FA"
                linha = ctk.CTkFrame(corpo_tab, fg_color=bg, corner_radius=4)
                linha.grid(row=i, column=0, sticky="ew", pady=1)
                valores = [(info["nome"] or "-", 240),
                           (info["serie"] or "-", 80),
                           (info["curso"] or "-", 220),
                           (info.get("hora", "") or "-", 120),
                           (info.get("aula", "Fora do horário"), 110)]
                n = len(valores)
                for j, (val, w) in enumerate(valores):
                    cor_t = "#2E7D32" if j == 0 else "#374151"
                    fonte = ("Segoe UI", 11, "bold") if j == 0 else ("Segoe UI", 11)
                    ctk.CTkLabel(linha, text=val, font=fonte,
                                  width=w, anchor="w", text_color=cor_t
                                  ).pack(side="left", expand=(j == n-1), fill="x", padx=6, pady=6)

            # Rodapé de paginação
            total_pags = max(1, -(-len(dados) // LIMITE))
            rod = ctk.CTkFrame(corpo_tab, fg_color="transparent")
            rod.grid(row=LIMITE + 1, column=0, sticky="ew", pady=(6, 2))
            ctk.CTkLabel(rod, text=f"Exibindo {inicio+1}–{min(inicio+LIMITE, len(dados))} de {len(dados)}",
                          font=("Segoe UI", 10), text_color=TEXTO_CINZA).pack(side="left", padx=4)
            if pag > 0:
                ctk.CTkButton(rod, text="← Anterior", width=90, height=26,
                               fg_color=VERDE_VIBRANTE, hover_color=VERDE_ESCURO,
                               font=("Segoe UI", 10, "bold"),
                               command=lambda: [_estado_pag_freq.update({"pagina": pag - 1}),
                                                _renderizar_pagina_freq()]
                               ).pack(side="left", padx=4)
            if inicio + LIMITE < len(dados):
                ctk.CTkButton(rod, text="Ver mais →", width=90, height=26,
                               fg_color=VERDE_VIBRANTE, hover_color=VERDE_ESCURO,
                               font=("Segoe UI", 10, "bold"),
                               command=lambda: [_estado_pag_freq.update({"pagina": pag + 1}),
                                                _renderizar_pagina_freq()]
                               ).pack(side="left", padx=4)

        _renderizar_pagina_freq()

    # ── Filtro por sala rápida ────────────────────────────────────────────
    def _filtrar_por_sigla(sigla):
        info = SIGLAS[sigla]
        cb_serie.set(info["serie"])
        cb_curso.set(info["curso"])
        ent_nome.delete(0, "end")
        for s, b in btn_sala_refs.items():
            b.configure(fg_color=CORES_ANO[s[0]], text_color="white")
        btn_sala_refs[sigla].configure(fg_color="white", text_color=CORES_ANO[sigla[0]])
        atualizar_freq()

    for sigla, label in SIGLAS_LABEL.items():
        ano = sigla[0]
        cor = CORES_ANO[ano]
        b = ctk.CTkButton(sala_row, text=label, font=("Segoe UI", 9, "bold"),
                           fg_color=cor, hover_color=VERDE_ESCURO,
                           text_color="white", width=64, height=26,
                           command=lambda s=sigla: _filtrar_por_sigla(s))
        b.pack(side="left", padx=2)
        btn_sala_refs[sigla] = b

    # ── Limpar filtros ────────────────────────────────────────────────────
    def limpar_filtros():
        cb_serie.set("(Todas)")
        cb_curso.set("(Todos)")
        ent_nome.delete(0, "end")
        for sigla, b in btn_sala_refs.items():
            b.configure(fg_color=CORES_ANO[sigla[0]], text_color="white")
        atualizar_freq()

    ctk.CTkButton(filtro_row, text="✕ Limpar", font=("Segoe UI", 10, "bold"),
                   fg_color="transparent", hover_color="#F0F0F0",
                   text_color=VERDE_VIBRANTE, width=80, height=30,
                   command=limpar_filtros).pack(side="left")

    # ── Ver ausentes (janela secundária CTk) ─────────────────────────────
    def abrir_ausentes():
        lista_todos = _estado["lista_todos"]
        presentes = set(_estado["alunos_unicos"].keys())
        ausentes = [al for al in lista_todos if al.get("matricula", "") not in presentes]

        _sel_aus = {"selecionado": None, "linha_widgets": {}}

        win = ctk.CTkToplevel(page)
        win.title("Alunos Ausentes Hoje")
        win.geometry("760x560")
        win.configure(fg_color=CINZA_BG)

        ctk.CTkLabel(win, text="👥  Alunos Ausentes Hoje",
                      font=("Segoe UI", 16, "bold"), text_color=TEXTO_ESCURO
                      ).pack(anchor="w", padx=20, pady=(16, 4))

        filt = ctk.CTkFrame(win, fg_color="transparent")
        filt.pack(fill="x", padx=20, pady=(0, 8))
        ctk.CTkLabel(filt, text="Série:", font=("Segoe UI", 11, "bold"),
                      text_color=TEXTO_ESCURO).pack(side="left", padx=(0, 6))
        cb_serie_aus = ctk.CTkOptionMenu(filt, values=["(Todas)", "1 Ano", "2 Ano", "3 Ano"],
                                          width=100, fg_color=VERDE_VIBRANTE,
                                          button_color=VERDE_ESCURO, button_hover_color=VERDE_ESCURO)
        cb_serie_aus.set("(Todas)")
        cb_serie_aus.pack(side="left", padx=(0, 14))

        ctk.CTkLabel(filt, text="Curso:", font=("Segoe UI", 11, "bold"),
                      text_color=TEXTO_ESCURO).pack(side="left", padx=(0, 6))
        cb_curso_aus = ctk.CTkOptionMenu(filt, values=["(Todos)", "Desenvolvimento de Sistemas",
                                                        "Hospedagem", "Enfermagem", "Modelagem do Vestuario"],
                                          width=200, fg_color=VERDE_VIBRANTE,
                                          button_color=VERDE_ESCURO, button_hover_color=VERDE_ESCURO)
        cb_curso_aus.set("(Todos)")
        cb_curso_aus.pack(side="left")

        lista_card = ctk.CTkFrame(win, fg_color=BRANCO, corner_radius=12)
        lista_card.pack(fill="both", expand=True, padx=20, pady=(0, 8))
        lista_card.grid_rowconfigure(1, weight=1)
        lista_card.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(lista_card, fg_color=VERDE_ESCURO, corner_radius=6)
        hdr.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 0))
        ctk.CTkLabel(hdr, text="Nome", font=("Segoe UI", 10, "bold"),
                      text_color="white", width=280, anchor="w").pack(side="left", padx=6, pady=8)
        ctk.CTkLabel(hdr, text="Série", font=("Segoe UI", 10, "bold"),
                      text_color="white", width=100, anchor="w").pack(side="left", padx=6, pady=8)
        ctk.CTkLabel(hdr, text="Curso", font=("Segoe UI", 10, "bold"),
                      text_color="white", anchor="w").pack(side="left", expand=True, fill="x", padx=6, pady=8)

        corpo_aus = ctk.CTkFrame(lista_card, fg_color="transparent")
        corpo_aus.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 14))
        corpo_aus.grid_columnconfigure(0, weight=1)

        lbl_cnt_aus = ctk.CTkLabel(win, text="", font=("Segoe UI", 10), text_color=TEXTO_CINZA)
        lbl_cnt_aus.pack(anchor="w", padx=20, pady=(0, 4))

        lbl_sel_aus = ctk.CTkLabel(win, text="Nenhum aluno selecionado.",
                                     font=("Segoe UI", 10, "bold"), text_color=VERDE_ESCURO)
        lbl_sel_aus.pack(anchor="w", padx=20, pady=(0, 8))

        def _selecionar_aus(al):
            _sel_aus["selecionado"] = al
            mat_sel = al.get("matricula", "")
            for mat, (frame, bg_original) in _sel_aus["linha_widgets"].items():
                frame.configure(fg_color=(bg_original if mat != mat_sel else "#E8F5E9"))
            lbl_sel_aus.configure(text=f"Selecionado: {al.get('nome', '-')}")
            btn_presenca.pack(side="left")

        def _preencher():
            _sel_aus["selecionado"] = None
            _sel_aus["linha_widgets"] = {}
            lbl_sel_aus.configure(text="Nenhum aluno selecionado.")
            btn_presenca.pack_forget()
            for w in corpo_aus.winfo_children():
                w.destroy()
            f_serie = cb_serie_aus.get()
            f_curso = cb_curso_aus.get()
            exibidos = []
            for al in ausentes:
                if not _serie_bate(al.get("serie", ""), f_serie): continue
                if not _curso_bate(al.get("curso", ""), f_curso): continue
                exibidos.append(al)

            lbl_cnt_aus.configure(text=f"{len(exibidos)} ausente(s) de {len(lista_todos)} cadastrado(s)")

            if not exibidos:
                ctk.CTkLabel(corpo_aus, text="Nenhum ausente encontrado.",
                              font=("Segoe UI", 12), text_color=TEXTO_CINZA
                              ).grid(row=0, column=0, pady=24)
                return

            for i, al in enumerate(sorted(exibidos, key=lambda a: a.get("nome", "").lower())):
                bg = BRANCO if i % 2 == 0 else "#F8F9FA"
                linha = ctk.CTkFrame(corpo_aus, fg_color=bg, corner_radius=4, cursor="hand2")
                linha.grid(row=i, column=0, sticky="ew", pady=1)

                lbl_n = ctk.CTkLabel(linha, text=al.get("nome", "-"), font=("Segoe UI", 11),
                              width=280, anchor="w", text_color="#C62828")
                lbl_n.pack(side="left", padx=6, pady=6)
                lbl_s = ctk.CTkLabel(linha, text=al.get("serie", "-"), font=("Segoe UI", 11),
                              width=100, anchor="w", text_color="#374151")
                lbl_s.pack(side="left", padx=6, pady=6)
                lbl_c = ctk.CTkLabel(linha, text=al.get("curso", "-"), font=("Segoe UI", 11),
                              anchor="w", text_color="#374151")
                lbl_c.pack(side="left", expand=True, fill="x", padx=6, pady=6)

                _sel_aus["linha_widgets"][al.get("matricula", "")] = (linha, bg)

                def _bind_click_aus(widget, a=al):
                    widget.bind("<Button-1>", lambda e, _a=a: _selecionar_aus(_a))

                for w in (linha, lbl_n, lbl_s, lbl_c):
                    _bind_click_aus(w)

        def _exportar():
            try:
                nome_arq = f"ausentes_frequencia_{_hoje().replace('/', '_')}.csv"
                f_serie = cb_serie_aus.get()
                f_curso = cb_curso_aus.get()
                exibidos = [al for al in ausentes
                             if _serie_bate(al.get("serie", ""), f_serie)
                             and _curso_bate(al.get("curso", ""), f_curso)]
                with open(nome_arq, "w", newline="", encoding="utf-8") as f:
                    w = csv.writer(f)
                    w.writerow(["Nome", "Série", "Curso"])
                    for al in sorted(exibidos, key=lambda a: a.get("nome", "").lower()):
                        w.writerow([al.get("nome", ""), al.get("serie", ""), al.get("curso", "")])
                messagebox.showinfo("Sucesso", f"CSV exportado:\n{nome_arq}")
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao exportar:\n{e}")

        lbl_status_aus = ctk.CTkLabel(win, text="", font=("Segoe UI", 10), text_color=VERDE_VIBRANTE)

        def _colocar_presenca():
            sel = _sel_aus.get("selecionado")
            if not sel:
                lbl_status_aus.configure(text="⚠ Selecione um aluno na lista de ausentes.",
                                          text_color="#C62828")
                win.after(3000, lambda: lbl_status_aus.configure(text=""))
                return

            matricula = sel.get("matricula", "")
            nome = sel.get("nome", "Desconhecido")
            serie = sel.get("serie", "N/A")
            curso = sel.get("curso", "N/A")

            if not messagebox.askyesno("Confirmar", f"Marcar presença de {nome} agora?"):
                return

            try:
                if _frequencia_duplicado_db(matricula):
                    messagebox.showinfo("Aviso", f"{nome} já está marcado como presente hoje.")
                else:
                    hora = _agora_br().strftime("%H:%M:%S")
                    aula = _aula_por_hora(hora)
                    registro = [_hoje(), hora, matricula, nome, serie, curso, aula]
                    _inserir_frequencia_db(registro)
                    lbl_status_aus.configure(text=f"✔ Presença registrada: {nome}",
                                              text_color=VERDE_VIBRANTE)
                    win.after(4000, lambda: lbl_status_aus.configure(text=""))
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao registrar presença:\n{e}")
                return

            ausentes[:] = [a for a in ausentes if a.get("matricula", "") != matricula]
            _preencher()
            atualizar_freq()

        btn_row_aus = ctk.CTkFrame(win, fg_color="transparent")
        btn_row_aus.pack(anchor="w", padx=20, pady=(0, 4))
        ctk.CTkButton(btn_row_aus, text="⬇  Exportar CSV", fg_color="#1565C0",
                       hover_color="#0D47A1", font=("Segoe UI", 11, "bold"),
                       height=34, command=_exportar).pack(side="left", padx=(0, 8))

        btn_presenca = ctk.CTkButton(btn_row_aus, text="✔  Colocar Presença", fg_color=VERDE_VIBRANTE,
                                      hover_color=VERDE_ESCURO, font=("Segoe UI", 11, "bold"),
                                      height=34, command=_colocar_presenca)
        # Só aparece depois que um aluno é selecionado na lista (ver _selecionar_aus / _preencher)

        lbl_status_aus.pack(anchor="w", padx=20, pady=(0, 16))

        cb_serie_aus.configure(command=lambda _: _preencher())
        cb_curso_aus.configure(command=lambda _: _preencher())
        _preencher()

    # ── Exportar CSV ──────────────────────────────────────────────────────
    def exportar_csv_freq():
        try:
            nome_arq = f"frequencia_{_hoje().replace('/', '_')}.csv"
            _escrever_csv(
                nome_arq,
                ["Data", "HoraEntrada", "Matricula", "Nome", "Serie", "Curso", "Aula"],
                _ler_frequencia_todos_db(),
            )
            lbl_acao_status.configure(text=f"✔ Exportado: {nome_arq}", text_color=VERDE_VIBRANTE)
        except Exception as e:
            lbl_acao_status.configure(text=f"⚠ Falha ao exportar: {e}", text_color="#C62828")
        page.after(4000, lambda: lbl_acao_status.configure(text=""))

    # ── Apagar registros de hoje ──────────────────────────────────────────
    def apagar_hoje_freq():
        if not messagebox.askyesno("Confirmar", f"Apagar todos os registros de hoje ({_hoje()})?"):
            return
        try:
            _apagar_frequencia_data_db(_hoje())
            lbl_acao_status.configure(text="✔ Registros de hoje apagados.", text_color=VERDE_VIBRANTE)
        except Exception as e:
            lbl_acao_status.configure(text=f"⚠ Falha ao apagar: {e}", text_color="#C62828")
        page.after(4000, lambda: lbl_acao_status.configure(text=""))
        atualizar_freq()

    ctk.CTkButton(btn_row, text="👁  Ver Ausentes", fg_color=VERDE_VIBRANTE,
                   hover_color=VERDE_ESCURO, font=("Segoe UI", 11, "bold"),
                   height=36, width=140, command=abrir_ausentes).pack(side="left", padx=(0, 8))
    ctk.CTkButton(btn_row, text="↻  Atualizar", fg_color="#1565C0",
                   hover_color="#0D47A1", font=("Segoe UI", 11, "bold"),
                   height=36, width=130, command=atualizar_freq).pack(side="left", padx=(0, 8))
    ctk.CTkButton(btn_row, text="⬇  Exportar CSV", fg_color="#6A1B9A",
                   hover_color="#4A148C", font=("Segoe UI", 11, "bold"),
                   height=36, width=150, command=exportar_csv_freq).pack(side="left", padx=(0, 8))
    ctk.CTkButton(btn_row, text="🗑  Apagar hoje", fg_color="#C62828",
                   hover_color="#8E1010", font=("Segoe UI", 11, "bold"),
                   height=36, width=140, command=apagar_hoje_freq).pack(side="left", padx=(0, 12))
    lbl_acao_status.pack(side="left")

    # Gatilhos automáticos de filtro
    cb_serie.configure(command=lambda _: atualizar_freq())
    cb_curso.configure(command=lambda _: atualizar_freq())
    ent_nome.bind("<KeyRelease>", lambda e: atualizar_freq())

    atualizar_freq()
    iniciar_polling(page, atualizar_freq())
    return page