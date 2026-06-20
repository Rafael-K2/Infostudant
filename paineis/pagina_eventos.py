"""
Aba "Editar Eventos" do Painel Administrativo.

Extraído de abrir_painel_admin_ctk (Servidor.py) sem alterar a lógica.
"""
import customtkinter as ctk
from tkinter import messagebox


def criar_pagina_eventos(_scroll_inner, cores, ler_json, salvar_json,
                          _sync_nuvem, _buscar_logo_png,
                          EVENTOS_FILE, EVENTOS_PADRAO):
    """Cria e retorna o frame da página "Editar Eventos".

    Parâmetros
    ----------
    _scroll_inner : CTkFrame
        Frame pai (área rolável) onde a página é desenhada.
    cores : dict
        Constantes de cor usadas no painel.
    ler_json, salvar_json : callables
        Funções utilitárias de leitura/escrita de JSON.
    _sync_nuvem : callable
        Função de sincronização com a API na nuvem.
    _buscar_logo_png : callable
        Função que localiza o arquivo de logo da escola.
    EVENTOS_FILE : str
        Caminho do arquivo eventos.json.
    EVENTOS_PADRAO : list
        Estrutura padrão usada quando o arquivo não existe ainda.
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
    page.grid_rowconfigure(1, weight=1)

    # ── Cabeçalho ─────────────────────────────────────────────────────────
    cab = ctk.CTkFrame(page, fg_color="transparent")
    cab.grid(row=0, column=0, columnspan=2, sticky="ew", padx=4, pady=(4, 16))
    ctk.CTkLabel(cab, text="Editar Eventos 📅",
                  font=("Segoe UI", 22, "bold"), text_color=TEXTO_ESCURO).pack(anchor="w")
    ctk.CTkLabel(cab, text="Adicione datas e descrições ao calendário escolar.",
                  font=("Segoe UI", 12), text_color=TEXTO_CINZA).pack(anchor="w")

    # ── Coluna esquerda: formulário de novo evento ──────────────────────────
    form_card = ctk.CTkFrame(page, fg_color=BRANCO, corner_radius=12, width=300)
    form_card.grid(row=1, column=0, sticky="ns", padx=(0, 16))
    form_card.grid_propagate(False)

    # Logo (se existir)
    logo_path = _buscar_logo_png()
    if logo_path:
        try:
            from PIL import Image as _PilImg
            _img_logo = _PilImg.open(logo_path).convert("RGBA")
            _img_logo.thumbnail((110, 110), _PilImg.LANCZOS)
            _ctk_logo = ctk.CTkImage(light_image=_img_logo, dark_image=_img_logo,
                                      size=_img_logo.size)
            ctk.CTkLabel(form_card, image=_ctk_logo, text="").pack(pady=(24, 8))
        except Exception:
            pass

    ctk.CTkLabel(form_card, text="Novo Evento",
                  font=("Segoe UI", 15, "bold"), text_color=TEXTO_ESCURO).pack(pady=(8, 2))
    ctk.CTkLabel(form_card, text="Cadastre datas especiais\ndo calendário escolar",
                  font=("Segoe UI", 10), text_color=TEXTO_CINZA,
                  justify="center").pack(pady=(0, 16))

    linha_div = ctk.CTkFrame(form_card, fg_color="#E5E7EB", height=1)
    linha_div.pack(fill="x", padx=20, pady=(0, 16))

    ctk.CTkLabel(form_card, text="Data", font=("Segoe UI", 11, "bold"),
                  text_color=TEXTO_ESCURO).pack(anchor="w", padx=20)
    ctk.CTkLabel(form_card, text="Formato: DD/MM  (ex: 15/07)",
                  font=("Segoe UI", 9), text_color=TEXTO_CINZA).pack(anchor="w", padx=20, pady=(0, 4))
    ent_data = ctk.CTkEntry(form_card, font=("Segoe UI", 13), height=38,
                             border_color=VERDE_VIBRANTE, border_width=2,
                             placeholder_text="01/01")
    ent_data.pack(fill="x", padx=20, pady=(0, 16))

    ctk.CTkLabel(form_card, text="Descrição", font=("Segoe UI", 11, "bold"),
                  text_color=TEXTO_ESCURO).pack(anchor="w", padx=20)
    ctk.CTkLabel(form_card, text="Nome do evento ou feriado",
                  font=("Segoe UI", 9), text_color=TEXTO_CINZA).pack(anchor="w", padx=20, pady=(0, 4))
    ent_desc = ctk.CTkEntry(form_card, font=("Segoe UI", 13), height=38,
                             border_color=VERDE_VIBRANTE, border_width=2,
                             placeholder_text="Ex: Feira Científica")
    ent_desc.pack(fill="x", padx=20, pady=(0, 8))

    lbl_form_status = ctk.CTkLabel(form_card, text="", font=("Segoe UI", 10),
                                    text_color=VERDE_VIBRANTE)
    lbl_form_status.pack(pady=(0, 4))

    # ── Coluna direita: lista de eventos cadastrados ────────────────────────
    lista_card = ctk.CTkFrame(page, fg_color=BRANCO, corner_radius=12)
    lista_card.grid(row=1, column=1, sticky="nsew")
    lista_card.grid_rowconfigure(2, weight=1)
    lista_card.grid_columnconfigure(0, weight=1)

    topo_lista = ctk.CTkFrame(lista_card, fg_color="transparent")
    topo_lista.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 4))
    ctk.CTkLabel(topo_lista, text="Eventos Cadastrados",
                  font=("Segoe UI", 14, "bold"), text_color=TEXTO_ESCURO).pack(side="left")
    lbl_total = ctk.CTkLabel(topo_lista, text="", font=("Segoe UI", 10),
                              text_color=TEXTO_CINZA)
    lbl_total.pack(side="right")

    # Cabeçalho da tabela
    header_ev = ctk.CTkFrame(lista_card, fg_color=VERDE_ESCURO, corner_radius=6)
    header_ev.grid(row=1, column=0, sticky="ew", padx=18)
    ctk.CTkLabel(header_ev, text="Data", font=("Segoe UI", 10, "bold"),
                  text_color="white", width=90, anchor="w"
                  ).pack(side="left", padx=8, pady=8)
    ctk.CTkLabel(header_ev, text="Evento", font=("Segoe UI", 10, "bold"),
                  text_color="white", anchor="w"
                  ).pack(side="left", expand=True, fill="x", padx=8, pady=8)
    ctk.CTkLabel(header_ev, text="", font=("Segoe UI", 10, "bold"),
                  text_color="white", width=40
                  ).pack(side="right", padx=8, pady=8)

    # Corpo scrollável da lista
    corpo_ev = ctk.CTkFrame(lista_card, fg_color="transparent")
    corpo_ev.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 16))
    corpo_ev.grid_columnconfigure(0, weight=1)

    # ── Funções de carregar / adicionar / remover ───────────────────────────
    def _ordenar_eventos(evs):
        try:
            return sorted(evs, key=lambda x: (int(x["data"].split("/")[1]),
                                                int(x["data"].split("/")[0])))
        except Exception:
            return evs

    def carregar_eventos():
        for w in corpo_ev.winfo_children():
            w.destroy()

        evs = ler_json(EVENTOS_FILE, EVENTOS_PADRAO)
        evs = _ordenar_eventos(evs)
        lbl_total.configure(text=f"{len(evs)} evento(s) cadastrado(s)")

        if not evs:
            ctk.CTkLabel(corpo_ev, text="Nenhum evento cadastrado.",
                          font=("Segoe UI", 12), text_color=TEXTO_CINZA
                          ).grid(row=0, column=0, pady=24)
            return

        for i, ev in enumerate(evs):
            bg = BRANCO if i % 2 == 0 else "#F8F9FA"
            linha = ctk.CTkFrame(corpo_ev, fg_color=bg, corner_radius=6)
            linha.grid(row=i, column=0, sticky="ew", pady=2)
            linha.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(linha, text=ev["data"], font=("Segoe UI", 11, "bold"),
                          text_color=VERDE_VIBRANTE, width=90, anchor="w"
                          ).grid(row=0, column=0, padx=8, pady=8, sticky="w")
            ctk.CTkLabel(linha, text=ev["evento"], font=("Segoe UI", 11),
                          text_color="#374151", anchor="w"
                          ).grid(row=0, column=1, padx=8, pady=8, sticky="ew")

            def _remover(e=ev):
                if not messagebox.askyesno("Confirmar", f"Remover o evento '{e['evento']}' ({e['data']})?"):
                    return
                atuais = ler_json(EVENTOS_FILE, EVENTOS_PADRAO)
                atuais = [x for x in atuais if not (x["data"] == e["data"] and x["evento"] == e["evento"])]
                salvar_json(EVENTOS_FILE, atuais)
                try:
                    _sync_nuvem("/admin/eventos", "PUT", atuais)
                except Exception:
                    pass
                carregar_eventos()

            ctk.CTkButton(linha, text="🗑", width=36, height=28,
                           fg_color="#FEE2E2", hover_color="#FCA5A5",
                           text_color="#C62828", font=("Segoe UI", 12),
                           command=_remover
                           ).grid(row=0, column=2, padx=8, pady=8)

    def adicionar_evento():
        data = ent_data.get().strip()
        desc = ent_desc.get().strip()

        if not data or not desc:
            lbl_form_status.configure(text="⚠ Preencha a data e a descrição.",
                                       text_color="#C62828")
            return
        if "/" not in data or len(data) != 5:
            lbl_form_status.configure(text="⚠ Use o formato DD/MM (ex: 15/07).",
                                       text_color="#C62828")
            return

        evs = ler_json(EVENTOS_FILE, EVENTOS_PADRAO)
        evs.append({"data": data, "evento": desc})
        salvar_json(EVENTOS_FILE, evs)
        try:
            _sync_nuvem("/admin/eventos", "PUT", evs)
        except Exception:
            pass

        lbl_form_status.configure(text="✔ Evento adicionado!", text_color=VERDE_VIBRANTE)
        ent_data.delete(0, "end")
        ent_desc.delete(0, "end")
        ent_data.focus()
        carregar_eventos()
        page.after(2500, lambda: lbl_form_status.configure(text=""))

    ctk.CTkButton(form_card, text="➕  Adicionar Evento",
                   fg_color=VERDE_VIBRANTE, hover_color=VERDE_ESCURO,
                   font=("Segoe UI", 12, "bold"), height=40,
                   command=adicionar_evento
                   ).pack(fill="x", padx=20, pady=(4, 24))

    ent_desc.bind("<Return>", lambda e: adicionar_evento())
    ent_data.bind("<Return>", lambda e: ent_desc.focus())

    carregar_eventos()
    return page
