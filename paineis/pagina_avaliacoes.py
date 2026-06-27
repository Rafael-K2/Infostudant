"""
Aba "Avaliações" do Painel Administrativo.

Extraído de abrir_painel_admin_ctk (Servidor.py) sem alterar a lógica.
"""
import threading
import customtkinter as ctk
from tkinter import messagebox

from paineis.helpers import card_resumo
from paineis.helpers import iniciar_polling


def criar_pagina_avaliacoes(_scroll_inner, cores, ler_json, salvar_json,
                             _sync_nuvem, _avaliacoes_para_linhas, _agora_br,
                             _apagar_avaliacoes_db, CONFIG_FILE):
    """Cria e retorna o frame da página "Avaliações".

    Parâmetros
    ----------
    _scroll_inner : CTkFrame
        Frame pai (área rolável) onde a página é desenhada.
    cores : dict
        Constantes de cor: CINZA_BG, BRANCO, TEXTO_CINZA, TEXTO_ESCURO,
        VERDE_VIBRANTE, VERDE_ESCURO, AZUL_CLARO, VERDE_CLARO, VERMELHO_CLARO.
    ler_json, salvar_json : callables
        Funções utilitárias de leitura/escrita de JSON.
    _sync_nuvem : callable
        Função de sincronização com a API na nuvem.
    _avaliacoes_para_linhas : callable
        Lê as avaliações do banco e devolve uma lista de linhas (tuplas).
    _agora_br : callable
        Devolve datetime atual no fuso do Brasil.
    _apagar_avaliacoes_db : callable
        Apaga todas as avaliações do banco.
    CONFIG_FILE : str
        Caminho do arquivo config_sistema.json.
    """
    CINZA_BG       = cores["CINZA_BG"]
    BRANCO         = cores["BRANCO"]
    TEXTO_CINZA    = cores["TEXTO_CINZA"]
    TEXTO_ESCURO   = cores["TEXTO_ESCURO"]
    VERDE_VIBRANTE = cores["VERDE_VIBRANTE"]
    VERDE_ESCURO   = cores["VERDE_ESCURO"]
    AZUL_CLARO     = cores["AZUL_CLARO"]
    VERDE_CLARO    = cores["VERDE_CLARO"]
    VERMELHO_CLARO = cores["VERMELHO_CLARO"]

    def _card_resumo(parent, row, col, icone, cor_fundo, cor_icone, titulo, valor, subtitulo):
        return card_resumo(parent, row, col, icone, cor_fundo, cor_icone, titulo, valor,
                            subtitulo, {"BRANCO": BRANCO, "TEXTO_CINZA": TEXTO_CINZA,
                                        "TEXTO_ESCURO": TEXTO_ESCURO})

    page = ctk.CTkFrame(_scroll_inner, fg_color=CINZA_BG)
    page.grid_columnconfigure(0, weight=1)
    page.grid_rowconfigure(3, weight=1)

    # Título
    bloco = ctk.CTkFrame(page, fg_color="transparent")
    bloco.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 12))
    ctk.CTkLabel(bloco, text="📋  Avaliações", font=("Segoe UI", 20, "bold"),
                  text_color=TEXTO_ESCURO).pack(anchor="w")
    ctk.CTkLabel(bloco, text="Acompanhe e filtre as avaliações dos alunos.",
                  font=("Segoe UI", 12), text_color=TEXTO_CINZA).pack(anchor="w")

    # ── Card de filtros ────────────────────────────────────────────
    filtros_card = ctk.CTkFrame(page, fg_color=BRANCO, corner_radius=12)
    filtros_card.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 12))

    linha1 = ctk.CTkFrame(filtros_card, fg_color="transparent")
    linha1.pack(fill="x", padx=18, pady=(18, 6))

    def _campo(parent, label, widget_cls, **kwargs):
        blk = ctk.CTkFrame(parent, fg_color="transparent")
        blk.pack(side="left", padx=(0, 16))
        ctk.CTkLabel(blk, text=label, font=("Segoe UI", 11),
                      text_color=TEXTO_CINZA).pack(anchor="w")
        w = widget_cls(blk, width=170, height=34, **kwargs)
        w.pack(anchor="w", pady=(4, 0))
        return w

    ent_nome = _campo(linha1, "Nome", ctk.CTkEntry, placeholder_text="Buscar por nome...")
    ent_data = _campo(linha1, "Data (dd/mm/aaaa)", ctk.CTkEntry, placeholder_text="dd/mm/aaaa")

    combo_est = _campo(linha1, "Estágio", ctk.CTkComboBox,
                          values=["Todos", "Comida", "Limpeza", "Ensino", "Semana"])
    combo_est.set("Todos")

    # ── Estatísticas (preenchidas em carregar_dados) ────────────────
    stats_frame = ctk.CTkFrame(page, fg_color="transparent")
    stats_frame.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 12))
    stats_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

    lbl_total, _ = _card_resumo(stats_frame, 0, 0, "👤", AZUL_CLARO, "#2196F3",
                                   "Alunos que avaliaram", "0", "")
    lbl_pos, sub_pos = _card_resumo(stats_frame, 0, 1, "🙂", VERDE_CLARO, "#4CAF50",
                                       "Positivas", "0", "")
    lbl_neu, sub_neu = _card_resumo(stats_frame, 0, 2, "😐", "#FFF8E1", "#FBC02D",
                                       "Neutras", "0", "")
    lbl_neg, sub_neg = _card_resumo(stats_frame, 0, 3, "🙁", VERMELHO_CLARO, "#F44336",
                                       "Negativas", "0", "")

    # ── Tabela (scrollable) ──────────────────────────────────────────
    tabela_card = ctk.CTkFrame(page, fg_color=BRANCO, corner_radius=12)
    tabela_card.grid(row=3, column=0, sticky="nsew", padx=24, pady=(0, 8))
    tabela_card.grid_rowconfigure(1, weight=1)
    tabela_card.grid_columnconfigure(0, weight=1)

    colunas = ["DATA", "ALUNO", "SÉRIE", "CURSO", "ESTÁGIO", "CATEGORIA", "ITEM", "RESPOSTA"]
    larguras = {0: 110, 1: 140, 2: 60, 3: 60, 4: 70, 5: 110, 6: 0, 7: 90}

    header_t = ctk.CTkFrame(tabela_card, fg_color=VERDE_ESCURO, corner_radius=6)
    header_t.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 0))
    n = len(colunas)
    for i, c in enumerate(colunas):
        ctk.CTkLabel(header_t, text=c, font=("Segoe UI", 10, "bold"),
                      text_color="white", width=larguras.get(i, 0),
                      anchor="w").pack(side="left", expand=(i == n - 1), fill="x", padx=8, pady=8)

    corpo = ctk.CTkFrame(tabela_card, fg_color="transparent")
    corpo.grid(row=1, column=0, sticky="nsew", padx=18)

    lbl_cnt = ctk.CTkLabel(tabela_card, text="0 registro(s)", font=("Segoe UI", 10),
                              text_color=TEXTO_CINZA)
    lbl_cnt.grid(row=2, column=0, sticky="w", padx=18, pady=(4, 4))

    btn_ver_mais = ctk.CTkButton(tabela_card, text="▼ Ver mais",
                                   fg_color="transparent", hover_color="#E8F5E9",
                                   text_color=VERDE_VIBRANTE, font=("Segoe UI", 11, "bold"),
                                   height=28, width=110, border_width=1,
                                   border_color=VERDE_VIBRANTE)
    btn_ver_mais.grid(row=3, column=0, sticky="w", padx=18, pady=(0, 14))
    btn_ver_mais.grid_remove()  # escondido até carregar dados
    _ativo_aval = {"vivo": True}
    page.bind("<Destroy>", lambda e: _ativo_aval.update({"vivo": False}))

    # ── Lógica ────────────────────────────────────────────────────────
    MAPA_ESTAGIO = {"Comida": "1", "Limpeza": "2", "Ensino": "3", "Semana": "4"}
    _PAGE_SIZE = 20
    # Estado da paginação — guardado entre chamadas
    _estado = {"linhas_filtradas": [], "exibindo": 0}

    def _eh_almoco_favorito(item):
        return "almoco favorito" in item.lower() or "almoço favorito" in item.lower()

    def _renderizar_linhas(linhas_vis, total_filtrado):
        """Desenha apenas as linhas recebidas no corpo da tabela."""
        for w in corpo.winfo_children():
            w.destroy()

        pos = neu = neg = 0
        for r in linhas_vis:
            if len(r) < 7:
                continue
            data, aluno, serie, curso, estagio, item, nota = r
            categoria = "Almoço favorito" if _eh_almoco_favorito(item) else "Avaliação"
            resposta = nota
            if str(estagio) == "4" and not _eh_almoco_favorito(item):
                try:
                    n_val = float(nota)
                    resposta = "Ruim" if n_val <= 1 else ("Medio" if n_val <= 3 else "Bom")
                except Exception:
                    pass
            if resposta == "Bom":   pos += 1
            elif resposta == "Medio": neu += 1
            elif resposta == "Ruim":  neg += 1

            linha_frame = ctk.CTkFrame(corpo, fg_color="transparent")
            linha_frame.pack(fill="x")
            valores = [data, aluno, serie, curso, estagio, categoria, item, resposta]
            nv = len(valores)
            for i, valor in enumerate(valores):
                ctk.CTkLabel(linha_frame, text=str(valor), font=("Segoe UI", 11),
                              width=larguras.get(i, 0), anchor="w",
                              text_color="#374151", wraplength=320 if i == 6 else 0
                              ).pack(side="left", expand=(i == nv - 1), fill="x", padx=8, pady=6)
            ctk.CTkFrame(corpo, fg_color="#F0F0F0", height=1).pack(fill="x")

        exibindo = len(linhas_vis)
        lbl_cnt.configure(text=f"{exibindo} de {total_filtrado} registro(s)")
        # Conta alunos únicos igual ao relatório semanal:
        # nomes identificados (únicos) + submissões anônimas (por data única)
        _nomes_id  = set()
        _anonimas  = set()
        for r in _estado["linhas_filtradas"]:
            if len(r) < 7:
                continue
            _data_r, _aluno_r = str(r[0]), str(r[1]).strip()
            if not _aluno_r or _aluno_r.lower() in ("", "anonimo", "anônimo"):
                _anonimas.add(_data_r)
            else:
                _nomes_id.add(_aluno_r.lower())
        alunos_unicos = len(_nomes_id) + len(_anonimas)
        lbl_total.configure(text=str(alunos_unicos))

        def _pct(v):
            return f"{(v / total_filtrado * 100):.1f}%" if total_filtrado else "0%"
        lbl_pos.configure(text=str(pos));  sub_pos.configure(text=_pct(pos))
        lbl_neu.configure(text=str(neu));  sub_neu.configure(text=_pct(neu))
        lbl_neg.configure(text=str(neg));  sub_neg.configure(text=_pct(neg))

        # Atualiza botão ver mais / ver menos
        if exibindo >= total_filtrado:
            btn_ver_mais.configure(text="▲ Ver menos", command=_ver_menos)
        else:
            btn_ver_mais.configure(text="▼ Ver mais", command=_ver_mais)
        btn_ver_mais.grid() if total_filtrado > _PAGE_SIZE else btn_ver_mais.grid_remove()

    def _ver_mais():
        _estado["exibindo"] = min(
            _estado["exibindo"] + _PAGE_SIZE, len(_estado["linhas_filtradas"])
        )
        _renderizar_linhas(
            _estado["linhas_filtradas"][: _estado["exibindo"]],
            len(_estado["linhas_filtradas"]),
        )

    def _ver_menos():
        _estado["exibindo"] = _PAGE_SIZE
        _renderizar_linhas(
            _estado["linhas_filtradas"][: _estado["exibindo"]],
            len(_estado["linhas_filtradas"]),
        )

    def carregar_dados():
        lbl_cnt.configure(text="Carregando...")

        nome_f = ent_nome.get().strip().lower()
        data_f = ent_data.get().strip()
        est_f  = combo_est.get()
        est_f  = MAPA_ESTAGIO.get(est_f) if est_f and est_f != "Todos" else None

        def _buscar():
            try:
                return _avaliacoes_para_linhas(), None
            except Exception as e:
                return None, e

        def _aplicar(linhas, erro):
            if not _ativo_aval["vivo"] or not page.winfo_exists():
                return
            if erro is not None:
                messagebox.showerror("Erro", f"Falha ao carregar avaliações do banco:\n{erro}")
                lbl_cnt.configure(text="0 registro(s)")
                return

            filtradas = []
            for r in linhas:
                if len(r) < 7:
                    continue
                data, aluno, serie, curso, estagio, item, nota = r
                if nome_f and nome_f not in str(aluno).lower():
                    continue
                if data_f and data_f not in str(data):
                    continue
                if est_f and str(estagio) != est_f:
                    continue
                filtradas.append(r)

            _estado["linhas_filtradas"] = filtradas
            _estado["exibindo"] = min(_PAGE_SIZE, len(filtradas))
            _renderizar_linhas(filtradas[: _estado["exibindo"]], len(filtradas))

        def _thread_body():
            linhas, erro = _buscar()
            corpo.after(0, lambda: _aplicar(linhas, erro))

        threading.Thread(target=_thread_body, daemon=True).start()

    # Botões Buscar / Exportar PDF
    ctk.CTkButton(linha1, text="🔍 Buscar", fg_color=VERDE_VIBRANTE, hover_color=VERDE_ESCURO,
                    width=100, height=34, font=("Segoe UI", 11, "bold"),
                    command=carregar_dados).pack(side="left", padx=(20, 4), pady=(18, 0))

    def exportar_pdf():
        def _gerar():
            try:
                reader = [["Data", "Aluno", "Serie", "Curso", "Estagio", "Item", "Nota"]] + _avaliacoes_para_linhas()
            except Exception as e:
                corpo.after(0, lambda: messagebox.showerror("Erro", f"Falha ao ler avaliações do banco:\n{e}"))
                return
            if len(reader) <= 1:
                corpo.after(0, lambda: messagebox.showwarning("Aviso", "Não há avaliações para exportar."))
                return
            try:
                from fpdf import FPDF
                pdf = FPDF()
                pdf.set_auto_page_break(True, margin=15)
                pdf.add_page()
                pdf.set_font("Arial", "B", 16)
                pdf.cell(0, 10, "AVALIACOES ESCOLARES - EEEP MARWIN", ln=True, align="C")
                pdf.set_font("Arial", "", 12)
                pdf.cell(0, 8, f"Data: {_agora_br().strftime('%d/%m/%Y %H:%M')}", ln=True)
                pdf.ln(6)
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 8, "Registros de avaliacao:", ln=True)
                pdf.ln(3)
                pdf.set_font("Arial", "", 10)
                for row in reader[1:]:
                    if len(row) < 7:
                        continue
                    pdf.multi_cell(0, 6, f"Data: {row[0]} | Aluno: {row[1]} | Serie: {row[2]} | Curso: {row[3]}")
                    pdf.multi_cell(0, 6, f"Estagio: {row[4]} | Item: {row[5]} | Nota: {row[6]}")
                    pdf.ln(2)
                nome_arq = f"avaliacoes_marwin_{_agora_br().strftime('%d_%m_%Y')}.pdf"
                pdf.output(nome_arq)
                corpo.after(0, lambda: messagebox.showinfo("Sucesso", f"PDF gerado com sucesso:\n{nome_arq}"))
            except Exception as e:
                corpo.after(0, lambda: messagebox.showerror("Erro ao exportar", f"Falha ao gerar PDF:\n{e}"))

        threading.Thread(target=_gerar, daemon=True).start()

    ctk.CTkButton(linha1, text="⭳ Exportar PDF", fg_color="#374151", hover_color="#1F2937",
                    width=130, height=34, font=("Segoe UI", 11, "bold"),
                    command=exportar_pdf).pack(side="left", padx=4, pady=(18, 0))

    # ── Linha 2: Avaliações ativas / modo de leitura / apagar tudo ───
    linha2 = ctk.CTkFrame(filtros_card, fg_color="transparent")
    linha2.pack(fill="x", padx=18, pady=(4, 18))

    cfg_sys = ler_json(CONFIG_FILE, {"avaliacoes_ativas": True, "modo_leitura": "camera"})

    var_ativas = ctk.BooleanVar(value=cfg_sys.get("avaliacoes_ativas", True))
    var_modo = ctk.StringVar(value=cfg_sys.get("modo_leitura", "camera"))

    def salvar_config():
        cfg_sys["avaliacoes_ativas"] = var_ativas.get()
        cfg_sys["modo_leitura"] = var_modo.get()
        salvar_json(CONFIG_FILE, cfg_sys)
        try:
            _sync_nuvem("/admin/config", "PUT", cfg_sys)
        except Exception:
            pass

    ctk.CTkCheckBox(linha2, text="Avaliações Ativas", variable=var_ativas,
                      fg_color=VERDE_VIBRANTE, hover_color=VERDE_ESCURO,
                      command=salvar_config).pack(side="left", padx=(0, 16))

    ctk.CTkLabel(linha2, text="Modo de leitura:", font=("Segoe UI", 11),
                  text_color=TEXTO_CINZA).pack(side="left", padx=(0, 8))
    ctk.CTkRadioButton(linha2, text="Webcam", variable=var_modo, value="camera",
                          fg_color=VERDE_VIBRANTE, command=salvar_config).pack(side="left", padx=6)
    ctk.CTkRadioButton(linha2, text="Leitor USB", variable=var_modo, value="usb",
                          fg_color=VERDE_VIBRANTE, command=salvar_config).pack(side="left", padx=6)

    def apagar_tudo():
        if messagebox.askyesno("Aviso", "Apagar todos os dados?"):
            try:
                _apagar_avaliacoes_db()
                carregar_dados()
                messagebox.showinfo("Sucesso", "Avaliações apagadas do banco.")
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao apagar avaliações:\n{e}")

    ctk.CTkButton(linha2, text="Apagar tudo", fg_color="#C62828", hover_color="#8E1F1F",
                    height=32, font=("Segoe UI", 11, "bold"),
                    command=apagar_tudo).pack(side="right")

    carregar_dados()
    iniciar_polling(page, carregar_dados())
    return page
