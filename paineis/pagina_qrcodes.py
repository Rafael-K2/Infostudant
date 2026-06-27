"""
Aba "QR Codes" do Painel Administrativo.

Extraído de abrir_painel_admin_ctk (Servidor.py) sem alterar a lógica.
"""
import os
import json
import csv
import threading
import qrcode
import customtkinter as ctk
from PIL import Image
from tkinter import messagebox


def criar_pagina_qrcodes(_scroll_inner, cores, DADOS_DIR):
    """Cria e retorna o frame da página "QR Codes".

    Parâmetros
    ----------
    _scroll_inner : CTkFrame
        Frame pai (área rolável) onde a página é desenhada.
    cores : dict
        Constantes de cor: CINZA_BG, BRANCO, TEXTO_CINZA, TEXTO_ESCURO,
        VERDE_VIBRANTE, VERDE_ESCURO.
    DADOS_DIR : str
        Pasta base de dados (onde fica lista_alunos.json).
    """
    CINZA_BG       = cores["CINZA_BG"]
    BRANCO         = cores["BRANCO"]
    TEXTO_CINZA    = cores["TEXTO_CINZA"]
    TEXTO_ESCURO   = cores["TEXTO_ESCURO"]
    VERDE_VIBRANTE = cores["VERDE_VIBRANTE"]
    VERDE_ESCURO   = cores["VERDE_ESCURO"]

    page = ctk.CTkFrame(_scroll_inner, fg_color=CINZA_BG)
    page.grid_columnconfigure(0, weight=0)
    page.grid_columnconfigure(1, weight=1)
    page.grid_columnconfigure(2, weight=0)
    page.grid_rowconfigure(1, weight=1)

    # ── Helpers / lógica reaproveitada do painel antigo ─────────────────────
    LISTA_FILE = os.path.join(DADOS_DIR, "lista_alunos.json")
    QR_DIR     = os.path.join(DADOS_DIR, "qrcodes_marwin")
    os.makedirs(QR_DIR, exist_ok=True)

    def _ler_lista():
        if os.path.exists(LISTA_FILE):
            with open(LISTA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def _salvar_lista(lista):
        with open(LISTA_FILE, "w", encoding="utf-8") as f:
            json.dump(lista, f, ensure_ascii=False, indent=2)

    def _extrair_ano_serie(serie):
        if not serie:
            return ""
        serie_strip = serie.strip()
        por_extenso = {
            "primeiro": "1", "primera": "1", "1o": "1",
            "segundo":  "2", "segunda":  "2", "2o": "2",
            "terceiro": "3", "terceira": "3", "3o": "3",
        }
        serie_lower = serie_strip.lower()
        for chave, val in por_extenso.items():
            if chave in serie_lower:
                return val
        for ch in serie_strip:
            if ch.isdigit():
                return ch
        return ""

    def _limpar_texto_pasta(texto):
        invalidos = r'\/:*?"<>|'
        resultado = ""
        for ch in str(texto):
            resultado += "_" if ch in invalidos else ch
        return resultado.strip()

    def _limpar_texto_arquivo(texto):
        return (str(texto)
                .replace(" ", "_")
                .replace("/", "_")
                .replace("\\", "_")
                .replace("º", "")
                .replace("°", "")
                .replace(":", "_")
                .replace("*", "_")
                .replace("?", "_")
                .replace('"', "_")
                .replace("<", "_")
                .replace(">", "_")
                .replace("|", "_")
                .strip("_"))

    def _pasta_turma(al):
        serie = al.get("serie", "").strip()
        curso = al.get("curso", "").strip()
        ano = _extrair_ano_serie(serie)
        nome_serie = f"{ano} Ano" if ano else "Sem Serie"
        nome_curso = _limpar_texto_pasta(curso) if curso else "Sem Curso"
        pasta = os.path.join(QR_DIR, nome_serie, nome_curso)
        os.makedirs(pasta, exist_ok=True)
        return pasta

    def _nome_arquivo(al):
        matricula = _limpar_texto_arquivo(al.get("matricula", "sem_matricula"))
        nome      = _limpar_texto_arquivo(al.get("nome",      "sem_nome"))
        serie     = _limpar_texto_arquivo(al.get("serie",     ""))
        curso     = _limpar_texto_arquivo(al.get("curso",     ""))
        partes = [matricula, nome]
        if serie: partes.append(serie)
        if curso: partes.append(curso)
        nome_arq = "_".join(partes) + ".png"
        pasta    = _pasta_turma(al)
        return os.path.join(pasta, nome_arq)

    def _gerar_png(al):
        payload = json.dumps({
            "matricula": al["matricula"],
            "nome":      al["nome"],
            "serie":     al.get("serie", ""),
            "curso":     al.get("curso", "")
        }, ensure_ascii=False)
        qr = qrcode.QRCode(
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10, border=4)
        qr.add_data(payload)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        caminho = _nome_arquivo(al)
        img.save(caminho)
        return caminho

    # ── Cabeçalho ─────────────────────────────────────────────────────────
    cab = ctk.CTkFrame(page, fg_color="transparent")
    cab.grid(row=0, column=0, columnspan=3, sticky="ew", padx=4, pady=(4, 12))
    ctk.CTkLabel(cab, text="QR Codes 🔳",
                  font=("Segoe UI", 22, "bold"), text_color=TEXTO_ESCURO).pack(anchor="w")
    ctk.CTkLabel(cab, text="Cadastre alunos e gere QR Codes individuais ou em lote.",
                  font=("Segoe UI", 12), text_color=TEXTO_CINZA).pack(anchor="w")

    # ══════════════════════════════════════════════════════════════════════
    # COLUNA ESQUERDA — Novo aluno + preview QR
    # ══════════════════════════════════════════════════════════════════════
    esq = ctk.CTkFrame(page, fg_color=BRANCO, corner_radius=12, width=300)
    esq.grid(row=1, column=0, sticky="ns", padx=(0, 12))
    esq.grid_propagate(False)

    ctk.CTkLabel(esq, text="Novo Aluno", font=("Segoe UI", 15, "bold"),
                  text_color=TEXTO_ESCURO).pack(pady=(18, 2))
    ctk.CTkFrame(esq, fg_color="#E5E7EB", height=1).pack(fill="x", padx=18, pady=(10, 12))

    campos = {}
    defs = [("Matrícula *", "matricula", "2026001"),
            ("Nome *", "nome", "Nome do Aluno"),
            ("Série (ex: 1 Ano, 2 Ano, 3 Ano)", "serie", "1 Ano"),
            ("Curso", "curso", "Desenvolvimento de Sistemas")]
    for lbl_txt, key, ph in defs:
        ctk.CTkLabel(esq, text=lbl_txt, font=("Segoe UI", 10, "bold"),
                      text_color=VERDE_VIBRANTE).pack(anchor="w", padx=18)
        e = ctk.CTkEntry(esq, font=("Segoe UI", 11), height=34,
                          placeholder_text=ph)
        e.pack(fill="x", padx=18, pady=(2, 8))
        campos[key] = e

    ctk.CTkFrame(esq, fg_color="#E5E7EB", height=1).pack(fill="x", padx=18, pady=(4, 8))

    dica_frame = ctk.CTkFrame(esq, fg_color="#F8F9FA", corner_radius=6)
    dica_frame.pack(fill="x", padx=18, pady=(0, 8))
    ctk.CTkLabel(dica_frame, text="Pasta gerada:", font=("Segoe UI", 9, "bold"),
                  text_color=VERDE_VIBRANTE).pack(anchor="w", padx=8, pady=(6, 0))
    dica_lbl = ctk.CTkLabel(dica_frame,
                             text="qrcodes_marwin/\n  1 Ano/\n    Desenvolvimento de Sistemas/",
                             font=("Courier", 9), text_color=TEXTO_CINZA, justify="left")
    dica_lbl.pack(anchor="w", padx=8, pady=(2, 6))

    def _atualizar_dica(*_):
        serie = campos["serie"].get().strip()
        curso = campos["curso"].get().strip()
        ano   = _extrair_ano_serie(serie)
        nome_s = f"{ano} Ano" if ano else "Sem Serie"
        nome_c = _limpar_texto_pasta(curso) if curso else "Sem Curso"
        dica_lbl.configure(text=f"qrcodes_marwin/\n  {nome_s}/\n    {nome_c}/")

    campos["serie"].bind("<KeyRelease>", _atualizar_dica)
    campos["curso"].bind("<KeyRelease>", _atualizar_dica)

    # Preview QR
    preview_frame = ctk.CTkFrame(esq, fg_color="#F8F9FA", corner_radius=8,
                                   width=250, height=250)
    preview_frame.pack(pady=6)
    preview_frame.pack_propagate(False)
    preview_lbl = ctk.CTkLabel(preview_frame, text="QR Code preview\nserá exibido aqui",
                                font=("Segoe UI", 10), text_color=TEXTO_CINZA)
    preview_lbl.pack(expand=True)
    _img_ref = {}

    def _preview_qr(al):
        payload = json.dumps({
            "matricula": al["matricula"], "nome": al["nome"],
            "serie": al.get("serie", ""), "curso": al.get("curso", "")
        }, ensure_ascii=False)
        qr2 = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,
                             box_size=6, border=2)
        qr2.add_data(payload); qr2.make(fit=True)
        img_pil = qr2.make_image(fill_color="black", back_color="white").convert("RGB")
        img_pil = img_pil.resize((230, 230), Image.NEAREST)
        img_ctk = ctk.CTkImage(light_image=img_pil, dark_image=img_pil, size=(230, 230))
        _img_ref["img"] = img_ctk
        preview_lbl.configure(image=img_ctk, text="")

    lbl_form_status = ctk.CTkLabel(esq, text="", font=("Segoe UI", 10),
                                    text_color=VERDE_VIBRANTE, wraplength=260, justify="center")
    lbl_form_status.pack(pady=(4, 4), padx=18)

    def _campos_para_dict():
        return {
            "matricula": campos["matricula"].get().strip(),
            "nome":      campos["nome"].get().strip(),
            "serie":     campos["serie"].get().strip(),
            "curso":     campos["curso"].get().strip(),
        }

    def adicionar_aluno():
        al = _campos_para_dict()
        if not al["matricula"] or not al["nome"]:
            lbl_form_status.configure(text="⚠ Informe Matrícula e Nome.", text_color="#C62828")
            return
        lista = _ler_lista()
        if any(a["matricula"] == al["matricula"] for a in lista):
            lbl_form_status.configure(text=f"⚠ Matrícula {al['matricula']} já cadastrada.",
                                       text_color="#C62828")
            return
        lista.append(al)
        _salvar_lista(lista)
        caminho = _gerar_png(al)
        _preview_qr(al)
        _atualizar_dica()
        carregar_lista()
        lbl_form_status.configure(text=f"✔ Aluno adicionado!\nQR salvo em:\n{caminho}",
                                   text_color=VERDE_VIBRANTE)

    def reemitir_selecionado():
        sel = _estado.get("selecionado")
        if not sel:
            lbl_form_status.configure(text="⚠ Selecione um aluno na lista.", text_color="#C62828")
            return
        lista = _ler_lista()
        al = next((a for a in lista if a["matricula"] == sel["matricula"]), None)
        if not al:
            return
        caminho = _gerar_png(al)
        _preview_qr(al)
        for key in ("matricula", "nome", "serie", "curso"):
            campos[key].delete(0, "end")
            campos[key].insert(0, al.get(key, ""))
        _atualizar_dica()
        lbl_form_status.configure(text=f"✔ QR reemitido!\nSalvo em:\n{caminho}",
                                   text_color=VERDE_VIBRANTE)

    ctk.CTkButton(esq, text="➕  Adicionar e Gerar QR", fg_color=VERDE_VIBRANTE,
                   hover_color=VERDE_ESCURO, font=("Segoe UI", 11, "bold"),
                   height=38, command=adicionar_aluno).pack(fill="x", padx=18, pady=(4, 4))
    ctk.CTkButton(esq, text="🔁  Reemitir QR Selecionado", fg_color="#1565C0",
                   hover_color="#0D47A1", font=("Segoe UI", 11, "bold"),
                   height=38, command=reemitir_selecionado).pack(fill="x", padx=18, pady=(0, 16))

    # ══════════════════════════════════════════════════════════════════════
    # COLUNA CENTRAL — Lista de alunos cadastrados
    # ══════════════════════════════════════════════════════════════════════
    mid = ctk.CTkFrame(page, fg_color=BRANCO, corner_radius=12)
    mid.grid(row=1, column=1, sticky="nsew", padx=(0, 12))
    mid.grid_rowconfigure(3, weight=1)
    mid.grid_columnconfigure(0, weight=1)

    topo_mid = ctk.CTkFrame(mid, fg_color="transparent")
    topo_mid.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 4))
    ctk.CTkLabel(topo_mid, text="Alunos Cadastrados", font=("Segoe UI", 14, "bold"),
                  text_color=TEXTO_ESCURO).pack(side="left")
    lbl_cnt = ctk.CTkLabel(topo_mid, text="", font=("Segoe UI", 10), text_color=TEXTO_CINZA)
    lbl_cnt.pack(side="left", padx=10)

    busca_row = ctk.CTkFrame(mid, fg_color="transparent")
    busca_row.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 8))
    ctk.CTkLabel(busca_row, text="Buscar:", font=("Segoe UI", 11),
                  text_color=TEXTO_ESCURO).pack(side="left", padx=(0, 6))
    ent_busca = ctk.CTkEntry(busca_row, height=32,
                              placeholder_text="Nome, matrícula, série ou curso...")
    ent_busca.pack(side="left", fill="x", expand=True)

    header_lista = ctk.CTkFrame(mid, fg_color=VERDE_ESCURO, corner_radius=6)
    header_lista.grid(row=2, column=0, sticky="ew", padx=14)
    COLS = [("QR", 50), ("Matrícula", 100), ("Nome", 220), ("Série", 110), ("Curso", 200)]
    for i, (col, w) in enumerate(COLS):
        ctk.CTkLabel(header_lista, text=col, font=("Segoe UI", 10, "bold"),
                      text_color="white", width=w, anchor="w"
                      ).pack(side="left", expand=(i == len(COLS)-1), fill="x", padx=6, pady=8)

    corpo_lista = ctk.CTkFrame(mid, fg_color="transparent")
    corpo_lista.grid(row=3, column=0, sticky="nsew", padx=14, pady=(0, 8))
    corpo_lista.grid_columnconfigure(0, weight=1)

    _estado = {"selecionado": None, "linha_widgets": {}}

    # Botões inferiores da coluna central
    btn_row_mid = ctk.CTkFrame(mid, fg_color="transparent")
    btn_row_mid.grid(row=4, column=0, sticky="ew", padx=14, pady=(0, 14))
    lbl_mid_status = ctk.CTkLabel(btn_row_mid, text="", font=("Segoe UI", 10),
                                   text_color=VERDE_VIBRANTE)

    def remover_aluno():
        sel = _estado.get("selecionado")
        if not sel:
            lbl_mid_status.configure(text="⚠ Selecione um aluno.", text_color="#C62828")
            page.after(3000, lambda: lbl_mid_status.configure(text=""))
            return
        if not messagebox.askyesno("Confirmar",
                f"Remover {sel['nome']} da lista?\n(O arquivo PNG não será apagado.)"):
            return
        lista = _ler_lista()
        lista = [a for a in lista if a["matricula"] != sel["matricula"]]
        _salvar_lista(lista)
        _estado["selecionado"] = None
        carregar_lista()

    def gerar_lote():
        lista = _ler_lista()
        if not lista:
            lbl_mid_status.configure(text="⚠ Nenhum aluno cadastrado.", text_color="#C62828")
            page.after(3000, lambda: lbl_mid_status.configure(text=""))
            return
        if not messagebox.askyesno("Confirmar",
                f"Gerar/atualizar QR Codes para {len(lista)} aluno(s)?\n\n"
                f"Estrutura de pastas:\n"
                f"  qrcodes_marwin/\n"
                f"    1 Ano/\n"
                f"      Desenvolvimento de Sistemas/\n"
                f"    2 Ano/\n"
                f"      ...\n"
                f"    3 Ano/\n"
                f"      ..."):
            return

        def _thread_body():
            erros = 0
            pastas_criadas = set()
            for al in lista:
                try:
                    _gerar_png(al)
                    pastas_criadas.add(_pasta_turma(al))
                except Exception:
                    erros += 1
            msg = (f"✔ {len(lista)-erros} QR Code(s) gerados em "
                   f"{len(pastas_criadas)} pasta(s) dentro de '{QR_DIR}/'.")
            if erros:
                msg += f" ({erros} erro(s))"
            page.after(0, lambda: (lbl_mid_status.configure(text=msg, text_color=VERDE_VIBRANTE),
                                    carregar_lista(ent_busca.get())))
            page.after(6000, lambda: lbl_mid_status.configure(text=""))

        threading.Thread(target=_thread_body, daemon=True).start()

    def abrir_pasta():
        import sys, subprocess as sp
        try:
            pasta = os.path.abspath(QR_DIR)
            if sys.platform == "win32":
                sp.Popen(["explorer", pasta])
            elif sys.platform == "darwin":
                sp.Popen(["open", pasta])
            else:
                sp.Popen(["xdg-open", pasta])
        except Exception as e:
            lbl_mid_status.configure(text=f"⚠ {e}", text_color="#C62828")
            page.after(4000, lambda: lbl_mid_status.configure(text=""))

    ctk.CTkButton(btn_row_mid, text="🗑  Remover", fg_color="#C62828",
                   hover_color="#8E1010", font=("Segoe UI", 11, "bold"),
                   height=36, width=110, command=remover_aluno).pack(side="left", padx=(0, 8))
    ctk.CTkButton(btn_row_mid, text="🔳  Gerar QRs (lote)", fg_color=VERDE_VIBRANTE,
                   hover_color=VERDE_ESCURO, font=("Segoe UI", 11, "bold"),
                   height=36, width=160, command=gerar_lote).pack(side="left", padx=(0, 8))
    ctk.CTkButton(btn_row_mid, text="📁  Abrir Pasta QRs", fg_color="#1565C0",
                   hover_color="#0D47A1", font=("Segoe UI", 11, "bold"),
                   height=36, width=160, command=abrir_pasta).pack(side="left", padx=(0, 12))
    lbl_mid_status.pack(side="left")

    # ── Carregamento da lista ────────────────────────────────────────────
    def _selecionar(al):
        _estado["selecionado"] = al
        for mat, frame in _estado["linha_widgets"].items():
            frame.configure(fg_color=(BRANCO if mat != al["matricula"] else "#E8F5E9"))

    def carregar_lista(filtro=""):
        for w in corpo_lista.winfo_children():
            w.destroy()
        _estado["linha_widgets"] = {}

        lista = _ler_lista()
        filtro_lower = filtro.lower()
        exibidos = []
        for al in lista:
            serie = al.get("serie", "")
            curso = al.get("curso", "")
            if filtro_lower and filtro_lower not in al.get("nome", "").lower() \
                    and filtro_lower not in al.get("matricula", "").lower() \
                    and filtro_lower not in curso.lower() \
                    and filtro_lower not in serie.lower():
                continue
            exibidos.append(al)

        lbl_cnt.configure(text=f"({len(exibidos)} de {len(lista)} aluno(s))")

        if not exibidos:
            ctk.CTkLabel(corpo_lista, text="Nenhum aluno encontrado.",
                          font=("Segoe UI", 12), text_color=TEXTO_CINZA
                          ).grid(row=0, column=0, pady=24)
            return

        _estado_pag_qr = {"pagina": 0, "exibidos": exibidos}
        LIMITE = 10

        def _renderizar_pagina_qr():
            for w in corpo_lista.winfo_children():
                w.destroy()
            _estado["linha_widgets"] = {}
            pag = _estado_pag_qr["pagina"]
            dados = _estado_pag_qr["exibidos"]
            inicio = pag * LIMITE
            fatia = dados[inicio:inicio + LIMITE]

            for i, al in enumerate(fatia):
                serie = al.get("serie", "")
                curso = al.get("curso", "")
                tem_png = os.path.exists(_nome_arquivo(al))
                ano = _extrair_ano_serie(serie)
                ano_exib = f"{ano}º Ano" if ano else "-"
                bg_normal = BRANCO if i % 2 == 0 else "#F8F9FA"
                if not tem_png:
                    bg_normal = "#FFF9C4"
                linha = ctk.CTkFrame(corpo_lista, fg_color=bg_normal, corner_radius=4, cursor="hand2")
                linha.grid(row=i, column=0, sticky="ew", pady=1)
                _estado["linha_widgets"][al["matricula"]] = linha
                icone_qr = "✔" if tem_png else "✘"
                cor_icone = "#2E7D32" if tem_png else "#C62828"
                valores = [(icone_qr, 50, cor_icone), (al.get("matricula", ""), 100, "#374151"),
                           (al.get("nome", ""), 220, "#374151"), (ano_exib, 110, "#374151"),
                           (curso or "-", 200, "#374151")]
                n = len(valores)
                widgets_linha = []
                for j, (val, w, cor_t) in enumerate(valores):
                    lbl = ctk.CTkLabel(linha, text=val, font=("Segoe UI", 11),
                                        width=w, anchor="w", text_color=cor_t)
                    lbl.pack(side="left", expand=(j == n-1), fill="x", padx=6, pady=6)
                    widgets_linha.append(lbl)

                def _bind_click(widget, a=al):
                    widget.bind("<Button-1>", lambda e, _a=a: _selecionar(_a))

                _bind_click(linha)
                for w in widgets_linha:
                    _bind_click(w)

            # Rodapé de paginação
            rod = ctk.CTkFrame(corpo_lista, fg_color="transparent")
            rod.grid(row=LIMITE + 1, column=0, sticky="ew", pady=(6, 2))
            ctk.CTkLabel(rod, text=f"Exibindo {inicio+1}–{min(inicio+LIMITE, len(dados))} de {len(dados)}",
                          font=("Segoe UI", 10), text_color=TEXTO_CINZA).pack(side="left", padx=4)
            if pag > 0:
                ctk.CTkButton(rod, text="← Anterior", width=90, height=26,
                               fg_color=VERDE_VIBRANTE, hover_color=VERDE_ESCURO,
                               font=("Segoe UI", 10, "bold"),
                               command=lambda: [_estado_pag_qr.update({"pagina": pag - 1}),
                                                _renderizar_pagina_qr()]
                               ).pack(side="left", padx=4)
            if inicio + LIMITE < len(dados):
                ctk.CTkButton(rod, text="Ver mais →", width=90, height=26,
                               fg_color=VERDE_VIBRANTE, hover_color=VERDE_ESCURO,
                               font=("Segoe UI", 10, "bold"),
                               command=lambda: [_estado_pag_qr.update({"pagina": pag + 1}),
                                                _renderizar_pagina_qr()]
                               ).pack(side="left", padx=4)

        _renderizar_pagina_qr()

    ent_busca.bind("<KeyRelease>", lambda e: carregar_lista(ent_busca.get()))

    # ══════════════════════════════════════════════════════════════════════
    # COLUNA DIREITA — Importar planilha
    # ══════════════════════════════════════════════════════════════════════
    dir_col = ctk.CTkFrame(page, fg_color=BRANCO, corner_radius=12, width=300)
    dir_col.grid(row=1, column=2, sticky="ns")

    ctk.CTkLabel(dir_col, text="Importar Planilha", font=("Segoe UI", 15, "bold"),
                  text_color=TEXTO_ESCURO).pack(pady=(18, 2))
    ctk.CTkLabel(dir_col, text="XLSX ou CSV com os alunos",
                  font=("Segoe UI", 10), text_color=TEXTO_CINZA).pack(pady=(0, 8))
    ctk.CTkFrame(dir_col, fg_color="#E5E7EB", height=1).pack(fill="x", padx=18, pady=(0, 12))

    frame_inst = ctk.CTkFrame(dir_col, fg_color="#F8F9FA", corner_radius=8)
    frame_inst.pack(fill="x", padx=18, pady=(0, 10))
    ctk.CTkLabel(frame_inst, text="Colunas esperadas:", font=("Segoe UI", 10, "bold"),
                  text_color=VERDE_VIBRANTE).pack(anchor="w", padx=10, pady=(8, 2))
    for col_txt in ["matrícula  (obrigatório)", "nome       (obrigatório)",
                    "série      (ex: 1 Ano, 2 Ano)", "curso      (ex: Des. Sistemas)"]:
        ctk.CTkLabel(frame_inst, text=f"• {col_txt}", font=("Segoe UI", 9),
                      text_color=TEXTO_ESCURO, justify="left").pack(anchor="w", padx=10)
    ctk.CTkLabel(frame_inst,
                  text="\nEstrutura gerada:\nqrcodes_marwin/\n"
                       "  1 Ano/\n    Desenvolvimento de Sistemas/\n"
                       "  2 Ano/\n    ...\n  3 Ano/\n    ...",
                  font=("Courier", 8), text_color=TEXTO_CINZA, justify="left"
                  ).pack(anchor="w", padx=10, pady=(4, 8))

    ctk.CTkLabel(dir_col, text="Mapear colunas (opcional)", font=("Segoe UI", 10, "bold"),
                  text_color=VERDE_VIBRANTE).pack(anchor="w", padx=18, pady=(4, 0))
    ctk.CTkLabel(dir_col, text="Deixe em branco p/ detecção automática.",
                  font=("Segoe UI", 9), text_color=TEXTO_CINZA).pack(anchor="w", padx=18, pady=(0, 6))

    map_vars = {}
    for campo_mk, rotulo_mk in [("matricula", "Col. Matrícula"), ("nome", "Col. Nome"),
                                 ("serie", "Col. Série"), ("curso", "Col. Curso")]:
        fr = ctk.CTkFrame(dir_col, fg_color="transparent")
        fr.pack(fill="x", padx=18, pady=(0, 4))
        ctk.CTkLabel(fr, text=rotulo_mk, font=("Segoe UI", 9),
                      text_color=TEXTO_ESCURO, width=110, anchor="w").pack(side="left")
        ent = ctk.CTkEntry(fr, height=28, font=("Segoe UI", 9))
        ent.pack(side="left", fill="x", expand=True)
        map_vars[campo_mk] = ent

    ctk.CTkFrame(dir_col, fg_color="#E5E7EB", height=1).pack(fill="x", padx=18, pady=(10, 10))

    gerar_qr_import_var = ctk.BooleanVar(value=True)
    ctk.CTkCheckBox(dir_col, text="Gerar QR Codes ao importar",
                     variable=gerar_qr_import_var, font=("Segoe UI", 10, "bold"),
                     text_color=VERDE_VIBRANTE, fg_color=VERDE_VIBRANTE,
                     hover_color=VERDE_ESCURO).pack(anchor="w", padx=18, pady=(0, 4))

    sobreescrever_var = ctk.BooleanVar(value=False)
    ctk.CTkCheckBox(dir_col, text="Atualizar duplicatas",
                     variable=sobreescrever_var, font=("Segoe UI", 10),
                     text_color=TEXTO_ESCURO, fg_color=VERDE_VIBRANTE,
                     hover_color=VERDE_ESCURO).pack(anchor="w", padx=18, pady=(0, 10))

    lbl_import_status = ctk.CTkLabel(dir_col, text="", font=("Segoe UI", 10, "bold"),
                                      text_color=VERDE_VIBRANTE, wraplength=250, justify="center")
    lbl_import_status.pack(pady=4, padx=18)

    prog_bar = ctk.CTkProgressBar(dir_col, height=10)
    prog_bar.set(0)
    prog_bar.pack(fill="x", padx=18, pady=(0, 10))

    def _normalizar_cabecalho(cabecalho):
        mapa_auto = {}
        sinonimos = {
            "matricula": ["matricula", "mat", "mat.", "codigo", "id", "registro"],
            "nome":      ["nome", "aluno", "estudante", "discente", "name", "nomecompleto"],
            "serie":     ["serie", "turma", "ano", "class", "classe", "periodo", "ano/serie"],
            "curso":     ["curso", "habilitacao", "area", "modalidade", "formacao"],
        }
        cab_lower = [str(c).strip().lower() for c in cabecalho]
        for campo, sinonimos_lista in sinonimos.items():
            manual = map_vars[campo].get().strip()
            if manual and manual in cabecalho:
                mapa_auto[campo] = cabecalho.index(manual)
                continue
            for s in sinonimos_lista:
                for idx_c, c in enumerate(cab_lower):
                    if s in c:
                        mapa_auto[campo] = idx_c
                        break
                if campo in mapa_auto:
                    break
        return mapa_auto

    def importar_planilha():
        from tkinter import filedialog
        caminho_pl = filedialog.askopenfilename(
            title="Selecionar planilha de alunos",
            filetypes=[("Planilhas", "*.xlsx *.xls *.csv *.tsv"),
                       ("Excel", "*.xlsx *.xls"),
                       ("CSV / TSV", "*.csv *.tsv"),
                       ("Todos", "*.*")])
        if not caminho_pl:
            return

        lbl_import_status.configure(text="Lendo arquivo...", text_color=TEXTO_CINZA)
        page.update()

        ext = os.path.splitext(caminho_pl)[1].lower()
        linhas_raw = []

        try:
            if ext in (".xlsx", ".xls"):
                try:
                    import openpyxl
                except ImportError:
                    lbl_import_status.configure(text="Instalando openpyxl...", text_color=TEXTO_CINZA)
                    page.update()
                    import sys, subprocess
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "openpyxl", "--quiet"])
                    import openpyxl
                wb = openpyxl.load_workbook(caminho_pl, read_only=True, data_only=True)
                ws = wb.active
                for row in ws.iter_rows(values_only=True):
                    linhas_raw.append([str(c).strip() if c is not None else "" for c in row])
                wb.close()
            elif ext in (".csv", ".tsv"):
                sep = "\t" if ext == ".tsv" else None
                for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
                    try:
                        with open(caminho_pl, "r", encoding=enc, newline="") as f:
                            sample = f.read(4096); f.seek(0)
                            if sep is None:
                                try: sep = csv.Sniffer().sniff(sample).delimiter
                                except: sep = ","
                            reader_pl = csv.reader(f, delimiter=sep)
                            linhas_raw = [[c.strip() for c in row] for row in reader_pl]
                        break
                    except (UnicodeDecodeError, Exception):
                        continue
            else:
                lbl_import_status.configure(text="⚠ Use .xlsx, .xls, .csv ou .tsv", text_color="#C62828")
                return
        except Exception as e:
            lbl_import_status.configure(text=f"⚠ Erro ao ler arquivo: {e}", text_color="#C62828")
            return

        if len(linhas_raw) < 2:
            lbl_import_status.configure(text="⚠ Arquivo sem dados suficientes.", text_color="#C62828")
            return

        cabecalho = linhas_raw[0]
        mapa = _normalizar_cabecalho(cabecalho)

        if "matricula" not in mapa or "nome" not in mapa:
            lbl_import_status.configure(
                text="⚠ Não foi possível identificar colunas de Matrícula e Nome.\n"
                     "Use o mapeamento manual.",
                text_color="#C62828")
            return

        lista_atual = _ler_lista()
        mats_existentes = {a["matricula"]: i for i, a in enumerate(lista_atual)}

        novos = 0; atualizados = 0; ignorados = 0
        dados_importados = []

        linhas_dados = [l for l in linhas_raw[1:] if any(c for c in l)]
        total_linhas = max(len(linhas_dados), 1)

        for idx_linha, linha in enumerate(linhas_dados):
            prog_bar.set((idx_linha + 1) / total_linhas)
            page.update_idletasks()

            def _cel(campo, _linha=linha):
                idx_c = mapa.get(campo)
                if idx_c is None or idx_c >= len(_linha):
                    return ""
                return str(_linha[idx_c]).strip()

            matricula = _cel("matricula")
            nome      = _cel("nome")
            serie     = _cel("serie")
            curso     = _cel("curso")

            if not matricula or not nome:
                ignorados += 1
                continue

            al = {"matricula": matricula, "nome": nome, "serie": serie, "curso": curso}

            if matricula in mats_existentes:
                if sobreescrever_var.get():
                    lista_atual[mats_existentes[matricula]] = al
                    atualizados += 1
                    dados_importados.append(al)
                else:
                    ignorados += 1
            else:
                lista_atual.append(al)
                mats_existentes[matricula] = len(lista_atual) - 1
                novos += 1
                dados_importados.append(al)

        _salvar_lista(lista_atual)

        msg_qr = ""
        if gerar_qr_import_var.get() and dados_importados:
            lbl_import_status.configure(text=f"Gerando {len(dados_importados)} QR Code(s)...",
                                         text_color=TEXTO_CINZA)
            prog_bar.set(0)
            erros_qr = 0
            pastas_criadas = set()
            total_al = max(len(dados_importados), 1)
            for idx_al, al in enumerate(dados_importados):
                prog_bar.set((idx_al + 1) / total_al)
                page.update_idletasks()
                try:
                    _gerar_png(al)
                    pastas_criadas.add(_pasta_turma(al))
                except Exception:
                    erros_qr += 1
            msg_qr = (f"\n{len(dados_importados)-erros_qr} QR Code(s) gerados "
                      f"em {len(pastas_criadas)} pasta(s) dentro de '{QR_DIR}/'.")
            if erros_qr:
                msg_qr += f" ({erros_qr} erros)"

        prog_bar.set(0)
        carregar_lista(ent_busca.get())

        resumo = (f"✔ Importação concluída!\n"
                  f"Novos: {novos}  |  Atualizados: {atualizados}  |  "
                  f"Ignorados: {ignorados}{msg_qr}")
        lbl_import_status.configure(text=resumo, text_color=VERDE_VIBRANTE)

    ctk.CTkButton(dir_col, text="📂  Selecionar Arquivo e Importar", fg_color=VERDE_VIBRANTE,
                   hover_color=VERDE_ESCURO, font=("Segoe UI", 11, "bold"),
                   height=42, command=importar_planilha).pack(fill="x", padx=18, pady=(0, 6))
    ctk.CTkButton(dir_col, text="📁  Abrir Pasta dos QR Codes", fg_color="#1565C0",
                   hover_color="#0D47A1", font=("Segoe UI", 10, "bold"),
                   height=34, command=abrir_pasta).pack(fill="x", padx=18, pady=(0, 18))

    carregar_lista()
    return page