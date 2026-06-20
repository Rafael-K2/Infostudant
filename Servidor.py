"""
SERVIDOR MARWIN - ServidorV15.py
======================================
Rode ESTE arquivo no PC da escola.

O que ele faz ao iniciar:
  1. Prepara o servidor Flask na porta 5000
  2. Conecta-se ao PostgreSQL Neon como fonte de dados
  3. Abre o painel admin Tkinter com IP local e botão copiar URL

Instalação (uma vez só):
  pip install flask flask-cors fpdf2 qrcode pillow psycopg2-binary

O index.html pode usar a API na nuvem (ApiNuvem.py) — configure dados/cloud_config.json.
O painel admin sincroniza cardápio/eventos/config com a nuvem automaticamente.

Organização dos QR Codes: qrcodes_marwin/
    1 Ano - Desenvolvimento de Sistemas/
      2026001_Joao_Silva_1_Ano_Desenvolvimento_de_Sistemas.png
      ...
    2 Ano - Redes de Computadores/
      ...
    3 Ano - Informatica/
      ...
"""

import os, json, csv, datetime, threading, calendar, time, io, base64, re, logging, smtplib, shutil, zipfile, unicodedata, socket
from collections import Counter
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import datetime

import qrcode
from PIL import Image

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from logging.handlers import TimedRotatingFileHandler

# Páginas do Painel Admin extraídas para módulos próprios (refatoração
# incremental — comportamento idêntico ao original, só organização do código).
from paineis.pagina_cardapio import criar_pagina_cardapio as _criar_pagina_cardapio_extraida
from paineis.pagina_eventos import criar_pagina_eventos as _criar_pagina_eventos_extraida
from paineis.helpers import card_resumo as _card_resumo_extraido, card_tabela as _card_tabela_extraido
from paineis.pagina_avaliacoes import criar_pagina_avaliacoes as _criar_pagina_avaliacoes_extraida
from paineis.pagina_relatorio_semanal import criar_pagina_relatorio_semanal as _criar_pagina_relatorio_semanal_extraida
from paineis.pagina_visao_geral import criar_pagina_visao_geral as _criar_pagina_visao_geral_extraida
from paineis.pagina_refeitorio import criar_pagina_refeitorio as _criar_pagina_refeitorio_extraida
from paineis.pagina_frequencia import criar_pagina_frequencia as _criar_pagina_frequencia_extraida
from paineis.pagina_historico import criar_pagina_historico as _criar_pagina_historico_extraida
from paineis.pagina_qrcodes import criar_pagina_qrcodes as _criar_pagina_qrcodes_extraida
from paineis.pagina_logs import criar_pagina_logs as _criar_pagina_logs_extraida

# ── Fuso horário oficial do Brasil ───────────────────────────────────────────
# Horário de Brasília = UTC-3, fixo (o Brasil não usa mais horário de verão
# desde 2019). Definido explicitamente para que o horário/data registrados
# ao ler o QR Code NÃO dependam do fuso horário configurado no sistema
# operacional/servidor onde este script está rodando (ex.: servidores em
# nuvem costumam usar UTC por padrão, o que atrasava/avançava os horários).
FUSO_BRASIL = datetime.timezone(datetime.timedelta(hours=-3))

def _agora_br():
    """Retorna o datetime atual já corrigido para o horário de Brasília (UTC-3)."""
    return datetime.datetime.now(FUSO_BRASIL)

app = Flask(__name__)
CORS(app)

DADOS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "dados"))
os.makedirs(DADOS_DIR, exist_ok=True)

# Subpastas organizacionais de dados/ — mantém a raiz só com os JSONs de
# configuração que o app lê/grava o tempo todo; tudo que é "histórico" ou
# "gerado" fica isolado em sua própria pasta.
LOGS_DIR    = os.path.join(DADOS_DIR, "logs")
LOGO_DIR    = os.path.join(DADOS_DIR, "logo")
EXPORTS_DIR = os.path.join(DADOS_DIR, "exports_manuais")
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(LOGO_DIR, exist_ok=True)
os.makedirs(EXPORTS_DIR, exist_ok=True)

# ── Configuração de Logging ───────────────────────────────────────────────────
LOG_FILE = os.path.join(LOGS_DIR, "marwin.log")
logger = logging.getLogger("marwin")
logger.setLevel(logging.DEBUG)
try:
    log_handler = TimedRotatingFileHandler(
        LOG_FILE, when="midnight", interval=1, backupCount=7, encoding="utf-8"
    )
    log_handler.setLevel(logging.DEBUG)
    log_format = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s",
                                     datefmt="%d/%m/%Y %H:%M:%S")
    log_handler.setFormatter(log_format)
    logger.addHandler(log_handler)
except Exception as e:
    print(f"[LOG] Erro ao configurar logging: {e}")

def _buscar_logo_png():
    # Procura primeiro em dados/logo/ (local correto e isolado). Mantém a
    # busca antiga em DADOS_DIR como fallback só por compatibilidade com
    # instalações antigas que ainda tenham o PNG solto na raiz.
    for pasta in (LOGO_DIR, DADOS_DIR):
        if os.path.isdir(pasta):
            logos = [n for n in os.listdir(pasta) if n.lower().endswith(".png")]
            if logos:
                for nome in logos:
                    if "logo" in nome.lower():
                        return os.path.join(pasta, nome)
                return os.path.join(pasta, logos[0])
    return None

CARDAPIO_FILE    = os.path.join(DADOS_DIR, "cardapio.json")
EVENTOS_FILE     = os.path.join(DADOS_DIR, "eventos.json")
CONFIG_FILE      = os.path.join(DADOS_DIR, "config_sistema.json")
TEMA_FILE        = os.path.join(DADOS_DIR, "tema_config.json")
LISTA_ALUNOS_FILE = os.path.join(DADOS_DIR, "lista_alunos.json")
DB_CONFIG_FILE   = os.path.join(DADOS_DIR, "db_config.json")
CLOUD_CONFIG_FILE = os.path.join(DADOS_DIR, "cloud_config.json")
# Pasta onde as imagens dos QR Codes ficam guardadas. O app procura aqui
# primeiro antes de gerar a imagem na hora.
QRCODES_DIR = os.path.join(DADOS_DIR, "qrcodes_marwin")
os.makedirs(QRCODES_DIR, exist_ok=True)
MESES_PT = (
    "janeiro", "fevereiro", "marco", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)
DEFAULT_ADMIN_PLAIN = "Marwin2026"
# Prefer env var MARWIN_ADMIN_PASS (pode conter hash bcrypt). Fallback para DEFAULT_ADMIN_PLAIN.
ADMIN_PASSWORD = os.getenv("MARWIN_ADMIN_PASS", DEFAULT_ADMIN_PLAIN)
# Senha em texto claro para envio no header X-Senha ao sincronizar com a nuvem.
# Se MARWIN_ADMIN_PASS for um hash bcrypt, use MARWIN_ADMIN_PLAIN_PASS com a senha real.
ADMIN_PLAIN_PASS = os.getenv("MARWIN_ADMIN_PLAIN_PASS", DEFAULT_ADMIN_PLAIN)
if ADMIN_PASSWORD == DEFAULT_ADMIN_PLAIN:
    print(
        "\n[AVISO DE SEGURANÇA] A variável de ambiente MARWIN_ADMIN_PASS não está definida.\n"
        "O servidor está usando a senha padrão. Defina MARWIN_ADMIN_PASS para maior segurança.\n"
    )

# Try to import bcrypt if available (optional). If ADMIN_PASSWORD is a bcrypt hash, we'll use it.
try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except Exception:
    BCRYPT_AVAILABLE = False

def _senha_bate(pw: str, senha_config: str) -> bool:
    """Compara `pw` com `senha_config`, aceitando tanto senha em texto puro
    quanto hash bcrypt (mesma regra usada para a senha de admin)."""
    if not pw or not senha_config:
        return False
    if BCRYPT_AVAILABLE and isinstance(senha_config, str) and senha_config.startswith("$2"):
        try:
            return bcrypt.checkpw(pw.encode("utf-8"), senha_config.encode("utf-8"))
        except Exception:
            return False
    return secrets.compare_digest(pw, senha_config)

# ── Hierarquia de senhas do Painel Administrativo (desktop) ────────────────
# Cada perfil tem sua própria senha e só enxerga as abas relevantes ao seu
# trabalho. ADM continua usando MARWIN_ADMIN_PASS (compatível com instalações
# já existentes) e sempre tem acesso a tudo.
DEFAULT_COOR_PLAIN       = "Coordenacao2026"
DEFAULT_SERC_PLAIN       = "Secretaria2026"
DEFAULT_REFEITORIO_PLAIN = "Refeitorio2026"

COOR_PASSWORD       = os.getenv("MARWIN_COOR_PASS", DEFAULT_COOR_PLAIN)
SERC_PASSWORD       = os.getenv("MARWIN_SERC_PASS", DEFAULT_SERC_PLAIN)
REFEITORIO_PASSWORD = os.getenv("MARWIN_REFEITORIO_PASS", DEFAULT_REFEITORIO_PLAIN)

for _nome_var, _valor_atual, _valor_padrao in (
    ("MARWIN_COOR_PASS", COOR_PASSWORD, DEFAULT_COOR_PLAIN),
    ("MARWIN_SERC_PASS", SERC_PASSWORD, DEFAULT_SERC_PLAIN),
    ("MARWIN_REFEITORIO_PASS", REFEITORIO_PASSWORD, DEFAULT_REFEITORIO_PLAIN),
):
    if _valor_atual == _valor_padrao:
        print(
            f"\n[AVISO DE SEGURANÇA] A variável de ambiente {_nome_var} não está definida.\n"
            f"O servidor está usando a senha padrão desse perfil. Defina {_nome_var} para maior segurança.\n"
        )

PERFIS_SENHAS = {
    "ADM": ADMIN_PASSWORD,
    "COOR": COOR_PASSWORD,
    "SERC": SERC_PASSWORD,
    "REFEITORIO": REFEITORIO_PASSWORD,
}
PERFIS_NOME_EXIBICAO = {
    "ADM": "Administrador(a)",
    "COOR": "Coordenação",
    "SERC": "Secretaria",
    "REFEITORIO": "Refeitório",
}
# Quais abas do Painel Administrativo cada perfil pode ver.
PERFIS_ABAS = {
    "ADM": {
        "Visão Geral", "Avaliações", "Relatório Semanal", "Editar Cardápio",
        "Editar Eventos", "Refeitório", "Frequência", "Histórico",
        "QR Codes", "Logs",
    },
    "COOR": {
        "Visão Geral", "Avaliações", "Relatório Semanal",
        "Editar Eventos", "Frequência", "Histórico",
    },
    "SERC": {
        "Visão Geral", "Editar Eventos", "Frequência", "Histórico", "QR Codes",
    },
    "REFEITORIO": {
        "Visão Geral", "Editar Cardápio", "Refeitório",
    },
}

def _identificar_perfil(pw: str):
    """Devolve o nome do perfil (ADM/COOR/SERC/REFEITORIO) cuja senha bate
    com `pw` — checa ADM primeiro — ou None se nenhuma senha bater."""
    for perfil, senha_config in PERFIS_SENHAS.items():
        if _senha_bate(pw, senha_config):
            return perfil
    return None

def ler_json(path, padrao):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return padrao

def salvar_json(path, dados):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def _buscar_aluno_por_matricula(matricula):
    """Busca o cadastro oficial do aluno (nome/serie/curso) pela matrícula.

    A matrícula é só dígitos, então nunca sofre a corrupção de acentos do
    leitor USB (que pode fundir um "acento morto" perdido com a vogal
    seguinte, virando p.ex. "Â" onde não deveria existir nenhum acento).
    Por isso ela é a única coisa do QR Code em que dá pra confiar 100%.
    Sempre que a matrícula bater com um cadastro em lista_alunos.json,
    o nome/série/curso usados no registro são os do cadastro — não o que
    o leitor "digitou" — evitando nomes com lixo na tela e ordenação
    alfabética quebrada por causa de um acento fantasma.
    """
    if not matricula:
        return None
    lista = ler_json(LISTA_ALUNOS_FILE, [])
    for aluno in lista:
        if str(aluno.get("matricula", "")).strip() == matricula:
            return aluno
    return None

def _ler_cloud_config():
    return ler_json(CLOUD_CONFIG_FILE, {"api_url": "", "sincronizar_automatico": True})

def _cloud_api_url():
    return _ler_cloud_config().get("api_url", "").strip().rstrip("/")

def _sync_nuvem(rota, metodo, dados=None):

    cfg = _ler_cloud_config()
    base = cfg.get("api_url", "").strip().rstrip("/")
    if not base:
        logger.debug(f"Sync nuvem ignorado ({rota}): api_url não configurada em cloud_config.json")
        return False
    if not cfg.get("sincroniz   ar_automatico", True):
        logger.debug(f"Sync nuvem ignorado ({rota}): sincronizar_automatico=false")
        return False
    import urllib.request
    url = base + rota
    body = json.dumps(dados, ensure_ascii=False).encode("utf-8") if dados is not None else None
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "X-Senha": ADMIN_PLAIN_PASS},
        method=metodo,
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            ok = 200 <= resp.status < 300
            if not ok:
                logger.warning(f"Sync nuvem ({rota}): HTTP {resp.status}")

            return ok
    except urllib.error.HTTPError as e:
        corpo = ""
        try:
            corpo = e.read().decode("utf-8", errors="replace")[:200]
        except Exception:
            pass
        logger.warning(f"Sync nuvem falhou ({rota}): HTTP {e.code} — {corpo}")
        return False
    except Exception as e:
        logger.warning(f"Sync nuvem falhou ({rota}): {e}")

        return False

def _sincronizar_tudo_nuvem():
    ok = True
    if not _sync_nuvem("/admin/cardapio", "PUT", ler_json(CARDAPIO_FILE, CARDAPIO_PADRAO)):
        ok = False
    if not _sync_nuvem("/admin/eventos", "PUT", ler_json(EVENTOS_FILE, EVENTOS_PADRAO)):
        ok = False
    if not _sync_nuvem("/admin/config", "PUT", ler_json(CONFIG_FILE, {"avaliacoes_ativas": True, "modo_leitura": "camera"})):
        ok = False
    if ok and _cloud_api_url():
        logger.info("Configurações sincronizadas com a API na nuvem")

    return ok

# ── Credenciais do banco — use variável de ambiente para evitar exposição ──────
# Defina MARWIN_DB_URL no sistema antes de rodar:
#   Windows : set MARWIN_DB_URL=postgresql://usuario:senha@host/neondb?sslmode=require
#   Linux   : export MARWIN_DB_URL=postgresql://...
_DB_FALLBACK = (
    "postgresql://neondb_owner:npg_ydP7rqBR0ZoQ@"
    "ep-broad-mountain-apatc77i-pooler.c-7.us-east-1.aws.neon.tech"
    "/neondb?sslmode=require&channel_binding=require"
)
DB_DEFAULT_CONNECTION = os.getenv("MARWIN_DB_URL", _DB_FALLBACK)
if DB_DEFAULT_CONNECTION == _DB_FALLBACK:
    print(
        "\n[AVISO DE SEGURANÇA] A variável de ambiente MARWIN_DB_URL não está definida.\n"
        "O servidor está usando a connection string padrão embutida no código.\n"
        "Defina MARWIN_DB_URL para evitar expor credenciais.\n"
    )
PG_POOL = None

def _carregar_db_config():
    cfg = ler_json(DB_CONFIG_FILE, {})
    if not cfg.get("connection_string"):
        cfg["connection_string"] = DB_DEFAULT_CONNECTION
        salvar_json(DB_CONFIG_FILE, cfg)
    return cfg

def _iniciar_pool_pg():
    global PG_POOL
    if PG_POOL is not None:
        return
    cfg = _carregar_db_config()
    try:
        import psycopg2
        from psycopg2 import pool
        PG_POOL = pool.ThreadedConnectionPool(1, 10, cfg["connection_string"])
        logger.info("Pool PostgreSQL inicializado")
    except Exception as e:
        PG_POOL = None
        logger.warning("PostgreSQL indisponível")

def get_pg_conn():
    global PG_POOL
    if PG_POOL is None:
        _iniciar_pool_pg()
    if PG_POOL is None:
        return None
    try:
        return PG_POOL.getconn()
    except Exception as e:
        logger.warning("Falha ao obter conexão PostgreSQL")
        return None

def _release_pg_conn(conn):
    global PG_POOL
    if not conn:
        return
    try:
        if PG_POOL:
            PG_POOL.putconn(conn)
        else:
            conn.close()
    except Exception:
        try:
            conn.close()
        except Exception:
            pass

def _executar_pg(sql, params=None, fetch=False):
    conn = get_pg_conn()
    if conn is None:
        raise RuntimeError("PostgreSQL indisponível")
    cur = None
    try:
        cur = conn.cursor()
        cur.execute(sql, params or ())
        if fetch:
            cols = [d[0] for d in cur.description] if cur.description else []
            rows = cur.fetchall()
            return [dict(zip(cols, row)) for row in rows]
        conn.commit()
        return []
    finally:
        if cur is not None:
            try:
                cur.close()
            except Exception:
                pass
        _release_pg_conn(conn)

def _get_local_ip():
    try:
        ip = socket.gethostbyname(socket.gethostname())
        if ip.startswith("127.") or ip == "0.0.0.0":
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
            finally:
                s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _criar_tabelas_neon():
    try:
        _executar_pg(
            """
            CREATE TABLE IF NOT EXISTS refeitorio (
                data TEXT NOT NULL,
                horaentrada TEXT NOT NULL,
                matricula TEXT NOT NULL,
                nome TEXT NOT NULL,
                serie TEXT,
                curso TEXT,
                refeicao TEXT
            );
            """
        )
        _executar_pg(
            """
            CREATE TABLE IF NOT EXISTS frequencia (
                data TEXT NOT NULL,
                horaentrada TEXT NOT NULL,
                matricula TEXT NOT NULL,
                nome TEXT NOT NULL,
                serie TEXT,
                curso TEXT,
                aula TEXT
            );
            """
        )
        _executar_pg(
            """
            CREATE TABLE IF NOT EXISTS avaliacoes (
                data TEXT NOT NULL,
                aluno TEXT NOT NULL,
                serie TEXT,
                curso TEXT,
                estagio TEXT,
                item TEXT,
                nota TEXT
            );
            """
        )
        _executar_pg(
            """
            CREATE TABLE IF NOT EXISTS sistema_config (
                chave TEXT PRIMARY KEY,
                valor JSONB NOT NULL
            );
            """
        )
        logger.info("Tabelas Neon verificadas/criadas")
    except Exception as e:
        logger.warning(f"Nao foi possivel criar tabelas Neon: {e}")


def _ler_refeitorio_hoje_db():
    rows = _executar_pg(
        "SELECT data, horaentrada, matricula, nome, serie, curso, refeicao FROM refeitorio WHERE data = %s",
        (_hoje(),),
        fetch=True
    )
    if not rows:
        return []
    return [
        [row["data"], row["horaentrada"], row["matricula"], row["nome"], row["serie"], row["curso"], row["refeicao"]]
        for row in rows
    ]


def _inserir_refeitorio_db(registro):
    _executar_pg(
        "INSERT INTO refeitorio (data, horaentrada, matricula, nome, serie, curso, refeicao) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (registro[0], registro[1], registro[2], registro[3], registro[4], registro[5], registro[6])
    )


def _apagar_refeitorio_data_db(data_alvo):
    _executar_pg("DELETE FROM refeitorio WHERE data = %s", (data_alvo,))


def _refeitorio_duplicado_db(matricula, refeicao):
    try:
        rows = _executar_pg(
            "SELECT horaentrada, nome FROM refeitorio WHERE data = %s AND matricula = %s AND refeicao = %s LIMIT 1",
            (_hoje(), matricula, refeicao),
            fetch=True
        )
        if not rows:
            return None

        total_hoje = _executar_pg(
            "SELECT COUNT(*) AS total FROM refeitorio WHERE data = %s",
            (_hoje(),),
            fetch=True
        )
        total_refeicao = _executar_pg(
            "SELECT COUNT(*) AS total FROM refeitorio WHERE data = %s AND refeicao = %s",
            (_hoje(), refeicao),
            fetch=True
        )
        return {
            "hora": rows[0]["horaentrada"],
            "nome": rows[0]["nome"],
            "total_hoje": total_hoje[0].get("total", 0) if total_hoje else 0,
            "total_refeicao": total_refeicao[0].get("total", 0) if total_refeicao else 0,
        }
    except Exception as e:
        logger.warning(f"PostgreSQL indisponível para verificação de duplicidade de refeitorio: {e}")
        return None


def _ler_frequencia_hoje_db():
    rows = _executar_pg(
        "SELECT data, horaentrada, matricula, nome, serie, curso, aula FROM frequencia WHERE data = %s",
        (_hoje(),),
        fetch=True
    )
    if not rows:
        return []
    return [
        [row["data"], row["horaentrada"], row["matricula"], row["nome"], row["serie"], row["curso"], row["aula"]]
        for row in rows
    ]


def _inserir_frequencia_db(registro):
    _executar_pg(
        "INSERT INTO frequencia (data, horaentrada, matricula, nome, serie, curso, aula) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (registro[0], registro[1], registro[2], registro[3], registro[4], registro[5], registro[6])
    )


def _apagar_frequencia_data_db(data_alvo):
    _executar_pg("DELETE FROM frequencia WHERE data = %s", (data_alvo,))


def _frequencia_duplicado_db(matricula):
    try:
        rows = _executar_pg(
            "SELECT horaentrada, nome FROM frequencia WHERE data = %s AND matricula = %s LIMIT 1",
            (_hoje(), matricula),
            fetch=True
        )
        if not rows:
            return None

        total_hoje = _executar_pg(
            "SELECT COUNT(*) AS total FROM frequencia WHERE data = %s",
            (_hoje(),),
            fetch=True
        )
        return {
            "hora": rows[0]["horaentrada"],
            "nome": rows[0]["nome"],
            "total_hoje": total_hoje[0].get("total", 0) if total_hoje else 0,
        }
    except Exception as e:
        logger.warning(f"PostgreSQL indisponível para verificação de duplicidade de frequencia: {e}")
        return None


def _inserir_avaliacao_db(registro):
    _executar_pg(
        "INSERT INTO avaliacoes (data, aluno, serie, curso, estagio, item, nota) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (registro[0], registro[1], registro[2], registro[3], registro[4], registro[5], registro[6])
    )


def _ler_avaliacoes_db():
    rows = _executar_pg(
        "SELECT data, aluno, serie, curso, estagio, item, nota FROM avaliacoes ORDER BY data DESC",
        (),
        fetch=True
    )
    if not rows:
        return []
    return [
        {
            "Data": row["data"],
            "Aluno": row["aluno"],
            "Serie": row["serie"],
            "Curso": row["curso"],
            "Estagio": row["estagio"],
            "Item": row["item"],
            "Nota": row["nota"],
        }
        for row in rows
    ]


def _ler_refeitorio_todos_db():
    rows = _executar_pg(
        "SELECT data, horaentrada, matricula, nome, serie, curso, refeicao FROM refeitorio ORDER BY data DESC, horaentrada DESC",
        (),
        fetch=True,
    )
    if not rows:
        return []
    return [
        [row["data"], row["horaentrada"], row["matricula"], row["nome"], row["serie"], row["curso"], row["refeicao"]]
        for row in rows
    ]


def _ler_frequencia_todos_db():
    rows = _executar_pg(
        "SELECT data, horaentrada, matricula, nome, serie, curso, aula FROM frequencia ORDER BY data DESC, horaentrada DESC",
        (),
        fetch=True,
    )
    if not rows:
        return []
    return [
        [row["data"], row["horaentrada"], row["matricula"], row["nome"], row["serie"], row["curso"], row["aula"]]
        for row in rows
    ]


def _avaliacoes_para_linhas():
    return [
        [r["Data"], r["Aluno"], r["Serie"], r["Curso"], r["Estagio"], r["Item"], r["Nota"]]
        for r in _ler_avaliacoes_db()
    ]


def _escrever_csv(caminho, header, linhas):
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(linhas)


def _csv_bytes(header, linhas):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(linhas)
    out = io.BytesIO(buf.getvalue().encode("utf-8"))
    out.seek(0)
    return out


def _nome_backup_mes_sugerido():
    hoje = _agora_br().date()
    return f"backup_{MESES_PT[hoje.month - 1]}_{hoje.year}"


def _exportar_backup_mensal_csv(nome_base):
    """Exporta todas as tabelas do banco para CSVs em dados/backups/YYYY_MM/."""
    nome_base = re.sub(r'[<>:"/\\|?*]', "_", (nome_base or "").strip())
    if not nome_base:
        raise ValueError("Nome do arquivo inválido")
    pasta = os.path.join(DADOS_DIR, "backups", _agora_br().date().strftime("%Y_%m"))
    os.makedirs(pasta, exist_ok=True)
    arquivos = []
    _escrever_csv(
        os.path.join(pasta, f"{nome_base}_avaliacoes_escola.csv"),
        ["Data", "Aluno", "Serie", "Curso", "Estagio", "Item", "Nota"],
        _avaliacoes_para_linhas(),
    )
    arquivos.append(f"{nome_base}_avaliacoes_escola.csv")
    _escrever_csv(
        os.path.join(pasta, f"{nome_base}_refeitorio.csv"),
        ["Data", "HoraEntrada", "Matricula", "Nome", "Serie", "Curso", "Refeicao"],
        _ler_refeitorio_todos_db(),
    )
    arquivos.append(f"{nome_base}_refeitorio.csv")
    _escrever_csv(
        os.path.join(pasta, f"{nome_base}_frequencia.csv"),
        ["Data", "HoraEntrada", "Matricula", "Nome", "Serie", "Curso", "Aula"],
        _ler_frequencia_todos_db(),
    )
    arquivos.append(f"{nome_base}_frequencia.csv")
    return pasta, arquivos


def _avaliacao_ja_existe_db(nome, semana_iso, ano_iso):
    if not nome:
        return False
    try:
        rows = _executar_pg(
            "SELECT data FROM avaliacoes WHERE lower(aluno) = lower(%s)",
            (nome,),
            fetch=True
        )
    except Exception as e:
        logger.warning(f"PostgreSQL indisponível para verificação de duplicidade: {e}")
        return False

    if not rows:
        return False
    for row in rows:
        try:
            data_str = row["data"].split(" ")[0]
            data_obj = datetime.datetime.strptime(data_str, "%d/%m/%Y").date()
            if data_obj.isocalendar()[1] == semana_iso and data_obj.isocalendar()[0] == ano_iso:
                return True
        except Exception:
            continue
    return False


def _apagar_avaliacoes_db():
    _executar_pg("DELETE FROM avaliacoes", ())


def _limpar_tabelas_neon():
    _executar_pg("DELETE FROM refeitorio", ())
    _executar_pg("DELETE FROM frequencia", ())
    _executar_pg("DELETE FROM avaliacoes", ())
    logger.info("Tabelas Neon refeitorio, frequencia e avaliacoes limpas")


# ── Colunas de cada tabela para detecção automática ──────────────────────────
_COLS_REFEITORIO  = {"Data", "HoraEntrada", "Matricula", "Nome", "Serie", "Curso", "Refeicao"}
_COLS_FREQUENCIA  = {"Data", "HoraEntrada", "Matricula", "Nome", "Serie", "Curso", "Aula"}
_COLS_AVALIACOES  = {"Data", "Aluno", "Serie", "Curso", "Estagio", "Item", "Nota"}


def _detectar_tabela_csv(colunas_csv):
    """Retorna 'refeitorio', 'frequencia', 'avaliacoes' ou None."""
    cols = set(colunas_csv)
    if "Refeicao" in cols and _COLS_REFEITORIO.issubset(cols):
        return "refeitorio"
    if "Aula" in cols and _COLS_FREQUENCIA.issubset(cols):
        return "frequencia"
    if "Nota" in cols and _COLS_AVALIACOES.issubset(cols):
        return "avaliacoes"
    return None


def _duplicata_existe(tabela, linha):
    """Verifica se o registro já existe no banco (comparação por campos-chave)."""
    try:
        if tabela == "refeitorio":
            rows = _executar_pg(
                "SELECT 1 FROM refeitorio WHERE data=%s AND horaentrada=%s AND matricula=%s AND refeicao=%s LIMIT 1",
                (linha.get("Data",""), linha.get("HoraEntrada",""),
                 linha.get("Matricula",""), linha.get("Refeicao","")),
                fetch=True,
            )
        elif tabela == "frequencia":
            rows = _executar_pg(
                "SELECT 1 FROM frequencia WHERE data=%s AND horaentrada=%s AND matricula=%s AND aula=%s LIMIT 1",
                (linha.get("Data",""), linha.get("HoraEntrada",""),
                 linha.get("Matricula",""), linha.get("Aula","")),
                fetch=True,
            )
        elif tabela == "avaliacoes":
            rows = _executar_pg(
                "SELECT 1 FROM avaliacoes WHERE data=%s AND aluno=%s AND estagio=%s AND item=%s LIMIT 1",
                (linha.get("Data",""), linha.get("Aluno",""),
                 linha.get("Estagio",""), linha.get("Item","")),
                fetch=True,
            )
        else:
            return False
        return bool(rows)
    except Exception:
        return False


def _importar_csv_para_banco(caminho_csv, ignorar_duplicatas=True, callback_progresso=None):
    """
    Lê o CSV, detecta a tabela pelo conjunto de colunas e insere os registros.

    Parâmetros
    ----------
    caminho_csv        : str  – caminho completo do arquivo CSV
    ignorar_duplicatas : bool – se True, pula linhas já existentes no banco
    callback_progresso : callable(atual, total) | None – chamado a cada linha processada

    Retorna
    -------
    dict com chaves: tabela, inseridos, ignorados, erros
    Levanta ValueError se o arquivo não puder ser identificado.
    """
    with open(caminho_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        linhas = list(reader)

    if not linhas:
        return {"tabela": "?", "inseridos": 0, "ignorados": 0, "erros": 0}

    tabela = _detectar_tabela_csv(list(linhas[0].keys()))

    if tabela is None:
        raise ValueError(
            "Colunas do CSV não correspondem a nenhuma tabela conhecida.\n"
            "Esperado:\n"
            f"  refeitorio  → {sorted(_COLS_REFEITORIO)}\n"
            f"  frequencia  → {sorted(_COLS_FREQUENCIA)}\n"
            f"  avaliacoes  → {sorted(_COLS_AVALIACOES)}"
        )

    total = len(linhas)
    inseridos = ignorados = erros = 0

    for i, linha in enumerate(linhas, 1):
        if callback_progresso:
            try:
                callback_progresso(i, total)
            except Exception:
                pass

        try:
            if ignorar_duplicatas and _duplicata_existe(tabela, linha):
                ignorados += 1
                continue

            if tabela == "refeitorio":
                _inserir_refeitorio_db([
                    linha.get("Data",""), linha.get("HoraEntrada",""),
                    linha.get("Matricula",""), linha.get("Nome",""),
                    linha.get("Serie",""), linha.get("Curso",""), linha.get("Refeicao",""),
                ])
            elif tabela == "frequencia":
                _inserir_frequencia_db([
                    linha.get("Data",""), linha.get("HoraEntrada",""),
                    linha.get("Matricula",""), linha.get("Nome",""),
                    linha.get("Serie",""), linha.get("Curso",""), linha.get("Aula",""),
                ])
            elif tabela == "avaliacoes":
                _inserir_avaliacao_db([
                    linha.get("Data",""), linha.get("Aluno",""),
                    linha.get("Serie",""), linha.get("Curso",""),
                    linha.get("Estagio",""), linha.get("Item",""), linha.get("Nota",""),
                ])
            inseridos += 1
        except Exception as e_linha:
            erros += 1
            logger.warning(f"_importar_csv_para_banco ({os.path.basename(caminho_csv)}) linha {i}: {e_linha}")

    logger.info(
        f"Importação CSV concluída — tabela={tabela} arquivo={os.path.basename(caminho_csv)} "
        f"inseridos={inseridos} ignorados={ignorados} erros={erros}"
    )
    return {"tabela": tabela, "inseridos": inseridos, "ignorados": ignorados, "erros": erros}


def _importar_csv_para_banco_forcado(caminho_csv, tabela, ignorar_duplicatas=True, callback_progresso=None):
    """
    Versão de _importar_csv_para_banco com tabela de destino forçada manualmente.
    Usada quando a detecção automática falha e o usuário escolheu a tabela no diálogo.
    """
    with open(caminho_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        linhas = list(reader)

    if not linhas:
        return {"tabela": tabela, "inseridos": 0, "ignorados": 0, "erros": 0}

    total = len(linhas)
    inseridos = ignorados = erros = 0

    for i, linha in enumerate(linhas, 1):
        if callback_progresso:
            try:
                callback_progresso(i, total)
            except Exception:
                pass
        try:
            if ignorar_duplicatas and _duplicata_existe(tabela, linha):
                ignorados += 1
                continue
            if tabela == "refeitorio":
                _inserir_refeitorio_db([
                    linha.get("Data", ""), linha.get("HoraEntrada", ""),
                    linha.get("Matricula", ""), linha.get("Nome", ""),
                    linha.get("Serie", ""), linha.get("Curso", ""), linha.get("Refeicao", ""),
                ])
            elif tabela == "frequencia":
                _inserir_frequencia_db([
                    linha.get("Data", ""), linha.get("HoraEntrada", ""),
                    linha.get("Matricula", ""), linha.get("Nome", ""),
                    linha.get("Serie", ""), linha.get("Curso", ""), linha.get("Aula", ""),
                ])
            elif tabela == "avaliacoes":
                _inserir_avaliacao_db([
                    linha.get("Data", ""), linha.get("Aluno", ""),
                    linha.get("Serie", ""), linha.get("Curso", ""),
                    linha.get("Estagio", ""), linha.get("Item", ""), linha.get("Nota", ""),
                ])
            inseridos += 1
        except Exception as e_linha:
            erros += 1
            logger.warning(f"_importar_csv_para_banco_forcado ({os.path.basename(caminho_csv)}) linha {i}: {e_linha}")

    logger.info(
        f"Importação forçada — tabela={tabela} arquivo={os.path.basename(caminho_csv)} "
        f"inseridos={inseridos} ignorados={ignorados} erros={erros}"
    )
    return {"tabela": tabela, "inseridos": inseridos, "ignorados": ignorados, "erros": erros}


CARDAPIO_PADRAO = {
    "SEGUNDA": ["Cuzcuz com ovo e cafe fresco", "Arroz, feijao, frango cozido e batata doce", "Pao com manteiga e vitamina de goiaba"],
    "TERCA":   ["Cuzcuz com ovo e cafe fresco", "Arroz, feijao, frango cozido e batata doce", "Pao com manteiga e vitamina de goiaba"],
    "QUARTA":  ["Cuzcuz com ovo e cafe fresco", "Arroz, feijao, frango cozido e batata doce", "Pao com manteiga e vitamina de goiaba"],
    "QUINTA":  ["Cuzcuz com ovo e cafe fresco", "Arroz, feijao, frango cozido e batata doce", "Pao com manteiga e vitamina de goiaba"],
    "SEXTA":   ["Cuzcuz com ovo e cafe fresco", "Arroz, feijao, frango cozido e batata doce", "Pao com manteiga e vitamina de goiaba"],
}
EVENTOS_PADRAO = [
    {"data": "03/02", "evento": "Inicio das Aulas"},
    {"data": "01/05", "evento": "Feriado: Dia do Trabalhador"},
    {"data": "24/06", "evento": "Arraia do Marwin"},
    {"data": "07/09", "evento": "Feriado: Independencia do Brasil"},
    {"data": "15/10", "evento": "Dia do Professor"},
    {"data": "25/12", "evento": "Natal"},
]

# ==============================================================================
# ROTAS FLASK
# ==============================================================================
import secrets

def checar_senha(req):
    hdr = req.headers.get("X-Senha", "")
    if not hdr:
        return False
    # If ADMIN_PASSWORD looks like a bcrypt hash and bcrypt is available, verify accordingly
    if BCRYPT_AVAILABLE and isinstance(ADMIN_PASSWORD, str) and ADMIN_PASSWORD.startswith("$2"):
        try:
            return bcrypt.checkpw(hdr.encode("utf-8"), ADMIN_PASSWORD.encode("utf-8"))
        except Exception:
            return False
    # Fallback: constant-time compare with configured plaintext
    return secrets.compare_digest(hdr, ADMIN_PASSWORD)

# Rota para servir o cliente web (index.html)
@app.route('/')
def serve_cliente():
    pasta_raiz = os.path.dirname(os.path.abspath(__file__))
    for nome in ('index.html', 'Index.html'):
        arquivo_index = os.path.join(pasta_raiz, nome)
        if os.path.isfile(arquivo_index):
            return send_from_directory(pasta_raiz, nome)
    return jsonify({'erro': 'index.html não encontrado'}), 404

# Rota para servir arquivos estáticos (CSS, JS, imagens, etc) da pasta raiz
@app.route('/<path:path>')
def serve_static(path):
    try:
        pasta_raiz = os.path.dirname(os.path.abspath(__file__))
        arquivo = os.path.join(pasta_raiz, path)
        # Segurança: evitar acesso fora da pasta raiz
        caminho_absoluto = os.path.abspath(arquivo)
        if not caminho_absoluto.startswith(os.path.abspath(pasta_raiz)):
            return jsonify({'erro': 'Acesso negado'}), 403
        if os.path.isfile(caminho_absoluto):
            return send_from_directory(pasta_raiz, path)
        return jsonify({'erro': 'Arquivo não encontrado'}), 404
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@app.route("/cardapio",  methods=["GET"])
def get_cardapio(): return jsonify(ler_json(CARDAPIO_FILE, CARDAPIO_PADRAO))

@app.route("/eventos",   methods=["GET"])
def get_eventos():  return jsonify(ler_json(EVENTOS_FILE, EVENTOS_PADRAO))

@app.route("/config",    methods=["GET"])
def get_config():   return jsonify(ler_json(CONFIG_FILE, {"avaliacoes_ativas": True, "modo_leitura": "camera"}))

@app.route("/avaliacoes", methods=["GET"])
def get_avaliacoes_publicas():
    """Retorna todos os registros de avaliações em formato JSON"""
    try:
        registros = _ler_avaliacoes_db()
        return jsonify({"avaliacoes": registros, "total": len(registros)})
    except RuntimeError as e:
        logger.error(f"PostgreSQL indisponível: {e}")
        return jsonify({"erro": "Banco de dados indisponível"}), 503
    except Exception as e:
        logger.error(f"Erro ao carregar avaliacoes: {e}")
        return jsonify({"erro": "Erro ao carregar avaliações"}), 500

@app.route("/avaliacao", methods=["POST"])
def post_avaliacao():
    dados = request.get_json()
    if not dados: return jsonify({"erro": "JSON invalido"}), 400
    nome, serie, curso = dados.get("nome","Anonimo"), dados.get("serie","N/A"), dados.get("curso","N/A")
    respostas = dados.get("respostas", {})

    # Verificar se já avaliou esta semana (apenas se não for anônimo)
    if nome and nome.strip().lower() not in {"anonimo", "anônimo"}:
        hoje = _agora_br().date()
        semana_iso = hoje.isocalendar()[1]
        ano_iso = hoje.isocalendar()[0]

        try:
            if _avaliacao_ja_existe_db(nome, semana_iso, ano_iso):
                logger.warning(f"Avaliação duplicada detectada: {nome} - Semana {semana_iso}/{ano_iso}")
                return jsonify({"status": "ja_avaliou", "mensagem": "Você já avaliou esta semana"}), 200
        except Exception as e:
            logger.error(f"Erro ao verificar duplicidade de avaliação: {e}")
            return jsonify({"erro": "Banco de dados indisponível"}), 503

    data_hora = _agora_br().strftime("%d/%m/%Y %H:%M:%S")
    registros = []
    for chave, nota in respostas.items():
        estagio, item = chave.split("|", 1)
        registros.append([data_hora, nome, serie, curso, estagio, item, nota])

    try:
        for registro in registros:
            _inserir_avaliacao_db(registro)
    except RuntimeError as e:
        logger.error(f"PostgreSQL indisponível: {e}")
        return jsonify({"erro": "Banco de dados indisponível"}), 503
    except Exception as e:
        logger.error(f"Erro ao salvar avaliação: {e}")
        return jsonify({"erro": "Erro ao salvar avaliação"}), 500
    logger.info(f"Avaliação recebida de {nome} ({len(respostas)} itens)")
    return jsonify({"status": "ok"})

@app.route("/avaliacao/verificar", methods=["GET"])
def verificar_avaliacao():
    nome = request.args.get("nome", "").strip()
    if not nome or nome.lower() in {"anonimo", "anônimo"}:
        return jsonify({"ja_avaliou": False}), 200

    hoje = _agora_br().date()
    semana_iso = hoje.isocalendar()[1]
    ano_iso = hoje.isocalendar()[0]

    try:
        ja_avaliou = _avaliacao_ja_existe_db(nome, semana_iso, ano_iso)
        return jsonify({"ja_avaliou": ja_avaliou}), 200
    except RuntimeError as e:
        logger.error(f"PostgreSQL indisponível: {e}")
        return jsonify({"erro": "Banco de dados indisponível"}), 503
    except Exception as e:
        logger.error(f"Erro ao verificar avaliação: {e}")
        return jsonify({"erro": "Erro ao verificar avaliação"}), 500

@app.route("/admin/avaliacoes", methods=["GET"])
def get_avaliacoes():
    if not checar_senha(request): return jsonify({"erro": "Acesso negado"}), 403
    try:
        registros = _ler_avaliacoes_db()
        return jsonify(registros)
    except RuntimeError as e:
        logger.error(f"PostgreSQL indisponível: {e}")
        return jsonify({"erro": "Banco de dados indisponível"}), 503
    except Exception as e:
        logger.error(f"Erro ao carregar avaliacoes: {e}")
        return jsonify({"erro": "Erro ao carregar avaliações"}), 500

@app.route("/admin/avaliacoes", methods=["DELETE"])
def del_avaliacoes():
    if not checar_senha(request): return jsonify({"erro": "Acesso negado"}), 403
    try:
        _apagar_avaliacoes_db()
        return jsonify({"status": "apagado"})
    except RuntimeError as e:
        logger.error(f"PostgreSQL indisponível: {e}")
        return jsonify({"erro": "Banco de dados indisponível"}), 503
    except Exception as e:
        logger.error(f"Erro ao apagar avaliações: {e}")
        return jsonify({"erro": "Erro ao apagar avaliações"}), 500

@app.route("/admin/cardapio", methods=["PUT"])
def put_cardapio():
    if not checar_senha(request): return jsonify({"erro": "Acesso negado"}), 403
    dados = request.get_json()
    salvar_json(CARDAPIO_FILE, dados)
    _sync_nuvem("/admin/cardapio", "PUT", dados)
    return jsonify({"status": "ok"})

@app.route("/admin/eventos", methods=["POST"])
def add_evento():
    if not checar_senha(request): return jsonify({"erro": "Acesso negado"}), 403
    ev = request.get_json()
    eventos = ler_json(EVENTOS_FILE, EVENTOS_PADRAO); eventos.append(ev)
    salvar_json(EVENTOS_FILE, eventos)
    _sync_nuvem("/admin/eventos", "PUT", eventos)
    return jsonify({"status": "ok"})

@app.route("/admin/eventos", methods=["DELETE"])
def del_evento():
    if not checar_senha(request): return jsonify({"erro": "Acesso negado"}), 403
    ev = request.get_json()
    eventos = ler_json(EVENTOS_FILE, EVENTOS_PADRAO)
    eventos = [e for e in eventos if not (e["data"]==ev["data"] and e["evento"]==ev["evento"])]
    salvar_json(EVENTOS_FILE, eventos)
    _sync_nuvem("/admin/eventos", "PUT", eventos)
    return jsonify({"status": "ok"})

@app.route("/admin/config", methods=["PUT"])
def put_config():
    if not checar_senha(request): return jsonify({"erro": "Acesso negado"}), 403
    dados = request.get_json()
    salvar_json(CONFIG_FILE, dados)
    _sync_nuvem("/admin/config", "PUT", dados)
    return jsonify({"status": "ok"})

# ==============================================================================
# ROTAS FLASK — REFEITÓRIO
# ==============================================================================
def _hoje():
    return _agora_br().strftime("%d/%m/%Y")

def _aula_por_hora(hora):
    """Retorna a aula ou intervalo correspondente ao horário de entrada."""
    try:
        hora_limpa = hora.strip().split(" ")[0]
        if len(hora_limpa) == 5:
            hora_limpa += ":00"
        t = datetime.datetime.strptime(hora_limpa, "%H:%M:%S").time()
    except Exception:
        return "Fora do horário"

    periodos = [
        ("07:10:00", "08:00:00", "Aula 1"),
        ("08:00:00", "08:50:00", "Aula 2"),
        ("08:50:00", "09:10:00", "Intervalo"),
        ("09:10:00", "10:00:00", "Aula 3"),
        ("10:00:00", "10:50:00", "Aula 4"),
        ("10:50:00", "11:40:00", "Aula 5"),
        ("11:40:00", "13:00:00", "Intervalo"),
        ("13:00:00", "13:50:00", "Aula 6"),
        ("13:50:00", "14:40:00", "Aula 7"),
        ("14:40:00", "15:00:00", "Intervalo"),
        ("15:00:00", "15:50:00", "Aula 8"),
        ("15:50:00", "16:40:00", "Aula 9"),
    ]
    for inicio, fim, nome_aula in periodos:
        if datetime.time.fromisoformat(inicio) <= t < datetime.time.fromisoformat(fim):
            return nome_aula
    return "Fora do horário"

def _registros_hoje():
    try:
        return _ler_refeitorio_hoje_db()
    except Exception as e:
        logger.error(f"Erro ao ler refeitorio do banco: {e}")
        return []

@app.route("/refeitorio/registrar", methods=["POST"])
def registrar_refeicao():
    dados = request.get_json()
    if not dados:
        return jsonify({"erro": "JSON invalido"}), 400
    matricula = dados.get("matricula", "").strip()
    refeicao  = dados.get("refeicao", "almoco").strip().lower()
    nome      = dados.get("nome", "Desconhecido").strip()
    serie     = dados.get("serie", "N/A").strip()
    curso     = dados.get("curso", "N/A").strip()

    # Limpa dados malformados do leitor USB (não use locals())
    nome = nome or "Desconhecido"
    serie = serie or "N/A"
    curso = curso or "N/A"
    matricula = matricula or ""

    def _limpar_campo(valor: str) -> str:
        if not valor:
            return valor
        v = valor
        if "^" in v or "Ç" in v:
            v = v.replace("^Ç", ":").replace("^", "").replace("Ç", "")
        v = re.sub(r"[^a-zA-Z0-9À-ÿ\s.'-]", "", v).strip()
        return v

    nome = _limpar_campo(nome)
    serie = _limpar_campo(serie)
    curso = _limpar_campo(curso)
    matricula = _limpar_campo(matricula)

    # Confia no cadastro oficial (pela matrícula) quando ele existir — a
    # matrícula nunca corrompe, então é a fonte mais confiável para
    # corrigir nome/série/curso, mesmo que o leitor tenha mandado lixo.
    aluno_cadastrado = _buscar_aluno_por_matricula(matricula)
    if aluno_cadastrado:
        nome = aluno_cadastrado.get("nome") or nome
        serie = aluno_cadastrado.get("serie") or serie
        curso = aluno_cadastrado.get("curso") or curso

    today      = _hoje()
    if not matricula:
        return jsonify({"erro": "Matricula nao informada"}), 400

    db_duplicado = _refeitorio_duplicado_db(matricula, refeicao)
    if db_duplicado:
        return jsonify({
            "status": "ja_registrado",
            "nome": db_duplicado["nome"],
            "hora": db_duplicado["hora"],
            "total_hoje": db_duplicado["total_hoje"],
            "total_refeicao": db_duplicado["total_refeicao"],
        }), 200

    hora = _agora_br().strftime("%H:%M:%S")
    periodo = _aula_por_hora(hora)
    registro = [today, hora, matricula, nome, serie, curso, refeicao]

    try:
        _inserir_refeitorio_db(registro)
    except RuntimeError as e:
        logger.error(f"PostgreSQL indisponível: {e}")
        return jsonify({"erro": "Banco de dados indisponível"}), 503
    except Exception as e:
        logger.error(f"Erro ao registrar refeição: {e}")
        return jsonify({"erro": "Erro ao registrar refeição"}), 500
    logger.info(f"Refeição registrada: {nome} ({matricula}) - {refeicao}")
    # Contagens após inserir
    registros = _ler_refeitorio_hoje_db()
    total_hoje = len(registros)
    total_refeicao = sum(1 for r in registros if r[6] == refeicao)
    return jsonify({"status": "ok", "nome": nome, "hora": hora, "aula": periodo,
                    "total_hoje": total_hoje, "total_refeicao": total_refeicao}), 200

@app.route("/refeitorio/hoje", methods=["GET"])
def get_refeitorio_hoje():
    if not checar_senha(request): return jsonify({"erro": "Acesso negado"}), 403
    try:
        registros = _ler_refeitorio_hoje_db()
        return jsonify(registros)
    except RuntimeError as e:
        logger.error(f"PostgreSQL indisponível: {e}")
        return jsonify({"erro": "Banco de dados indisponível"}), 503
    except Exception as e:
        logger.error(f"Erro ao ler refeitorio: {e}")
        return jsonify({"erro": "Erro ao ler dados de refeitório"}), 500

@app.route("/refeitorio/exportar", methods=["GET"])
def exportar_refeitorio():
    if not checar_senha(request): return jsonify({"erro": "Acesso negado"}), 403
    try:
        linhas = _ler_refeitorio_todos_db()
        buf = _csv_bytes(
            ["Data", "HoraEntrada", "Matricula", "Nome", "Serie", "Curso", "Refeicao"],
            linhas,
        )
        return send_file(
            buf,
            as_attachment=True,
            download_name=f"refeitorio_{_hoje().replace('/', '_')}.csv",
            mimetype="text/csv",
        )
    except RuntimeError as e:
        logger.error(f"PostgreSQL indisponível: {e}")
        return jsonify({"erro": "Banco de dados indisponível"}), 503
    except Exception as e:
        logger.error(f"Erro ao exportar refeitorio: {e}")
        return jsonify({"erro": "Erro ao exportar refeitório"}), 500

@app.route("/refeitorio/apagar", methods=["DELETE"])
def apagar_refeitorio():
    if not checar_senha(request): return jsonify({"erro": "Acesso negado"}), 403
    data_alvo = request.args.get("data", _hoje())
    try:
        _apagar_refeitorio_data_db(data_alvo)
        return jsonify({"status": "apagado", "data": data_alvo})
    except RuntimeError as e:
        logger.error(f"PostgreSQL indisponível: {e}")
        return jsonify({"erro": "Banco de dados indisponível"}), 503
    except Exception as e:
        logger.error(f"Erro ao apagar refeitorio: {e}")
        return jsonify({"erro": "Erro ao apagar refeitório"}), 500

@app.route("/refeitorio/qrcode/<matricula>", methods=["GET"])
def gerar_qrcode_img(matricula):
    matricula = (matricula or "").strip()

    # 1) Procura a imagem já salva em dados/qrcodes_marwin/ (e em qualquer
    #    subpasta, já que lá os PNGs ficam organizados por turma/curso —
    #    ex: "1 Ano/DS/3282472_ANA_KELLY_..._1_DS.png"). Aceita o nome
    #    "matricula.png", "matricula_qualquercoisa.png" e também o prefixo
    #    antigo "qrcode_matricula...png" (de versões anteriores).
    def _bate_com_matricula(nome_arquivo):
        n = nome_arquivo
        if n.startswith("qrcode_"):
            n = n[len("qrcode_"):]
        return n == f"{matricula}.png" or n.startswith(f"{matricula}_")

    caminho_salvo = None
    if os.path.isdir(QRCODES_DIR):
        for raiz, _subpastas, arquivos in os.walk(QRCODES_DIR):
            for arq in arquivos:
                if arq.lower().endswith(".png") and _bate_com_matricula(arq):
                    caminho_salvo = os.path.join(raiz, arq)
                    break
            if caminho_salvo:
                break
    if caminho_salvo:
        return send_file(caminho_salvo, mimetype="image/png", download_name=os.path.basename(caminho_salvo))

    # 2) Não encontrou: gera na hora (usando o cadastro oficial, se existir,
    #    senão os parâmetros da URL) e já salva em dados/qrcodes_marwin/
    #    para as próximas vezes não precisarem gerar de novo.
    aluno = _buscar_aluno_por_matricula(matricula)
    nome  = (aluno.get("nome")  if aluno else None) or request.args.get("nome", "")
    serie = (aluno.get("serie") if aluno else None) or request.args.get("serie", "")
    curso = (aluno.get("curso") if aluno else None) or request.args.get("curso", "")

    payload = json.dumps({"matricula": matricula, "nome": nome, "serie": serie, "curso": curso}, ensure_ascii=False)
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2)
    qr.add_data(payload); qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    def _slug(texto):
        t = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode("ascii")
        return re.sub(r"[^a-zA-Z0-9]+", "_", t).strip("_")

    nome_arquivo = "_".join(filter(None, [matricula, _slug(nome), _slug(serie), _slug(curso)])) + ".png"
    subpasta = f"{serie} - {curso}".strip(" -") if (serie or curso) else ""
    pasta_destino = os.path.join(QRCODES_DIR, subpasta) if subpasta else QRCODES_DIR
    os.makedirs(pasta_destino, exist_ok=True)
    caminho_novo = os.path.join(pasta_destino, nome_arquivo)
    try:
        img.save(caminho_novo, format="PNG")
    except Exception as e:
        logger.error(f"Erro ao salvar QR Code em {caminho_novo}: {e}")

    buf = io.BytesIO(); img.save(buf, format="PNG"); buf.seek(0)
    return send_file(buf, mimetype="image/png", download_name=nome_arquivo)

@app.route("/aluno/<matricula>", methods=["GET"])
def buscar_aluno_cadastro(matricula):
    """Retorna o cadastro oficial (nome/serie/curso) de um aluno pela
    matrícula. Usado pelo index.html para corrigir, no instante da
    leitura do QR Code, nomes que o leitor USB tenha corrompido (acento
    fantasma fundido pelo Windows etc.) — antes mesmo de registrar
    presença/refeição."""
    aluno = _buscar_aluno_por_matricula((matricula or "").strip())
    if not aluno:
        return jsonify({"erro": "Aluno nao encontrado"}), 404
    return jsonify({
        "matricula": aluno.get("matricula", matricula),
        "nome": aluno.get("nome", ""),
        "serie": aluno.get("serie", ""),
        "curso": aluno.get("curso", ""),
    }), 200

# ==============================================================================
# ROTAS FLASK — FREQUÊNCIA
# ==============================================================================

def _registros_freq_hoje():
    try:
        return _ler_frequencia_hoje_db()
    except Exception as e:
        logger.error(f"Erro ao ler frequencia do banco: {e}")
        return []

@app.route("/frequencia/registrar", methods=["POST"])
def registrar_frequencia():
    dados = request.get_json()
    if not dados:
        return jsonify({"erro": "JSON invalido"}), 400
    matricula = dados.get("matricula", "").strip()
    nome      = dados.get("nome", "Desconhecido").strip()
    serie     = dados.get("serie", "N/A").strip()
    curso     = dados.get("curso", "N/A").strip()

    # Limpa dados malformados do leitor USB
    def _limpar_campo(valor: str) -> str:
        if not valor:
            return valor
        v = valor
        if "^" in v or "Ç" in v:
            v = v.replace("^Ç", ":").replace("^", "").replace("Ç", "")
        v = re.sub(r"[^a-zA-Z0-9À-ÿ\s.'-]", "", v).strip()
        return v

    nome = _limpar_campo(nome)
    serie = _limpar_campo(serie)
    curso = _limpar_campo(curso)
    matricula = _limpar_campo(matricula)

    nome = nome or "Desconhecido"
    serie = serie or "N/A"
    curso = curso or "N/A"

    # Confia no cadastro oficial (pela matrícula) quando ele existir — a
    # matrícula nunca corrompe, então é a fonte mais confiável para
    # corrigir nome/série/curso, mesmo que o leitor tenha mandado lixo.
    aluno_cadastrado = _buscar_aluno_por_matricula(matricula)
    if aluno_cadastrado:
        nome = aluno_cadastrado.get("nome") or nome
        serie = aluno_cadastrado.get("serie") or serie
        curso = aluno_cadastrado.get("curso") or curso

    hoje = _hoje()
    if not matricula:
        return jsonify({"erro": "Matricula nao informada"}), 400

    db_duplicado = _frequencia_duplicado_db(matricula)
    if db_duplicado:
        return jsonify({"status": "ja_registrado", "nome": db_duplicado["nome"], "hora": db_duplicado["hora"], "total_hoje": db_duplicado["total_hoje"]}), 200

    hora = _agora_br().strftime("%H:%M:%S")
    aula = _aula_por_hora(hora)
    registro = [hoje, hora, matricula, nome, serie, curso, aula]

    try:
        _inserir_frequencia_db(registro)
    except RuntimeError as e:
        logger.error(f"PostgreSQL indisponível: {e}")
        return jsonify({"erro": "Banco de dados indisponível"}), 503
    except Exception as e:
        logger.error(f"Erro ao registrar frequência: {e}")
        return jsonify({"erro": "Erro ao registrar frequência"}), 500

    logger.info(f"Frequência registrada: {nome} ({matricula})")

    registros = _ler_frequencia_hoje_db()
    total_hoje = len(registros)
    return jsonify({"status": "ok", "nome": nome, "hora": hora, "aula": aula, "total_hoje": total_hoje}), 200

@app.route("/frequencia/hoje", methods=["GET"])
def get_frequencia_hoje():
    if not checar_senha(request): return jsonify({"erro": "Acesso negado"}), 403
    try:
        registros = _ler_frequencia_hoje_db()
        return jsonify(registros)
    except RuntimeError as e:
        logger.error(f"PostgreSQL indisponível: {e}")
        return jsonify({"erro": "Banco de dados indisponível"}), 503
    except Exception as e:
        logger.error(f"Erro ao ler frequencia: {e}")
        return jsonify({"erro": "Erro ao ler dados de frequência"}), 500

@app.route("/frequencia/exportar", methods=["GET"])
def exportar_frequencia():
    if not checar_senha(request): return jsonify({"erro": "Acesso negado"}), 403
    try:
        linhas = _ler_frequencia_todos_db()
        buf = _csv_bytes(
            ["Data", "HoraEntrada", "Matricula", "Nome", "Serie", "Curso", "Aula"],
            linhas,
        )
        return send_file(
            buf,
            as_attachment=True,
            download_name=f"frequencia_{_hoje().replace('/', '_')}.csv",
            mimetype="text/csv",
        )
    except RuntimeError as e:
        logger.error(f"PostgreSQL indisponível: {e}")
        return jsonify({"erro": "Banco de dados indisponível"}), 503
    except Exception as e:
        logger.error(f"Erro ao exportar frequencia: {e}")
        return jsonify({"erro": "Erro ao exportar frequência"}), 500

@app.route("/frequencia/apagar", methods=["DELETE"])
def apagar_frequencia():
    if not checar_senha(request): return jsonify({"erro": "Acesso negado"}), 403
    data_alvo = request.args.get("data", _hoje())
    try:
        _apagar_frequencia_data_db(data_alvo)
        return jsonify({"status": "apagado", "data": data_alvo})
    except RuntimeError as e:
        logger.error(f"PostgreSQL indisponível: {e}")
        return jsonify({"erro": "Banco de dados indisponível"}), 503
    except Exception as e:
        logger.error(f"Erro ao apagar frequencia: {e}")
        return jsonify({"erro": "Erro ao apagar frequência"}), 500

@app.route("/admin/limpar_neon", methods=["DELETE"])
def admin_limpar_neon():
    if not checar_senha(request):
        return jsonify({"erro": "Acesso negado"}), 403
    try:
        _limpar_tabelas_neon()
        return jsonify({"status": "neon_limpo"}), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

# ==============================================================================
# BACKUP POR E-MAIL (opcional)
# ==============================================================================
def _enviar_backup_email():
    """Envia backup compactado por e-mail."""
    try:
        cfg = ler_json(CONFIG_FILE, {})
        if not cfg.get("email_backup_ativo", False):
            return

        email_remetente = cfg.get("email_remetente", "")
        email_senha = cfg.get("email_senha_app", "")
        email_destino = cfg.get("email_destino", "")
        email_smtp = cfg.get("email_smtp", "smtp.gmail.com")
        email_porta = cfg.get("email_porta", 587)

        if not all([email_remetente, email_senha, email_destino]):
            logger.warning("Backup por e-mail desativado: credenciais incompletas")
            return

        ts = _agora_br().strftime("%Y%m%d_%H%M%S")
        zip_name = f"backup_marwin_{ts}.zip"
        pasta_exp, arquivos_csv = _exportar_backup_mensal_csv(f"email_{ts}")
        with zipfile.ZipFile(zip_name, "w") as zf:
            for nome_arq in arquivos_csv:
                zf.write(os.path.join(pasta_exp, nome_arq), arcname=nome_arq)
            if os.path.exists(LISTA_ALUNOS_FILE):
                zf.write(LISTA_ALUNOS_FILE, arcname="lista_alunos.json")

        # Enviar por SMTP
        msg = MIMEMultipart()
        msg["From"] = email_remetente
        msg["To"] = email_destino
        msg["Subject"] = f"Backup MARWIN - {_agora_br().strftime('%d/%m/%Y %H:%M')}"

        body = f"Backup automático do sistema MARWIN - {_agora_br().strftime('%d/%m/%Y %H:%M:%S')}"
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with open(zip_name, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename= {zip_name}")
            msg.attach(part)

        server = smtplib.SMTP(email_smtp, email_porta)
        server.starttls()
        server.login(email_remetente, email_senha)
        server.send_message(msg)
        server.quit()

        os.remove(zip_name)
        logger.info(f"Backup enviado por e-mail para {email_destino}")
    except Exception as e:
        logger.error(f"Erro ao enviar backup por e-mail: {e}")

def _agendar_backup_email():
    """Agenda backup automático para 23h30 todos os dias."""
    def _loop_backup():
        while True:
            agora = _agora_br()
            proxima_exec = agora.replace(hour=23, minute=30, second=0, microsecond=0)
            if agora >= proxima_exec:
                proxima_exec += datetime.timedelta(days=1)
            tempo_espera = (proxima_exec - agora).total_seconds()
            time.sleep(tempo_espera)
            _enviar_backup_email()

    thread = threading.Thread(target=_loop_backup, daemon=True)
    thread.start()

def _iniciar_fluxo_backup_mes(btn_backup=None):
    """Fluxo guiado: nome do arquivo → exportar CSV → confirmação dupla → limpar banco."""
    def _habilitar_btn(estado):
        if btn_backup is not None:
            try:
                btn_backup.config(state=estado)
            except Exception:
                pass

    _habilitar_btn("disabled")

    dlg_nome = tk.Toplevel(janela)
    dlg_nome.title("Backup do Mês")
    dlg_nome.configure(bg=T["BG_CARD"])
    dlg_nome.transient(janela)
    dlg_nome.grab_set()
    dlg_nome.resizable(False, False)

    tk.Label(dlg_nome, text="Nome do arquivo de backup",
             font=("Segoe UI", 12, "bold"), bg=T["BG_CARD"], fg=T["ACCENT_VIBRANT"]).pack(padx=20, pady=(16, 6))
    tk.Label(dlg_nome, text="Os CSVs serão salvos em dados/backups/AAAA_MM/",
             font=("Segoe UI", 9), bg=T["BG_CARD"], fg=T["FRASE_FG"]).pack(padx=20, pady=(0, 10))

    nome_var = tk.StringVar(value=_nome_backup_mes_sugerido())
    entry_nome = tk.Entry(dlg_nome, textvariable=nome_var, font=("Segoe UI", 11),
                          bg=T["ENTRY_BG"], fg=T["FG_TEXT"], width=36)
    entry_nome.pack(padx=20, pady=(0, 16))
    entry_nome.focus_set()
    entry_nome.select_range(0, "end")

    resultado = {"cancelado": True, "nome": ""}

    def _cancelar_inicio():
        resultado["cancelado"] = True
        dlg_nome.destroy()
        _habilitar_btn("normal")

    def _confirmar_nome():
        nome = nome_var.get().strip()
        if not nome:
            messagebox.showwarning("Aviso", "Informe um nome para o backup.", parent=dlg_nome)
            return
        resultado["cancelado"] = False
        resultado["nome"] = nome
        dlg_nome.destroy()

    btn_row = tk.Frame(dlg_nome, bg=T["BG_CARD"])
    btn_row.pack(pady=(0, 16))
    tk.Button(btn_row, text="Cancelar", command=_cancelar_inicio,
              bg=T["FRASE_FG"], fg="white", font=("Segoe UI", 10, "bold"),
              padx=14, pady=6, bd=0, cursor="hand2").pack(side="left", padx=6)
    tk.Button(btn_row, text="Continuar", command=_confirmar_nome,
              bg=T["ACCENT_SOFT"], fg="white", font=("Segoe UI", 10, "bold"),
              padx=14, pady=6, bd=0, cursor="hand2").pack(side="left", padx=6)

    dlg_nome.wait_window()
    if resultado["cancelado"]:
        return

    try:
        pasta, arquivos = _exportar_backup_mensal_csv(resultado["nome"])
        lista = "\n".join(f"• {a}" for a in arquivos)
        messagebox.showinfo(
            "Backup exportado",
            f"CSVs gerados com sucesso em:\n{pasta}\n\n{lista}",
        )
        logger.info(f"Backup do mês exportado: {pasta}")
    except Exception as e:
        logger.error(f"Falha ao exportar backup do mês: {e}")
        messagebox.showerror("Erro", f"Falha ao exportar backup:\n{e}")
        _habilitar_btn("normal")
        return

    if not messagebox.askyesno(
        "Confirmar exclusão",
        "Tem certeza que deseja apagar todos os dados do banco?\n"
        "Esta ação não pode ser desfeita.",
        icon="warning",
    ):
        messagebox.showinfo("Cancelado", "Nenhum dado foi removido do banco. O backup CSV foi mantido.")
        _habilitar_btn("normal")
        return

    dlg_final = tk.Toplevel(janela)
    dlg_final.title("Confirmação final")
    dlg_final.configure(bg=T["BG_CARD"])
    dlg_final.transient(janela)
    dlg_final.grab_set()
    dlg_final.resizable(False, False)

    tk.Label(
        dlg_final,
        text="Confirmação final: os dados serão permanentemente removidos do banco.\n"
             "Digite CONFIRMAR para prosseguir.",
        font=("Segoe UI", 10),
        bg=T["BG_CARD"],
        fg=T["FG_TEXT"],
        justify="left",
    ).pack(padx=20, pady=(16, 10))

    conf_var = tk.StringVar()
    entry_conf = tk.Entry(dlg_final, textvariable=conf_var, font=("Segoe UI", 11),
                          bg=T["ENTRY_BG"], fg=T["FG_TEXT"], width=28)
    entry_conf.pack(padx=20, pady=(0, 12))

    btn_apagar = tk.Button(
        dlg_final, text="Apagar dados do banco", state="disabled",
        bg="#c62828", fg="white", font=("Segoe UI", 10, "bold"),
        padx=14, pady=6, bd=0,
    )
    confirmado = {"ok": False}

    def _atualizar_btn(*_):
        if conf_var.get() == "CONFIRMAR":
            btn_apagar.config(state="normal", cursor="hand2")
        else:
            btn_apagar.config(state="disabled", cursor="")

    def _executar_apagar():
        confirmado["ok"] = True
        dlg_final.destroy()

    def _cancelar_final():
        confirmado["ok"] = False
        dlg_final.destroy()

    conf_var.trace_add("write", _atualizar_btn)
    btn_apagar.config(command=_executar_apagar)

    btn_row2 = tk.Frame(dlg_final, bg=T["BG_CARD"])
    btn_row2.pack(pady=(0, 16))
    tk.Button(btn_row2, text="Cancelar", command=_cancelar_final,
              bg=T["FRASE_FG"], fg="white", font=("Segoe UI", 10, "bold"),
              padx=14, pady=6, bd=0, cursor="hand2").pack(side="left", padx=6)
    btn_apagar.pack(in_=btn_row2, side="left", padx=6)

    dlg_final.wait_window()

    if not confirmado["ok"]:
        messagebox.showinfo("Cancelado", "Nenhum dado foi removido do banco. O backup CSV foi mantido.")
        _habilitar_btn("normal")
        return

    try:
        _limpar_tabelas_neon()
        messagebox.showinfo("Concluído", "Dados do banco removidos com sucesso. O backup CSV foi mantido.")
        logger.info("Backup do mês concluído: banco limpo após exportação")
    except Exception as e:
        logger.error(f"Falha ao limpar banco após backup: {e}")
        messagebox.showerror(
            "Erro",
            f"O backup CSV foi salvo, mas falhou ao apagar o banco:\n{e}",
        )
    finally:
        _habilitar_btn("normal")

# ==============================================================================
# PAINEL ADMIN TKINTER
# ==============================================================================
TEMAS = {
    "claro": {
        "BG_MAIN":"#f2f8f2","BG_CARD":"#ffffff","ACCENT_VIBRANT":"#1b5e20",
        "ACCENT_SOFT":"#388e3c","FG_TEXT":"#1a2a1a","BORDER_GRID":"#c8e6c9",
        "HIGHLIGHT_YELLOW":"#f9a825","OBS_BG":"#e8f5e9","BTN_CARDAPIO":"#2e7d32",
        "FRASE_FG":"#4a7a4a","ENTRY_BG":"#f0f8f0","BTN_VOLTAR":"#1b5e20"
    },
    "escuro": {
        "BG_MAIN":"#0a1a0a","BG_CARD":"#142014","ACCENT_VIBRANT":"#4caf50",
        "ACCENT_SOFT":"#388e3c","FG_TEXT":"#c8e6c9","BORDER_GRID":"#2e5e2e",
        "HIGHLIGHT_YELLOW":"#f9a825","OBS_BG":"#1a3a1a","BTN_CARDAPIO":"#2e7d32",
        "FRASE_FG":"#81c784","ENTRY_BG":"#1a2e1a","BTN_VOLTAR":"#1b5e20"
    }
}

janela = None
T = None
tema_atual = None
url_ngrok_global = ""
btn_tema = None

def carregar_tema():
    if os.path.exists(TEMA_FILE):
        with open(TEMA_FILE) as f: return json.load(f).get("tema","claro")
    return "claro"

def salvar_tema_tk(tema):
    with open(TEMA_FILE,"w") as f: json.dump({"tema":tema},f)

def pedir_senha_tk():
    win = tk.Toplevel(janela); win.title("Acesso Administrativo"); win.resizable(False, False)
    win.configure(bg=T["BG_MAIN"]); win.transient(janela); win.grab_set()
    win.update_idletasks()
    w, h = 420, 300
    sw = win.winfo_screenwidth(); sh = win.winfo_screenheight()
    win.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    # Barra verde no topo do diálogo
    barra = tk.Frame(win, bg=T["ACCENT_VIBRANT"], height=44)
    barra.pack(fill="x"); barra.pack_propagate(False)
    tk.Label(barra, text="🔒  Acesso Administrativo", font=("Segoe UI", 12, "bold"),
             bg=T["ACCENT_VIBRANT"], fg="white").pack(side="left", padx=16, pady=12)
    tk.Frame(win, bg=T["HIGHLIGHT_YELLOW"], height=3).pack(fill="x")

    frame = tk.Frame(win, bg=T["BG_CARD"], padx=36, pady=28)
    frame.pack(expand=True, fill="both", padx=24, pady=20)
    tk.Label(frame, text="Digite a senha para continuar",
             font=("Segoe UI", 11), bg=T["BG_CARD"], fg=T["FRASE_FG"]).pack(pady=(0, 16))
    senha_var = tk.StringVar()
    entry = tk.Entry(frame, textvariable=senha_var, show="*", font=("Segoe UI", 13),
                     bg=T["ENTRY_BG"], fg=T["FG_TEXT"], relief="solid", bd=1,
                     insertbackground=T["ACCENT_VIBRANT"])
    entry.pack(fill="x", ipady=8, pady=(0, 20)); entry.focus()
    resultado = {"senha": None}
    def confirmar(): resultado["senha"] = senha_var.get(); win.destroy()
    def cancelar(): win.destroy()
    bf = tk.Frame(frame, bg=T["BG_CARD"]); bf.pack(fill="x")
    tk.Button(bf, text="Cancelar", bg=T["OBS_BG"], fg=T["ACCENT_VIBRANT"],
              font=("Segoe UI", 11, "bold"), bd=0, padx=15, pady=10,
              cursor="hand2", command=cancelar).pack(side="left", expand=True, fill="x", padx=(0, 6))
    tk.Button(bf, text="Entrar", bg=T["ACCENT_VIBRANT"], fg="white",
              font=("Segoe UI", 11, "bold"), bd=0, padx=15, pady=10,
              cursor="hand2", activebackground=T["ACCENT_SOFT"],
              command=confirmar).pack(side="right", expand=True, fill="x", padx=(6, 0))
    win.bind("<Return>", lambda e: confirmar()); win.wait_window(); return resultado["senha"]
# ── Cores do novo tema ──────────────────────────────────────────────────────
VERDE_ESCURO   = "#0F3D2E"
VERDE_VIBRANTE = "#1F6B45"
VERDE_SIDEBAR  = "#123D2C"
VERDE_SELECAO  = "#1F6B45"
VERDE_HOVER    = "#1A4D38"
VERDE_CLARO    = "#E8F5E9"
AZUL_CLARO     = "#E3F2FD"
ROXO_CLARO     = "#F3E5F5"
LARANJA_CLARO  = "#FFF3E0"
VERMELHO_CLARO = "#FFEBEE"
CINZA_BG       = "#F5F6F8"
BRANCO         = "#FFFFFF"
TEXTO_CINZA    = "#6B7280"
TEXTO_ESCURO   = "#1F2937"
TEXTO_CLARO    = "#D7E8DE"


def abrir_painel_admin_ctk(event=None):
    """Abre o Painel Administrativo com o novo visual (CustomTkinter).
 
    Mantém a MESMA verificação de senha e as MESMAS funções de leitura
    de dados do painel original — só muda a interface.
    """
    senha = pedir_senha_tk()

    perfil = _identificar_perfil(senha)
    if not perfil:
        if senha is not None:
            logger.warning("Tentativa de acesso admin com senha incorreta")
            messagebox.showerror("Acesso negado", "Senha incorreta!")
        return

    abas_permitidas = PERFIS_ABAS.get(perfil, set())
    logger.info(f"Painel admin (CTk) aberto com sucesso — perfil: {perfil}")

    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("green")

    jd = ctk.CTkToplevel(janela)
    jd.title("Painel Administrativo — EEEP MARWIN")
    jd.geometry("1400x850")
    jd.state("zoomed")
    jd.configure(fg_color=CINZA_BG)
    jd.attributes("-topmost", True)
    jd.lift()
    jd.focus_force()
    jd.after(100, lambda: jd.attributes("-topmost", False))

    jd.grid_columnconfigure(0, weight=0)
    jd.grid_columnconfigure(1, weight=1)
    jd.grid_rowconfigure(0, weight=1)

    paginas = {}

    # ──────────────────────────────────────────────────────────────────
    # SIDEBAR
    # ──────────────────────────────────────────────────────────────────
    sidebar = ctk.CTkFrame(jd, width=230, corner_radius=0, fg_color=VERDE_SIDEBAR)
    sidebar.grid(row=0, column=0, sticky="nsew")
    sidebar.grid_propagate(False)

    topo = ctk.CTkFrame(sidebar, fg_color="transparent")
    topo.pack(fill="x", padx=20, pady=(24, 20))

    logo_path = _buscar_logo_png()
    logo_ref = None
    if logo_path:
        try:
            from PIL import Image
            img = Image.open(logo_path).convert("RGBA")
            img.thumbnail((40, 40), Image.LANCZOS)
            logo_ref = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
            ctk.CTkLabel(topo, image=logo_ref, text="").pack(side="left")
        except Exception:
            ctk.CTkLabel(topo, text="🏫", font=("Segoe UI", 28), width=40).pack(side="left")
    else:
        ctk.CTkLabel(topo, text="🏫", font=("Segoe UI", 28), width=40).pack(side="left")
    jd._logo_ref = logo_ref  # mantém referência viva

    textos_logo = ctk.CTkFrame(topo, fg_color="transparent")
    textos_logo.pack(side="left", padx=(8, 0))
    ctk.CTkLabel(textos_logo, text="Painel Administrativo",
                  font=("Segoe UI", 14, "bold"), text_color="white").pack(anchor="w")
    ctk.CTkLabel(textos_logo, text=f"EEEP MARWIN · {PERFIS_NOME_EXIBICAO.get(perfil, perfil)}",
                  font=("Segoe UI", 11), text_color=TEXTO_CLARO).pack(anchor="w")

    TODOS_ITENS_MENU = [
        ("🏠", "Visão Geral"),
        ("📋", "Avaliações"),
        ("📅", "Relatório Semanal"),
        ("🍽️", "Editar Cardápio"),
        ("🗓️", "Editar Eventos"),
        ("👤", "Refeitório"),
        ("⏱️", "Frequência"),
        ("🕘", "Histórico"),
        ("🔲", "QR Codes"),
        ("📄", "Logs"),
    ]
    # Só mostra, no menu lateral, as abas liberadas para o perfil logado.
    itens_menu = [(icone, nome) for icone, nome in TODOS_ITENS_MENU if nome in abas_permitidas]

    botoes_menu = {}

    def selecionar_botao(nome):
        for n, b in botoes_menu.items():
            if n == nome:
                b.configure(fg_color=VERDE_SELECAO, text_color="white", hover_color=VERDE_SELECAO)
            else:
                b.configure(fg_color="transparent", text_color=TEXTO_CLARO, hover_color=VERDE_HOVER)

    # Páginas com muitos CTkOptionMenu que consomem handles de menu do Tkinter.
    # Essas páginas são destruídas e recriadas a cada navegação para evitar o
    # erro "No more menus can be allocated".
    PAGINAS_RECRIAR = {"Refeitório", "Frequência", "Histórico", "QR Codes",
                        "Editar Cardápio", "Editar Eventos", "Relatório Semanal"}

    def mostrar_pagina(nome):
        if nome not in abas_permitidas:
            logger.warning(f"Perfil {perfil} tentou abrir aba não permitida: {nome}")
            return
        selecionar_botao(nome)
        _scroll_canvas.yview_moveto(0)  # Volta ao topo ao trocar de página

        # Destrói página anterior para liberar handles GDI/Tk
        if nome in paginas:
            try:
                plt.close("all")
                paginas[nome].destroy()
            except Exception:
                pass
            del paginas[nome]

        if nome not in paginas:
            try:
                if nome == "Visão Geral":
                    paginas[nome] = _criar_pagina_visao_geral_extraida(
                        _scroll_inner,
                        {
                            "CINZA_BG": CINZA_BG, "BRANCO": BRANCO,
                            "TEXTO_CINZA": TEXTO_CINZA, "TEXTO_ESCURO": TEXTO_ESCURO,
                            "VERDE_VIBRANTE": VERDE_VIBRANTE, "VERDE_ESCURO": VERDE_ESCURO,
                            "AZUL_CLARO": AZUL_CLARO, "VERDE_CLARO": VERDE_CLARO,
                            "ROXO_CLARO": ROXO_CLARO,
                        },
                        jd, logger,
                        _agora_br, _hoje,
                        _ler_refeitorio_hoje_db, _ler_frequencia_hoje_db,
                        _ler_avaliacoes_db, ler_json,
                        EVENTOS_FILE, EVENTOS_PADRAO, DADOS_DIR,
                        _detectar_tabela_csv, _importar_csv_para_banco_forcado,
                    )
                elif nome == "Avaliações":
                    paginas[nome] = _criar_pagina_avaliacoes_extraida(
                        _scroll_inner,
                        {
                            "CINZA_BG": CINZA_BG, "BRANCO": BRANCO,
                            "TEXTO_CINZA": TEXTO_CINZA, "TEXTO_ESCURO": TEXTO_ESCURO,
                            "VERDE_VIBRANTE": VERDE_VIBRANTE, "VERDE_ESCURO": VERDE_ESCURO,
                            "AZUL_CLARO": AZUL_CLARO, "VERDE_CLARO": VERDE_CLARO,
                            "VERMELHO_CLARO": VERMELHO_CLARO,
                        },
                        ler_json, salvar_json, _sync_nuvem,
                        _avaliacoes_para_linhas, _agora_br, _apagar_avaliacoes_db,
                        CONFIG_FILE,
                    )
                elif nome == "Relatório Semanal":
                    paginas[nome] = _criar_pagina_relatorio_semanal_extraida(
                        _scroll_inner,
                        {
                            "CINZA_BG": CINZA_BG, "BRANCO": BRANCO,
                            "TEXTO_CINZA": TEXTO_CINZA, "TEXTO_ESCURO": TEXTO_ESCURO,
                            "VERDE_VIBRANTE": VERDE_VIBRANTE, "VERDE_ESCURO": VERDE_ESCURO,
                            "AZUL_CLARO": AZUL_CLARO, "VERDE_CLARO": VERDE_CLARO,
                            "ROXO_CLARO": ROXO_CLARO,
                        },
                        _agora_br, _ler_avaliacoes_db,
                    )
                elif nome == "Editar Cardápio":
                    paginas[nome] = _criar_pagina_cardapio_extraida(
                        _scroll_inner,
                        {
                            "CINZA_BG": CINZA_BG, "BRANCO": BRANCO,
                            "TEXTO_CINZA": TEXTO_CINZA, "TEXTO_ESCURO": TEXTO_ESCURO,
                            "VERDE_VIBRANTE": VERDE_VIBRANTE, "VERDE_ESCURO": VERDE_ESCURO,
                        },
                        ler_json, salvar_json, _sync_nuvem,
                        CARDAPIO_FILE, CARDAPIO_PADRAO,
                    )
                elif nome == "Editar Eventos":
                     paginas[nome] = _criar_pagina_eventos_extraida(
                        _scroll_inner,
                        {
                            "CINZA_BG": CINZA_BG, "BRANCO": BRANCO,
                            "TEXTO_CINZA": TEXTO_CINZA, "TEXTO_ESCURO": TEXTO_ESCURO,
                            "VERDE_VIBRANTE": VERDE_VIBRANTE, "VERDE_ESCURO": VERDE_ESCURO,
                        },
                        ler_json, salvar_json, _sync_nuvem, _buscar_logo_png,
                        EVENTOS_FILE, EVENTOS_PADRAO,
                    )
                elif nome == "Refeitório":
                    paginas[nome] = _criar_pagina_refeitorio_extraida(
                        _scroll_inner,
                        {
                            "CINZA_BG": CINZA_BG, "BRANCO": BRANCO,
                            "TEXTO_CINZA": TEXTO_CINZA, "TEXTO_ESCURO": TEXTO_ESCURO,
                            "VERDE_VIBRANTE": VERDE_VIBRANTE, "VERDE_ESCURO": VERDE_ESCURO,
                            "VERDE_CLARO": VERDE_CLARO, "ROXO_CLARO": ROXO_CLARO,
                        },
                        _hoje, _registros_hoje, _aula_por_hora, _escrever_csv,
                        _apagar_refeitorio_data_db, _ler_refeitorio_todos_db,
                    )
                elif nome == "Frequência":
                    paginas[nome] = _criar_pagina_frequencia_extraida(
                        _scroll_inner,
                        {
                            "CINZA_BG": CINZA_BG, "BRANCO": BRANCO,
                            "TEXTO_CINZA": TEXTO_CINZA, "TEXTO_ESCURO": TEXTO_ESCURO,
                            "VERDE_VIBRANTE": VERDE_VIBRANTE, "VERDE_ESCURO": VERDE_ESCURO,
                            "VERDE_CLARO": VERDE_CLARO, "AZUL_CLARO": AZUL_CLARO,
                        },
                        _hoje, _agora_br, _registros_freq_hoje, _aula_por_hora,
                        _frequencia_duplicado_db, _inserir_frequencia_db,
                        _escrever_csv, _ler_frequencia_todos_db,
                        _apagar_frequencia_data_db, LISTA_ALUNOS_FILE,
                    )
                elif nome == "Histórico":
                    paginas[nome] = _criar_pagina_historico_extraida(
                        _scroll_inner,
                        {
                            "CINZA_BG": CINZA_BG, "BRANCO": BRANCO,
                            "TEXTO_CINZA": TEXTO_CINZA, "TEXTO_ESCURO": TEXTO_ESCURO,
                            "VERDE_VIBRANTE": VERDE_VIBRANTE, "VERDE_ESCURO": VERDE_ESCURO,
                            "AZUL_CLARO": AZUL_CLARO, "ROXO_CLARO": ROXO_CLARO,
                        },
                        _agora_br, _ler_frequencia_todos_db, _ler_refeitorio_todos_db,
                    )
                elif nome == "QR Codes":
                    paginas[nome] = _criar_pagina_qrcodes_extraida(
                        _scroll_inner,
                        {
                            "CINZA_BG": CINZA_BG, "BRANCO": BRANCO,
                            "TEXTO_CINZA": TEXTO_CINZA, "TEXTO_ESCURO": TEXTO_ESCURO,
                            "VERDE_VIBRANTE": VERDE_VIBRANTE, "VERDE_ESCURO": VERDE_ESCURO,
                        },
                        DADOS_DIR,
                    )
                elif nome == "Logs":
                    paginas[nome] = _criar_pagina_logs_extraida(
                        _scroll_inner,
                        {
                            "CINZA_BG": CINZA_BG, "BRANCO": BRANCO,
                            "TEXTO_CINZA": TEXTO_CINZA, "TEXTO_ESCURO": TEXTO_ESCURO,
                            "VERDE_VIBRANTE": VERDE_VIBRANTE, "VERDE_ESCURO": VERDE_ESCURO,
                            "AZUL_CLARO": AZUL_CLARO, "VERDE_CLARO": VERDE_CLARO,
                            "LARANJA_CLARO": LARANJA_CLARO, "VERMELHO_CLARO": VERMELHO_CLARO,
                        },
                        logger, _agora_br, LOG_FILE,
                    )
                else:
                    paginas[nome] = criar_pagina_em_construcao(nome)
            except Exception as e:
                import traceback
                paginas[nome] = criar_pagina_erro(nome, traceback.format_exc())
                print(traceback.format_exc())
        for pg in paginas.values():
            pg.grid_remove()
        paginas[nome].grid(row=0, column=0, sticky="nsew")

    def criar_pagina_erro(nome, erro_texto):
        page = ctk.CTkFrame(_scroll_inner, fg_color=CINZA_BG)
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(page, text=f"Erro ao abrir '{nome}'",
                      font=("Segoe UI", 16, "bold"), text_color="#F44336"
                      ).grid(row=0, column=0, sticky="w", padx=24, pady=(24, 8))
        box = ctk.CTkTextbox(page, font=("Consolas", 11))
        box.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 24))
        box.insert("1.0", erro_texto)
        box.configure(state="disabled")
        return page

    for icone, nome in itens_menu:
        btn = ctk.CTkButton(
            sidebar, text=f"  {icone}   {nome}", anchor="w", font=("Segoe UI", 13),
            fg_color="transparent", text_color=TEXTO_CLARO, hover_color=VERDE_HOVER,
            corner_radius=8, height=38,
            command=lambda n=nome: mostrar_pagina(n),
        )
        btn.pack(fill="x", padx=12, pady=2)
        botoes_menu[nome] = btn

    rodape = ctk.CTkFrame(sidebar, fg_color=VERDE_SELECAO, corner_radius=10)
    rodape.pack(fill="x", padx=12, pady=16, side="bottom")
    ctk.CTkLabel(rodape, text="👤", font=("Segoe UI", 22), text_color="white"
                   ).pack(side="left", padx=(12, 8), pady=12)
    info_rodape = ctk.CTkFrame(rodape, fg_color="transparent")
    info_rodape.pack(side="left", pady=12)
    ctk.CTkLabel(info_rodape, text="Administrador", font=("Segoe UI", 12, "bold"),
                  text_color="white").pack(anchor="w")
    ctk.CTkLabel(info_rodape, text="Sistema", font=("Segoe UI", 10),
                  text_color="#B2DFB4").pack(anchor="w")
    ctk.CTkLabel(info_rodape, text="● Online", font=("Segoe UI", 10),
                  text_color="#7BE08C").pack(anchor="w")

    # ──────────────────────────────────────────────────────────────────
    # ÁREA DE CONTEÚDO + HEADER
    # ──────────────────────────────────────────────────────────────────
    container = ctk.CTkFrame(jd, fg_color=CINZA_BG, corner_radius=0)
    container.grid(row=0, column=1, sticky="nsew")
    container.grid_rowconfigure(1, weight=1)
    container.grid_columnconfigure(0, weight=1)
    container.grid_columnconfigure(1, weight=0)

    header = ctk.CTkFrame(container, fg_color=VERDE_VIBRANTE, height=56, corner_radius=0)
    header.grid(row=0, column=0, sticky="ew")
    header.grid_propagate(False)
    ctk.CTkLabel(header, text="", fg_color="transparent").pack(side="left", expand=True)
    status = ctk.CTkFrame(header, fg_color="transparent")
    status.pack(side="right", padx=20)
    ctk.CTkLabel(status, text="●", font=("Segoe UI", 14), text_color="#4CAF50").pack(side="left")
    servidor_txt = f"  Servidor: {url_ngrok_global}" if url_ngrok_global else "  Servidor: indisponível"
    ctk.CTkLabel(status, text=servidor_txt, font=("Segoe UI", 12), text_color="white").pack(side="left")

    # Canvas de scroll único — compartilhado por todas as páginas.
    # Cada página é um CTkFrame normal colocado dentro deste canvas.
    # Isso evita o esgotamento de handles GDI que ocorre quando cada
    # página cria seu próprio CTkScrollableFrame com Canvas interno.
    _scroll_canvas = tk.Canvas(container, bg=CINZA_BG, highlightthickness=0)
    _scroll_canvas.grid(row=1, column=0, sticky="nsew")
    _vsb = ctk.CTkScrollbar(container, orientation="vertical",
                              command=_scroll_canvas.yview)
    _vsb.grid(row=1, column=1, sticky="ns")
    _scroll_canvas.configure(yscrollcommand=_vsb.set)

    _scroll_inner = ctk.CTkFrame(_scroll_canvas, fg_color=CINZA_BG, corner_radius=0)
    _scroll_inner.grid_columnconfigure(0, weight=1)
    _scroll_inner_id = _scroll_canvas.create_window((0, 0), window=_scroll_inner, anchor="nw")

    def _on_inner_configure(event):
        _scroll_canvas.configure(scrollregion=_scroll_canvas.bbox("all"))

    def _on_canvas_configure(event):
        _scroll_canvas.itemconfig(_scroll_inner_id, width=event.width)

    _scroll_inner.bind("<Configure>", _on_inner_configure)
    _scroll_canvas.bind("<Configure>", _on_canvas_configure)

    def _on_mousewheel(event):
        _scroll_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    _scroll_canvas.bind_all("<MouseWheel>", _on_mousewheel)

    # ──────────────────────────────────────────────────────────────────
    # HELPERS DE LAYOUT (cards / tabelas)
    # ──────────────────────────────────────────────────────────────────
    def card_resumo(parent, row, col, icone, cor_fundo, cor_icone, titulo, valor, subtitulo):
        return _card_resumo_extraido(
            parent, row, col, icone, cor_fundo, cor_icone, titulo, valor, subtitulo,
            {"BRANCO": BRANCO, "TEXTO_CINZA": TEXTO_CINZA, "TEXTO_ESCURO": TEXTO_ESCURO},
        )

    def card_tabela(parent, titulo, colunas, linhas, rodape="", larguras=None):
        return _card_tabela_extraido(
            parent, titulo, colunas, linhas,
            {"BRANCO": BRANCO, "TEXTO_ESCURO": TEXTO_ESCURO,
             "VERDE_ESCURO": VERDE_ESCURO, "TEXTO_CINZA": TEXTO_CINZA},
            rodape=rodape, larguras=larguras,
        )

    # ──────────────────────────────────────────────────────────────────
    # PÁGINA: VISÃO GERAL (ligada ao banco)
    # ──────────────────────────────────────────────────────────────────
    def criar_pagina_em_construcao(nome):
        page = ctk.CTkFrame(_scroll_inner, fg_color=CINZA_BG)
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(0, weight=1)
        ctk.CTkLabel(page, text=f"Página '{nome}' — em construção\n(em breve será migrada para o novo visual)",
                      font=("Segoe UI", 16), text_color=TEXTO_CINZA, justify="center"
                      ).grid(row=0, column=0)
        return page

    pagina_inicial = "Visão Geral" if "Visão Geral" in abas_permitidas else (itens_menu[0][1] if itens_menu else None)
    if pagina_inicial:
        mostrar_pagina(pagina_inicial)
    # ──────────────────────────────────────────────────────────────────
    # PÁGINA: AVALIAÇÕES (ligada ao banco)
    # ──────────────────────────────────────────────────────────────────

def aplicar_tema(parent):
    for w in parent.winfo_children():
        cls = w.winfo_class()
        try:
            if cls in ("Frame", "Labelframe"):
                bg = w.cget("bg")
                for nome_tema in TEMAS.values():
                    if bg == nome_tema["BG_CARD"]:        w.configure(bg=T["BG_CARD"]); break
                    if bg == nome_tema["BG_MAIN"]:        w.configure(bg=T["BG_MAIN"]); break
                    if bg == nome_tema["ENTRY_BG"]:       w.configure(bg=T["ENTRY_BG"]); break
                    if bg == nome_tema["OBS_BG"]:         w.configure(bg=T["OBS_BG"]); break
                    if bg == nome_tema["ACCENT_VIBRANT"]: w.configure(bg=T["ACCENT_VIBRANT"]); break
                    if bg == nome_tema["BORDER_GRID"]:    w.configure(bg=T["BORDER_GRID"]); break
            elif cls == "Label":
                bg = w.cget("bg"); fg = w.cget("fg")
                for nome_tema in TEMAS.values():
                    if bg == nome_tema["BG_CARD"]:        w.configure(bg=T["BG_CARD"]); break
                    if bg == nome_tema["BG_MAIN"]:        w.configure(bg=T["BG_MAIN"]); break
                    if bg == nome_tema["ENTRY_BG"]:       w.configure(bg=T["ENTRY_BG"]); break
                    if bg == nome_tema["OBS_BG"]:         w.configure(bg=T["OBS_BG"]); break
                    if bg == nome_tema["ACCENT_VIBRANT"]: w.configure(bg=T["ACCENT_VIBRANT"]); break
                for nome_tema in TEMAS.values():
                    if fg == nome_tema["ACCENT_VIBRANT"]: w.configure(fg=T["ACCENT_VIBRANT"]); break
                    if fg == nome_tema["FRASE_FG"]:       w.configure(fg=T["FRASE_FG"]); break
                    if fg == nome_tema["FG_TEXT"]:        w.configure(fg=T["FG_TEXT"]); break
            elif cls == "Button":
                bg = w.cget("bg")
                for nome_tema in TEMAS.values():
                    if bg == nome_tema["ACCENT_VIBRANT"]: w.configure(bg=T["ACCENT_VIBRANT"], fg="white"); break
                    if bg == nome_tema["ACCENT_SOFT"]:    w.configure(bg=T["ACCENT_SOFT"],    fg="white"); break
                    if bg == nome_tema["BTN_CARDAPIO"]:   w.configure(bg=T["BTN_CARDAPIO"],   fg="white"); break
                    if bg == nome_tema["BTN_VOLTAR"]:     w.configure(bg=T["BTN_VOLTAR"],     fg="white"); break
                    if bg == nome_tema["OBS_BG"]:         w.configure(bg=T["OBS_BG"],  fg=T["ACCENT_VIBRANT"]); break
                    if bg == nome_tema["BG_MAIN"]:        w.configure(bg=T["BG_MAIN"], fg=T["ACCENT_VIBRANT"]); break
                    if bg == nome_tema["BG_CARD"]:        w.configure(bg=T["BG_CARD"], fg=T["FRASE_FG"]); break
            elif cls == "Entry":
                w.configure(bg=T["ENTRY_BG"], fg=T["FG_TEXT"], insertbackground=T["ACCENT_VIBRANT"])
            elif cls == "Canvas":
                bg = w.cget("bg")
                for nome_tema in TEMAS.values():
                    if bg == nome_tema["BG_CARD"]: w.configure(bg=T["BG_CARD"]); break
                    if bg == nome_tema["BG_MAIN"]: w.configure(bg=T["BG_MAIN"]); break
            elif cls == "Checkbutton":
                w.configure(bg=T["BG_CARD"], fg=T["ACCENT_VIBRANT"],
                            activebackground=T["BG_CARD"], selectcolor=T["ENTRY_BG"])
        except Exception:
            pass
        if w.winfo_children():
            aplicar_tema(w)

def alternar_tema():
    global tema_atual, T
    tema_atual = "escuro" if tema_atual=="claro" else "claro"
    T = TEMAS[tema_atual]; salvar_tema_tk(tema_atual)
    janela.configure(bg=T["BG_MAIN"])
    btn_tema.configure(text="☀️ Tema" if tema_atual=="escuro" else "🌙 Tema",
                       bg=T["ACCENT_VIBRANT"], fg="#b2dfb4")
    aplicar_tema(janela)
    for w in janela.winfo_children():
        if w.winfo_class() == "Toplevel":
            w.configure(bg=T["BG_MAIN"]); aplicar_tema(w)

def iniciar_tkinter(url_publica):
    global janela, T, tema_atual, url_ngrok_global, btn_tema
    url_ngrok_global = url_publica
    tema_atual = carregar_tema()
    T = TEMAS[tema_atual]
    janela = tk.Tk()
    janela.title("EEEP MARWIN — Servidor Admin")
    janela.state("zoomed"); janela.configure(bg=T["BG_MAIN"])
    janela.bind("<F11>", lambda e: janela.attributes("-fullscreen", not janela.attributes("-fullscreen")))

    # ── Barra de topo institucional ──────────────────────────────────────────
    barra_topo = tk.Frame(janela, bg=T["ACCENT_VIBRANT"], height=64)
    barra_topo.pack(fill="x"); barra_topo.pack_propagate(False)
    tk.Label(barra_topo, text="EEEP MARWIN",
             font=("Segoe UI", 15, "bold"), bg=T["ACCENT_VIBRANT"], fg="white").pack(side="left", padx=28, pady=16)
    tk.Label(barra_topo, text="Painel do Servidor Admin",
             font=("Segoe UI", 9), bg=T["ACCENT_VIBRANT"], fg="#b2dfb4").pack(side="left", padx=(0, 0), pady=22)

    # URL + botão copiar à direita
    url_frame = tk.Frame(barra_topo, bg=T["ACCENT_VIBRANT"]); url_frame.pack(side="right", padx=16)
    tk.Label(url_frame, text=f"● {url_publica}", font=("Segoe UI", 9),
             bg=T["ACCENT_VIBRANT"], fg="#b2dfb4").pack(side="left", padx=(0, 8))
    tk.Button(url_frame, text="Copiar URL", font=("Segoe UI", 8, "bold"),
              bg=T["ACCENT_SOFT"], fg="white", bd=0, padx=10, pady=4, cursor="hand2",
              command=lambda: [janela.clipboard_clear(),
                               janela.clipboard_append(url_publica),
                               messagebox.showinfo("Copiado", "URL copiada para a área de transferência!")]
              ).pack(side="left")

    # Botão tema na barra de topo
    btn_tema = tk.Button(barra_topo, text="🌙 Tema", font=("Segoe UI", 10),
                         bg=T["ACCENT_VIBRANT"], fg="#b2dfb4", bd=0,
                         cursor="hand2", activebackground=T["ACCENT_SOFT"],
                         command=alternar_tema)
    btn_tema.pack(side="right", padx=4)

    # ── Relógio em tempo real na barra de topo ───────────────────────────────
    lbl_relogio = tk.Label(barra_topo, text="", font=("Segoe UI", 10, "bold"),
                           bg=T["ACCENT_VIBRANT"], fg="#b2dfb4")
    lbl_relogio.pack(side="right", padx=(0, 16))

    def _atualizar_relogio():
        agora = _agora_br()
        lbl_relogio.config(text=agora.strftime("%d/%m/%Y  %H:%M:%S"))
        janela.after(1000, _atualizar_relogio)

    _atualizar_relogio()

    # Linha amarela accent
    tk.Frame(janela, bg=T["HIGHLIGHT_YELLOW"], height=4).pack(fill="x")

    # ── Conteúdo central ────────────────────────────────────────────────────
    main = tk.Frame(janela, bg=T["BG_MAIN"]); main.pack(expand=True, fill="both")
    center_wrap = tk.Frame(main, bg=T["BG_MAIN"])
    center_wrap.place(relx=0.5, rely=0.5, anchor="center")

    # Logo / ícone
    try:
        from PIL import Image as _PilImg, ImageTk as _PilImgTk
        _path_marwin = _buscar_logo_png()
        if not _path_marwin:
            _pasta = os.path.dirname(os.path.abspath(__file__))
            _path_marwin = os.path.join(_pasta, "logo_marwin.png")
        if os.path.exists(_path_marwin):
            _img = _PilImg.open(_path_marwin).convert("RGBA")
            _img.thumbnail((520, 520), _PilImg.LANCZOS)
            _logo_tk = _PilImgTk.PhotoImage(_img, master=janela)
            tk.Label(center_wrap, image=_logo_tk, bg=T["BG_MAIN"]).pack(pady=(0, 10))
            center_wrap._logo_ref = _logo_tk   # evitar GC
    except Exception:
        tk.Label(center_wrap, text="🏫", font=("Segoe UI", 44), bg=T["BG_MAIN"]).pack(pady=(0, 8))

    tk.Label(center_wrap, text="Escola Estadual de Educação Profissional",
             font=("Segoe UI", 13), bg=T["BG_MAIN"], fg=T["FRASE_FG"]).pack()
    tk.Label(center_wrap, text="MARWIN",
             font=("Segoe UI", 44, "bold"), bg=T["BG_MAIN"], fg=T["ACCENT_VIBRANT"]).pack(pady=(2, 4))
    tk.Label(center_wrap, text="Painel do Servidor",
             font=("Segoe UI", 11), bg=T["BG_MAIN"], fg=T["FRASE_FG"]).pack()

    tk.Frame(center_wrap, bg=T["BORDER_GRID"], height=1).pack(fill="x", pady=(18, 14))

    # ── Cards de status em tempo real ────────────────────────────────────────
    cards_frame = tk.Frame(center_wrap, bg=T["BG_MAIN"])
    cards_frame.pack(fill="x", pady=(0, 14))

    def _criar_card_status(parent, titulo, col):
        card = tk.Frame(parent, bg=T["BG_CARD"],
                        highlightbackground=T["BORDER_GRID"], highlightthickness=1)
        card.grid(row=0, column=col, padx=6, pady=0, sticky="nsew")
        lbl_titulo = tk.Label(card, text=titulo, font=("Segoe UI", 8),
                              bg=T["BG_CARD"], fg=T["FRASE_FG"])
        lbl_titulo.pack(pady=(8, 2), padx=14)
        lbl_valor = tk.Label(card, text="—", font=("Segoe UI", 22, "bold"),
                             bg=T["BG_CARD"], fg=T["ACCENT_VIBRANT"])
        lbl_valor.pack(pady=(0, 2), padx=14)
        lbl_sub = tk.Label(card, text="", font=("Segoe UI", 8),
                           bg=T["BG_CARD"], fg=T["FRASE_FG"])
        lbl_sub.pack(pady=(0, 8), padx=14)
        return lbl_valor, lbl_sub

    for c in range(3):
        cards_frame.grid_columnconfigure(c, weight=1, uniform="sc")

    lbl_val_ref,  lbl_sub_ref  = _criar_card_status(cards_frame, "Refeições hoje",   0)
    lbl_val_freq, lbl_sub_freq = _criar_card_status(cards_frame, "Presenças hoje",   1)
    lbl_val_db,   lbl_sub_db   = _criar_card_status(cards_frame, "Banco de dados",   2)

    # Indicador de saúde: ponto colorido no card de banco
    _dot_colors = {"ok": "#4caf50", "erro": "#f44336", "verificando": "#fdd835"}

    def _atualizar_cards_status():
        """Atualiza os cards de status a cada 15 segundos.

        A consulta ao banco roda em thread separada (evita travar a UI com
        a latência de rede do Neon), mas TODA atualização de widgets é feita
        de volta na thread principal via janela.after — Tkinter não é
        thread-safe e chamar .config() direto de outra thread pode travar
        ou corromper o loop de eventos da aplicação inteira.
        """
        def _tarefa():
            # Refeitório hoje
            try:
                total_ref = len(_ler_refeitorio_hoje_db())
                ref_result = (str(total_ref), "registros no refeitório")
            except Exception:
                ref_result = ("—", "indisponível")

            # Frequência hoje
            try:
                total_freq = len(_ler_frequencia_hoje_db())
                freq_result = (str(total_freq), "alunos registrados")
            except Exception:
                freq_result = ("—", "indisponível")

            # Saúde do banco
            try:
                conn = get_pg_conn()
                if conn:
                    _release_pg_conn(conn)
                    db_result = ("● Online", _dot_colors["ok"], "PostgreSQL Neon")
                else:
                    db_result = ("● Offline", _dot_colors["erro"], "sem conexão")
            except Exception:
                db_result = ("● Erro", _dot_colors["erro"], "falha na verificação")

            def _aplicar():
                lbl_val_ref.config(text=ref_result[0])
                lbl_sub_ref.config(text=ref_result[1])
                lbl_val_freq.config(text=freq_result[0])
                lbl_sub_freq.config(text=freq_result[1])
                lbl_val_db.config(text=db_result[0], fg=db_result[1])
                lbl_sub_db.config(text=db_result[2])

            janela.after(0, _aplicar)

        threading.Thread(target=_tarefa, daemon=True).start()
        janela.after(15000, _atualizar_cards_status)

    _atualizar_cards_status()

    tk.Button(center_wrap, text="  ABRIR PAINEL ADMIN  ",
              font=("Segoe UI", 17, "bold"),
              bg=T["ACCENT_VIBRANT"], fg="white", bd=0,
              padx=50, pady=20, cursor="hand2",
              activebackground=T["ACCENT_SOFT"], activeforeground="white",
              command=abrir_painel_admin_ctk).pack(fill="x")

    tk.Label(center_wrap,
             text="💚 Servidor ativo — aguardando conexões dos clientes.",
             bg=T["BG_MAIN"], fg=T["FRASE_FG"],
             font=("Segoe UI", 10, "italic")).pack(pady=(24, 0))

    janela.mainloop()

# ==============================================================================
# INICIALIZACAO
# ==============================================================================
if __name__ == "__main__":
    _iniciar_pool_pg()
    try:
        _criar_tabelas_neon()
    except Exception:
        pass
    if _cloud_api_url():
        threading.Thread(target=_sincronizar_tudo_nuvem, daemon=True).start()

    threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=5000, use_reloader=False, debug=False, threaded=True),
        daemon=True
    ).start()
    time.sleep(1)

    local_ip = _get_local_ip()
    url = f"http://{local_ip}:5000"
    logger.info(f"Servidor MARWIN iniciado em {url}")
    print(f"\n[CLIENTE] Acesse localmente em: {url}")
    print(f"[CLIENTE] Ou use http://localhost:5000 no proprio computador")

    iniciar_tkinter(url)