"""
Helpers de UI compartilhados entre as páginas do Painel Administrativo.

Extraídos de abrir_painel_admin_ctk (Servidor.py) sem alterar a lógica.
São fábricas de "cards" (resumo numérico e tabela) usadas em praticamente
todas as abas: Visão Geral, Avaliações, Relatório Semanal, Refeitório,
Frequência, Histórico, Logs.
"""
import customtkinter as ctk


def card_resumo(parent, row, col, icone, cor_fundo, cor_icone, titulo, valor,
                 subtitulo, cores):
    """Card pequeno com ícone + número + subtítulo (ex: "Total: 42 alunos").

    cores : dict
        Precisa conter BRANCO, TEXTO_CINZA, TEXTO_ESCURO.
    Retorna (valor_lbl, sub_lbl) — os dois CTkLabel que o chamador atualiza
    depois de buscar os dados (ex: lbl.configure(text=...)).
    """
    BRANCO       = cores["BRANCO"]
    TEXTO_CINZA  = cores["TEXTO_CINZA"]
    TEXTO_ESCURO = cores["TEXTO_ESCURO"]

    card = ctk.CTkFrame(parent, fg_color=BRANCO, corner_radius=12)
    card.grid(row=row, column=col, sticky="nsew", padx=8, pady=4)
    conteudo = ctk.CTkFrame(card, fg_color="transparent")
    conteudo.pack(fill="x", padx=18, pady=18)
    icone_box = ctk.CTkFrame(conteudo, fg_color=cor_fundo, corner_radius=10, width=48, height=48)
    icone_box.pack(side="left", padx=(0, 14))
    icone_box.pack_propagate(False)
    ctk.CTkLabel(icone_box, text=icone, font=("Segoe UI", 20),
                  text_color=cor_icone).place(relx=0.5, rely=0.5, anchor="center")
    textos = ctk.CTkFrame(conteudo, fg_color="transparent")
    textos.pack(side="left", fill="x", expand=True)
    ctk.CTkLabel(textos, text=titulo, font=("Segoe UI", 12), text_color=TEXTO_CINZA).pack(anchor="w")
    valor_lbl = ctk.CTkLabel(textos, text=valor, font=("Segoe UI", 26, "bold"), text_color=TEXTO_ESCURO)
    valor_lbl.pack(anchor="w")
    sub_lbl = ctk.CTkLabel(textos, text=subtitulo, font=("Segoe UI", 10), text_color=TEXTO_CINZA)
    sub_lbl.pack(anchor="w")
    return valor_lbl, sub_lbl


def card_tabela(parent, titulo, colunas, linhas, cores, rodape="", larguras=None):
    """Card com cabeçalho colorido + linhas de dados (mini-tabela).

    cores : dict
        Precisa conter BRANCO, TEXTO_ESCURO, VERDE_ESCURO, TEXTO_CINZA.
    """
    BRANCO       = cores["BRANCO"]
    TEXTO_ESCURO = cores["TEXTO_ESCURO"]
    VERDE_ESCURO = cores["VERDE_ESCURO"]
    TEXTO_CINZA  = cores["TEXTO_CINZA"]

    card = ctk.CTkFrame(parent, fg_color=BRANCO, corner_radius=12)
    topo = ctk.CTkFrame(card, fg_color="transparent")
    topo.pack(fill="x", padx=18, pady=(16, 10))
    ctk.CTkLabel(topo, text=titulo, font=("Segoe UI", 13, "bold"), text_color=TEXTO_ESCURO).pack(side="left")

    header_t = ctk.CTkFrame(card, fg_color=VERDE_ESCURO, corner_radius=6)
    header_t.pack(fill="x", padx=18)
    n = len(colunas)
    for i, c in enumerate(colunas):
        w = larguras.get(i) if larguras else None
        ctk.CTkLabel(header_t, text=c, font=("Segoe UI", 10, "bold"), text_color="white",
                      width=w or 0, anchor="w").pack(side="left", expand=(i == n - 1),
                                                        fill="x", padx=8, pady=8)

    if not linhas:
        ctk.CTkLabel(card, text="Nenhum registro encontrado.", font=("Segoe UI", 11),
                      text_color=TEXTO_CINZA).pack(anchor="w", padx=18, pady=12)
    else:
        for linha in linhas:
            linha_frame = ctk.CTkFrame(card, fg_color="transparent")
            linha_frame.pack(fill="x", padx=18)
            for i, valor in enumerate(linha):
                w = larguras.get(i) if larguras else None
                ctk.CTkLabel(linha_frame, text=str(valor), font=("Segoe UI", 11),
                              width=w or 0, anchor="w",
                              text_color="#374151").pack(side="left", expand=(i == n - 1),
                                                            fill="x", padx=8, pady=8)
            ctk.CTkFrame(card, fg_color="#F0F0F0", height=1).pack(fill="x", padx=18)

    if rodape:
        ctk.CTkLabel(card, text=rodape, font=("Segoe UI", 10),
                      text_color="#2E7D32").pack(anchor="w", padx=18, pady=(10, 16))
    else:
        ctk.CTkFrame(card, fg_color="transparent", height=10).pack()
    return card


def iniciar_polling(page, fn_carregar, intervalo_ms=5000,
                    api_url="https://marwin-api-uuul.onrender.com/ultimo-update"):
    """Verifica /ultimo-update a cada `intervalo_ms` ms.
    Chama fn_carregar() apenas quando o timestamp mudar (novo dado no Neon).

    page        : CTkFrame da aba — o polling para automaticamente quando
                  a página for destruída.
    fn_carregar : função sem argumentos que recarrega os dados da aba.
    """
    import threading
    import urllib.request

    _estado = {"ts": None, "vivo": True}
    page.bind("<Destroy>", lambda e: _estado.update({"vivo": False}))

    def _verificar():
        if not _estado["vivo"]:
            return
        try:
            with urllib.request.urlopen(api_url, timeout=4) as r:
                import json as _json
                data = _json.loads(r.read())
            ts = data.get("ts")
            if ts and ts != _estado["ts"]:
                _estado["ts"] = ts
                if _estado["vivo"] and page.winfo_exists():
                    page.after(0, fn_carregar)
        except Exception:
            pass  # API offline — silencia e tenta na próxima rodada
        if _estado["vivo"]:
            try:
                page.after(intervalo_ms, _agendar)
            except Exception:
                pass

    def _agendar():
        threading.Thread(target=_verificar, daemon=True).start()

    # Inicia após 5s para não competir com o carregamento inicial
    try:
        page.after(intervalo_ms, _agendar)
    except Exception:
        pass
