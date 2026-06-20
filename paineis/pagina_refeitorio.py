"""
Aba "Refeitório" do Painel Administrativo.

Extraído de abrir_painel_admin_ctk (Servidor.py) sem alterar a lógica.
"""
import unicodedata as _ud
import threading
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox

from paineis.helpers import card_resumo


def criar_pagina_refeitorio(_scroll_inner, cores, _hoje,
                             _registros_hoje, _aula_por_hora, _escrever_csv,
                             _apagar_refeitorio_data_db, _ler_refeitorio_todos_db):
    """Cria e retorna o frame da página "Refeitório".

    Parâmetros
    ----------
    _scroll_inner : CTkFrame
        Frame pai (área rolável) onde a página é desenhada.
    cores : dict
        Constantes de cor: CINZA_BG, BRANCO, TEXTO_CINZA, TEXTO_ESCURO,
        VERDE_VIBRANTE, VERDE_ESCURO, VERDE_CLARO, ROXO_CLARO.
    _hoje : callable
        Devolve a data de hoje formatada (dd/mm/aaaa).
    _registros_hoje : callable
        Lê do banco os registros de refeitório de hoje.
    _aula_por_hora : callable
        Deduz a aula/turno a partir do horário de entrada.
    _escrever_csv : callable
        Escreve um arquivo CSV utilitário.
    _apagar_refeitorio_data_db : callable
        Apaga os registros de refeitório de uma data específica.
    _ler_refeitorio_todos_db : callable
        Lê todos os registros de refeitório (usado na exportação CSV).
    """
    CINZA_BG       = cores["CINZA_BG"]
    BRANCO         = cores["BRANCO"]
    TEXTO_CINZA    = cores["TEXTO_CINZA"]
    TEXTO_ESCURO   = cores["TEXTO_ESCURO"]
    VERDE_VIBRANTE = cores["VERDE_VIBRANTE"]
    VERDE_ESCURO   = cores["VERDE_ESCURO"]
    VERDE_CLARO    = cores["VERDE_CLARO"]
    ROXO_CLARO     = cores["ROXO_CLARO"]

    def _card_resumo(parent, row, col, icone, cor_fundo, cor_icone, titulo, valor, subtitulo):
        return card_resumo(parent, row, col, icone, cor_fundo, cor_icone, titulo, valor,
                            subtitulo, {"BRANCO": BRANCO, "TEXTO_CINZA": TEXTO_CINZA,
                                        "TEXTO_ESCURO": TEXTO_ESCURO})

    page = ctk.CTkFrame(_scroll_inner, fg_color=CINZA_BG)
    page.grid_columnconfigure(0, weight=1)
    page.grid_rowconfigure(4, weight=1)

    # ── Mapas de siglas / cursos / normalização (mesma lógica do painel antigo) ──
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
    ctk.CTkLabel(cab, text="Refeitório 🍽️",
                  font=("Segoe UI", 22, "bold"), text_color=TEXTO_ESCURO).pack(anchor="w")
    ctk.CTkLabel(cab, text=f"Controle de refeições — hoje ({_hoje()})",
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
    cards_row.grid_columnconfigure((0, 1, 2, 3), weight=1)

    lbl_total, sub_total = _card_resumo(cards_row, 0, 0, "👥", VERDE_CLARO, VERDE_VIBRANTE,
                                        "Total Filtrado", "0", "alunos")
    lbl_sim,   sub_sim   = _card_resumo(cards_row, 0, 1, "✔️", "#E8F5E9", "#2E7D32",
                                        "Almoçaram", "0", "confirmados")
    lbl_nao,   sub_nao   = _card_resumo(cards_row, 0, 2, "✘", "#FFEBEE", "#C62828",
                                        "Não Almoçaram", "0", "pendentes")
    lbl_pct,   sub_pct   = _card_resumo(cards_row, 0, 3, "📊", ROXO_CLARO, "#6A1B9A",
                                        "Adesão", "0%", "geral hoje")

    # ── Linha: gráfico de rosca + tabela ────────────────────────────────────
    meio_row = ctk.CTkFrame(page, fg_color="transparent")
    meio_row.grid(row=3, column=0, sticky="ew", pady=(0, 12))
    meio_row.grid_columnconfigure(0, weight=0)
    meio_row.grid_columnconfigure(1, weight=1)

    # Donut
    donut_card = ctk.CTkFrame(meio_row, fg_color=BRANCO, corner_radius=12, width=260)
    donut_card.grid(row=0, column=0, sticky="ns", padx=(0, 12))
    donut_card.grid_propagate(False)
    ctk.CTkLabel(donut_card, text="Adesão Geral",
                  font=("Segoe UI", 13, "bold"), text_color=TEXTO_ESCURO).pack(pady=(16, 4))

    cv_donut = tk.Canvas(donut_card, bg=BRANCO, highlightthickness=0, height=180)
    cv_donut.pack(fill="x", padx=20, pady=(4, 8))

    legenda_donut = ctk.CTkFrame(donut_card, fg_color="transparent")
    legenda_donut.pack(pady=(0, 16))

    # Tabela de alunos
    tabela_card = ctk.CTkFrame(meio_row, fg_color=BRANCO, corner_radius=12)
    tabela_card.grid(row=0, column=1, sticky="nsew")
    tabela_card.grid_rowconfigure(2, weight=1)
    tabela_card.grid_columnconfigure(0, weight=1)

    topo_tab = ctk.CTkFrame(tabela_card, fg_color="transparent")
    topo_tab.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 6))
    ctk.CTkLabel(topo_tab, text="Alunos — hoje",
                  font=("Segoe UI", 13, "bold"), text_color=TEXTO_ESCURO).pack(side="left")
    lbl_filtro_ativo = ctk.CTkLabel(topo_tab, text="", font=("Segoe UI", 9),
                                     text_color=TEXTO_CINZA)
    lbl_filtro_ativo.pack(side="right")

    header_tab = ctk.CTkFrame(tabela_card, fg_color=VERDE_ESCURO, corner_radius=6)
    header_tab.grid(row=1, column=0, sticky="ew", padx=14)
    COLS = [("Aluno", 220), ("Série", 80), ("Curso", 200), ("Almoço", 90), ("Aula", 110)]
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
    btn_row.grid(row=4, column=0, sticky="sw", pady=(0, 4))

    lbl_acao_status = ctk.CTkLabel(btn_row, text="", font=("Segoe UI", 10),
                                    text_color=VERDE_VIBRANTE)

    # ── Função de desenho do donut ───────────────────────────────────────
    def _desenhar_donut(sim, nao):
        cv_donut.delete("all")
        cv_donut.update_idletasks()
        w = cv_donut.winfo_width() or 220
        h = cv_donut.winfo_height() or 180
        cx, cy = w / 2, h / 2
        r_ext, r_int = min(w, h) / 2 - 10, (min(w, h) / 2 - 10) * 0.55

        total = sim + nao
        if total == 0:
            cv_donut.create_oval(cx - r_ext, cy - r_ext, cx + r_ext, cy + r_ext,
                                  fill="#F0F0F0", outline="")
            cv_donut.create_oval(cx - r_int, cy - r_int, cx + r_int, cy + r_int,
                                  fill=BRANCO, outline="")
            cv_donut.create_text(cx, cy, text="Sem\ndados", font=("Segoe UI", 11),
                                  fill=TEXTO_CINZA)
            return

        angulo = 90
        for valor, cor in [(sim, "#4CAF50"), (nao, "#F44336")]:
            if valor <= 0:
                continue
            ext_ang = -(valor / total) * 360
            cv_donut.create_arc(cx - r_ext, cy - r_ext, cx + r_ext, cy + r_ext,
                                 start=angulo, extent=ext_ang,
                                 fill=cor, outline=BRANCO, width=2, style="pieslice")
            angulo += ext_ang

        cv_donut.create_oval(cx - r_int, cy - r_int, cx + r_int, cy + r_int,
                              fill=BRANCO, outline="")
        pct = (sim / total * 100) if total else 0
        cv_donut.create_text(cx, cy - 8, text=f"{pct:.0f}%",
                              font=("Segoe UI", 16, "bold"), fill="#2E7D32")
        cv_donut.create_text(cx, cy + 12, text="almoçaram",
                              font=("Segoe UI", 8), fill=TEXTO_CINZA)

    def _atualizar_legenda(sim, nao):
        for w in legenda_donut.winfo_children():
            w.destroy()
        total = sim + nao
        for label_l, val_l, cor_l in [("Almoçaram", sim, "#4CAF50"), ("Não almoçaram", nao, "#F44336")]:
            pct_l = (val_l / total * 100) if total else 0
            row_l = ctk.CTkFrame(legenda_donut, fg_color="transparent")
            row_l.pack(fill="x", pady=1, padx=4)
            ctk.CTkFrame(row_l, fg_color=cor_l, width=12, height=12, corner_radius=2).pack(side="left", padx=(0, 6))
            ctk.CTkLabel(row_l, text=label_l, font=("Segoe UI", 10),
                          text_color=TEXTO_ESCURO).pack(side="left")
            ctk.CTkLabel(row_l, text=f"{val_l} ({pct_l:.0f}%)", font=("Segoe UI", 10, "bold"),
                          text_color=TEXTO_CINZA).pack(side="right")

    # ── Atualização principal ────────────────────────────────────────────
    def atualizar_ref():
        f_serie = cb_serie.get()
        f_curso = cb_curso.get()
        f_nome = ent_nome.get().strip().lower()

        def _thread_body():
            registros = _registros_hoje()
            page.after(0, lambda: _renderizar(registros, f_serie, f_curso, f_nome))

        threading.Thread(target=_thread_body, daemon=True).start()

    def _renderizar(registros, f_serie, f_curso, f_nome):
        alunos = {}
        for r in registros:
            mat   = r[2]
            nome  = r[3]
            serie = r[4] if len(r) > 4 else ""
            curso = r[5] if len(r) > 5 else ""
            ref   = r[6].strip().lower() if len(r) > 6 else ""
            hora  = r[1] if len(r) > 1 else ""
            if mat not in alunos:
                aula = _aula_por_hora(hora)
                alunos[mat] = {"nome": nome, "serie": serie, "curso": curso,
                               "almoca": False, "hora": hora, "aula": aula}
            else:
                if hora and alunos[mat].get("hora", "") and hora < alunos[mat]["hora"]:
                    alunos[mat]["hora"] = hora
                    alunos[mat]["aula"] = _aula_por_hora(hora)
            if ref == "almoco":
                alunos[mat]["almoca"] = True

        exibidos = []
        for info in alunos.values():
            if not _serie_bate(info["serie"], f_serie): continue
            if not _curso_bate(info["curso"], f_curso): continue
            if f_nome and f_nome not in info["nome"].lower(): continue
            exibidos.append(info)

        cnt_total = len(exibidos)
        cnt_sim = sum(1 for a in exibidos if a["almoca"])
        cnt_nao = cnt_total - cnt_sim
        pct = (cnt_sim / cnt_total * 100) if cnt_total else 0

        lbl_total.configure(text=str(cnt_total))
        lbl_sim.configure(text=str(cnt_sim))
        lbl_nao.configure(text=str(cnt_nao))
        lbl_pct.configure(text=f"{pct:.0f}%")

        partes_filtro = []
        if f_serie not in ("(Todas)", ""): partes_filtro.append(f_serie)
        if f_curso not in ("(Todos)", ""): partes_filtro.append(f_curso)
        if f_nome: partes_filtro.append(f'"{f_nome}"')
        lbl_filtro_ativo.configure(
            text=("Filtro: " + " | ".join(partes_filtro)) if partes_filtro else "")

        _desenhar_donut(cnt_sim, cnt_nao)
        _atualizar_legenda(cnt_sim, cnt_nao)

        # Tabela
        for w in corpo_tab.winfo_children():
            w.destroy()

        if not exibidos:
            ctk.CTkLabel(corpo_tab, text="Nenhum registro encontrado.",
                          font=("Segoe UI", 12), text_color=TEXTO_CINZA
                          ).grid(row=0, column=0, pady=24)
            return

        for i, info in enumerate(sorted(exibidos, key=lambda a: a["nome"].lower())):
            bg = BRANCO if i % 2 == 0 else "#F8F9FA"
            cor_status = "#2E7D32" if info["almoca"] else "#C62828"
            texto_status = "✔ Sim" if info["almoca"] else "✘ Não"

            linha = ctk.CTkFrame(corpo_tab, fg_color=bg, corner_radius=4)
            linha.grid(row=i, column=0, sticky="ew", pady=1)

            valores = [(info["nome"] or "-", 220, "#374151"),
                       (info["serie"] or "-", 80, "#374151"),
                       (info["curso"] or "-", 200, "#374151"),
                       (texto_status, 90, cor_status),
                       (info.get("aula", "Fora do horário"), 110, "#374151")]
            n = len(valores)
            for j, (val, w, cor_t) in enumerate(valores):
                ctk.CTkLabel(linha, text=val, font=("Segoe UI", 11),
                              width=w, anchor="w", text_color=cor_t
                              ).pack(side="left", expand=(j == n-1), fill="x", padx=6, pady=6)

    # ── Filtro por sala rápida ────────────────────────────────────────────
    def _filtrar_por_sigla(sigla):
        info = SIGLAS[sigla]
        cb_serie.set(info["serie"])
        cb_curso.set(info["curso"])
        ent_nome.delete(0, "end")
        for s, b in btn_sala_refs.items():
            b.configure(fg_color=CORES_ANO[s[0]], text_color="white")
        btn_sala_refs[sigla].configure(fg_color="white", text_color=CORES_ANO[sigla[0]])
        atualizar_ref()

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
        atualizar_ref()

    ctk.CTkButton(filtro_row, text="✕ Limpar", font=("Segoe UI", 10, "bold"),
                   fg_color="transparent", hover_color="#F0F0F0",
                   text_color=VERDE_VIBRANTE, width=80, height=30,
                   command=limpar_filtros).pack(side="left")

    # ── Exportar CSV ──────────────────────────────────────────────────────
    def exportar_csv_ref():
        try:
            nome_arq = f"refeitorio_{_hoje().replace('/', '_')}.csv"
            _escrever_csv(
                nome_arq,
                ["Data", "HoraEntrada", "Matricula", "Nome", "Serie", "Curso", "Refeicao"],
                _ler_refeitorio_todos_db(),
            )
            lbl_acao_status.configure(text=f"✔ Exportado: {nome_arq}", text_color=VERDE_VIBRANTE)
        except Exception as e:
            lbl_acao_status.configure(text=f"⚠ Falha ao exportar: {e}", text_color="#C62828")
        page.after(4000, lambda: lbl_acao_status.configure(text=""))

    # ── Apagar registros de hoje ──────────────────────────────────────────
    def apagar_hoje():
        if not messagebox.askyesno("Confirmar", f"Apagar todos os registros de hoje ({_hoje()})?"):
            return
        try:
            _apagar_refeitorio_data_db(_hoje())
            lbl_acao_status.configure(text="✔ Registros de hoje apagados.", text_color=VERDE_VIBRANTE)
        except Exception as e:
            lbl_acao_status.configure(text=f"⚠ Falha ao apagar: {e}", text_color="#C62828")
        page.after(4000, lambda: lbl_acao_status.configure(text=""))
        atualizar_ref()

    ctk.CTkButton(btn_row, text="↻  Atualizar", fg_color=VERDE_VIBRANTE,
                   hover_color=VERDE_ESCURO, font=("Segoe UI", 11, "bold"),
                   height=36, width=130, command=atualizar_ref).pack(side="left", padx=(0, 8))
    ctk.CTkButton(btn_row, text="⬇  Exportar CSV", fg_color="#1565C0",
                   hover_color="#0D47A1", font=("Segoe UI", 11, "bold"),
                   height=36, width=150, command=exportar_csv_ref).pack(side="left", padx=(0, 8))
    ctk.CTkButton(btn_row, text="🗑  Apagar hoje", fg_color="#C62828",
                   hover_color="#8E1010", font=("Segoe UI", 11, "bold"),
                   height=36, width=140, command=apagar_hoje).pack(side="left", padx=(0, 12))
    lbl_acao_status.pack(side="left")

    # Gatilhos automáticos de filtro
    cb_serie.configure(command=lambda _: atualizar_ref())
    cb_curso.configure(command=lambda _: atualizar_ref())
    ent_nome.bind("<KeyRelease>", lambda e: atualizar_ref())

    # Carrega na primeira abertura
    page.after(150, atualizar_ref)
    cv_donut.bind("<Configure>", lambda e: atualizar_ref())

    return page
