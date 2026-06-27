"""
Aba "Relatório Semanal" do Painel Administrativo.

Reescrita para focar no CONTEÚDO das avaliações coletadas (notas por
setor — Comida, Limpeza, Ensino e Semana/Experiência) em vez de apenas
contar quantas avaliações/presenças/refeições aconteceram.

Layout em estilo "dashboard" (cards): resumo geral no topo (alunos,
total, média geral, almoço favorito), card "Geral" com média por setor
+ donut de distribuição das notas, e um card por setor (Comida,
Limpeza, Ensino, Semana) com a lista de itens avaliados em formato de
barra de progresso + nota + nº de avaliações, destacando a maior e a
menor avaliação de cada setor.

Setores e itens batem com o que o index.html envia em AVAL_ITENS:
  Estágio 1 — Comida   (Almoço-Segunda...Sexta, Merenda manhã/tarde)
  Estágio 2 — Limpeza  (Salas de Aula, Refeitório, Banheiros, ...)
  Estágio 3 — Ensino   (Linguagens, Humanas, Ciências, Matemática)
  Estágio 4 — Semana   (3 perguntas de estrela + "melhor almoço da
                         semana", que é um VOTO em dia da semana, não
                         estrela — tratado separado para o card de
                         almoço favorito).
"""
import threading
import textwrap
import unicodedata
from collections import Counter

import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from paineis.helpers import card_resumo
from paineis.helpers import iniciar_polling


def criar_pagina_relatorio_semanal(_scroll_inner, cores, _agora_br, _ler_avaliacoes_db):
    """Cria e retorna o frame da página "Relatório Semanal" (avaliações).

    Parâmetros
    ----------
    _scroll_inner : CTkFrame
        Frame pai (área rolável) onde a página é desenhada.
    cores : dict
        Constantes de cor: CINZA_BG, BRANCO, TEXTO_CINZA, TEXTO_ESCURO,
        VERDE_VIBRANTE, VERDE_ESCURO, AZUL_CLARO, VERDE_CLARO, ROXO_CLARO.
    _agora_br : callable
        Devolve datetime atual no fuso do Brasil.
    _ler_avaliacoes_db : callable
        Lê todos os registros de avaliações do banco (lista de dicts com
        Data, Aluno, Serie, Curso, Estagio, Item, Nota).
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

    # Cores auxiliares (combinam com a paleta já usada no projeto)
    AZUL_FORTE  = "#1565C0"   # mesmo azul usado em Limpeza no gráfico antigo
    ROXO_FORTE  = "#6A1B9A"   # mesmo roxo usado em Ensino no gráfico antigo
    LARANJA     = "#EF6C00"   # mesmo laranja usado em Semana no gráfico antigo
    VERDE_OK    = "#2E7D32"   # boa (4-5★) / maior avaliação
    AMARELO_OK  = "#F9A825"   # média (2-3★)
    VERMELHO_OK = "#D32F2F"   # ruim (1★) / menor avaliação
    BORDA_CLARA = "#E5E7EB"

    def _card_resumo(parent, row, col, icone, cor_fundo, cor_icone, titulo, valor, subtitulo):
        return card_resumo(parent, row, col, icone, cor_fundo, cor_icone, titulo, valor,
                            subtitulo, {"BRANCO": BRANCO, "TEXTO_CINZA": TEXTO_CINZA,
                                        "TEXTO_ESCURO": TEXTO_ESCURO})

    # ── Mapas de setor (estágio do questionário) ───────────────────
    SETOR_LABEL = {1: "🍽️ Comida", 2: "🧹 Limpeza", 3: "📚 Ensino", 4: "✨ Acolhimento"}
    SETOR_ICONE = {1: "🍽️", 2: "🧹", 3: "📚", 4: "✨"}
    SETOR_TITULO = {1: "COMIDA", 2: "LIMPEZA", 3: "ENSINO", 4: "ACOLHIMENTO"}
    SETOR_SUBTITULO = {
        1: "Avaliações do setor de alimentação",
        2: "Avaliações do setor de limpeza",
        3: "Avaliações do setor de ensino",
        4: "Avaliações de acolhimento da semana",
    }
    SETOR_POR_LABEL = {v: k for k, v in SETOR_LABEL.items()}
    SETOR_COR = {1: VERDE_VIBRANTE, 2: AZUL_FORTE, 3: ROXO_FORTE, 4: LARANJA}
    SETOR_COR_CLARA = {1: VERDE_CLARO, 2: AZUL_CLARO, 3: ROXO_CLARO, 4: "#FFF3E0"}
    VALORES_SELETOR = ["Geral"] + [SETOR_LABEL[e] for e in (1, 2, 3, 4)]

    def _norm(texto):
        return unicodedata.normalize("NFD", str(texto).lower()).encode("ascii", "ignore").decode("ascii")

    def _nota_numerica(valor):
        """Converte Nota em número de 1 a 5, ou None se não for estrela
        (ex.: a Nota do "melhor almoço da semana" é o nome de um dia)."""
        try:
            n = int(float(str(valor).strip().replace(",", ".")))
            if 1 <= n <= 5:
                return n
        except (TypeError, ValueError):
            pass
        return None

    def _label_curto(item, largura=34):
        t = item.replace("Almoço-", "").replace("-Todos os dias", "")
        return textwrap.shorten(t, width=largura, placeholder="…")

    DIAS_ORDEM = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira"]
    DIAS_ABREV = {"Segunda-feira": "Seg", "Terça-feira": "Ter", "Quarta-feira": "Qua",
                  "Quinta-feira": "Qui", "Sexta-feira": "Sex"}

    def _processar_avaliacoes(registros):
        por_setor_item = {1: {}, 2: {}, 3: {}, 4: {}}
        boa = media = ruim = 0
        votos_almoco = Counter()
        alunos = set()
        submissoes_anonimas = set()

        for r in registros:
            try:
                estagio = int(str(r.get("Estagio", "")).strip())
            except (TypeError, ValueError):
                continue
            if estagio not in por_setor_item:
                continue

            item = str(r.get("Item", "")).strip()
            nome_aluno = str(r.get("Aluno", "")).strip()
            if not nome_aluno or _norm(nome_aluno) == "anonimo":
                submissoes_anonimas.add(str(r.get("Data", "")))
            else:
                alunos.add(nome_aluno.lower())

            # "Qual foi o melhor almoço da semana?" é um VOTO em dia da
            # semana (vem de um <select>), não uma nota de 1-5 estrelas —
            # tratado à parte e fora das médias/contagens de estrela.
            if estagio == 4 and "melhor almoco da semana" in _norm(item):
                dia = str(r.get("Nota", "")).strip()
                if dia and _norm(dia) != "nenhum":
                    votos_almoco[dia] += 1
                continue

            nota = _nota_numerica(r.get("Nota"))
            if nota is None:
                continue
            por_setor_item[estagio].setdefault(item, []).append(nota)
            if nota >= 4:
                boa += 1
            elif nota >= 2:
                media += 1
            else:
                ruim += 1

        media_setor = {}
        total_setor = {}
        for estagio, itens in por_setor_item.items():
            todas = [n for lista in itens.values() for n in lista]
            media_setor[estagio] = (sum(todas) / len(todas)) if todas else 0.0
            total_setor[estagio] = len(todas)

        mais_votado = votos_almoco.most_common(1)
        almoco_favorito = mais_votado[0] if mais_votado else (None, 0)

        total_estrelas = boa + media + ruim
        media_geral = 0.0
        if total_estrelas:
            soma = sum(n for itens in por_setor_item.values() for lista in itens.values() for n in lista)
            media_geral = soma / total_estrelas

        return {
            "total_registros": len(registros),
            "total_estrelas": total_estrelas,
            "por_setor_item": por_setor_item,
            "media_setor": media_setor,
            "total_setor": total_setor,
            "media_geral": media_geral,
            "boa": boa, "media": media, "ruim": ruim,
            "alunos_identificados": len(alunos),
            "avaliacoes_anonimas": len(submissoes_anonimas),
            "alunos_avaliaram": len(alunos) + len(submissoes_anonimas),
            "almoco_favorito": almoco_favorito,
            "votos_almoco": votos_almoco,
        }

    # ── Layout ───────────────────────────────────────────────────
    page = ctk.CTkFrame(_scroll_inner, fg_color=CINZA_BG)
    page.grid_columnconfigure(0, weight=1)

    # ── Estado do filtro de curso ──────────────────────────────────
    _filtro_curso = {"valor": "Todos"}
    _registros_cache = {"dados": []}

    # Cabeçalho
    cab = ctk.CTkFrame(page, fg_color="transparent")
    cab.grid(row=0, column=0, sticky="ew", pady=(4, 16))
    topo_cab = ctk.CTkFrame(cab, fg_color="transparent")
    topo_cab.pack(fill="x")
    ctk.CTkLabel(topo_cab, text="Relatório de Avaliações 📊",
                  font=("Segoe UI", 22, "bold"), text_color=TEXTO_ESCURO).pack(side="left", anchor="w")
    lbl_atualizado = ctk.CTkLabel(topo_cab, text="", font=("Segoe UI", 10),
                                   text_color=TEXTO_CINZA)
    lbl_atualizado.pack(side="right", anchor="e")
    ctk.CTkLabel(cab, text="O que os alunos disseram sobre comida, limpeza, ensino e a semana.",
                  font=("Segoe UI", 12), text_color=TEXTO_CINZA).pack(anchor="w")

    # Barra de filtro por turma/curso
    filtro_bar = ctk.CTkFrame(cab, fg_color="transparent")
    filtro_bar.pack(fill="x", pady=(10, 0))
    ctk.CTkLabel(filtro_bar, text="Filtrar por curso/turma:",
                  font=("Segoe UI", 11, "bold"), text_color=TEXTO_ESCURO).pack(side="left", padx=(0, 8))
    cb_curso = ctk.CTkOptionMenu(filtro_bar, values=["Todos"],
                                  width=200, fg_color=VERDE_VIBRANTE,
                                  button_color=VERDE_ESCURO, button_hover_color=VERDE_ESCURO,
                                  font=("Segoe UI", 11))
    cb_curso.set("Todos")
    cb_curso.pack(side="left", padx=(0, 10))
    lbl_filtro_info = ctk.CTkLabel(filtro_bar, text="", font=("Segoe UI", 10),
                                    text_color=TEXTO_CINZA)
    lbl_filtro_info.pack(side="left")

    # ── Cards de resumo (4 no topo, igual ao mockup) ───────────────
    cards_row = ctk.CTkFrame(page, fg_color="transparent")
    cards_row.grid(row=1, column=0, sticky="ew", pady=(0, 16))
    cards_row.grid_columnconfigure((0, 1, 2), weight=1)

    lbl_alunos, sub_alunos = _card_resumo(
        cards_row, 0, 0, "🙋", VERDE_CLARO, VERDE_VIBRANTE,
        "Alunos que avaliaram", "...", "respostas coletadas")
    lbl_media, sub_media = _card_resumo(
        cards_row, 0, 1, "⭐", ROXO_CLARO, ROXO_FORTE,
        "Média geral", "...", "de 5 estrelas")
    lbl_almoco, sub_almoco = _card_resumo(
        cards_row, 0, 2, "🍽️", "#FFF3E0", LARANJA,
        "Almoço favorito", "...", "dia mais votado")

    # ════════════════════════════════════════════════════════════
    # CARD "GERAL" — média por setor + donut de distribuição
    # ════════════════════════════════════════════════════════════
    geral_card = ctk.CTkFrame(page, fg_color=BRANCO, corner_radius=12,
                               border_width=1, border_color=BORDA_CLARA)
    geral_card.grid(row=2, column=0, sticky="ew", pady=(0, 16))
    geral_card.grid_columnconfigure((0, 1), weight=1, uniform="geral")

    topo_geral = ctk.CTkFrame(geral_card, fg_color="transparent")
    topo_geral.grid(row=0, column=0, columnspan=2, sticky="ew", padx=18, pady=(16, 6))
    ctk.CTkLabel(topo_geral, text="📊  AVALIAÇÕES GERAIS",
                  font=("Segoe UI", 14, "bold"), text_color=TEXTO_ESCURO).pack(side="left")

    # Coluna esquerda: "Média por setor" (barras horizontais simples em CTk)
    col_media_setor = ctk.CTkFrame(geral_card, fg_color="transparent")
    col_media_setor.grid(row=1, column=0, sticky="new", padx=(18, 9), pady=(4, 18))
    ctk.CTkLabel(col_media_setor, text="Média por setor",
                  font=("Segoe UI", 12, "bold"), text_color=TEXTO_ESCURO).pack(anchor="w", pady=(0, 8))
    linhas_media_setor = {}
    for estagio in (1, 2, 4):
        linha = ctk.CTkFrame(col_media_setor, fg_color="transparent")
        linha.pack(fill="x", pady=4)
        linha.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(linha, text=SETOR_LABEL[estagio], font=("Segoe UI", 11),
                      text_color=TEXTO_ESCURO, width=90, anchor="w").grid(row=0, column=0, sticky="w")
        barra = ctk.CTkProgressBar(linha, height=14, corner_radius=7,
                                     progress_color=SETOR_COR[estagio], fg_color=CINZA_BG)
        barra.set(0)
        barra.grid(row=0, column=1, sticky="ew", padx=8)
        lbl_valor = ctk.CTkLabel(linha, text="–", font=("Segoe UI", 11, "bold"),
                                   text_color=TEXTO_ESCURO, width=48, anchor="e")
        lbl_valor.grid(row=0, column=2, sticky="e")
        linhas_media_setor[estagio] = (barra, lbl_valor)

    # Coluna direita: donut de distribuição (matplotlib, combina com o
    # resto do projeto que já usa matplotlib nos gráficos)
    col_donut = ctk.CTkFrame(geral_card, fg_color="transparent")
    col_donut.grid(row=1, column=1, sticky="new", padx=(9, 18), pady=(4, 18))
    ctk.CTkLabel(col_donut, text="Distribuição das avaliações",
                  font=("Segoe UI", 12, "bold"), text_color=TEXTO_ESCURO).pack(anchor="w", pady=(0, 8))
    frame_donut = ctk.CTkFrame(col_donut, fg_color="transparent")
    frame_donut.pack(fill="x")

    msg_resumo = ctk.CTkLabel(col_donut, text="", font=("Segoe UI", 11),
                                text_color=TEXTO_CINZA, justify="left", wraplength=380)
    msg_resumo.pack(anchor="w", pady=(8, 0), fill="x")

    canvas_ref_donut = {}

    def _limpar_donut():
        if "fig" in canvas_ref_donut:
            try:
                plt.close(canvas_ref_donut["fig"])
            except Exception:
                pass
            canvas_ref_donut.clear()
        for w in frame_donut.winfo_children():
            w.destroy()

    def _renderizar_donut(stats):
        _limpar_donut()
        boa, media, ruim = stats["boa"], stats["media"], stats["ruim"]
        total = boa + media + ruim
        if not total:
            ctk.CTkLabel(frame_donut, text="Sem avaliações registradas ainda.",
                          font=("Segoe UI", 11), text_color=TEXTO_CINZA).pack(pady=20)
            msg_resumo.configure(text="")
            return

        valores = [boa, media, ruim]
        cores_donut = [VERDE_OK, AMARELO_OK, VERMELHO_OK]

        fig, ax = plt.subplots(figsize=(3.0, 3.0))
        fig.patch.set_facecolor(BRANCO)
        wedges, _ = ax.pie(valores, colors=cores_donut, startangle=90,
                            wedgeprops=dict(width=0.38, edgecolor=BRANCO, linewidth=2))
        ax.text(0, 0.12, f"{total}", ha="center", va="center",
                fontsize=20, fontweight="bold", color=TEXTO_ESCURO)
        ax.text(0, -0.18, "avaliações", ha="center", va="center",
                fontsize=9, color=TEXTO_CINZA)
        ax.set_aspect("equal")
        fig.tight_layout(pad=0.3)

        canvas_tk = FigureCanvasTkAgg(fig, master=frame_donut)
        canvas_tk.draw()
        canvas_widget = canvas_tk.get_tk_widget()
        canvas_widget.pack(side="left", padx=(0, 12))
        canvas_ref_donut["canvas"] = canvas_tk
        canvas_ref_donut["fig"] = fig

        legenda = ctk.CTkFrame(frame_donut, fg_color="transparent")
        legenda.pack(side="left", fill="y", expand=True)
        itens_legenda = [
            (VERDE_OK, "Boas (4-5)", boa),
            (AMARELO_OK, "Médias (2-3)", media),
            (VERMELHO_OK, "Ruins (1)", ruim),
        ]
        for cor, nome, qtd in itens_legenda:
            pct = round(100 * qtd / total) if total else 0
            linha = ctk.CTkFrame(legenda, fg_color="transparent")
            linha.pack(fill="x", pady=3, anchor="w")
            ctk.CTkLabel(linha, text="●", font=("Segoe UI", 13), text_color=cor,
                          width=16).pack(side="left")
            ctk.CTkLabel(linha, text=nome, font=("Segoe UI", 11), text_color=TEXTO_ESCURO,
                          anchor="w", width=92).pack(side="left")
            ctk.CTkLabel(linha, text=f"{pct}%", font=("Segoe UI", 11, "bold"),
                          text_color=TEXTO_ESCURO, width=36).pack(side="left")
            ctk.CTkLabel(linha, text=str(qtd), font=("Segoe UI", 11), text_color=TEXTO_CINZA,
                          width=40).pack(side="left")

        pct_boa = round(100 * boa / total) if total else 0
        if pct_boa >= 70:
            msg_resumo.configure(text=f"✅ Excelente! {pct_boa}% das avaliações são positivas. Continue assim!")
        elif pct_boa >= 50:
            msg_resumo.configure(text=f"🙂 Bom! {pct_boa}% das avaliações são positivas, mas dá pra melhorar.")
        else:
            msg_resumo.configure(text=f"⚠️ Atenção: apenas {pct_boa}% das avaliações são positivas.")

    # ════════════════════════════════════════════════════════════
    # CARDS POR SETOR (grid 2×2) — lista de itens com barra + nota + nº
    # ════════════════════════════════════════════════════════════
    setores_grid = ctk.CTkFrame(page, fg_color="transparent")
    setores_grid.grid(row=3, column=0, sticky="ew", pady=(0, 16))
    setores_grid.grid_columnconfigure((0, 1), weight=1, uniform="setores")

    cards_setor = {}   # estagio -> dict com referências de widgets

    def _criar_card_setor(parent, row, col, estagio):
        card = ctk.CTkFrame(parent, fg_color=BRANCO, corner_radius=12,
                             border_width=1, border_color=BORDA_CLARA)
        card.grid(row=row, column=col, sticky="nsew",
                  padx=(0, 9) if col == 0 else (9, 0),
                  pady=(0, 18))
        card.grid_columnconfigure(0, weight=1)

        topo = ctk.CTkFrame(card, fg_color="transparent")
        topo.pack(fill="x", padx=16, pady=(14, 4))
        esquerda = ctk.CTkFrame(topo, fg_color="transparent")
        esquerda.pack(side="left")
        ctk.CTkLabel(esquerda, text=f"{SETOR_ICONE[estagio]}  {SETOR_TITULO[estagio]}",
                      font=("Segoe UI", 13, "bold"), text_color=TEXTO_ESCURO).pack(anchor="w")
        ctk.CTkLabel(esquerda, text=SETOR_SUBTITULO[estagio], font=("Segoe UI", 10),
                      text_color=TEXTO_CINZA).pack(anchor="w")

        badge = ctk.CTkFrame(topo, fg_color=SETOR_COR_CLARA[estagio], corner_radius=8)
        badge.pack(side="right")
        ctk.CTkLabel(badge, text="Média do setor", font=("Segoe UI", 9),
                      text_color=SETOR_COR[estagio]).pack(padx=10, pady=(4, 0))
        lbl_badge_valor = ctk.CTkLabel(badge, text="–", font=("Segoe UI", 14, "bold"),
                                         text_color=SETOR_COR[estagio])
        lbl_badge_valor.pack(padx=10, pady=(0, 4))

        # Cabeçalho da "tabela"
        cab_tabela = ctk.CTkFrame(card, fg_color="transparent")
        cab_tabela.pack(fill="x", padx=16, pady=(10, 2))
        cab_tabela.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(cab_tabela, text="Item avaliado", font=("Segoe UI", 10, "bold"),
                      text_color=TEXTO_CINZA).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(cab_tabela, text="Média", font=("Segoe UI", 10, "bold"),
                      text_color=TEXTO_CINZA, width=56).grid(row=0, column=1, sticky="e")
        ctk.CTkLabel(cab_tabela, text="Avaliações", font=("Segoe UI", 10, "bold"),
                      text_color=TEXTO_CINZA, width=70).grid(row=0, column=2, sticky="e")

        frame_itens = ctk.CTkFrame(card, fg_color="transparent")
        frame_itens.pack(fill="x", padx=16, pady=(2, 8))

        rodape = ctk.CTkFrame(card, fg_color="transparent")
        rodape.pack(fill="x", padx=16, pady=(2, 14))
        ctk.CTkLabel(rodape, text="● Maior avaliação", font=("Segoe UI", 9),
                      text_color=VERDE_OK).pack(side="left")
        ctk.CTkLabel(rodape, text="   ● Menor avaliação", font=("Segoe UI", 9),
                      text_color=VERMELHO_OK).pack(side="left")

        cards_setor[estagio] = {
            "lbl_badge_valor": lbl_badge_valor,
            "frame_itens": frame_itens,
        }

    _criar_card_setor(setores_grid, 0, 0, 1)   # Comida
    _criar_card_setor(setores_grid, 0, 1, 2)   # Limpeza
    # Acolhimento ocupa a linha inteira abaixo
    acolhimento_card_outer = ctk.CTkFrame(setores_grid, fg_color="transparent")
    acolhimento_card_outer.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(0, 18))
    acolhimento_card_outer.grid_columnconfigure(0, weight=1)
    acolhimento_card_outer.grid_rowconfigure(0, weight=1)
    # Recria o card de Acolhimento (estagio 4) dentro do frame expandido
    _criar_card_setor(acolhimento_card_outer, 0, 0, 4)   # Acolhimento

    # Mapa de almoço por dia (preenchido ao processar avaliações)
    # usado pelo tooltip do card de Comida
    _almoco_por_dia = {}

    def _extrair_almoco_por_dia(_registros=None):
        """Lê o cardapio.json e monta {dia: almoco} para o tooltip do card de Comida."""
        import os, json
        mapa = {}
        try:
            # Sobe até a pasta raiz do projeto (onde fica a pasta dados/)
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cardapio_path = os.path.join(base, "dados", "cardapio.json")
            with open(cardapio_path, "r", encoding="utf-8") as f:
                cardapio = json.load(f)
            # cardapio.json tem formato: {"SEGUNDA": ["merenda manha", "almoco", "merenda tarde"], ...}
            CHAVES = {
                "Segunda-feira": "SEGUNDA",
                "Terça-feira":   "TERCA",
                "Quarta-feira":  "QUARTA",
                "Quinta-feira":  "QUINTA",
                "Sexta-feira":   "SEXTA",
            }
            for dia, chave in CHAVES.items():
                refeicoes = cardapio.get(chave, [])
                # índice 1 é o almoço (merenda manhã=0, almoço=1, merenda tarde=2)
                if len(refeicoes) > 1 and refeicoes[1]:
                    mapa[dia] = refeicoes[1]
        except Exception:
            pass
        return mapa

    def _tooltip_mostrar(widget, texto):
        """Exibe um tooltip flutuante próximo ao widget."""
        tip = ctk.CTkToplevel(widget)
        tip.wm_overrideredirect(True)
        tip.configure(fg_color="#1C1C1C")
        tip.attributes("-topmost", True)
        ctk.CTkLabel(tip, text=texto, font=("Segoe UI", 10),
                      text_color="white", wraplength=220).pack(padx=10, pady=6)
        x = widget.winfo_rootx() + 10
        y = widget.winfo_rooty() - 36
        tip.wm_geometry(f"+{x}+{y}")
        widget._tooltip_win = tip

    def _tooltip_esconder(widget):
        if hasattr(widget, "_tooltip_win"):
            try:
                widget._tooltip_win.destroy()
            except Exception:
                pass
            widget._tooltip_win = None

    def _renderizar_card_setor(estagio, stats):
        refs = cards_setor[estagio]
        refs["lbl_badge_valor"].configure(
            text=f"{stats['media_setor'].get(estagio, 0.0):.2f} ★" if stats["total_setor"].get(estagio) else "–")

        frame_itens = refs["frame_itens"]
        for w in frame_itens.winfo_children():
            w.destroy()

        itens = stats["por_setor_item"].get(estagio, {})
        if not itens:
            ctk.CTkLabel(frame_itens, text="Sem avaliações nesse setor ainda.",
                          font=("Segoe UI", 11), text_color=TEXTO_CINZA).pack(pady=14)
            return

        medias_item = {item: (sum(v) / len(v) if v else 0.0) for item, v in itens.items()}
        item_maior = max(medias_item, key=medias_item.get)
        item_menor = min(medias_item, key=medias_item.get)
        empate = item_maior == item_menor

        # ── Setor de Comida: ordenar seg→sex, manhã antes da tarde ──
        if estagio == 1:
            ORDEM_PERIODO = ["manhã", "manha", "mañana", "tarde"]
            def _chave_comida(item_nome):
                nome_lower = item_nome.lower()
                idx_dia = 99
                for i, dia in enumerate(DIAS_ORDEM):
                    if dia.lower() in nome_lower or DIAS_ABREV.get(dia, "").lower() in nome_lower:
                        idx_dia = i
                        break
                idx_periodo = 99
                for i, p in enumerate(ORDEM_PERIODO):
                    if p in nome_lower:
                        idx_periodo = i // 2  # manhã=0, tarde=1
                        break
                return (idx_dia, idx_periodo)
            itens_ord = sorted(itens.items(), key=lambda x: _chave_comida(x[0]))
        else:
            itens_ord = list(itens.items())

        for item, lista_notas in itens_ord:
            media_item = medias_item[item]
            qtd = len(lista_notas)

            linha = ctk.CTkFrame(frame_itens, fg_color="transparent")
            linha.pack(fill="x", pady=5)
            linha.grid_columnconfigure(0, weight=1)

            cor_barra = SETOR_COR[estagio]
            if not empate and item == item_maior:
                cor_barra = VERDE_OK
            elif not empate and item == item_menor:
                cor_barra = VERMELHO_OK

            cabeca_linha = ctk.CTkFrame(linha, fg_color="transparent")
            cabeca_linha.grid(row=0, column=0, columnspan=3, sticky="ew")
            cabeca_linha.grid_columnconfigure(0, weight=1)

            # Acolhimento ocupa linha inteira — exibe texto completo sem truncar
            _texto_item = _label_curto(item) if estagio != 4 else item
            lbl_item = ctk.CTkLabel(cabeca_linha, text=_texto_item, font=("Segoe UI", 11),
                          text_color=TEXTO_ESCURO, anchor="w", wraplength=600 if estagio == 4 else 0)
            lbl_item.grid(row=0, column=0, sticky="w")

            # Tooltip com almoço do dia — só para o card de Comida
            if estagio == 1:
                almoco_txt = None
                for dia in DIAS_ORDEM:
                    if dia.lower() in item.lower() or DIAS_ABREV.get(dia,"").lower() in item.lower():
                        almoco_txt = _almoco_por_dia.get(dia)
                        if not almoco_txt:
                            almoco_txt = f"Almoço de {DIAS_ABREV.get(dia, dia)}"
                        break
                if almoco_txt:
                    tip_texto = f"🍽️ Almoço: {almoco_txt}"
                    lbl_item.bind("<Enter>", lambda e, w=lbl_item, t=tip_texto: _tooltip_mostrar(w, t))
                    lbl_item.bind("<Leave>", lambda e, w=lbl_item: _tooltip_esconder(w))

            ctk.CTkLabel(cabeca_linha, text=f"{media_item:.2f} ★", font=("Segoe UI", 11, "bold"),
                          text_color=TEXTO_ESCURO, width=56, anchor="e").grid(row=0, column=1, sticky="e")
            ctk.CTkLabel(cabeca_linha, text=str(qtd), font=("Segoe UI", 11),
                          text_color=TEXTO_CINZA, width=70, anchor="e").grid(row=0, column=2, sticky="e")

            barra = ctk.CTkProgressBar(linha, height=10, corner_radius=5,
                                         progress_color=cor_barra, fg_color=CINZA_BG)
            barra.set(min(media_item / 5.0, 1.0))
            barra.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(3, 0))

    # ════════════════════════════════════════════════════════════
    # CARD "Melhor almoço da semana" (votação por dia)
    # ════════════════════════════════════════════════════════════
    almoco_card = ctk.CTkFrame(page, fg_color=BRANCO, corner_radius=12,
                                border_width=1, border_color=BORDA_CLARA)
    almoco_card.grid(row=4, column=0, sticky="ew", pady=(0, 24))

    topo_almoco = ctk.CTkFrame(almoco_card, fg_color="transparent")
    topo_almoco.pack(fill="x", padx=18, pady=(16, 8))
    ctk.CTkLabel(topo_almoco, text="🏆  Melhor almoço da semana (votação)",
                  font=("Segoe UI", 13, "bold"), text_color=TEXTO_ESCURO).pack(side="left")

    corpo_almoco = ctk.CTkFrame(almoco_card, fg_color="transparent")
    corpo_almoco.pack(fill="x", padx=18, pady=(0, 18))

    canvas_ref_almoco = {}

    def _limpar_almoco_chart():
        if "fig" in canvas_ref_almoco:
            try:
                plt.close(canvas_ref_almoco["fig"])
            except Exception:
                pass
            canvas_ref_almoco.clear()
        for w in corpo_almoco.winfo_children():
            w.destroy()

    def _renderizar_almoco(stats):
        _limpar_almoco_chart()
        votos_almoco = stats["votos_almoco"]
        dia_top, qtd_top = stats["almoco_favorito"]

        if not votos_almoco:
            ctk.CTkLabel(corpo_almoco, text="Ainda sem votos de almoço favorito.",
                          font=("Segoe UI", 11), text_color=TEXTO_CINZA).pack(pady=20)
            return

        esquerda = ctk.CTkFrame(corpo_almoco, fg_color=CINZA_BG, corner_radius=10)
        esquerda.pack(side="left", padx=(0, 16), pady=2, ipadx=14, ipady=10)
        ctk.CTkLabel(esquerda, text="🏆", font=("Segoe UI", 22)).pack()
        ctk.CTkLabel(esquerda, text=dia_top or "—", font=("Segoe UI", 15, "bold"),
                      text_color=TEXTO_ESCURO).pack()
        ctk.CTkLabel(esquerda, text=f"{qtd_top} voto{'s' if qtd_top != 1 else ''}",
                      font=("Segoe UI", 10), text_color=TEXTO_CINZA).pack(pady=(0, 2))

        dias = [d for d in DIAS_ORDEM if d in votos_almoco] or list(votos_almoco.keys())
        valores = [votos_almoco.get(d, 0) for d in dias]
        labels = [DIAS_ABREV.get(d, _label_curto(d, 10)) for d in dias]
        cores_barras = [LARANJA if d == dia_top else "#BDBDBD" for d in dias]

        fig, ax = plt.subplots(figsize=(6.0, 2.2))
        fig.patch.set_facecolor(BRANCO)
        ax.set_facecolor(BRANCO)
        barras = ax.bar(labels, valores, color=cores_barras, width=0.55)
        ax.set_ylim(0, max(valores) * 1.3 if valores else 1)
        for spine in ("top", "right", "left"):
            ax.spines[spine].set_visible(False)
        ax.get_yaxis().set_visible(False)
        ax.tick_params(axis="x", labelsize=10, colors=TEXTO_ESCURO)
        for barra, valor in zip(barras, valores):
            ax.annotate(str(valor), (barra.get_x() + barra.get_width() / 2, valor),
                         textcoords="offset points", xytext=(0, 4),
                         ha="center", fontsize=9, color=TEXTO_ESCURO, fontweight="bold")
        fig.tight_layout(pad=0.4)

        canvas_tk = FigureCanvasTkAgg(fig, master=corpo_almoco)
        canvas_tk.draw()
        canvas_tk.get_tk_widget().pack(side="left", fill="x", expand=True)
        canvas_ref_almoco["canvas"] = canvas_tk
        canvas_ref_almoco["fig"] = fig

    # ── Estado / ciclo de vida ──────────────────────────────────
    cache = {}
    _ativo = {"vivo": True}

    def _renderizar_tudo(stats):
        if not _ativo["vivo"] or not page.winfo_exists():
            return

        lbl_alunos.configure(text=str(stats["alunos_avaliaram"]))
        if stats["avaliacoes_anonimas"]:
            sub_alunos.configure(
                text=f"{stats['alunos_identificados']} identificados + {stats['avaliacoes_anonimas']} anônimas")
        else:
            sub_alunos.configure(text="respostas coletadas")



        lbl_media.configure(text=f"{stats['media_geral']:.2f}" if stats["total_estrelas"] else "–")
        sub_media.configure(text="de 5 estrelas")

        dia, votos = stats["almoco_favorito"]
        lbl_almoco.configure(text=dia or "—")
        sub_almoco.configure(
            text=f"{votos} voto{'s' if votos != 1 else ''}" if dia else "ainda sem votos")

        # Média por setor (barras CTk da coluna esquerda do card Geral)
        for estagio in (1, 2, 4):
            barra, lbl_valor = linhas_media_setor[estagio]
            media_e = stats["media_setor"].get(estagio, 0.0)
            barra.set(min(media_e / 5.0, 1.0) if stats["total_setor"].get(estagio) else 0)
            lbl_valor.configure(text=f"{media_e:.2f} ★" if stats["total_setor"].get(estagio) else "–")

        _renderizar_donut(stats)

        for estagio in (1, 2, 4):
            _renderizar_card_setor(estagio, stats)

        _renderizar_almoco(stats)

        lbl_atualizado.configure(text=f"Atualizado em {_agora_br().strftime('%H:%M:%S')}")

    # ── Função de carga de dados ──────────────────────────────────
    def _carregar():
        try:
            registros = _ler_avaliacoes_db()
        except Exception:
            registros = []

        _registros_cache["dados"] = registros

        # Descobre cursos presentes nos dados
        cursos_detectados = sorted({
            str(r.get("Curso", "")).strip()
            for r in registros
            if str(r.get("Curso", "")).strip() not in ("", "N/A")
        })
        opcoes = ["Todos"] + cursos_detectados

        # Aplica filtro de curso
        curso_selecionado = _filtro_curso["valor"]
        if curso_selecionado != "Todos":
            registros_filtrados = [
                r for r in registros
                if str(r.get("Curso", "")).strip() == curso_selecionado
            ]
        else:
            registros_filtrados = registros

        stats = _processar_avaliacoes(registros_filtrados)
        # Alimenta o mapa de almoço por dia para os tooltips do card de Comida
        _almoco_por_dia.update(_extrair_almoco_por_dia(registros_filtrados))

        def _atualizar_ui():
            if not _ativo["vivo"] or not page.winfo_exists():
                return
            # Atualiza opções do filtro sem perder a seleção atual
            valor_atual = cb_curso.get()
            cb_curso.configure(values=opcoes)
            if valor_atual in opcoes:
                cb_curso.set(valor_atual)
            else:
                cb_curso.set("Todos")
                _filtro_curso["valor"] = "Todos"

            # Info de quantos registros filtrados
            if curso_selecionado != "Todos":
                total_geral = len(_registros_cache["dados"])
                lbl_filtro_info.configure(
                    text=f"{len(registros_filtrados)} de {total_geral} avaliações")
            else:
                lbl_filtro_info.configure(text="")

            cache["stats"] = stats
            _renderizar_tudo(stats)

        page.after(0, _atualizar_ui)

    def _limpar_ao_destruir(event=None):
        _ativo["vivo"] = False  # sinaliza threads para pararem
        _limpar_donut()
        _limpar_almoco_chart()

    def _aplicar_filtro_curso(valor):
        _filtro_curso["valor"] = valor
        threading.Thread(target=_carregar, daemon=True).start()

    cb_curso.configure(command=_aplicar_filtro_curso)

    page.bind("<Destroy>", _limpar_ao_destruir)

    threading.Thread(target=_carregar, daemon=True).start()

    # Botão Atualizar
    btn_row = ctk.CTkFrame(page, fg_color="transparent")
    btn_row.grid(row=5, column=0, sticky="w", pady=(0, 24))
    ctk.CTkButton(btn_row, text="↻  Atualizar", fg_color=VERDE_VIBRANTE,
                   hover_color=VERDE_ESCURO, width=130, height=36,
                   font=("Segoe UI", 11, "bold"),
                   command=lambda: threading.Thread(target=_carregar, daemon=True).start()
                   ).pack(side="left")
    iniciar_polling(page, _carregar)
    return page