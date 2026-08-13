import streamlit as st
import pandas as pd
import numpy as np
import re
import hashlib
import os
import binascii
import hmac
import base64
from io import BytesIO
from PIL import Image
from datetime import datetime
import json

try:
    import pypdf
    PYPDF_DISPONIVEL = True
except ImportError:
    PYPDF_DISPONIVEL = False

try:
    import openpyxl
    OPENPYXL_DISPONIVEL = True
except ImportError:
    OPENPYXL_DISPONIVEL = False

try:
    import psycopg2
    PSYCOPG2_DISPONIVEL = True
except ImportError:
    PSYCOPG2_DISPONIVEL = False

try:
    from sqlalchemy import create_engine, text
    DB_LIBS_DISPONIVEIS = True
except ImportError:
    DB_LIBS_DISPONIVEIS = False

st.set_page_config(
    page_title="OutLog - DISTRIBOX",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main { background-color: #0a0a1a; color: #e0e0e0; }
    .stApp { background-color: #0a0a1a; }
    .css-1d391kg { background-color: #0a0a1a; }
    .css-1d391kg h1, .css-1d391kg h2, .css-1d391kg h3 { color: #ffcc00; }
    .card { background: linear-gradient(145deg, #1a1a2e, #16213e); border-radius: 10px; padding: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); border-left: 4px solid #ffcc00; margin-bottom: 10px; }
    .card-success { border-left-color: #00cc88; }
    .card-danger { border-left-color: #ff4444; }
    .card-info { border-left-color: #4488ff; }
    .title-main { text-align: center; color: #ffcc00; font-size: 2.5em; font-weight: 700; text-shadow: 0 0 20px rgba(255,204,0,0.3); margin-bottom: 10px; }
    .subtitle { text-align: center; color: #8892b0; font-size: 1.1em; margin-bottom: 30px; }
    .stButton > button { background: linear-gradient(135deg, #ffcc00, #f0a500); color: #0a0a1a; font-weight: 600; border: none; border-radius: 8px; padding: 10px 25px; transition: all 0.3s ease; }
    .stButton > button:hover { transform: scale(1.02); box-shadow: 0 0 20px rgba(255,204,0,0.3); }
    .metric-box { background: #1a1a2e; border-radius: 10px; padding: 15px; text-align: center; border: 1px solid #2a2a4e; }
    .metric-value { font-size: 2em; font-weight: 700; color: #ffcc00; }
    .metric-label { color: #8892b0; font-size: 0.9em; }
    .stTabs [data-baseweb="tab-list"] { gap: 2px; background: #1a1a2e; border-radius: 8px; padding: 4px; }
    .stTabs [data-baseweb="tab"] { background: transparent; color: #8892b0; border-radius: 6px; padding: 8px 16px; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { background: #ffcc00; color: #0a0a1a; }
</style>
""", unsafe_allow_html=True)

ESTRUTURA_CD = {
    "Rua 01": {"tipo": "Morta"},
    "Rua 02": {"tipo": "Misto_Transicao", "cols_impar": list(range(21, 94, 2)), "cols_par": list(range(22, 103, 2)) + list(range(103, 141, 1))},
    "Rua 03": {"tipo": "P", "cols_impar": list(range(1, 101, 2)), "cols_par": list(range(2, 102, 2))},
    "Rua 04": {"tipo": "Misto_Lado", "cols_impar": list(range(1, 101, 2)), "cols_par": list(range(2, 102, 2))},
    "Rua 05": {"tipo": "M", "cols_impar": list(range(21, 101, 2)), "cols_par": list(range(22, 103, 2))},
    "Rua 06": {"tipo": "M", "cols_impar": list(range(1, 82, 2)), "cols_par": list(range(2, 83, 2))},
    "Rua 07": {"tipo": "M", "cols_impar": list(range(59, 140, 2)), "cols_par": list(range(60, 141, 2))},
    "Rua 08": {"tipo": "M", "cols_impar": list(range(1, 82, 2)), "cols_par": list(range(2, 83, 2))},
    "Rua 09": {"tipo": "M", "cols_impar": list(range(21, 104, 2)), "cols_par": list(range(22, 101, 2))},
    "Rua 10": {"tipo": "G", "cols_impar": list(range(21, 104, 2)), "cols_par": list(range(22, 103, 2))},
    "Rua 11": {"tipo": "G_Unilateral", "cols_par": list(range(22, 95, 2))},
    "Rua 12": {"tipo": "Inexistente"},
    "Rua 13": {"tipo": "Inexistente"},
    "Rua 14": {"tipo": "Especial_Rua_14", "cols_seq": list(range(1, 32, 1)) + list(range(42, 49, 1))},
    "Rua 15": {"tipo": "Misto_Lado_15", "cols_impar": list(range(1, 88, 2)), "cols_par": list(range(2, 139, 2))},
    "Rua 16": {"tipo": "G", "cols_impar": list(range(1, 101, 2)), "cols_par": list(range(2, 102, 2)), "metal": [43]},
    "Rua 17": {"tipo": "G", "cols_impar": list(range(1, 115, 2)), "cols_par": list(range(2, 116, 2)), "metal": [101,102,103,104,105,106]},
    "Rua 18": {"tipo": "M", "cols_impar": list(range(1, 81, 2)), "cols_par": list(range(2, 82, 2)), "metal": [35,36,37,38,39,40]},
    "Rua 19": {"tipo": "P", "cols_impar": list(range(1, 115, 2)), "cols_par": list(range(2, 116, 2)), "metal": [101,102,103,104,105,106]},
    "Rua 20": {"tipo": "Aramado_P_Seq_20", "cols_seq": list(range(35, 138, 2)), "metal_cols": [35,37,39]},
    "Rua 21": {"tipo": "Metal_Seq_21", "cols_seq": list(range(1, 78, 2))}
}

CAPACIDADE_VERAO_FEMININO = {
    "Regatas/Bodys/Tops/Croppeds": {"P": (8,10), "M": (16,20), "G": (35,40), "Metal Raso (GG)": (80,100), "Madeira/Metal Prof. (3G)": (180,220)},
    "Camisetas/Camisas M.Curta Finas": {"P": (7,8), "M": (14,16), "G": (28,32), "Metal Raso (GG)": (60,70), "Madeira/Metal Prof. (3G)": (130,160)},
}

CAPACIDADE_INVERNO_FEMININO = {
    "Camisetas M.Longa/Cacharrel Fina": {"P": (5,6), "M": (10,12), "G": (20,24), "Metal Raso (GG)": (40,50), "Madeira/Metal Prof. (3G)": (90,110)},
}

CAPACIDADE_VERAO_MASCULINO = {
    "Camisetas": {"P": (8,10), "M": (14,16), "G": (28,32), "Metal Raso (GG)": (60,70), "Madeira/Metal Prof. (3G)": (130,160)},
}

CAPACIDADE_INVERNO_MASCULINO = {
    "Camisetas ML": {"P": (5,6), "M": (10,12), "G": (20,24), "Metal Raso (GG)": (40,50), "Madeira/Metal Prof. (3G)": (90,110)},
}

GENERO_RUA = {
    "Rua 02": "Feminino", "Rua 03": "Feminino", "Rua 04": "Feminino",
    "Rua 05": "Feminino", "Rua 06": "Feminino", "Rua 07": "Feminino",
    "Rua 08": "Feminino", "Rua 09": "Feminino", "Rua 10": "Feminino",
    "Rua 11": "Feminino", "Rua 14": "Feminino",
    "Rua 15": "Masculino", "Rua 16": "Masculino", "Rua 17": "Masculino",
    "Rua 18": "Masculino", "Rua 19": "Masculino", "Rua 20": "Masculino",
    "Rua 21": "Masculino"
}

def obter_conexao_bd():
    try:
        if not DB_LIBS_DISPONIVEIS or "postgres" not in st.secrets:
            return None
        host = st.secrets["postgres"]["host"]
        port = st.secrets["postgres"]["port"]
        dbname = st.secrets["postgres"]["dbname"]
        user = st.secrets["postgres"]["user"]
        password = st.secrets["postgres"]["password"]
        url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}?sslmode=require"
        engine = create_engine(url)
        return engine.connect()
    except Exception as e:
        st.session_state.ultimo_erro_bd = str(e)
        return None

def parse_range_input(input_str):
    if not input_str or input_str.strip() == "":
        return []
    result = []
    for part in input_str.split(","):
        part = part.strip()
        if "-" in part:
            parts = part.split("-")
            start = int(parts[0])
            if len(parts) == 2:
                end = int(parts[1])
                step = 1
            elif len(parts) == 3:
                end = int(parts[1])
                step = int(parts[2])
            else:
                continue
            result.extend(list(range(start, end + 1, step)))
        else:
            try:
                result.append(int(part))
            except ValueError:
                continue
    return sorted(set(result))

def salvar_estrutura_rua_no_banco(rua_nome, config):
    conn = obter_conexao_bd()
    if conn is None:
        return False
    try:
        with conn.begin() as cur:
            cur.execute("""
                INSERT INTO estrutura_cd (rua_nome, tipo, cols_impar, cols_par, cols_seq, metal, metal_cols, atualizado_em)
                VALUES (%s, %s, %s, %s, %s, %s, %s, now())
                ON CONFLICT (rua_nome) DO UPDATE SET 
                    tipo = EXCLUDED.tipo, cols_impar = EXCLUDED.cols_impar,
                    cols_par = EXCLUDED.cols_par, cols_seq = EXCLUDED.cols_seq,
                    metal = EXCLUDED.metal, metal_cols = EXCLUDED.metal_cols,
                    atualizado_em = now()
            """, (rua_nome, config.get("tipo", "P"), config.get("cols_impar", []),
                  config.get("cols_par", []), config.get("cols_seq", []),
                  config.get("metal", []), config.get("metal_cols", [])))
        conn.close()
        return True
    except Exception as e:
        try: conn.close()
        except: pass
        st.session_state.ultimo_erro_bd = str(e)
        return False

def carregar_estrutura_do_banco():
    conn = obter_conexao_bd()
    if conn is None:
        return dict(ESTRUTURA_CD)
    try:
        with conn.execute(text("SELECT rua_nome, tipo, cols_impar, cols_par, cols_seq, metal, metal_cols FROM estrutura_cd")) as cur:
            linhas = cur.fetchall()
        conn.close()
    except Exception as e:
        try: conn.close()
        except: pass
        st.session_state.ultimo_erro_bd = str(e)
        return dict(ESTRUTURA_CD)
    if not linhas:
        return dict(ESTRUTURA_CD)
    estrutura = {}
    for rua, tipo, cols_impar, cols_par, cols_seq, metal, metal_cols in linhas:
        cfg = {"tipo": tipo}
        if cols_impar and len(cols_impar) > 0:
            cfg["cols_impar"] = list(cols_impar)
        if cols_par and len(cols_par) > 0:
            cfg["cols_par"] = list(cols_par)
        if cols_seq and len(cols_seq) > 0:
            cfg["cols_seq"] = list(cols_seq)
        if metal and len(metal) > 0:
            cfg["metal"] = list(metal)
        if metal_cols and len(metal_cols) > 0:
            cfg["metal_cols"] = list(metal_cols)
        estrutura[rua] = cfg
    return estrutura

def salvar_capacidade_no_banco(categoria, estacao, tipo_casulo, genero, min_val, max_val):
    conn = obter_conexao_bd()
    if conn is None:
        return False
    try:
        with conn.begin() as cur:
            cur.execute(text("""
                INSERT INTO capacidade_casulo (categoria_peca, estacao, tipo_casulo, genero, capacidade_min, capacidade_max, atualizado_em)
                VALUES (:categoria, :estacao, :tipo, :genero, :min, :max, now())
                ON CONFLICT (categoria_peca, estacao, tipo_casulo, genero) DO UPDATE SET
                    capacidade_min = EXCLUDED.capacidade_min, capacidade_max = EXCLUDED.capacidade_max,
                    atualizado_em = now()
            """), {"categoria": categoria, "estacao": estacao, "tipo": tipo_casulo,
                   "genero": genero, "min": min_val, "max": max_val})
        conn.close()
        return True
    except Exception as e:
        try: conn.close()
        except: pass
        st.session_state.ultimo_erro_bd = str(e)
        return False

def hash_senha(senha):
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac('sha256', senha.encode('utf-8'), salt, 100000)
    return salt + key

def verificar_senha(senha, hash_armazenado):
    salt = hash_armazenado[:32]
    key = hash_armazenado[32:]
    novo_hash = hashlib.pbkdf2_hmac('sha256', senha.encode('utf-8'), salt, 100000)
    return hmac.compare_digest(key, novo_hash)

def autenticar_usuario(usuario, senha):
    conn = obter_conexao_bd()
    if conn is None:
        if usuario == "admin" and senha == "admin123":
            return "gerente"
        return None
    try:
        with conn.execute(text("SELECT senha_hash, papel FROM usuarios WHERE usuario = :usuario"), {"usuario": usuario}) as cur:
            linha = cur.fetchone()
        conn.close()
        if linha:
            hash_armazenado = linha[0]
            papel = linha[1]
            if isinstance(hash_armazenado, str):
                hash_armazenado = bytes.fromhex(hash_armazenado)
            if verificar_senha(senha, hash_armazenado):
                return papel
        return None
    except Exception as e:
        try: conn.close()
        except: pass
        st.session_state.ultimo_erro_bd = str(e)
        if usuario == "admin" and senha == "admin123":
            return "gerente"
        return None

def criar_usuario(usuario, senha, papel):
    conn = obter_conexao_bd()
    if conn is None:
        return False
    try:
        hash_bytes = hash_senha(senha)
        with conn.begin() as cur:
            cur.execute(text("INSERT INTO usuarios (usuario, senha_hash, papel, criado_em) VALUES (:usuario, :senha_hash, :papel, now())"),
                       {"usuario": usuario, "senha_hash": hash_bytes, "papel": papel})
        conn.close()
        return True
    except Exception as e:
        try: conn.close()
        except: pass
        st.session_state.ultimo_erro_bd = str(e)
        return False

def listar_usuarios():
    conn = obter_conexao_bd()
    if conn is None:
        return [("admin", "gerente")]
    try:
        with conn.execute(text("SELECT usuario, papel FROM usuarios ORDER BY usuario")) as cur:
            linhas = cur.fetchall()
        conn.close()
        return [(u, p) for u, p in linhas]
    except Exception as e:
        try: conn.close()
        except: pass
        st.session_state.ultimo_erro_bd = str(e)
        return [("admin", "gerente")]

def obter_capacidade(categoria, estacao, tipo_casulo, genero):
    tabela_verao, tabela_inverno = (CAPACIDADE_VERAO_FEMININO, CAPACIDADE_INVERNO_FEMININO) if genero == "Feminino" else (CAPACIDADE_VERAO_MASCULINO, CAPACIDADE_INVERNO_MASCULINO)
    tabela_alvo = tabela_inverno if estacao == "Inverno" else tabela_verao
    return tabela_alvo.get(categoria, {}).get(tipo_casulo)

def calcular_ocupacao(categoria, estacao, tipo_casulo, genero, quantidade):
    capacidade = obter_capacidade(categoria, estacao, tipo_casulo, genero)
    if capacidade is None or capacidade[1] == 0:
        return None
    return (quantidade / capacidade[1]) * 100

def salvar_no_banco(chave_casulo, categoria_peca, estacao, quantidade, usuario="sistema"):
    conn = obter_conexao_bd()
    if conn is None:
        return False
    try:
        with conn.execute(text("SELECT quantidade FROM estoque_casulo WHERE chave_casulo = :chave AND categoria_peca = :cat AND estacao = :est"),
                         {"chave": chave_casulo, "cat": categoria_peca, "est": estacao}) as cur:
            anterior = cur.fetchone()
        quant_anterior = anterior[0] if anterior else 0
        with conn.begin() as cur:
            cur.execute(text("INSERT INTO estoque_casulo (chave_casulo, categoria_peca, estacao, quantidade, atualizado_em) VALUES (:chave, :cat, :est, :qtd, now()) ON CONFLICT (chave_casulo, categoria_peca, estacao) DO UPDATE SET quantidade = EXCLUDED.quantidade, atualizado_em = now()"),
                       {"chave": chave_casulo, "cat": categoria_peca, "est": estacao, "qtd": quantidade})
            if quant_anterior != quantidade:
                cur.execute(text("INSERT INTO movimentacoes_estoque (chave_casulo, categoria_peca, estacao, quantidade_anterior, quantidade_nova, tipo_movimento, usuario) VALUES (:chave, :cat, :est, :anterior, :nova, 'atualizacao', :usuario)"),
                           {"chave": chave_casulo, "cat": categoria_peca, "est": estacao, "anterior": quant_anterior, "nova": quantidade, "usuario": usuario})
        conn.close()
        return True
    except Exception as e:
        try: conn.close()
        except: pass
        st.session_state.ultimo_erro_bd = str(e)
        return False

def carregar_estoque_do_banco():
    conn = obter_conexao_bd()
    if conn is None:
        return {}
    try:
        with conn.execute(text("SELECT chave_casulo, categoria_peca, estacao, quantidade FROM estoque_casulo")) as cur:
            linhas = cur.fetchall()
        conn.close()
        estoque = {}
        for chave, cat, est, qtd in linhas:
            estoque[(chave, cat, est)] = qtd
        return estoque
    except Exception as e:
        try: conn.close()
        except: pass
        st.session_state.ultimo_erro_bd = str(e)
        return {}

def salvar_lote_no_banco(dados, usuario="sistema"):
    conn = obter_conexao_bd()
    if conn is None:
        return False
    try:
        for chave, cat, est, qtd in dados:
            with conn.execute(text("SELECT quantidade FROM estoque_casulo WHERE chave_casulo = :chave AND categoria_peca = :cat AND estacao = :est"),
                             {"chave": chave, "cat": cat, "est": est}) as cur:
                anterior = cur.fetchone()
            quant_anterior = anterior[0] if anterior else 0
            with conn.begin() as cur:
                cur.execute(text("INSERT INTO estoque_casulo (chave_casulo, categoria_peca, estacao, quantidade, atualizado_em) VALUES (:chave, :cat, :est, :qtd, now()) ON CONFLICT (chave_casulo, categoria_peca, estacao) DO UPDATE SET quantidade = EXCLUDED.quantidade, atualizado_em = now()"),
                           {"chave": chave, "cat": cat, "est": est, "qtd": qtd})
                if quant_anterior != qtd:
                    cur.execute(text("INSERT INTO movimentacoes_estoque (chave_casulo, categoria_peca, estacao, quantidade_anterior, quantidade_nova, tipo_movimento, usuario) VALUES (:chave, :cat, :est, :anterior, :nova, 'lote', :usuario)"),
                               {"chave": chave, "cat": cat, "est": est, "anterior": quant_anterior, "nova": qtd, "usuario": usuario})
        conn.close()
        return True
    except Exception as e:
        try: conn.close()
        except: pass
        st.session_state.ultimo_erro_bd = str(e)
        return False

def gerar_chaves_casulo(estrutura):
    chaves = []
    for rua, cfg in estrutura.items():
        tipo = cfg.get("tipo", "P")
        cols_impar = cfg.get("cols_impar", [])
        cols_par = cfg.get("cols_par", [])
        cols_seq = cfg.get("cols_seq", [])
        if tipo in ["P", "Misto_Lado", "Misto_Transicao", "Misto_Lado_15"]:
            niveis = 21
        elif tipo in ["M", "Especial_Rua_14"]:
            niveis = 14
        elif tipo in ["G", "G_Unilateral", "Aramado_P_Seq_20"]:
            niveis = 7
        elif tipo == "Metal_Seq_21":
            niveis = 7
        elif tipo == "Morta":
            niveis = 0
        else:
            niveis = 21
        if cols_seq:
            for col in cols_seq:
                for nivel in range(1, niveis + 1):
                    chaves.append(f"{rua}-{col}-{nivel}")
            continue
        for col in cols_impar:
            for nivel in range(1, niveis + 1):
                chaves.append(f"{rua}-{col}-{nivel}")
        for col in cols_par:
            for nivel in range(1, niveis + 1):
                chaves.append(f"{rua}-{col}-{nivel}")
    return chaves

def gerar_estrutura_rua_para_visualizacao(estrutura):
    dados = []
    for rua, cfg in estrutura.items():
        tipo = cfg.get("tipo", "P")
        cols_impar = cfg.get("cols_impar", [])
        cols_par = cfg.get("cols_par", [])
        cols_seq = cfg.get("cols_seq", [])
        metal = cfg.get("metal", [])
        metal_cols = cfg.get("metal_cols", [])
        total_cols = len(cols_impar) + len(cols_par) + len(cols_seq)
        if tipo in ["P", "Misto_Lado", "Misto_Transicao", "Misto_Lado_15"]:
            niveis = 21
        elif tipo in ["M", "Especial_Rua_14"]:
            niveis = 14
        elif tipo in ["G", "G_Unilateral", "Aramado_P_Seq_20"]:
            niveis = 7
        elif tipo == "Metal_Seq_21":
            niveis = 7
        elif tipo == "Morta":
            niveis = 0
        else:
            niveis = 21
        total_casulos = total_cols * niveis
        genero = GENERO_RUA.get(rua, "Indefinido")
        dados.append({"Rua": rua, "Tipo": tipo, "Colunas": total_cols, "Níveis": niveis,
                      "Casulos": total_casulos, "Gênero": genero, "Metal": "✓" if metal else "",
                      "Metal Cols": "✓" if metal_cols else "", "Lado Ímpar": len(cols_impar),
                      "Lado Par": len(cols_par), "Seq": len(cols_seq)})
    return dados

def mostrar_metricas_cds(estrutura):
    total_casulos = 0
    total_ruas = 0
    total_colunas = 0
    for rua, cfg in estrutura.items():
        if cfg.get("tipo") in ["Morta", "Inexistente"]:
            continue
        total_ruas += 1
        cols_impar = cfg.get("cols_impar", [])
        cols_par = cfg.get("cols_par", [])
        cols_seq = cfg.get("cols_seq", [])
        total_colunas += len(cols_impar) + len(cols_par) + len(cols_seq)
        tipo = cfg.get("tipo", "P")
        if tipo in ["P", "Misto_Lado", "Misto_Transicao", "Misto_Lado_15"]:
            niveis = 21
        elif tipo in ["M", "Especial_Rua_14"]:
            niveis = 14
        elif tipo in ["G", "G_Unilateral", "Aramado_P_Seq_20"]:
            niveis = 7
        elif tipo == "Metal_Seq_21":
            niveis = 7
        else:
            niveis = 21
        total_casulos += (len(cols_impar) + len(cols_par) + len(cols_seq)) * niveis
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-box"><div class="metric-value">{total_ruas}</div><div class="metric-label">Ruas Ativas</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-box"><div class="metric-value">{total_colunas}</div><div class="metric-label">Colunas</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-box"><div class="metric-value">{total_casulos:,}</div><div class="metric-label">Casulos Totais</div></div>', unsafe_allow_html=True)
    with col4:
        fem = 0
        masc = 0
        for rua, cfg in estrutura.items():
            if cfg.get("tipo") in ["Morta", "Inexistente"]:
                continue
            genero = GENERO_RUA.get(rua, "Indefinido")
            tipo = cfg.get("tipo", "P")
            if tipo in ["P", "Misto_Lado", "Misto_Transicao", "Misto_Lado_15"]:
                niveis = 21
            elif tipo in ["M", "Especial_Rua_14"]:
                niveis = 14
            elif tipo in ["G", "G_Unilateral", "Aramado_P_Seq_20"]:
                niveis = 7
            elif tipo == "Metal_Seq_21":
                niveis = 7
            else:
                niveis = 21
            cols = len(cfg.get("cols_impar", [])) + len(cfg.get("cols_par", [])) + len(cfg.get("cols_seq", []))
            qtd = cols * niveis
            if genero == "Feminino":
                fem += qtd
            elif genero == "Masculino":
                masc += qtd
        st.markdown(f'<div class="metric-box"><div class="metric-value" style="font-size: 1.2em;">👩 {fem:,} | 👨 {masc:,}</div><div class="metric-label">Feminino / Masculino</div></div>', unsafe_allow_html=True)

def tela_inicial():
    st.markdown('<h1 class="title-main">📦 OutLog - DISTRIBOX</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Sistema de Gestão de Estoque por Casulos</p>', unsafe_allow_html=True)
    estrutura_atual = carregar_estrutura_do_banco()
    mostrar_metricas_cds(estrutura_atual)
    st.markdown("---")
    st.markdown("### 📋 Últimas Movimentações")
    conn = obter_conexao_bd()
    if conn is not None:
        try:
            with conn.execute(text("SELECT chave_casulo, categoria_peca, quantidade_anterior, quantidade_nova, tipo_movimento, usuario, registrado_em FROM movimentacoes_estoque ORDER BY registrado_em DESC LIMIT 10")) as cur:
                movs = cur.fetchall()
            conn.close()
            if movs:
                for chave, cat, ant, novo, tipo, usuario, data in movs:
                    st.markdown(f'<div style="background: #1a1a2e; padding: 10px 15px; border-radius: 8px; margin-bottom: 5px; border-left: 3px solid {"#00cc88" if novo > ant else "#ff4444"};"><span style="color: #8892b0; font-size: 0.8em;">{data.strftime("%d/%m/%Y %H:%M")}</span> <span style="color: #ffcc00; font-weight: 600;">{chave}</span> <span style="color: #e0e0e0;">{cat}</span> <span style="color: #8892b0;">{ant} → {novo}</span> <span style="color: #8892b0; font-size: 0.8em;">por {usuario}</span></div>', unsafe_allow_html=True)
            else:
                st.info("Nenhuma movimentação registrada ainda.")
        except Exception as e:
            conn.close()
            st.warning(f"Não foi possível carregar movimentações: {e}")
    else:
        st.warning("Banco de dados não disponível. Usando modo offline.")

def tela_visualizador():
    st.markdown('<h3 style="text-align: center; color: #ffcc00;">🔍 Visualizador de Casulos</h3>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #8892b0;">Visualize a estrutura completa do CD</p>', unsafe_allow_html=True)
    estrutura_atual = carregar_estrutura_do_banco()
    col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
    with col_f1:
        ruas_disponiveis = [r for r in estrutura_atual.keys() if estrutura_atual[r].get("tipo") not in ["Morta", "Inexistente"]]
        rua_selecionada = st.selectbox("Selecione uma Rua:", ["Todas"] + ruas_disponiveis)
    with col_f2:
        genero_filtro = st.selectbox("Gênero:", ["Todos", "Feminino", "Masculino"])
    with col_f3:
        tipo_filtro = st.selectbox("Tipo:", ["Todos", "P", "M", "G", "Misto_Lado", "Misto_Transicao", "G_Unilateral", "Especial_Rua_14"])
    dados = gerar_estrutura_rua_para_visualizacao(estrutura_atual)
    if rua_selecionada != "Todas":
        dados = [d for d in dados if d["Rua"] == rua_selecionada]
    if genero_filtro != "Todos":
        dados = [d for d in dados if d["Gênero"] == genero_filtro]
    if tipo_filtro != "Todos":
        dados = [d for d in dados if d["Tipo"] == tipo_filtro]
    if dados:
        df = pd.DataFrame(dados)
        st.dataframe(df, use_container_width=True, hide_index=True)
        total_casulos = sum(d["Casulos"] for d in dados)
        st.markdown(f"<p style='text-align: right; color: #8892b0;'>Total de casulos: <strong style='color: #ffcc00;'>{total_casulos:,}</strong></p>", unsafe_allow_html=True)
    else:
        st.info("Nenhum dado encontrado com os filtros selecionados.")

def tela_consulta_rapida():
    st.markdown('<h3 style="text-align: center; color: #ffcc00;">⚡ Consulta Rápida</h3>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #8892b0;">Consulte a ocupação de um casulo específico</p>', unsafe_allow_html=True)
    estrutura_atual = carregar_estrutura_do_banco()
    todas_chaves = gerar_chaves_casulo(estrutura_atual)
    chave_busca = st.text_input("Digite a chave do casulo (ex: Rua 03-5-3):")
    if chave_busca:
        chave_busca = chave_busca.strip()
        if chave_busca in todas_chaves:
            st.success(f"✅ Casulo {chave_busca} encontrado!")
            estoque = carregar_estoque_do_banco()
            dados_encontrados = []
            for (chave, cat, est), qtd in estoque.items():
                if chave == chave_busca:
                    dados_encontrados.append((cat, est, qtd))
            if dados_encontrados:
                for cat, est, qtd in dados_encontrados:
                    genero = GENERO_RUA.get(chave_busca.split("-")[0], "Indefinido")
                    ocupacao = calcular_ocupacao(cat, est, "P", genero, qtd)
                    st.markdown(f'<div class="card card-success"><div style="display: flex; justify-content: space-between; align-items: center;"><div><strong style="color: #ffcc00;">{cat}</strong> <span style="color: #8892b0;">• {est}</span></div><div style="text-align: right;"><div style="font-size: 1.5em; font-weight: 700; color: #e0e0e0;">{qtd}</div><div style="color: #8892b0; font-size: 0.85em;">{f"Ocupação: {ocupacao:.1f}%" if ocupacao is not None else "Sem capacidade definida"}</div></div></div></div>', unsafe_allow_html=True)
            else:
                st.info(f"ℹ️ Casulo {chave_busca} está vazio (sem dados de estoque).")
        else:
            st.error(f"❌ Casulo {chave_busca} não encontrado na estrutura.")

def tela_estatisticas():
    st.markdown('<h3 style="text-align: center; color: #ffcc00;">📊 Estatísticas</h3>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #8892b0;">Análise detalhada do estoque</p>', unsafe_allow_html=True)
    estoque = carregar_estoque_do_banco()
    if estoque:
        total_itens = sum(estoque.values())
        categorias = {}
        estacoes = {}
        for (chave, cat, est), qtd in estoque.items():
            categorias[cat] = categorias.get(cat, 0) + qtd
            estacoes[est] = estacoes.get(est, 0) + qtd
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total de Peças", f"{total_itens:,}")
        with col2:
            st.metric("Categorias", len(categorias))
        with col3:
            st.metric("Estações", len(estacoes))
        with col4:
            st.metric("Casulos Ocupados", len([k for k, v in estoque.items() if v > 0]))
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("##### 📈 Por Categoria")
            df_cat = pd.DataFrame(categorias.items(), columns=["Categoria", "Quantidade"])
            df_cat = df_cat.sort_values("Quantidade", ascending=False).head(10)
            st.bar_chart(df_cat.set_index("Categoria"))
        with col2:
            st.markdown("##### 📈 Por Estação")
            df_est = pd.DataFrame(estacoes.items(), columns=["Estação", "Quantidade"])
            st.bar_chart(df_est.set_index("Estação"))
        st.markdown("##### 🏆 Top Casulos por Quantidade")
        top_casulos = sorted(estoque.items(), key=lambda x: x[1], reverse=True)[:10]
        for (chave, cat, est), qtd in top_casulos:
            st.markdown(f'<div style="background: #1a1a2e; padding: 8px 15px; border-radius: 6px; margin-bottom: 3px; display: flex; justify-content: space-between;"><span><span style="color: #ffcc00;">{chave}</span> <span style="color: #8892b0;">{cat} • {est}</span></span><span style="color: #e0e0e0; font-weight: 600;">{qtd}</span></div>', unsafe_allow_html=True)
    else:
        st.info("ℹ️ Nenhum dado de estoque disponível.")

def tela_entrada_dados():
    st.markdown('<h3 style="text-align: center; color: #ffcc00;">📝 Entrada de Dados</h3>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #8892b0;">Adicione ou atualize itens no estoque</p>', unsafe_allow_html=True)
    estrutura_atual = carregar_estrutura_do_banco()
    todas_chaves = gerar_chaves_casulo(estrutura_atual)
    col1, col2 = st.columns(2)
    with col1:
        chave = st.selectbox("Selecione o Casulo:", todas_chaves)
    with col2:
        categoria = st.text_input("Categoria da Peça:", placeholder="Ex: Camiseta, Calça, Vestido...")
    col3, col4 = st.columns(2)
    with col3:
        estacao = st.selectbox("Estação:", ["Verão", "Inverno", "Meia-Estação"])
    with col4:
        quantidade = st.number_input("Quantidade:", min_value=0, step=1, value=0)
    if st.button("💾 Salvar", type="primary"):
        if chave and categoria and quantidade >= 0:
            usuario = st.session_state.get("usuario_atual", "sistema")
            if salvar_no_banco(chave, categoria, estacao, quantidade, usuario):
                st.success(f"✅ {chave} atualizado com sucesso!")
                st.balloons()
            else:
                st.error(f"❌ Erro ao salvar: {st.session_state.get('ultimo_erro_bd', 'Erro desconhecido')}")
        else:
            st.warning("⚠️ Preencha todos os campos.")
    st.markdown("---")
    st.markdown("#### 📤 Importar em Lote")
    arquivo = st.file_uploader("Selecione um arquivo CSV ou Excel", type=["csv", "xlsx"])
    if arquivo is not None:
        try:
            if arquivo.name.endswith('.csv'):
                df = pd.read_csv(arquivo)
            else:
                df = pd.read_excel(arquivo)
            st.dataframe(df)
            if st.button("📥 Importar Dados"):
                dados = []
                for _, row in df.iterrows():
                    chave_imp = str(row.get("chave", row.get("Chave", "")))
                    cat_imp = str(row.get("categoria", row.get("Categoria", "")))
                    est_imp = str(row.get("estacao", row.get("Estacao", "Verão")))
                    qtd_imp = int(row.get("quantidade", row.get("Quantidade", 0)))
                    if chave_imp and cat_imp:
                        dados.append((chave_imp, cat_imp, est_imp, qtd_imp))
                if dados:
                    if salvar_lote_no_banco(dados, st.session_state.get("usuario_atual", "sistema")):
                        st.success(f"✅ {len(dados)} itens importados com sucesso!")
                    else:
                        st.error(f"❌ Erro na importação: {st.session_state.get('ultimo_erro_bd', 'Erro desconhecido')}")
        except Exception as e:
            st.error(f"❌ Erro ao processar arquivo: {e}")

def tela_gerenciador():
    st.markdown('<h3 style="text-align: center; color: #ffcc00;">🛠️ Gerenciador (Admin)</h3>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #8892b0;">Funções críticas disponíveis apenas para o papel de Gerente</p>', unsafe_allow_html=True)
    if st.session_state.get("papel_atual") != "gerente":
        st.error("⛔ Acesso restrito a usuários com papel de Gerente.")
        return
    tab_ger1, tab_ger2, tab_ger3, tab_ger4 = st.tabs(["👥 Gestão de Logins", "📐 Editar Estrutura", "📊 Editar Capacidade", "🧾 Usuários Cadastrados"])
    with tab_ger1:
        st.markdown("#### 👥 Gestão de Logins")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("##### Criar Novo Usuário")
            novo_usuario = st.text_input("Usuário:")
            nova_senha = st.text_input("Senha:", type="password")
            novo_papel = st.selectbox("Papel:", ["operador", "gerente"])
            if st.button("➕ Criar Usuário"):
                if novo_usuario and nova_senha:
                    if criar_usuario(novo_usuario, nova_senha, novo_papel):
                        st.success(f"✅ Usuário {novo_usuario} criado com sucesso!")
                    else:
                        st.error(f"❌ Erro ao criar usuário: {st.session_state.get('ultimo_erro_bd', 'Erro desconhecido')}")
                else:
                    st.warning("⚠️ Preencha todos os campos.")
        with col2:
            st.markdown("##### Remover Usuário")
            usuarios = listar_usuarios()
            usuarios_disponiveis = [u for u, p in usuarios if u != "admin"]
            if usuarios_disponiveis:
                usuario_remover = st.selectbox("Selecione o usuário para remover:", usuarios_disponiveis)
                if st.button("🗑️ Remover Usuário", type="secondary"):
                    st.info("Função de remoção disponível apenas via banco de dados.")
            else:
                st.info("ℹ️ Nenhum outro usuário cadastrado.")
    with tab_ger2:
        st.markdown("#### 📐 Editar Estrutura Física das Ruas")
        st.caption("⚠️ Alterar a estrutura afeta QUANTOS casulos existem. Use com cuidado.")
        estrutura_atual = carregar_estrutura_do_banco()
        ruas_existentes = list(estrutura_atual.keys())
        rua_editar = st.selectbox("Selecione a Rua para editar:", ruas_existentes)
        if rua_editar:
            config_atual = estrutura_atual.get(rua_editar, {})
            col1, col2 = st.columns(2)
            with col1:
                tipos_disponiveis = ["P", "M", "G", "Misto_Lado", "Misto_Lado_15", "G_Unilateral", "Especial_Rua_14", "Misto_Transicao", "Aramado_P_Seq_20", "Metal_Seq_21", "Morta", "Inexistente"]
                tipo_atual = config_atual.get("tipo", "P")
                try:
                    idx = tipos_disponiveis.index(tipo_atual)
                except ValueError:
                    idx = 0
                novo_tipo = st.selectbox("Tipo da Rua:", tipos_disponiveis, index=idx)
            with col2:
                if novo_tipo in ["P", "M", "G"]:
                    st.info(f"Tipo {novo_tipo}: usa níveis padrão.")
                elif novo_tipo == "Misto_Lado":
                    st.info("Misto por lado: Par=G, Ímpar=P")
                elif novo_tipo == "Misto_Lado_15":
                    st.info("Misto por lado (Rua 15): Par=M, Ímpar=G")
                elif novo_tipo in ["Morta", "Inexistente"]:
                    st.warning(f"Tipo {novo_tipo}: não possui casulos.")
            st.markdown("##### Colunas por Lado")
            col_impar_input = st.text_input("Colunas Ímpares (ex: 1-101,2 ou 1,3,5):", value=",".join(map(str, config_atual.get("cols_impar", []))), key="cols_impar_edit")
            col_par_input = st.text_input("Colunas Pares (ex: 2-102,2 ou 2,4,6):", value=",".join(map(str, config_atual.get("cols_par", []))), key="cols_par_edit")
            if "cols_seq" in config_atual:
                col_seq_input = st.text_input("Colunas Sequenciais (ex: 1-31 ou 42-48):", value=",".join(map(str, config_atual.get("cols_seq", []))), key="cols_seq_edit")
            else:
                col_seq_input = ""
            st.markdown("##### Metadados Extras")
            metal_input = st.text_input("Colunas com Metal (ex: 43 ou 101,102):", value=",".join(map(str, config_atual.get("metal", []))), key="metal_edit")
            metal_cols_input = st.text_input("Metal Columns (ex: 35,37,39):", value=",".join(map(str, config_atual.get("metal_cols", []))), key="metal_cols_edit")
            if st.button("💾 Salvar Estrutura", type="primary"):
                try:
                    cols_impar = parse_range_input(col_impar_input)
                    cols_par = parse_range_input(col_par_input)
                    cols_seq = parse_range_input(col_seq_input) if col_seq_input else []
                    metal = parse_range_input(metal_input) if metal_input else []
                    metal_cols = parse_range_input(metal_cols_input) if metal_cols_input else []
                    novo_config = {"tipo": novo_tipo}
                    if cols_impar:
                        novo_config["cols_impar"] = cols_impar
                    if cols_par:
                        novo_config["cols_par"] = cols_par
                    if cols_seq:
                        novo_config["cols_seq"] = cols_seq
                    if metal:
                        novo_config["metal"] = metal
                    if metal_cols:
                        novo_config["metal_cols"] = metal_cols
                    if salvar_estrutura_rua_no_banco(rua_editar, novo_config):
                        st.success(f"✅ Estrutura da {rua_editar} atualizada com sucesso!")
                        st.info("🔄 Recarregue a página para ver os efeitos.")
                    else:
                        st.error(f"❌ Erro ao salvar: {st.session_state.get('ultimo_erro_bd', 'Erro desconhecido')}")
                except Exception as e:
                    st.error(f"❌ Erro ao processar: {e}")
    with tab_ger3:
        st.markdown("#### 📊 Editar Capacidade dos Casulos")
        st.caption("⚠️ Alterar a capacidade afeta os cálculos de ocupação. Use com cuidado.")
        col1, col2, col3 = st.columns(3)
        with col1:
            estacoes = ["Verão", "Inverno", "Meia-Estação"]
            estacao_editar = st.selectbox("Estação:", estacoes)
        with col2:
            generos = ["Feminino", "Masculino"]
            genero_editar = st.selectbox("Gênero:", generos)
        with col3:
            tipos_casulo = ["P", "M", "G", "Metal Raso (GG)", "Madeira/Metal Prof. (3G)"]
            tipo_editar = st.selectbox("Tipo de Casulo:", tipos_casulo)
        tabela_verao, tabela_inverno = (CAPACIDADE_VERAO_FEMININO, CAPACIDADE_INVERNO_FEMININO) if genero_editar == "Feminino" else (CAPACIDADE_VERAO_MASCULINO, CAPACIDADE_INVERNO_MASCULINO)
        tabela_alvo = tabela_inverno if estacao_editar == "Inverno" else tabela_verao
        todas_categorias = set(tabela_alvo.keys())
        if todas_categorias:
            categoria_editar = st.selectbox("Categoria:", sorted(list(todas_categorias)))
            valor_atual = tabela_alvo.get(categoria_editar, {}).get(tipo_editar)
            if valor_atual:
                min_atual, max_atual = valor_atual
                st.info(f"Valor atual: {min_atual} a {max_atual} peças")
            else:
                st.warning("⚠️ Esta combinação não possui capacidade definida")
                min_atual, max_atual = 0, 0
            col1, col2 = st.columns(2)
            with col1:
                nova_min = st.number_input("Capacidade Mínima:", min_value=0, value=min_atual)
            with col2:
                nova_max = st.number_input("Capacidade Máxima:", min_value=0, value=max_atual)
            proibir = st.checkbox("🚫 Proibir esta combinação (deixar vazio)", value=(nova_min == 0 and nova_max == 0))
            if st.button("💾 Salvar Capacidade", type="primary"):
                try:
                    if proibir:
                        nova_min = None
                        nova_max = None
                    if salvar_capacidade_no_banco(categoria_editar, estacao_editar, tipo_editar, genero_editar, nova_min, nova_max):
                        st.success(f"✅ Capacidade atualizada: {categoria_editar} / {estacao_editar} / {tipo_editar}")
                        st.info("🔄 Recarregue a página para ver os efeitos.")
                    else:
                        st.error(f"❌ Erro ao salvar: {st.session_state.get('ultimo_erro_bd', 'Erro desconhecido')}")
                except Exception as e:
                    st.error(f"❌ Erro: {e}")
        else:
            st.info("ℹ️ Nenhuma categoria encontrada para esta combinação.")
    with tab_ger4:
        st.markdown("#### 🧾 Usuários Cadastrados")
        usuarios = listar_usuarios()
        if usuarios:
            df_usuarios = pd.DataFrame(usuarios, columns=["Usuário", "Papel"])
            st.dataframe(df_usuarios, hide_index=True, use_container_width=True)
        else:
            st.info("ℹ️ Nenhum usuário cadastrado.")

def main():
    if "logado" not in st.session_state:
        st.session_state.logado = False
    if "usuario_atual" not in st.session_state:
        st.session_state.usuario_atual = ""
    if "papel_atual" not in st.session_state:
        st.session_state.papel_atual = ""
    if "aba_ativa_selecionada" not in st.session_state:
        st.session_state.aba_ativa_selecionada = "🏠 Inicial"
    if "ultimo_erro_bd" not in st.session_state:
        st.session_state.ultimo_erro_bd = ""
    if not st.session_state.logado:
        st.markdown('<h1 class="title-main">🔐 Login</h1>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("login_form"):
                usuario = st.text_input("Usuário:")
                senha = st.text_input("Senha:", type="password")
                submit = st.form_submit_button("Entrar")
                if submit:
                    papel = autenticar_usuario(usuario, senha)
                    if papel:
                        st.session_state.logado = True
                        st.session_state.usuario_atual = usuario
                        st.session_state.papel_atual = papel
                        st.rerun()
                    else:
                        st.error("❌ Usuário ou senha inválidos.")
        return
    with st.sidebar:
        st.markdown("### 📦 OutLog - DISTRIBOX")
        st.markdown(f"👤 **{st.session_state.usuario_atual}** ({st.session_state.papel_atual})")
        st.markdown("---")
        opcoes_menu = ["🏠 Inicial", "🔍 Visualizador", "⚡ Consulta Rápida", "📊 Estatísticas", "📝 Entrada de Dados"]
        if st.session_state.papel_atual == "gerente":
            opcoes_menu.append("🛠️ Gerenciador (Admin)")
        for opcao in opcoes_menu:
            if st.button(opcao, use_container_width=True):
                st.session_state.aba_ativa_selecionada = opcao
                st.rerun()
        st.markdown("---")
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.logado = False
            st.session_state.usuario_atual = ""
            st.session_state.papel_atual = ""
            st.rerun()
        st.markdown("---")
        st.caption("🔧 Versão 2.0 - Supabase")
    aba = st.session_state.aba_ativa_selecionada
    if aba == "🏠 Inicial":
        tela_inicial()
    elif aba == "🔍 Visualizador":
        tela_visualizador()
    elif aba == "⚡ Consulta Rápida":
        tela_consulta_rapida()
    elif aba == "📊 Estatísticas":
        tela_estatisticas()
    elif aba == "📝 Entrada de Dados":
        tela_entrada_dados()
    elif aba == "🛠️ Gerenciador (Admin)":
        tela_gerenciador()

if __name__ == "__main__":
    main()
