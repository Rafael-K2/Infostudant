"""
Aba "Histórico" do Painel Administrativo.

Extraído de abrir_painel_admin_ctk (Servidor.py) sem alterar a lógica —
inclusive a peculiaridade de que `threading.Thread(target=_thread_body, ...)`
fica no escopo de criar_pagina_historico (não dentro de buscar_historico),
exatamente como no código original.
"""
import csv
import datetime
import threading
import customtkinter as ctk
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from paineis.helpers import card_resumo


def criar_pagina_historico(_scroll_inner, cores, _agora_br,
                            _ler_frequencia_todos_db, _ler_refeitorio_todos_db):
    """Cria e retorna o frame da página "Histórico".

    Parâmetros
    ----------
    _scroll_inner : CTkFrame
        Frame pai (área rolável) onde a página é desenhada.
    cores : dict
        Constantes de cor: CINZA_BG, BRANCO, TEXTO_CINZA, TEXTO_ESCURO,
        VERDE_VIBRANTE, VERDE_ESCURO, AZUL_CLARO, ROXO_CLARO.
    _agora_br : callable
        Devolve datetime atual no fuso do Brasil.
    _ler_frequencia_todos_db, _ler_refeitorio_todos_db : callables
        Leem todos os registros do banco para montar o histórico.
    """
    CINZA_BG       = cores["CINZA_BG"]
    BRANCO         = cores["BRANCO"]
    TEXTO_CINZA    = cores["TEXTO_CINZA"]
    TEXTO_ESCURO   = cores["TEXTO_ESCURO"]
    VERDE_VIBRANTE = cores["VERDE_VIBRANTE"]
    VERDE_ESCURO   = cores["VERDE_ESCURO"]
    AZUL_CLARO     = cores["AZUL_CLARO"]
    ROXO_CLARO     = cores["ROXO_CLARO"]

    def _card_resumo(parent, row, col, icone, cor_fundo, cor_icone, titulo, valor, subtitulo):
        return card_resumo(parent, row, col, icone, cor_fundo, cor_icone, titulo, valor,
                            subtitulo, {"BRANCO": BRANCO, "TEXTO_CINZA": TEXTO_CINZA,
                                        "TEXTO_ESCURO": TEXTO_ESCURO})

    page = ctk.CTkFrame(_scroll_inner, fg_color=CINZA_BG)
    page.grid_columnconfigure(0, weight=1)

    # ── Estado ────────────────────────────────────────────────────────────
    _estado = {"tipo": "refeitorio", "periodo": "hoje", "dados_por_data": {}}

    # ── Cabeçalho ─────────────────────────────────────────────────────────
    cab = ctk.CTkFrame(page, fg_color="transparent")
    cab.grid(row=0, column=0, sticky="ew", pady=(4, 12))
    ctk.CTkLabel(cab, text="Histórico 📚",
                  font=("Segoe UI", 22, "bold"), text_color=TEXTO_ESCURO).pack(anchor="w")
    ctk.CTkLabel(cab, text="Consulte o histórico de refeições ou frequência por período.",
                  font=("Segoe UI", 12), text_color=TEXTO_CINZA).pack(anchor="w")

    # ── Card de filtros ───────────────────────────────────────────────────
    filtro_card = ctk.CTkFrame(page, fg_color=BRANCO, corner_radius=12)
    filtro_card.grid(row=1, column=0, sticky="ew", pady=(0, 12))

    # Linha 1: seletor de tipo (segmented button)
    topo_filtro = ctk.CTkFrame(filtro_card, fg_color="transparent")
    topo_filtro.pack(fill="x", padx=14, pady=(14, 8))
    ctk.CTkLabel(topo_filtro, text="Histórico de:", font=("Segoe UI", 12, "bold"),
                  text_color=TEXTO_ESCURO).pack(side="left", padx=(0, 10))

    seg_tipo = ctk.CTkSegmentedButton(topo_filtro, values=["Refeitório", "Frequência"],
                                       fg_color="#F0F0F0", selected_color=VERDE_VIBRANTE,
                                       selected_hover_color=VERDE_ESCURO,
                                       unselected_color="#F0F0F0",
                                       text_color=TEXTO_ESCURO)
    seg_tipo.set("Refeitório")
    seg_tipo.pack(side="left")

    # Linha 2: período
    periodo_row = ctk.CTkFrame(filtro_card, fg_color="transparent")
    periodo_row.pack(fill="x", padx=14, pady=(0, 8))
    ctk.CTkLabel(periodo_row, text="Período:", font=("Segoe UI", 12, "bold"),
                  text_color=TEXTO_ESCURO).pack(side="left", padx=(0, 10))

    seg_periodo = ctk.CTkSegmentedButton(periodo_row,
                                          values=["Hoje", "Esta semana", "Este mês", "Personalizado"],
                                          fg_color="#F0F0F0", selected_color="#1565C0",
                                          selected_hover_color="#0D47A1",
                                          unselected_color="#F0F0F0",
                                          text_color=TEXTO_ESCURO)
    seg_periodo.set("Hoje")
    seg_periodo.pack(side="left")

    # Linha 3: período personalizado (oculta por padrão)
    custom_row = ctk.CTkFrame(filtro_card, fg_color="transparent")

    ctk.CTkLabel(custom_row, text="De:", font=("Segoe UI", 11),
                  text_color=TEXTO_ESCURO).pack(side="left", padx=(0, 6))
    ent_data_ini = ctk.CTkEntry(custom_row, width=110, height=30, placeholder_text="01/01/2026")
    ent_data_ini.insert(0, "01/01/2026")
    ent_data_ini.pack(side="left", padx=(0, 14))

    ctk.CTkLabel(custom_row, text="Até:", font=("Segoe UI", 11),
                  text_color=TEXTO_ESCURO).pack(side="left", padx=(0, 6))
    ent_data_fim = ctk.CTkEntry(custom_row, width=110, height=30)
    ent_data_fim.insert(0, _agora_br().date().strftime("%d/%m/%Y"))
    ent_data_fim.pack(side="left")

    # Linha 4: série / curso
    serie_curso_row = ctk.CTkFrame(filtro_card, fg_color="transparent")
    serie_curso_row.pack(fill="x", padx=14, pady=(0, 14))

    ctk.CTkLabel(serie_curso_row, text="Série:", font=("Segoe UI", 11, "bold"),
                  text_color=TEXTO_ESCURO).pack(side="left", padx=(0, 6))
    cb_serie = ctk.CTkOptionMenu(serie_curso_row, values=["(Todas)", "1 Ano", "2 Ano", "3 Ano"],
                                  width=110, fg_color=VERDE_VIBRANTE,
                                  button_color=VERDE_ESCURO, button_hover_color=VERDE_ESCURO)
    cb_serie.set("(Todas)")
    cb_serie.pack(side="left", padx=(0, 14))

    ctk.CTkLabel(serie_curso_row, text="Curso:", font=("Segoe UI", 11, "bold"),
                  text_color=TEXTO_ESCURO).pack(side="left", padx=(0, 6))
    cb_curso = ctk.CTkOptionMenu(serie_curso_row,
                                  values=["(Todos)", "Desenvolvimento de Sistemas", "Hospedagem",
                                          "Enfermagem", "Modelagem do Vestuario"],
                                  width=220, fg_color=VERDE_VIBRANTE,
                                  button_color=VERDE_ESCURO, button_hover_color=VERDE_ESCURO)
    cb_curso.set("(Todos)")
    cb_curso.pack(side="left", padx=(0, 14))

    ctk.CTkButton(serie_curso_row, text="🔍  Buscar", fg_color=VERDE_VIBRANTE,
                   hover_color=VERDE_ESCURO, font=("Segoe UI", 11, "bold"),
                   height=32, width=110,
                   command=lambda: buscar_historico()).pack(side="left")

    # ── Resumo geral ──────────────────────────────────────────────────────
    resumo_row = ctk.CTkFrame(page, fg_color="transparent")
    resumo_row.grid(row=2, column=0, sticky="ew", pady=(0, 12))
    resumo_row.grid_columnconfigure((0, 1, 2), weight=1)

    lbl_total, sub_total = _card_resumo(resumo_row, 0, 0, "📋", AZUL_CLARO, "#1565C0",
                                        "Total Geral", "0", "registros")
    lbl_pos,   sub_pos   = _card_resumo(resumo_row, 0, 1, "✔️", "#E8F5E9", "#2E7D32",
                                        "Almoços / Presentes", "0", "no período")
    lbl_pct,   sub_pct   = _card_resumo(resumo_row, 0, 2, "📊", ROXO_CLARO, "#6A1B9A",
                                        "% Geral", "0%", "adesão / presença")

    # ── Gráfico ───────────────────────────────────────────────────────────
    grafico_card = ctk.CTkFrame(page, fg_color=BRANCO, corner_radius=12)
    grafico_card.grid(row=3, column=0, sticky="ew", pady=(0, 12))
    ctk.CTkLabel(grafico_card, text="Evolução diária (últimos 30 dias do período)",
                  font=("Segoe UI", 13, "bold"), text_color=TEXTO_ESCURO
                  ).pack(anchor="w", padx=18, pady=(16, 4))
    frame_graf = ctk.CTkFrame(grafico_card, fg_color="transparent")
    frame_graf.pack(fill="x", padx=18, pady=(0, 16))
    canvas_ref = {}
    _ativo_hist = {"vivo": True}

    # ── Tabela ────────────────────────────────────────────────────────────
    tabela_card = ctk.CTkFrame(page, fg_color=BRANCO, corner_radius=12)
    tabela_card.grid(row=4, column=0, sticky="ew", pady=(0, 12))

    topo_tab = ctk.CTkFrame(tabela_card, fg_color="transparent")
    topo_tab.pack(fill="x", padx=14, pady=(14, 6))
    ctk.CTkLabel(topo_tab, text="Detalhe por dia",
                  font=("Segoe UI", 13, "bold"), text_color=TEXTO_ESCURO).pack(side="left")

    header_tab = ctk.CTkFrame(tabela_card, fg_color=VERDE_ESCURO, corner_radius=6)
    header_tab.pack(fill="x", padx=14)
    col_labels = {}
    COLS = [("Data", 110), ("Total", 130), ("Almoços", 130), ("Não Almoços", 150), ("% Adesão", 110)]
    for i, (col, w) in enumerate(COLS):
        lbl = ctk.CTkLabel(header_tab, text=col, font=("Segoe UI", 10, "bold"),
                            text_color="white", width=w, anchor="w")
        lbl.pack(side="left", expand=(i == len(COLS)-1), fill="x", padx=6, pady=8)
        col_labels[col] = lbl

    corpo_tab = ctk.CTkFrame(tabela_card, fg_color="transparent")
    corpo_tab.pack(fill="x", padx=14, pady=(0, 14))

    # ── Botões inferiores ─────────────────────────────────────────────────
    btn_row = ctk.CTkFrame(page, fg_color="transparent")
    btn_row.grid(row=5, column=0, sticky="w", pady=(0, 24))
    lbl_status = ctk.CTkLabel(btn_row, text="", font=("Segoe UI", 10), text_color=VERDE_VIBRANTE)

    # ── Lógica de busca ───────────────────────────────────────────────────
    def buscar_historico():
        tipo_label = seg_tipo.get()
        eh_frequencia = (tipo_label == "Frequência")
        _estado["tipo"] = "frequencia" if eh_frequencia else "refeitorio"

        periodo_label = seg_periodo.get()
        hoje = _agora_br().date()
        if periodo_label == "Hoje":
            d_inicio = d_fim = hoje
        elif periodo_label == "Esta semana":
            d_inicio = hoje - datetime.timedelta(days=hoje.weekday())
            d_fim = hoje
        elif periodo_label == "Este mês":
            d_inicio = hoje.replace(day=1)
            d_fim = hoje
        else:
            try:
                d_inicio = datetime.datetime.strptime(ent_data_ini.get().strip(), "%d/%m/%Y").date()
                d_fim = datetime.datetime.strptime(ent_data_fim.get().strip(), "%d/%m/%Y").date()
            except Exception:
                lbl_status.configure(text="⚠ Data inválida. Use DD/MM/AAAA.", text_color="#C62828")
                return

        f_serie = cb_serie.get()
        f_curso = cb_curso.get()

        def _thread_body():
            try:
                linhas = _ler_frequencia_todos_db() if eh_frequencia else _ler_refeitorio_todos_db()
            except Exception as e:
                page.after(0, lambda: lbl_status.configure(
                    text=f"⚠ Falha ao carregar: {e}", text_color="#C62828"))
                return

            dados_por_data = {}
            for row in linhas:
                if len(row) < 7:
                    continue
                try:
                    data_obj = datetime.datetime.strptime(row[0], "%d/%m/%Y").date()
                except Exception:
                    continue
                if not (d_inicio <= data_obj <= d_fim):
                    continue

                serie = row[4] if len(row) > 4 else ""
                curso = row[5] if len(row) > 5 else ""
                if f_serie != "(Todas)" and f_serie not in serie:
                    continue
                if f_curso != "(Todos)" and f_curso not in curso:
                    continue

                if data_obj not in dados_por_data:
                    dados_por_data[data_obj] = {"total": 0, "presentes": 0,
                                                   "almocou": 0, "nao_almocou": 0}

                if eh_frequencia:
                    dados_por_data[data_obj]["presentes"] += 1
                    dados_por_data[data_obj]["total"] += 1
                else:
                    refeicao = row[6] if len(row) > 6 else ""
                    if refeicao.strip().lower() == "almoco":
                        dados_por_data[data_obj]["almocou"] += 1
                    else:
                        dados_por_data[data_obj]["nao_almocou"] += 1
                    dados_por_data[data_obj]["total"] += 1

            page.after(0, lambda: _renderizar(dados_por_data, eh_frequencia))

        def _limpar_hist(event=None):
            _ativo_hist["vivo"] = False
            if "canvas" in canvas_ref:
                try:
                    canvas_ref["canvas"].get_tk_widget().pack_forget()
                    canvas_ref["canvas"].get_tk_widget().destroy()
                except Exception:
                    pass
                try:
                    plt.close(canvas_ref.get("fig"))
                except Exception:
                    pass
                canvas_ref.clear()

        page.bind("<Destroy>", _limpar_hist)

    threading.Thread(target=_thread_body, daemon=True).start()

    def _renderizar(dados_por_data, eh_frequencia):
        if not _ativo_hist["vivo"] or not page.winfo_exists():
            return
        _estado["dados_por_data"] = dados_por_data

        if eh_frequencia:
            col_labels["Total"].configure(text="Total Alunos")
            col_labels["Almoços"].configure(text="Presentes")
            col_labels["Não Almoços"].configure(text="Ausentes")
            col_labels["% Adesão"].configure(text="% Presença")
            sub_pos.configure(text="presentes")
            sub_pct.configure(text="presença")
        else:
            col_labels["Total"].configure(text="Total Registros")
            col_labels["Almoços"].configure(text="Total Almoços")
            col_labels["Não Almoços"].configure(text="Não Almoços")
            col_labels["% Adesão"].configure(text="% Adesão")
            sub_pos.configure(text="almoços")
            sub_pct.configure(text="adesão")

        for w in corpo_tab.winfo_children():
            w.destroy()

        if not dados_por_data:
            ctk.CTkLabel(corpo_tab, text="Nenhum dado para o período selecionado.",
                          font=("Segoe UI", 12), text_color=TEXTO_CINZA).pack(pady=20)
            lbl_total.configure(text="0")
            lbl_pos.configure(text="0")
            lbl_pct.configure(text="0%")
            _renderizar_grafico({}, eh_frequencia)
            return

        total_geral = 0
        pos_geral = 0  # presentes ou almoços, dependendo do tipo

        for i, data_obj in enumerate(sorted(dados_por_data.keys(), reverse=True)):
            dados = dados_por_data[data_obj]
            data_str = data_obj.strftime("%d/%m/%Y")
            total = dados["total"]

            if eh_frequencia:
                valor_pos = dados["presentes"]
                valor_neg = total - valor_pos
            else:
                valor_pos = dados["almocou"]
                valor_neg = dados["nao_almocou"]

            pct = (valor_pos / total * 100) if total else 0
            total_geral += total
            pos_geral += valor_pos

            if pct >= 70:
                cor_pct = "#2E7D32"
            elif pct >= 40:
                cor_pct = "#E65100"
            else:
                cor_pct = "#C62828"

            bg = BRANCO if i % 2 == 0 else "#F8F9FA"
            linha = ctk.CTkFrame(corpo_tab, fg_color=bg, corner_radius=4)
            linha.pack(fill="x", pady=1)

            valores = [(data_str, 110, "#374151"), (str(total), 130, "#374151"),
                       (str(valor_pos), 130, "#2E7D32"), (str(valor_neg), 150, "#C62828"),
                       (f"{pct:.1f}%", 110, cor_pct)]
            n = len(valores)
            for j, (val, w, cor_t) in enumerate(valores):
                ctk.CTkLabel(linha, text=val, font=("Segoe UI", 11, "bold" if j == 4 else "normal"),
                              width=w, anchor="w", text_color=cor_t
                              ).pack(side="left", expand=(j == n-1), fill="x", padx=6, pady=6)

        pct_geral = (pos_geral / total_geral * 100) if total_geral else 0
        lbl_total.configure(text=str(total_geral))
        lbl_pos.configure(text=str(pos_geral))
        lbl_pct.configure(text=f"{pct_geral:.1f}%")

        _renderizar_grafico(dados_por_data, eh_frequencia)

    # ── Gráfico matplotlib ────────────────────────────────────────────────
    def _renderizar_grafico(dados_por_data, eh_frequencia):
        if not _ativo_hist["vivo"] or not page.winfo_exists():
            return
        if "canvas" in canvas_ref:
            try:
                canvas_ref["canvas"].get_tk_widget().pack_forget()
                canvas_ref["canvas"].get_tk_widget().destroy()
            except Exception:
                pass
            try:
                plt.close(canvas_ref["fig"])
            except Exception:
                pass
            del canvas_ref["canvas"]

        for w in frame_graf.winfo_children():
            w.destroy()

        if not dados_por_data:
            ctk.CTkLabel(frame_graf, text="Sem dados para exibir.",
                          font=("Segoe UI", 12), text_color=TEXTO_CINZA).pack(pady=40)
            return

        datas_ordenadas = sorted(dados_por_data.keys())[-30:]
        labels = [d.strftime("%d/%m") for d in datas_ordenadas]

        if eh_frequencia:
            valores = [dados_por_data[d]["presentes"] for d in datas_ordenadas]
            totais  = [dados_por_data[d]["total"] for d in datas_ordenadas]
            cor_label = "Presentes"
        else:
            valores = [dados_por_data[d]["almocou"] for d in datas_ordenadas]
            totais  = [dados_por_data[d]["total"] for d in datas_ordenadas]
            cor_label = "Almoços"

        cores = []
        for v, t in zip(valores, totais):
            pct = (v / t * 100) if t else 0
            if pct >= 70:
                cores.append("#4CAF50")
            elif pct >= 40:
                cores.append("#FDD835")
            else:
                cores.append("#F44336")

        fig, ax = plt.subplots(figsize=(10, 3.6))
        fig.patch.set_facecolor(BRANCO)
        ax.set_facecolor(CINZA_BG)

        bars = ax.bar(labels, valores, color=cores, edgecolor="white", linewidth=1.5)
        for b, v in zip(bars, valores):
            if v > 0:
                ax.annotate(str(v), (b.get_x() + b.get_width() / 2, b.get_height()),
                             textcoords="offset points", xytext=(0, 4),
                             ha="center", fontsize=9, color="#374151")

        ax.set_ylabel(cor_label, fontsize=10)
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", linestyle="--", alpha=0.4)
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=8)
        fig.tight_layout()

        canvas_tk = FigureCanvasTkAgg(fig, master=frame_graf)
        canvas_tk.draw()
        canvas_tk.get_tk_widget().pack(fill="x")
        canvas_ref["canvas"] = canvas_tk
        canvas_ref["fig"] = fig

    # ── Exportações ───────────────────────────────────────────────────────
    def exportar_csv_historico():
        dados = _estado["dados_por_data"]
        if not dados:
            lbl_status.configure(text="⚠ Nenhum dado para exportar.", text_color="#C62828")
            page.after(4000, lambda: lbl_status.configure(text=""))
            return
        try:
            nome_arq = f"historico_marwin_{_agora_br().strftime('%d_%m_%Y')}.csv"
            eh_frequencia = _estado["tipo"] == "frequencia"
            with open(nome_arq, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["Data", "Total", "Almocos/Presentes", "NaoAlmocos/Ausentes", "%Adesao/Presenca"])
                for data_obj in sorted(dados.keys(), reverse=True):
                    d = dados[data_obj]
                    total = d["total"]
                    if eh_frequencia:
                        pos, neg = d["presentes"], total - d["presentes"]
                    else:
                        pos, neg = d["almocou"], d["nao_almocou"]
                    pct = (pos / total * 100) if total else 0
                    w.writerow([data_obj.strftime("%d/%m/%Y"), total, pos, neg, f"{pct:.1f}%"])
            lbl_status.configure(text=f"✔ CSV gerado: {nome_arq}", text_color=VERDE_VIBRANTE)
        except Exception as e:
            lbl_status.configure(text=f"⚠ Falha: {e}", text_color="#C62828")
        page.after(4000, lambda: lbl_status.configure(text=""))

    def exportar_pdf_historico():
        dados = _estado["dados_por_data"]
        if not dados:
            lbl_status.configure(text="⚠ Nenhum dado para exportar.", text_color="#C62828")
            page.after(4000, lambda: lbl_status.configure(text=""))
            return
        try:
            from fpdf import FPDF
            eh_frequencia = _estado["tipo"] == "frequencia"
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            titulo = "HISTORICO DE FREQUENCIA" if eh_frequencia else "HISTORICO DE REFEICOES"
            pdf.cell(0, 10, f"{titulo} - EEEP MARWIN", ln=True, align="C")
            pdf.set_font("Arial", "", 12)
            pdf.cell(0, 8, f"Gerado em: {_agora_br().strftime('%d/%m/%Y %H:%M')}", ln=True)
            pdf.ln(4)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(40, 8, "Data", border=1)
            pdf.cell(40, 8, "Total", border=1)
            pdf.cell(50, 8, "Almocos/Pres.", border=1)
            pdf.cell(50, 8, "Nao Alm./Aus.", border=1)
            pdf.cell(0, 8, "% Adesao/Pres.", border=1, ln=True)
            pdf.set_font("Arial", "", 10)
            for data_obj in sorted(dados.keys(), reverse=True):
                d = dados[data_obj]
                total = d["total"]
                if eh_frequencia:
                    pos, neg = d["presentes"], total - d["presentes"]
                else:
                    pos, neg = d["almocou"], d["nao_almocou"]
                pct = (pos / total * 100) if total else 0
                pdf.cell(40, 7, data_obj.strftime("%d/%m/%Y"), border=1)
                pdf.cell(40, 7, str(total), border=1)
                pdf.cell(50, 7, str(pos), border=1)
                pdf.cell(50, 7, str(neg), border=1)
                pdf.cell(0, 7, f"{pct:.1f}%", border=1, ln=True)
            nome_arq = f"historico_marwin_{_agora_br().strftime('%d_%m_%Y')}.pdf"
            pdf.output(nome_arq)
            lbl_status.configure(text=f"✔ PDF gerado: {nome_arq}", text_color=VERDE_VIBRANTE)
        except Exception as e:
            lbl_status.configure(text=f"⚠ Falha: {e}", text_color="#C62828")
        page.after(4000, lambda: lbl_status.configure(text=""))

    ctk.CTkButton(btn_row, text="⬇  Exportar CSV", fg_color="#1565C0",
                   hover_color="#0D47A1", font=("Segoe UI", 11, "bold"),
                   height=36, width=150, command=exportar_csv_historico).pack(side="left", padx=(0, 8))
    ctk.CTkButton(btn_row, text="📄  Exportar PDF", fg_color="#6A1B9A",
                   hover_color="#4A148C", font=("Segoe UI", 11, "bold"),
                   height=36, width=150, command=exportar_pdf_historico).pack(side="left", padx=(0, 12))
    lbl_status.pack(side="left")

    # ── Mostrar/ocultar período personalizado ────────────────────────────
    def _on_periodo_change(valor):
        if valor == "Personalizado":
            custom_row.pack(fill="x", padx=14, pady=(0, 8), after=periodo_row)
        else:
            custom_row.pack_forget()
        buscar_historico()

    def _on_tipo_change(valor):
        buscar_historico()

    seg_periodo.configure(command=_on_periodo_change)
    seg_tipo.configure(command=_on_tipo_change)
    cb_serie.configure(command=lambda _: buscar_historico())
    cb_curso.configure(command=lambda _: buscar_historico())

    buscar_historico()
    return page
