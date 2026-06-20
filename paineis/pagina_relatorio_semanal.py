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
    SETOR_LABEL = {1: "🍽️ Comida", 2: "🧹 Limpeza", 3: "📚 Ensino", 4: "✨ Semana"}
    SETOR_ICONE = {1: "🍽️", 2: "🧹", 3: "📚", 4: "✨"}
    SETOR_TITULO = {1: "COMIDA", 2: "LIMPEZA", 3: "ENSINO", 4: "SEMANA"}
    SETOR_SUBTITULO = {
        1: "Avaliações do setor de alimentação",
        2: "Avaliações do setor de limpeza",
        3: "Avaliações do setor de ensino",
        4: "Avaliações gerais da semana",
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

    # ── Cards de resumo (4 no topo, igual ao mockup) ───────────────
    cards_row = ctk.CTkFrame(page, fg_color="transparent")
    cards_row.grid(row=1, column=0, sticky="ew", pady=(0, 16))
    cards_row.grid_columnconfigure((0, 1, 2, 3), weight=1)

    lbl_alunos, sub_alunos = _card_resumo(
        cards_row, 0, 0, "🙋", VERDE_CLARO, VERDE_VIBRANTE,
        "Alunos que avaliaram", "...", "respostas coletadas")
    lbl_total, sub_total = _card_resumo(
        cards_row, 0, 1, "📋", AZUL_CLARO, AZUL_FORTE,
        "Total de avaliações", "...", "registros no banco")
    lbl_media, sub_media = _card_resumo(
        cards_row, 0, 2, "⭐", ROXO_CLARO, ROXO_FORTE,
        "Média geral", "...", "de 5 estrelas")
    lbl_almoco, sub_almoco = _card_resumo(
        cards_row, 0, 3, "🍽️", "#FFF3E0", LARANJA,
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
    for estagio in (1, 2, 3, 4):
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
    _criar_card_setor(setores_grid, 1, 0, 3)   # Ensino
    _criar_card_setor(setores_grid, 1, 1, 4)   # Semana

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

        for item, lista_notas in itens.items():
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
            ctk.CTkLabel(cabeca_linha, text=_label_curto(item), font=("Segoe UI", 11),
                          text_color=TEXTO_ESCURO, anchor="w").grid(row=0, column=0, sticky="w")
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

        lbl_total.configure(text=str(stats["total_registros"]))
        sub_total.configure(text="registros no banco")

        lbl_media.configure(text=f"{stats['media_geral']:.2f}" if stats["total_estrelas"] else "–")
        sub_media.configure(text="de 5 estrelas")

        dia, votos = stats["almoco_favorito"]
        lbl_almoco.configure(text=dia or "—")
        sub_almoco.configure(
            text=f"{votos} voto{'s' if votos != 1 else ''}" if dia else "ainda sem votos")

        # Média por setor (barras CTk da coluna esquerda do card Geral)
        for estagio in (1, 2, 3, 4):
            barra, lbl_valor = linhas_media_setor[estagio]
            media_e = stats["media_setor"].get(estagio, 0.0)
            barra.set(min(media_e / 5.0, 1.0) if stats["total_setor"].get(estagio) else 0)
            lbl_valor.configure(text=f"{media_e:.2f} ★" if stats["total_setor"].get(estagio) else "–")

        _renderizar_donut(stats)

        for estagio in (1, 2, 3, 4):
            _renderizar_card_setor(estagio, stats)

        _renderizar_almoco(stats)

        lbl_atualizado.configure(text=f"Atualizado em {_agora_br().strftime('%H:%M:%S')}")

    # ── Função de carga de dados ──────────────────────────────────
    def _carregar():
        try:
            registros = _ler_avaliacoes_db()
        except Exception:
            registros = []

        stats = _processar_avaliacoes(registros)

        def _atualizar_ui():
            if not _ativo["vivo"] or not page.winfo_exists():
                return
            cache["stats"] = stats
            _renderizar_tudo(stats)

        page.after(0, _atualizar_ui)

    def _limpar_ao_destruir(event=None):
        _ativo["vivo"] = False  # sinaliza threads para pararem
        _limpar_donut()
        _limpar_almoco_chart()

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
    return page