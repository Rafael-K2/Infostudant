"""
Aba "Visão Geral" do Painel Administrativo.

Extraído de abrir_painel_admin_ctk (Servidor.py) sem alterar a lógica.
Versão atualizada com gráficos Donut modernos, interativos e layout repaginado.
"""
import os
import csv
import datetime
import threading
import customtkinter as ctk
from tkinter import messagebox

from paineis.helpers import card_resumo
from paineis.helpers import iniciar_polling, card_tabela


def criar_pagina_visao_geral(_scroll_inner, cores, jd, logger,
                              _agora_br, _hoje,
                              _ler_refeitorio_hoje_db, _ler_frequencia_hoje_db,
                              _ler_avaliacoes_db, ler_json,
                              EVENTOS_FILE, EVENTOS_PADRAO, DADOS_DIR,
                              _detectar_tabela_csv, _importar_csv_para_banco_forcado):
    """Cria e retorna o frame da página "Visão Geral" com design moderno e limpo."""
    CINZA_BG       = cores["CINZA_BG"]
    BRANCO         = cores["BRANCO"]
    TEXTO_CINZA    = cores["TEXTO_CINZA"]
    TEXTO_ESCURO   = cores["TEXTO_ESCURO"]
    VERDE_VIBRANTE = cores["VERDE_VIBRANTE"]
    VERDE_ESCURO   = cores["VERDE_ESCURO"]
    AZUL_CLARO     = cores["AZUL_CLARO"]
    VERDE_CLARO    = cores["VERDE_CLARO"]
    ROXO_CLARO     = cores["ROXO_CLARO"]

    def _card_resumo(parent, row, col, icone, cor_fundo, cor_icone, titulo, valor, subtitulo):
        return card_resumo(parent, row, col, icone, cor_fundo, cor_icone, titulo, valor,
                            subtitulo, {"BRANCO": BRANCO, "TEXTO_CINZA": TEXTO_CINZA,
                                        "TEXTO_ESCURO": TEXTO_ESCURO})

    page = ctk.CTkFrame(_scroll_inner, fg_color=CINZA_BG)
    page.grid_columnconfigure((0, 1, 2), weight=1, uniform="col")
    page.pack_configure(padx=24, pady=20, fill="both", expand=True)

    # ── Detecta estado do banco nas leituras iniciais ────────────────
    _db_erros = []

    try:
        refeitorio_hoje = _ler_refeitorio_hoje_db()
    except Exception as e:
        logger.error(f"Erro ao ler refeitorio do banco: {e}")
        refeitorio_hoje = []
        _db_erros.append("refeitório")

    try:
        freq_hoje = _ler_frequencia_hoje_db()
    except Exception as e:
        logger.error(f"Erro ao ler frequencia do banco: {e}")
        freq_hoje = []
        _db_erros.append("frequência")

    try:
        avaliacoes_todas = _ler_avaliacoes_db()
    except Exception as e:
        logger.error(f"Erro ao ler avaliacoes do banco: {e}")
        avaliacoes_todas = []
        _db_erros.append("avaliações")

    # ── Cabeçalho com saudação dinâmica + status do banco ───────────
    cab = ctk.CTkFrame(page, fg_color="transparent")
    cab.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 24))
    cab.grid_columnconfigure(0, weight=1)

    # Saudação dinâmica baseada no horário
    _hora = _agora_br().hour
    if _hora < 12:
        _saudacao = "Bom dia"
    elif _hora < 18:
        _saudacao = "Boa tarde"
    else:
        _saudacao = "Boa noite"

    textos = ctk.CTkFrame(cab, fg_color="transparent")
    textos.grid(row=0, column=0, sticky="w")
    ctk.CTkLabel(textos, text=f"{_saudacao}, Administrador! 👋",
                  font=("Segoe UI", 24, "bold"), text_color=TEXTO_ESCURO).pack(anchor="w")
    ctk.CTkLabel(textos, text="Aqui está um resumo em tempo real das atividades escolares hoje.",
                  font=("Segoe UI", 13), text_color=TEXTO_CINZA).pack(anchor="w")

    # Lado direito: data + tag de status do banco
    meta_right = ctk.CTkFrame(cab, fg_color="transparent")
    meta_right.grid(row=0, column=1, sticky="e")

    _db_online  = len(_db_erros) == 0
    _db_parcial = 0 < len(_db_erros) < 3

    if not _db_online:
        cor_status_bg = "#FEF2F2" if not _db_parcial else "#FFFBEB"
        cor_status_tx = "#EF4444" if not _db_parcial else "#D97706"
        txt_status    = "⚠️ Banco Parcial" if _db_parcial else "🔴 Desconectado"
        # Tooltip com detalhe das tabelas com erro
        tip_status = f"Falha em: {', '.join(_db_erros)}"
    else:
        cor_status_bg = "#F0FDF4"
        cor_status_tx = "#16A34A"
        txt_status    = "🟢 Banco Conectado"
        tip_status    = "Todas as tabelas respondendo normalmente."

    status_tag = ctk.CTkFrame(meta_right, fg_color=cor_status_bg, corner_radius=6)
    status_tag.pack(side="right", padx=(12, 0), ipady=4, ipadx=8)
    lbl_status_tag = ctk.CTkLabel(status_tag, text=txt_status,
                                   font=("Segoe UI", 11, "bold"), text_color=cor_status_tx)
    lbl_status_tag.pack()
    # Tooltip simples: mostra detalhe ao passar o mouse
    lbl_status_tag.bind("<Enter>", lambda e: lbl_status_tag.configure(text=tip_status))
    lbl_status_tag.bind("<Leave>", lambda e: lbl_status_tag.configure(text=txt_status))

    hoje_dt = _agora_br().date()
    dias_semana_pt = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira",
                       "Sexta-feira", "Sábado", "Domingo"]

    data_box = ctk.CTkFrame(meta_right, fg_color=BRANCO, corner_radius=10,
                             border_width=1, border_color="#E5E7EB")
    data_box.pack(side="right")
    ctk.CTkLabel(data_box, text="📅", font=("Segoe UI", 16)).pack(side="left", padx=(12, 6), pady=8)
    txt_data = ctk.CTkFrame(data_box, fg_color="transparent")
    txt_data.pack(side="left", padx=(0, 14), pady=6)
    ctk.CTkLabel(txt_data, text=_hoje(), font=("Segoe UI", 11, "bold"),
                  text_color=TEXTO_ESCURO).pack(anchor="w")
    ctk.CTkLabel(txt_data, text=dias_semana_pt[hoje_dt.weekday()], font=("Segoe UI", 10),
                  text_color=TEXTO_CINZA).pack(anchor="w")

    # ── Cards de métricas principais ─────────────────────────────────
    inicio_semana = hoje_dt - datetime.timedelta(days=hoje_dt.weekday())
    fim_semana    = inicio_semana + datetime.timedelta(days=6)
    avaliacoes_semana = 0
    for av in avaliacoes_todas:
        try:
            d = datetime.datetime.strptime(av["Data"], "%d/%m/%Y").date()
            if inicio_semana <= d <= fim_semana:
                avaliacoes_semana += 1
        except Exception:
            continue

    _card_resumo(page, 1, 0, "📋", VERDE_CLARO, VERDE_VIBRANTE,
                  "Refeições hoje", str(len(refeitorio_hoje)), "registros no refeitório")
    _card_resumo(page, 1, 1, "👥", AZUL_CLARO, "#2196F3",
                  "Presenças hoje", str(len(freq_hoje)), "alunos registrados")
    _card_resumo(page, 1, 2, "⭐", ROXO_CLARO, "#9C27B0",
                  "Avaliações (semana)", str(avaliacoes_semana), "respostas esta semana")

    try:
        lista_alunos_total = ler_json(os.path.join(DADOS_DIR, "lista_alunos.json"), [])
        total_alunos = len(lista_alunos_total)
    except Exception:
        total_alunos = 0

    COR_VERDE_MODERNO   = "#2ECC71"
    COR_VERMELHO_MODERNO = "#E74C3C"

    # ── Gráfico de rosca — Refeitório hoje ───────────────────────────
    entraram_ref     = len(refeitorio_hoje)
    nao_entraram_ref = max(total_alunos - entraram_ref, 0)

    rosca_ref_card = ctk.CTkFrame(page, fg_color=BRANCO, corner_radius=12,
                                   border_width=1, border_color="#E5E7EB")
    rosca_ref_card.grid(row=2, column=0, sticky="nsew", padx=(0, 8), pady=(20, 0))

    ctk.CTkLabel(rosca_ref_card, text="📥  Refeitório hoje",
                  font=("Segoe UI", 14, "bold"), text_color=TEXTO_ESCURO
                  ).pack(anchor="w", padx=18, pady=(16, 2))

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        import math

        fig_ref, ax_ref = plt.subplots(figsize=(2.8, 2.8), dpi=100, facecolor="none")
        ax_ref.set_facecolor("none")

        valores_ref = [entraram_ref, nao_entraram_ref] if (entraram_ref + nao_entraram_ref) > 0 else [1, 0]
        cores_ref   = [COR_VERDE_MODERNO, COR_VERMELHO_MODERNO]
        _hover_ref  = {"idx": -1}

        wedges_ref, _ = ax_ref.pie(
            valores_ref, colors=cores_ref, startangle=90,
            wedgeprops={"width": 0.28, "edgecolor": "none"},
        )
        lbl_centro_ref = ax_ref.text(0, 0.08, str(entraram_ref),
                                      ha="center", va="center",
                                      fontsize=24, fontweight="bold", color=COR_VERDE_MODERNO)
        lbl_sub_ref = ax_ref.text(0, -0.20, "entraram",
                                   ha="center", va="center", fontsize=10, color=TEXTO_CINZA)
        ax_ref.set_aspect("equal")
        plt.tight_layout(pad=0.2)

        canvas_ref = FigureCanvasTkAgg(fig_ref, master=rosca_ref_card)
        canvas_ref.draw()
        canvas_ref.get_tk_widget().pack(padx=8, pady=0)

        def _hover_ref_cb(event):
            if event.inaxes != ax_ref:
                if _hover_ref["idx"] != -1:
                    _hover_ref["idx"] = -1
                    for w in wedges_ref:
                        w.set_center((0, 0))
                    lbl_centro_ref.set_text(str(entraram_ref))
                    lbl_centro_ref.set_color(COR_VERDE_MODERNO)
                    lbl_sub_ref.set_text("entraram")
                    canvas_ref.draw_idle()
                return
            for i, wedge in enumerate(wedges_ref):
                if wedge.contains_point([event.x, event.y]):
                    if _hover_ref["idx"] == i:
                        return
                    _hover_ref["idx"] = i
                    for j, w in enumerate(wedges_ref):
                        ang = (w.theta1 + w.theta2) / 2
                        r = 0.06 if j == i else 0.0
                        w.set_center((r * math.cos(math.radians(ang)),
                                      r * math.sin(math.radians(ang))))
                    if i == 0:
                        lbl_centro_ref.set_text(str(entraram_ref))
                        lbl_centro_ref.set_color(COR_VERDE_MODERNO)
                        lbl_sub_ref.set_text("entraram")
                    else:
                        lbl_centro_ref.set_text(str(nao_entraram_ref))
                        lbl_centro_ref.set_color(COR_VERMELHO_MODERNO)
                        lbl_sub_ref.set_text("não entraram")
                    canvas_ref.draw_idle()
                    return

        canvas_ref.mpl_connect("motion_notify_event", _hover_ref_cb)

        leg_ref = ctk.CTkFrame(rosca_ref_card, fg_color="transparent")
        leg_ref.pack(pady=(4, 16))
        for cor, txt in [(COR_VERDE_MODERNO, f"Sim: {entraram_ref}"),
                          (COR_VERMELHO_MODERNO, f"Não: {nao_entraram_ref}")]:
            row_l = ctk.CTkFrame(leg_ref, fg_color="transparent")
            row_l.pack(side="left", padx=10)
            ctk.CTkFrame(row_l, fg_color=cor, width=10, height=10,
                          corner_radius=3).pack(side="left", padx=(0, 4))
            ctk.CTkLabel(row_l, text=txt, font=("Segoe UI", 11),
                          text_color=TEXTO_CINZA).pack(side="left")

    except Exception as e_graf:
        ctk.CTkLabel(rosca_ref_card, text=f"Gráfico indisponível:\n{e_graf}",
                      font=("Segoe UI", 10), text_color=TEXTO_CINZA).pack(padx=18, pady=24)

    # ── Gráfico de rosca — Presenças hoje ────────────────────────────
    vieram     = len(freq_hoje)
    nao_vieram = max(total_alunos - vieram, 0)

    rosca_freq_card = ctk.CTkFrame(page, fg_color=BRANCO, corner_radius=12,
                                    border_width=1, border_color="#E5E7EB")
    rosca_freq_card.grid(row=2, column=1, sticky="nsew", padx=(8, 8), pady=(20, 0))

    ctk.CTkLabel(rosca_freq_card, text="👥  Presenças hoje",
                  font=("Segoe UI", 14, "bold"), text_color=TEXTO_ESCURO
                  ).pack(anchor="w", padx=18, pady=(16, 2))

    try:
        fig_freq, ax_freq = plt.subplots(figsize=(2.8, 2.8), dpi=100, facecolor="none")
        ax_freq.set_facecolor("none")

        valores_freq = [vieram, nao_vieram] if (vieram + nao_vieram) > 0 else [1, 0]
        cores_freq   = [COR_VERDE_MODERNO, COR_VERMELHO_MODERNO]
        _hover_freq  = {"idx": -1}

        wedges_freq, _ = ax_freq.pie(
            valores_freq, colors=cores_freq, startangle=90,
            wedgeprops={"width": 0.28, "edgecolor": "none"},
        )
        lbl_centro_freq = ax_freq.text(0, 0.08, str(vieram),
                                        ha="center", va="center",
                                        fontsize=24, fontweight="bold", color=COR_VERDE_MODERNO)
        lbl_sub_freq = ax_freq.text(0, -0.20, "vieram",
                                     ha="center", va="center", fontsize=10, color=TEXTO_CINZA)
        ax_freq.set_aspect("equal")
        plt.tight_layout(pad=0.2)

        canvas_freq = FigureCanvasTkAgg(fig_freq, master=rosca_freq_card)
        canvas_freq.draw()
        canvas_freq.get_tk_widget().pack(padx=8, pady=0)

        def _hover_freq_cb(event):
            if event.inaxes != ax_freq:
                if _hover_freq["idx"] != -1:
                    _hover_freq["idx"] = -1
                    for w in wedges_freq:
                        w.set_center((0, 0))
                    lbl_centro_freq.set_text(str(vieram))
                    lbl_centro_freq.set_color(COR_VERDE_MODERNO)
                    lbl_sub_freq.set_text("vieram")
                    canvas_freq.draw_idle()
                return
            for i, wedge in enumerate(wedges_freq):
                if wedge.contains_point([event.x, event.y]):
                    if _hover_freq["idx"] == i:
                        return
                    _hover_freq["idx"] = i
                    for j, w in enumerate(wedges_freq):
                        ang = (w.theta1 + w.theta2) / 2
                        r = 0.06 if j == i else 0.0
                        w.set_center((r * math.cos(math.radians(ang)),
                                      r * math.sin(math.radians(ang))))
                    if i == 0:
                        lbl_centro_freq.set_text(str(vieram))
                        lbl_centro_freq.set_color(COR_VERDE_MODERNO)
                        lbl_sub_freq.set_text("vieram")
                    else:
                        lbl_centro_freq.set_text(str(nao_vieram))
                        lbl_centro_freq.set_color(COR_VERMELHO_MODERNO)
                        lbl_sub_freq.set_text("não vieram")
                    canvas_freq.draw_idle()
                    return

        canvas_freq.mpl_connect("motion_notify_event", _hover_freq_cb)

        leg_frame = ctk.CTkFrame(rosca_freq_card, fg_color="transparent")
        leg_frame.pack(pady=(4, 16))
        for cor, txt in [(COR_VERDE_MODERNO, f"Sim: {vieram}"),
                          (COR_VERMELHO_MODERNO, f"Não: {nao_vieram}")]:
            row_l = ctk.CTkFrame(leg_frame, fg_color="transparent")
            row_l.pack(side="left", padx=10)
            ctk.CTkFrame(row_l, fg_color=cor, width=10, height=10,
                          corner_radius=3).pack(side="left", padx=(0, 4))
            ctk.CTkLabel(row_l, text=txt, font=("Segoe UI", 11),
                          text_color=TEXTO_CINZA).pack(side="left")

    except Exception as e_graf2:
        ctk.CTkLabel(rosca_freq_card, text=f"Gráfico indisponível:\n{e_graf2}",
                      font=("Segoe UI", 10), text_color=TEXTO_CINZA).pack(padx=18, pady=24)


    # ── Calendário Escolar ────────────────────────────────────────────
    import calendar as _calendar

    cal_card = ctk.CTkFrame(page, fg_color=BRANCO, corner_radius=12,
                             border_width=1, border_color="#E5E7EB")
    cal_card.grid(row=2, column=2, rowspan=2, sticky="nsew", padx=(8, 0), pady=(20, 0))
    cal_card.grid_columnconfigure(0, weight=1)

    MESES_PT = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
                "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
    DIAS_PT  = ["SEG","TER","QUA","QUI","SEX","SÁB","DOM"]

    _estado_cal = {"ano": hoje_dt.year, "mes": hoje_dt.month}

    nav_frame = ctk.CTkFrame(cal_card, fg_color="transparent")
    nav_frame.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 8))
    nav_frame.grid_columnconfigure(1, weight=1)

    ctk.CTkLabel(nav_frame, text="📅  Calendário Escolar",
                  font=("Segoe UI", 14, "bold"), text_color=TEXTO_ESCURO
                  ).grid(row=0, column=0, sticky="w")
    lbl_mes_ano = ctk.CTkLabel(nav_frame, text="",
                                font=("Segoe UI", 13, "bold"), text_color=VERDE_VIBRANTE)
    lbl_mes_ano.grid(row=0, column=1)

    btn_nav_frame = ctk.CTkFrame(nav_frame, fg_color="transparent")
    btn_nav_frame.grid(row=0, column=2, sticky="e")
    ctk.CTkButton(btn_nav_frame, text="❮", width=32, height=28,
                   fg_color=VERDE_VIBRANTE, hover_color=VERDE_ESCURO,
                   font=("Segoe UI", 11, "bold"),
                   command=lambda: _navegar(-1)).pack(side="left", padx=(0, 4))
    ctk.CTkButton(btn_nav_frame, text="❯", width=32, height=28,
                   fg_color=VERDE_VIBRANTE, hover_color=VERDE_ESCURO,
                   font=("Segoe UI", 11, "bold"),
                   command=lambda: _navegar(1)).pack(side="left")

    grade_cal = ctk.CTkFrame(cal_card, fg_color="transparent")
    grade_cal.grid(row=1, column=0, sticky="ew", padx=18, pady=(4, 0))
    for c in range(7):
        grade_cal.grid_columnconfigure(c, weight=1)

    detalhe_frame = ctk.CTkFrame(cal_card, fg_color="#F0FFF4", corner_radius=8,
                                  border_width=1, border_color="#DCFCE7")
    detalhe_frame.grid(row=2, column=0, sticky="ew", padx=18, pady=(12, 16))
    lbl_detalhe = ctk.CTkLabel(detalhe_frame,
                                text="Clique em um dia destacado para ver os eventos agendados.",
                                font=("Segoe UI", 11), text_color=TEXTO_CINZA,
                                wraplength=900, justify="left")
    lbl_detalhe.pack(anchor="w", padx=14, pady=10)

    def _eventos_do_mes(ano, mes):
        try:
            evs = ler_json(EVENTOS_FILE, EVENTOS_PADRAO)
        except Exception:
            evs = []
        mapa = {}
        for ev in evs:
            try:
                d, m = ev["data"].split("/")
                d, m = int(d), int(m)
                if m == mes:
                    mapa.setdefault(d, []).append(ev["evento"])
            except Exception:
                continue
        return mapa

    def _renderizar_mes():
        for w in grade_cal.winfo_children():
            w.destroy()

        ano = _estado_cal["ano"]
        mes = _estado_cal["mes"]
        lbl_mes_ano.configure(text=MESES_PT[mes - 1].upper() + f"  {ano}")

        for c, d in enumerate(DIAS_PT):
            ctk.CTkLabel(grade_cal, text=d, font=("Segoe UI", 10, "bold"),
                          text_color=VERDE_VIBRANTE if d in ("SÁB", "DOM") else TEXTO_CINZA,
                          width=50).grid(row=0, column=c, pady=(0, 6))

        mapa_evs = _eventos_do_mes(ano, mes)
        hoje_local = datetime.date.today()

        for r, semana in enumerate(_calendar.monthcalendar(ano, mes)):
            for c, dia in enumerate(semana):
                if dia == 0:
                    ctk.CTkLabel(grade_cal, text="", width=50, height=36
                                  ).grid(row=r + 1, column=c, padx=2, pady=2)
                    continue

                tem_evento = dia in mapa_evs
                eh_hoje    = (dia == hoje_local.day and mes == hoje_local.month and ano == hoje_local.year)

                if tem_evento:
                    fg = VERDE_VIBRANTE; txt = "white"
                elif eh_hoje:
                    fg = "#E8F5E9"; txt = VERDE_VIBRANTE
                else:
                    fg = "transparent"; txt = TEXTO_ESCURO

                btn = ctk.CTkButton(
                    grade_cal,
                    text=str(dia) + ("\n·" if tem_evento else ""),
                    width=48, height=38,
                    fg_color=fg,
                    hover_color="#A5D6A7" if tem_evento else "#F3F4F6",
                    text_color=txt,
                    font=("Segoe UI", 11, "bold" if (tem_evento or eh_hoje) else "normal"),
                    corner_radius=6,
                    border_width=1 if eh_hoje else 0,
                    border_color=VERDE_VIBRANTE if eh_hoje else None,
                    command=lambda d=dia, ev=mapa_evs.get(dia, []): _mostrar_evento(d, ev),
                )
                btn.grid(row=r + 1, column=c, padx=3, pady=3)

    def _mostrar_evento(dia, descricoes):
        if not descricoes:
            lbl_detalhe.configure(text="Nenhum evento neste dia.", text_color=TEXTO_CINZA)
            return
        mes_nome = MESES_PT[_estado_cal["mes"] - 1]
        txt = f"📅  {dia:02d} DE {mes_nome.upper()}\n" + "\n".join(f"✨ {d}" for d in descricoes)
        lbl_detalhe.configure(text=txt, text_color=TEXTO_ESCURO)

    def _navegar(delta):
        mes = _estado_cal["mes"] + delta
        ano = _estado_cal["ano"]
        if mes > 12: mes, ano = 1, ano + 1
        elif mes < 1: mes, ano = 12, ano - 1
        _estado_cal["mes"] = mes
        _estado_cal["ano"] = ano
        lbl_detalhe.configure(
            text="Clique em um dia destacado para ver os eventos agendados.",
            text_color=TEXTO_CINZA)
        _renderizar_mes()

    _renderizar_mes()

    # ── Importação de CSV ─────────────────────────────────────────────
    def _dialogo_mapeamento_manual(nome_arquivo, colunas_csv):
        resultado = {"tabela": None}
        dlg = ctk.CTkToplevel(jd)
        dlg.title("Mapeamento manual de tabela")
        dlg.configure(fg_color=BRANCO)
        dlg.transient(jd)
        dlg.grab_set()
        dlg.resizable(False, False)
        dlg.geometry("440x320")

        ctk.CTkLabel(dlg, text="Tabela de destino não reconhecida",
                      font=("Segoe UI", 14, "bold"), text_color=VERDE_VIBRANTE
                      ).pack(padx=20, pady=(20, 4))
        ctk.CTkLabel(dlg, text=f"Arquivo: {nome_arquivo}",
                      font=("Segoe UI", 10, "italic"), text_color=TEXTO_CINZA
                      ).pack(padx=20)
        ctk.CTkLabel(dlg, text=f"Colunas detectadas: {', '.join(colunas_csv)}",
                      font=("Segoe UI", 9), text_color=TEXTO_ESCURO,
                      wraplength=400, justify="left").pack(padx=20, pady=(4, 12))
        ctk.CTkLabel(dlg, text="Selecione a tabela de destino para esta importação:",
                      font=("Segoe UI", 10), text_color=TEXTO_ESCURO).pack(padx=20, pady=(0, 8))

        tabela_var = ctk.StringVar(value="")
        opcoes = [
            ("refeitorio", "Refeitório  (Data, HoraEntrada, Matricula, Nome, Serie, Curso, Refeicao)"),
            ("frequencia", "Frequência  (Data, HoraEntrada, Matricula, Nome, Serie, Curso, Aula)"),
            ("avaliacoes", "Avaliações  (Data, Aluno, Serie, Curso, Estagio, Item, Nota)"),
        ]
        for val, texto in opcoes:
            ctk.CTkRadioButton(dlg, text=texto, variable=tabela_var, value=val,
                                font=("Segoe UI", 10), fg_color=VERDE_VIBRANTE,
                                hover_color=VERDE_ESCURO, wraplength=380
                                ).pack(anchor="w", padx=30, pady=4)

        def _confirmar():
            if not tabela_var.get():
                messagebox.showwarning("Aviso", "Selecione uma tabela de destino.", parent=dlg)
                return
            resultado["tabela"] = tabela_var.get()
            dlg.destroy()

        btn_r = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_r.pack(pady=(16, 16))
        ctk.CTkButton(btn_r, text="Cancelar", command=dlg.destroy,
                       fg_color="#6B7280", hover_color="#4B5563",
                       font=("Segoe UI", 11, "bold")).pack(side="left", padx=6)
        ctk.CTkButton(btn_r, text="Importar", command=_confirmar,
                       fg_color=VERDE_VIBRANTE, hover_color=VERDE_ESCURO,
                       font=("Segoe UI", 11, "bold")).pack(side="left", padx=6)

        dlg.wait_window()
        return resultado["tabela"]

    import_card = ctk.CTkFrame(page, fg_color=BRANCO, corner_radius=12,
                                border_width=1, border_color="#E5E7EB")
    import_card.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(20, 16))

    ctk.CTkLabel(import_card, text="💾  Importar CSV(s) para o banco de dados",
                  font=("Segoe UI", 14, "bold"), text_color=TEXTO_ESCURO
                  ).pack(anchor="w", padx=18, pady=(16, 2))
    ctk.CTkLabel(import_card,
                  text="Selecione arquivos de relatórios CSV para sincronizar ou restaurar os dados ausentes no servidor.",
                  font=("Segoe UI", 11), text_color=TEXTO_CINZA).pack(anchor="w", padx=18, pady=(0, 14))

    linha_import = ctk.CTkFrame(import_card, fg_color="transparent")
    linha_import.pack(fill="x", padx=18, pady=(0, 16))

    var_ignorar_dup = ctk.BooleanVar(value=True)
    ctk.CTkCheckBox(linha_import, text="Ignorar registros duplicados",
                     variable=var_ignorar_dup, fg_color=VERDE_VIBRANTE,
                     hover_color=VERDE_ESCURO, font=("Segoe UI", 11)
                     ).pack(side="left", padx=(0, 20))

    prog_import = ctk.CTkProgressBar(linha_import, width=200)
    prog_import.set(0)

    lbl_import_status = ctk.CTkLabel(import_card, text="", font=("Segoe UI", 10),
                                      text_color=TEXTO_CINZA, wraplength=1000, justify="left")

    def _selecionar_e_importar():
        from tkinter import filedialog
        pasta_backups = os.path.join(DADOS_DIR, "backups")
        inicial = pasta_backups if os.path.isdir(pasta_backups) else DADOS_DIR
        caminhos = filedialog.askopenfilenames(
            parent=jd,
            title="Selecionar CSV(s) para importar",
            initialdir=inicial,
            filetypes=[("Arquivos CSV", "*.csv"), ("Todos os arquivos", "*.*")],
        )
        if not caminhos:
            return

        tarefas = []
        for caminho in caminhos:
            nome_arq = os.path.basename(caminho)
            try:
                with open(caminho, "r", encoding="utf-8") as f:
                    primeiras = list(csv.DictReader(f))
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao ler {nome_arq}:\n{e}")
                continue
            if not primeiras:
                continue
            colunas_csv = list(primeiras[0].keys())
            tabela = _detectar_tabela_csv(colunas_csv)
            if tabela is None:
                tabela = _dialogo_mapeamento_manual(nome_arq, colunas_csv)
                if tabela is None:
                    continue
            tarefas.append((caminho, tabela))

        if not tarefas:
            return

        ignorar_dup    = var_ignorar_dup.get()
        total_arquivos = len(tarefas)

        btn_import.configure(state="disabled")
        prog_import.set(0)
        prog_import.pack(side="left", padx=(0, 12))
        lbl_import_status.configure(text="Iniciando processamento...")
        lbl_import_status.pack(anchor="w", padx=18, pady=(0, 12))

        def _thread_body():
            resumo_total = {"inseridos": 0, "ignorados": 0, "erros": 0}
            detalhes = []

            for idx_arq, (caminho, tabela) in enumerate(tarefas, 1):
                nome_arq = os.path.basename(caminho)

                def _progresso(atual, total, _a=idx_arq, _t=total_arquivos, _nome=nome_arq):
                    frac = (_a - 1 + atual / max(total, 1)) / _t
                    page.after(0, lambda: (
                        prog_import.set(frac),
                        lbl_import_status.configure(
                            text=f"[{_a}/{_t}] {_nome} — {atual}/{total}")
                    ))

                try:
                    resultado = _importar_csv_para_banco_forcado(caminho, tabela, ignorar_dup, _progresso)
                except Exception as e_imp:
                    resumo_total["erros"] += 1
                    detalhes.append(f"❌ {nome_arq}: {e_imp}")
                    continue

                resumo_total["inseridos"] += resultado["inseridos"]
                resumo_total["ignorados"] += resultado["ignorados"]
                resumo_total["erros"]     += resultado["erros"]
                detalhes.append(
                    f"✅ {nome_arq} → {resultado['tabela']}: "
                    f"{resultado['inseridos']} inserido(s), "
                    f"{resultado['ignorados']} ignorado(s), "
                    f"{resultado['erros']} erro(s)."
                )

            def _finalizar():
                prog_import.set(1)
                btn_import.configure(state="normal")
                lbl_import_status.configure(text="Sincronização realizada.")
                msg = (
                    f"Processo Concluído!\n\n"
                    f"✅ Inseridos: {resumo_total['inseridos']}\n"
                    f"⏭ Ignorados: {resumo_total['ignorados']}\n"
                    f"❌ Erros: {resumo_total['erros']}\n\n"
                    + "\n".join(detalhes)
                )
                messagebox.showinfo("Resultado da Importação", msg)
                page.after(2000, lambda: (prog_import.pack_forget(),
                                           lbl_import_status.pack_forget()))

            page.after(0, _finalizar)

        threading.Thread(target=_thread_body, daemon=True).start()

    btn_import = ctk.CTkButton(linha_import, text="📂  Localizar Arquivo CSV",
                                fg_color=VERDE_VIBRANTE, hover_color=VERDE_ESCURO,
                                font=("Segoe UI", 11, "bold"), height=32,
                                command=_selecionar_e_importar)
    btn_import.pack(side="left")

    iniciar_polling(page, _renderizar_mes)
    return page