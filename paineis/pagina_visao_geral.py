"""
Aba "Visão Geral" do Painel Administrativo.

Extraído de abrir_painel_admin_ctk (Servidor.py) sem alterar a lógica.
"""
import os
import csv
import datetime
import threading
import customtkinter as ctk
from tkinter import messagebox

from paineis.helpers import card_resumo, card_tabela


def criar_pagina_visao_geral(_scroll_inner, cores, jd, logger,
                              _agora_br, _hoje,
                              _ler_refeitorio_hoje_db, _ler_frequencia_hoje_db,
                              _ler_avaliacoes_db, ler_json,
                              EVENTOS_FILE, EVENTOS_PADRAO, DADOS_DIR,
                              _detectar_tabela_csv, _importar_csv_para_banco_forcado):
    """Cria e retorna o frame da página "Visão Geral".

    Parâmetros
    ----------
    _scroll_inner : CTkFrame
        Frame pai (área rolável) onde a página é desenhada.
    cores : dict
        Constantes de cor: CINZA_BG, BRANCO, TEXTO_CINZA, TEXTO_ESCURO,
        VERDE_VIBRANTE, VERDE_ESCURO, AZUL_CLARO, VERDE_CLARO, ROXO_CLARO.
    jd : CTkToplevel
        Janela do painel admin (usada nos diálogos modais).
    logger : Logger
        Logger usado para registrar falhas de leitura do banco.
    _agora_br, _hoje : callables
        Data/hora atual no fuso do Brasil.
    _ler_refeitorio_hoje_db, _ler_frequencia_hoje_db, _ler_avaliacoes_db : callables
        Leitura de registros do banco.
    ler_json : callable
        Leitura de JSON utilitária.
    EVENTOS_FILE, EVENTOS_PADRAO : str, list
        Caminho e estrutura padrão de eventos.json.
    DADOS_DIR : str
        Pasta base de dados (usada para localizar a pasta de backups).
    _detectar_tabela_csv, _importar_csv_para_banco_forcado : callables
        Lógica de importação de CSV usada no card "Importar CSV(s)".
    """
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

    def _card_tabela(parent, titulo, colunas, linhas, rodape="", larguras=None):
        return card_tabela(parent, titulo, colunas, linhas,
                            {"BRANCO": BRANCO, "TEXTO_ESCURO": TEXTO_ESCURO,
                             "VERDE_ESCURO": VERDE_ESCURO, "TEXTO_CINZA": TEXTO_CINZA},
                            rodape=rodape, larguras=larguras)

    page = ctk.CTkFrame(_scroll_inner, fg_color=CINZA_BG)
    page.grid_columnconfigure((0, 1, 2), weight=1)

    # Cabeçalho com data de hoje
    cab = ctk.CTkFrame(page, fg_color="transparent")
    cab.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 16))
    cab.grid_columnconfigure(0, weight=1)

    textos = ctk.CTkFrame(cab, fg_color="transparent")
    textos.grid(row=0, column=0, sticky="w")
    ctk.CTkLabel(textos, text="Bom dia, Administrador! 👋",
                  font=("Segoe UI", 22, "bold"), text_color=TEXTO_ESCURO).pack(anchor="w")
    ctk.CTkLabel(textos, text="Aqui está um resumo das atividades de hoje.",
                  font=("Segoe UI", 12), text_color=TEXTO_CINZA).pack(anchor="w")

    hoje_dt = _agora_br().date()
    dias_semana_pt = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira",
                        "Sexta-feira", "Sábado", "Domingo"]
    data_box = ctk.CTkFrame(cab, fg_color=BRANCO, corner_radius=10)
    data_box.grid(row=0, column=1, sticky="e", padx=4)
    ctk.CTkLabel(data_box, text="📅", font=("Segoe UI", 18)).pack(side="left", padx=(14, 6), pady=10)
    txt_data = ctk.CTkFrame(data_box, fg_color="transparent")
    txt_data.pack(side="left", padx=(0, 16), pady=8)
    ctk.CTkLabel(txt_data, text=_hoje(), font=("Segoe UI", 12, "bold"),
                  text_color=TEXTO_ESCURO).pack(anchor="w")
    ctk.CTkLabel(txt_data, text=dias_semana_pt[hoje_dt.weekday()], font=("Segoe UI", 10),
                  text_color=TEXTO_CINZA).pack(anchor="w")

    # ── Cards de resumo ──────────────────────────────────────────
    try:
        refeitorio_hoje = _ler_refeitorio_hoje_db()
    except Exception as e:
        logger.error(f"Erro ao ler refeitorio do banco: {e}")
        refeitorio_hoje = []

    try:
        freq_hoje = _ler_frequencia_hoje_db()
    except Exception as e:
        logger.error(f"Erro ao ler frequencia do banco: {e}")
        freq_hoje = []

    try:
        avaliacoes_todas = _ler_avaliacoes_db()
    except Exception as e:
        logger.error(f"Erro ao ler avaliacoes do banco: {e}")
        avaliacoes_todas = []

    # Conta avaliações da semana atual (segunda a domingo)
    inicio_semana = hoje_dt - datetime.timedelta(days=hoje_dt.weekday())
    fim_semana = inicio_semana + datetime.timedelta(days=6)
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

    # ── Últimas entradas no refeitório ─────────────────────────────
    ultimas_refeicoes = refeitorio_hoje[-5:][::-1]  # 5 mais recentes
    linhas_ref = [
        (r[1], r[3], r[4], r[5], r[6])  # hora, nome, serie, curso, refeicao
        for r in ultimas_refeicoes
    ]
    tabela1 = _card_tabela(page, "📥  Últimas entradas no refeitório hoje",
                             ["HORA", "NOME", "SÉRIE", "CURSO", "REFEIÇÃO"],
                             linhas_ref, rodape=f"Total: {len(refeitorio_hoje)} registros")
    tabela1.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=(0, 8), pady=(8, 0))

    # ── Últimas presenças registradas hoje ──────────────────────────
    ultimas_presencas = freq_hoje[-5:][::-1]
    linhas_freq = [
        (f[1], f[3], f[4], f[5], f[6])  # hora, nome, serie, curso, aula
        for f in ultimas_presencas
    ]
    tabela2 = _card_tabela(page, "👥  Últimas presenças registradas hoje",
                             ["HORA", "NOME", "SÉRIE", "CURSO", "AULA"],
                             linhas_freq, rodape=f"Total: {len(freq_hoje)} registros")
    tabela2.grid(row=2, column=2, columnspan=1, sticky="nsew", padx=(8, 0), pady=(8, 0))

    # ── Eventos cadastrados ───────────────────────────────────────
    try:
        eventos = ler_json(EVENTOS_FILE, EVENTOS_PADRAO)
    except Exception:
        eventos = []
    linhas_eventos = [(ev.get("data", ""), ev.get("evento", "")) for ev in eventos]
    tabela_eventos = _card_tabela(page, "📅  Eventos cadastrados",
                                     ["DATA", "EVENTO"], linhas_eventos, larguras={0: 80})
    tabela_eventos.grid(row=3, column=0, columnspan=3, sticky="nsew", pady=(16, 0))

    # ── Importar CSV(s) para o banco de dados ──────────────────────
    def _dialogo_mapeamento_manual(nome_arquivo, colunas_csv):
        """Pede ao usuário a tabela de destino quando a detecção automática falha.
        Retorna 'refeitorio', 'frequencia', 'avaliacoes' ou None (cancelado)."""
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

        def _cancelar():
            dlg.destroy()

        btn_r = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_r.pack(pady=(16, 16))
        ctk.CTkButton(btn_r, text="Cancelar", command=_cancelar,
                       fg_color="#6B7280", hover_color="#4B5563",
                       font=("Segoe UI", 11, "bold")).pack(side="left", padx=6)
        ctk.CTkButton(btn_r, text="Importar", command=_confirmar,
                       fg_color=VERDE_VIBRANTE, hover_color=VERDE_ESCURO,
                       font=("Segoe UI", 11, "bold")).pack(side="left", padx=6)

        dlg.wait_window()
        return resultado["tabela"]

    import_card = ctk.CTkFrame(page, fg_color=BRANCO, corner_radius=12)
    import_card.grid(row=4, column=0, columnspan=3, sticky="nsew", pady=(16, 0))

    ctk.CTkLabel(import_card, text="💾  Importar CSV(s) para o banco de dados",
                  font=("Segoe UI", 13, "bold"), text_color=TEXTO_ESCURO
                  ).pack(anchor="w", padx=18, pady=(16, 4))
    ctk.CTkLabel(import_card,
                  text="Selecione um ou mais arquivos CSV (refeitório, frequência ou avaliações) "
                       "para importar/restaurar no banco. A tabela de destino é detectada "
                       "automaticamente pelas colunas do arquivo; se não for reconhecida, "
                       "você poderá escolher manualmente.",
                  font=("Segoe UI", 11), text_color=TEXTO_CINZA,
                  wraplength=1000, justify="left").pack(anchor="w", padx=18, pady=(0, 10))

    linha_import = ctk.CTkFrame(import_card, fg_color="transparent")
    linha_import.pack(fill="x", padx=18, pady=(0, 6))

    var_ignorar_dup = ctk.BooleanVar(value=True)
    ctk.CTkCheckBox(linha_import, text="Ignorar duplicatas (recomendado)",
                      variable=var_ignorar_dup, fg_color=VERDE_VIBRANTE,
                      hover_color=VERDE_ESCURO, font=("Segoe UI", 11)
                      ).pack(side="left", padx=(0, 16))

    prog_import = ctk.CTkProgressBar(linha_import, width=240)
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

        # Pré-leitura e detecção da tabela de cada arquivo (rápido, local)
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

        ignorar_dup = var_ignorar_dup.get()
        total_arquivos = len(tarefas)

        btn_import.configure(state="disabled")
        prog_import.set(0)
        prog_import.pack(side="left", padx=(0, 12))
        lbl_import_status.configure(text="Iniciando importação...")
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
                        lbl_import_status.configure(text=f"[{_a}/{_t}] {_nome} — {atual}/{total}")
                    ))

                try:
                    resultado = _importar_csv_para_banco_forcado(caminho, tabela, ignorar_dup, _progresso)
                except Exception as e_imp:
                    resumo_total["erros"] += 1
                    detalhes.append(f"❌ {nome_arq}: {e_imp}")
                    continue

                resumo_total["inseridos"] += resultado["inseridos"]
                resumo_total["ignorados"] += resultado["ignorados"]
                resumo_total["erros"] += resultado["erros"]
                detalhes.append(
                    f"✅ {nome_arq} → {resultado['tabela']}: "
                    f"{resultado['inseridos']} inserido(s), "
                    f"{resultado['ignorados']} ignorado(s), "
                    f"{resultado['erros']} erro(s)."
                )

            def _finalizar():
                prog_import.set(1)
                btn_import.configure(state="normal")
                lbl_import_status.configure(text="Importação concluída.")
                msg = (
                    f"Importação concluída!\n\n"
                    f"✅ Inseridos: {resumo_total['inseridos']}\n"
                    f"⏭ Ignorados: {resumo_total['ignorados']}\n"
                    f"❌ Erros: {resumo_total['erros']}\n\n"
                    + "\n".join(detalhes)
                )
                messagebox.showinfo("Resumo da importação", msg)
                page.after(2500, lambda: (prog_import.pack_forget(), lbl_import_status.pack_forget()))

            page.after(0, _finalizar)

        threading.Thread(target=_thread_body, daemon=True).start()

    btn_import = ctk.CTkButton(linha_import, text="📂  Selecionar CSV(s) e importar para o banco",
                                 fg_color=VERDE_VIBRANTE, hover_color=VERDE_ESCURO,
                                 font=("Segoe UI", 11, "bold"), height=34,
                                 command=_selecionar_e_importar)
    btn_import.pack(side="left")

    ctk.CTkFrame(import_card, fg_color="transparent", height=8).pack()

    return page
