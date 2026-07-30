import streamlit as st
import pandas as pd
import numpy as np
import re

# 1. CONFIGURAÇÃO DE PÁGINA
st.set_page_config(
    page_title="Stock Control - Sistema de Gestão por Peças",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# BLOCO 1: CAMADA DE DADOS E ESTADO DO SISTEMA
# ==========================================

ESTRUTURA_CD = {
    "Rua 01": {"tipo": "Morta", "cols_impar": [], "cols_par": []},
    "Rua 02": {"tipo": "Misto_Transicao", "cols_impar": list(range(21, 94, 2)), "cols_par": list(range(22, 103, 2)) + list(range(103, 141))},
    "Rua 03": {"tipo": "P", "cols_impar": list(range(1, 101, 2)), "cols_par": list(range(2, 102, 2))},
    "Rua 04": {"tipo": "Misto_Lado", "cols_impar": list(range(1, 101, 2)), "cols_par": list(range(2, 102, 2))},
    "Rua 05": {"tipo": "M", "cols_impar": list(range(21, 101, 2)), "cols_par": list(range(22, 103, 2))},
    "Rua 06": {"tipo": "M", "cols_impar": list(range(1, 82, 2)), "cols_par": list(range(2, 83, 2))},
    "Rua 07": {"tipo": "M", "cols_impar": list(range(59, 140, 2)), "cols_par": list(range(60, 141, 2))},
    "Rua 08": {"tipo": "M", "cols_impar": list(range(1, 82, 2)), "cols_par": list(range(2, 83, 2))},
    "Rua 09": {"tipo": "M", "cols_impar": list(range(21, 104, 2)), "cols_par": list(range(22, 101, 2))},
    "Rua 10": {"tipo": "G", "cols_impar": list(range(21, 104, 2)), "cols_par": list(range(22, 103, 2))},
    "Rua 11": {"tipo": "G_Unilateral", "cols_impar": [], "cols_par": list(range(22, 95, 2))},
    "Rua 12": {"tipo": "Inexistente", "cols_impar": [], "cols_par": []},
    "Rua 13": {"tipo": "Inexistente", "cols_impar": [], "cols_par": []},
    "Rua 14": {"tipo": "Especial_Rua_14", "cols_impar": [], "cols_par": [], "cols_seq": list(range(1, 32)) + list(range(42, 49))},
    "Rua 15": {"tipo": "Misto_Lado_15", "cols_impar": list(range(1, 88, 2)), "cols_par": list(range(2, 139, 2))},
    "Rua 16": {"tipo": "G", "metal": [43], "cols_impar": list(range(1, 101, 2)), "cols_par": list(range(2, 102, 2))},
    "Rua 17": {"tipo": "G", "metal": [101, 102, 103, 104, 105, 106], "cols_impar": list(range(1, 115, 2)), "cols_par": list(range(2, 116, 2))},
    "Rua 18": {"tipo": "M", "metal": [35, 36, 37, 38, 39, 40], "cols_impar": list(range(1, 81, 2)), "cols_par": list(range(2, 82, 2))},
    "Rua 19": {"tipo": "P", "metal": [101, 102, 103, 104, 105, 106], "cols_impar": list(range(1, 115, 2)), "cols_par": list(range(2, 116, 2))},
    "Rua 20": {"tipo": "Aramado_P_Seq_20", "metal_cols": [35, 37, 39], "cols_impar": [], "cols_par": [], "cols_seq": list(range(35, 138, 2))},
    "Rua 21": {"tipo": "Metal_Seq_21", "cols_impar": [], "cols_par": [], "cols_seq": list(range(1, 78, 2))}
}

# Mapeamento de gênero por rua, conforme sua apresentação (slides "Estoque
# Feminino" e "Estoque Masculino"). Usado para escolher a tabela de
# capacidade correta.
RUA_GENERO = {
    "Rua 02": "Feminino", "Rua 03": "Feminino", "Rua 04": "Feminino",
    "Rua 05": "Feminino", "Rua 06": "Feminino", "Rua 07": "Feminino",
    "Rua 08": "Feminino", "Rua 09": "Feminino", "Rua 10": "Feminino",
    "Rua 11": "Feminino", "Rua 14": "Feminino",
    "Rua 15": "Masculino", "Rua 16": "Masculino", "Rua 17": "Masculino",
    "Rua 18": "Masculino", "Rua 19": "Masculino", "Rua 20": "Masculino",
    "Rua 21": "Masculino",
}

def obter_genero_rua(rua_nome):
    return RUA_GENERO.get(rua_nome, "Feminino")

NIVEIS_G = ["B", "E", "H", "K", "N", "Q", "T"]
NIVEIS_M = ["B", "D", "E", "G", "H", "J", "K", "M", "N", "P", "Q", "S", "T", "V"]
NIVEIS_P = ["B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V"]
NIVEIS_METAL_5 = ["B", "C", "D", "E", "F"]

# ==========================================
# MOTOR DE CAPACIDADE — TABELA EMPÍRICA REAL
# (extraída da apresentação "Capacidade e Controle de Estoque")
# ==========================================
# Cada célula é uma faixa (mínimo, máximo) de peças por casulo. O sistema usa
# sempre o MÍNIMO da faixa (decisão tomada com você: mais conservador).
# None = combinação proibida (ex: jaqueta pesada em aramado).

CAPACIDADE_VERAO_FEMININO = {
    "Regatas/Bodys/Tops/Croppeds":              {"P": (8, 10),  "M": (16, 20), "G": (35, 40), "Metal Raso (GG)": (80, 100),  "Madeira/Metal Prof. (3G)": (180, 220)},
    "Camisetas/Camisas M.Curta Finas":          {"P": (7, 8),   "M": (14, 16), "G": (28, 32), "Metal Raso (GG)": (60, 70),   "Madeira/Metal Prof. (3G)": (130, 160)},
    "Shorts Finos/Bermudas Verão/Saia":         {"P": (5, 6),   "M": (10, 12), "G": (20, 24), "Metal Raso (GG)": (45, 55),   "Madeira/Metal Prof. (3G)": (100, 120)},
    "Calças Leves (Sarja Fina, Viscose, Linho)":{"P": (3, 4),   "M": (7, 8),   "G": (14, 16), "Metal Raso (GG)": (30, 35),   "Madeira/Metal Prof. (3G)": (65, 80)},
    "Conjuntos Leves/Macaquinhos":              {"P": (3, 4),   "M": (6, 8),   "G": (12, 15), "Metal Raso (GG)": (25, 30),   "Madeira/Metal Prof. (3G)": (55, 70)},
    "Macacões/Vestidos Curtos":                 {"P": (2, 3),   "M": (5, 6),   "G": (10, 12), "Metal Raso (GG)": (20, 25),   "Madeira/Metal Prof. (3G)": (45, 55)},
    "Vestidos Longos":                          {"P": (1, 2),   "M": (3, 4),   "G": (7, 8),   "Metal Raso (GG)": (15, 18),   "Madeira/Metal Prof. (3G)": (30, 40)},
}

CAPACIDADE_INVERNO_FEMININO = {
    "Camisetas M.Longa/Cacharrel Fina":     {"P": (5, 6), "M": (10, 12), "G": (20, 24), "Metal Raso (GG)": (40, 50), "Madeira/Metal Prof. (3G)": (90, 110)},
    "Tricots Leves/Blusões Finos":          {"P": (3, 4), "M": (6, 8),   "G": (12, 15), "Metal Raso (GG)": (25, 30), "Madeira/Metal Prof. (3G)": (55, 70)},
    "Calças Jeans/Moletons/Corduroy":       {"P": (2, 3), "M": (4, 5),   "G": (8, 10),  "Metal Raso (GG)": (20, 25), "Madeira/Metal Prof. (3G)": (45, 55)},
    "Jaquetas Leves/Corta-Vento/Blazers":   {"P": (1, 2), "M": (3, 4),   "G": (6, 8),   "Metal Raso (GG)": (15, 18), "Madeira/Metal Prof. (3G)": (30, 40)},
    "Jaquetas Pesadas/Casacos/Parkas":      {"P": None,   "M": None,     "G": None,     "Metal Raso (GG)": (8, 12),  "Madeira/Metal Prof. (3G)": (20, 30)},
}

# ⚠️ PLACEHOLDER: ainda não recebi a tabela real de capacidade do estoque
# MASCULINO. Até você me passar os números, as ruas masculinas usam a
# tabela feminina como estimativa provisória (a UI avisa isso claramente).
CAPACIDADE_VERAO_MASCULINO = CAPACIDADE_VERAO_FEMININO
CAPACIDADE_INVERNO_MASCULINO = CAPACIDADE_INVERNO_FEMININO

ESTACOES_PECA = ["Verão", "Inverno", "Meia-Estação"]

def obter_tabelas_genero(genero):
    if genero == "Masculino":
        return CAPACIDADE_VERAO_MASCULINO, CAPACIDADE_INVERNO_MASCULINO
    return CAPACIDADE_VERAO_FEMININO, CAPACIDADE_INVERNO_FEMININO

# Meia-Estação não teve tabela própria na apresentação — reaproveita a de
# Verão (feminina ou masculina, conforme a rua) até você me passar uma
# tabela específica.
CATEGORIAS_POR_ESTACAO_FEMININO = {
    "Verão": list(CAPACIDADE_VERAO_FEMININO.keys()),
    "Meia-Estação": list(CAPACIDADE_VERAO_FEMININO.keys()),
    "Inverno": list(CAPACIDADE_INVERNO_FEMININO.keys()),
}
CATEGORIAS_POR_ESTACAO_MASCULINO = {
    "Verão": list(CAPACIDADE_VERAO_MASCULINO.keys()),
    "Meia-Estação": list(CAPACIDADE_VERAO_MASCULINO.keys()),
    "Inverno": list(CAPACIDADE_INVERNO_MASCULINO.keys()),
}

def obter_categorias_por_estacao(genero):
    return CATEGORIAS_POR_ESTACAO_MASCULINO if genero == "Masculino" else CATEGORIAS_POR_ESTACAO_FEMININO

# Tipo estrutural do casulo (retornado por obter_especificacao_casulo) mapeado
# para a categoria de casulo usada nas tabelas acima.
CATEGORIA_CASULO_POR_TIPO_ESTRUTURAL = {
    "aramado_P": "P",
    "aramado_M": "M",
    "aramado_G": "G",
    "metal_raso": "Metal Raso (GG)",
    "metal_profundo": "Madeira/Metal Prof. (3G)",
    "madeira": "Madeira/Metal Prof. (3G)",
}

# Categoria usada só como referência para mostrar um número de capacidade no
# Visualizador (existe nas duas tabelas, com número real em todos os 5 tipos
# de casulo). A % de ocupação real do nicho sempre vem do mix de fato guardado.
CATEGORIA_REFERENCIA_DISPLAY = "Camisetas/Camisas M.Curta Finas"

# ==========================================
# ATUALIZAÇÃO — Documento "Diretrizes e Parâmetros Operacionais" (Verão)
# ==========================================
# Travas rígidas de ergonomia — valem em qualquer rua, sobrepõem a tabela de
# categoria quando o resultado dela for maior que a trava.
TRAVA_MAXIMA_P = 6              # "6 a 7 peças" -> uso o mínimo, mais conservador
TRAVA_MAXIMA_M_VESTIDOS = 4     # vestidos em casulo M

# Densidade FIXA por rua x tipo estrutural — fonte de verdade mais recente
# para as ruas MASCULINAS (15 a 21). Casulos GG e "Caixote" ficam de fora por
# enquanto (aguardando mapeamento físico exato). Onde não há densidade fixa
# aqui (feminino, e os tipos GG/madeira ainda não cobertos), o sistema cai
# para a tabela por categoria.
CAPACIDADE_FIXA_POR_RUA = {
    "Rua 15": {"aramado_M": 7, "aramado_G": 12},
    "Rua 16": {"aramado_G": 10},
    "Rua 17": {"aramado_G": 12},
    "Rua 18": {"aramado_M": 12},
    "Rua 19": {"aramado_P": 6},
    "Rua 20": {"aramado_P": 6},
    "Rua 21": {"metal_raso": 40},
}

def obter_chave_casulo(rua_nome, lado, coluna, nivel):
    try:
        col_int = int(coluna)
    except:
        col_int = 1
    return f"{rua_nome}|{lado}|{col_int:03d}|{str(nivel).upper()}"

def obter_chave_estoque(categoria_peca, estacao):
    return f"{categoria_peca}|{estacao}"

def obter_especificacao_casulo(rua_nome, coluna, lado="impar"):
    """
    Retorna a especificação física de uma coluna/lado de uma rua: níveis
    válidos, tipo estrutural (aramado_P/aramado_M/aramado_G/madeira/
    metal_profundo/metal_raso) e descrição.
    """
    try:
        col = int(coluna)
    except (ValueError, TypeError):
        col = 1

    config = ESTRUTURA_CD.get(rua_nome, {})
    tipo = config.get("tipo", "")
    vazio = {"niveis": [], "tipo_estrutural": None, "tipo_desc": "Inexistente"}

    if tipo == "Inexistente":
        return vazio

    is_metal = False
    if "metal" in config and col in config["metal"]:
        is_metal = True
    if "metal_cols" in config and col in config["metal_cols"]:
        is_metal = True

    if is_metal:
        return {"niveis": NIVEIS_METAL_5, "tipo_estrutural": "metal_raso", "tipo_desc": "Metal Infiltrado"}

    if tipo in ("Aramado_P_Seq_20", "P"):
        return {"niveis": NIVEIS_P, "tipo_estrutural": "aramado_P", "tipo_desc": "Pequeno (P)"}
    elif tipo == "G":
        return {"niveis": NIVEIS_G, "tipo_estrutural": "aramado_G", "tipo_desc": "Grande (G)"}
    elif tipo == "M":
        return {"niveis": NIVEIS_M, "tipo_estrutural": "aramado_M", "tipo_desc": "Médio (M)"}
    elif tipo == "G_Unilateral":
        if lado == "par":
            return {"niveis": NIVEIS_G, "tipo_estrutural": "aramado_G", "tipo_desc": "Grande (G) - Unilateral"}
        else:
            return vazio
    elif tipo == "Metal_Seq_21":
        return {"niveis": NIVEIS_METAL_5, "tipo_estrutural": "metal_raso", "tipo_desc": "Metal Sequencial Rua 21"}
    elif tipo == "Especial_Rua_14":
        if 1 <= col <= 23:
            return {"niveis": ["D", "G", "J", "M", "P"], "tipo_estrutural": "madeira", "tipo_desc": "Rua 14 - Madeira Gigante"}
        elif 24 <= col <= 31:
            return {"niveis": NIVEIS_METAL_5, "tipo_estrutural": "metal_profundo", "tipo_desc": "Rua 14 - Metal Profundo"}
        elif 42 <= col <= 48:
            return {"niveis": NIVEIS_METAL_5, "tipo_estrutural": "metal_raso", "tipo_desc": "Rua 14 - Metal Raso"}
        else:
            return vazio
    elif tipo == "Misto_Transicao":
        if col < 103:
            return {"niveis": NIVEIS_P, "tipo_estrutural": "aramado_P", "tipo_desc": "Pequeno (P)"}
        else:
            return {"niveis": NIVEIS_G, "tipo_estrutural": "aramado_G", "tipo_desc": "Grande (G)"}
    elif tipo == "Misto_Lado":
        if lado == "par":
            return {"niveis": NIVEIS_G, "tipo_estrutural": "aramado_G", "tipo_desc": "Grande (G)"}
        else:
            return {"niveis": NIVEIS_P, "tipo_estrutural": "aramado_P", "tipo_desc": "Pequeno (P)"}
    elif tipo == "Misto_Lado_15":
        if lado == "par":
            return {"niveis": NIVEIS_M, "tipo_estrutural": "aramado_M", "tipo_desc": "Médio (M)"}
        else:
            return {"niveis": NIVEIS_G, "tipo_estrutural": "aramado_G", "tipo_desc": "Grande (G)"}

    return {"niveis": NIVEIS_P, "tipo_estrutural": "aramado_P", "tipo_desc": "Padrão"}

def obter_faixa_categoria(categoria_peca, tipo_estrutural, estacao, rua_nome):
    """Faixa (mín,máx) pura da tabela por categoria — usada só para checar a
    regra de PERMISSÃO (ex: Jaquetas Pesadas = None = proibido em P/M/G),
    independente de haver densidade fixa por rua."""
    genero = obter_genero_rua(rua_nome)
    tabela_verao, tabela_inverno = obter_tabelas_genero(genero)
    tabela = tabela_inverno if estacao == "Inverno" else tabela_verao
    categoria_casulo = CATEGORIA_CASULO_POR_TIPO_ESTRUTURAL.get(tipo_estrutural, "P")
    return tabela.get(categoria_peca, {}).get(categoria_casulo)

def peca_permitida(categoria_peca, tipo_estrutural, estacao, rua_nome):
    return obter_faixa_categoria(categoria_peca, tipo_estrutural, estacao, rua_nome) is not None

def obter_faixa_capacidade(categoria_peca, tipo_estrutural, estacao, rua_nome):
    """Faixa exibida na tela: densidade fixa da rua quando existir, senão a
    faixa da tabela por categoria."""
    fixa = CAPACIDADE_FIXA_POR_RUA.get(rua_nome, {}).get(tipo_estrutural)
    if fixa is not None:
        return (fixa, fixa)
    return obter_faixa_categoria(categoria_peca, tipo_estrutural, estacao, rua_nome)

def obter_capacidade_minima(categoria_peca, tipo_estrutural, estacao, rua_nome):
    # A proibição (ex: Jaquetas Pesadas em aramado) vale sempre, mesmo em
    # ruas com densidade fixa.
    if not peca_permitida(categoria_peca, tipo_estrutural, estacao, rua_nome):
        return 0

    fixa = CAPACIDADE_FIXA_POR_RUA.get(rua_nome, {}).get(tipo_estrutural)
    if fixa is not None:
        return fixa

    faixa = obter_faixa_categoria(categoria_peca, tipo_estrutural, estacao, rua_nome)
    valor = faixa[0] if faixa else 0
    if valor and tipo_estrutural == "aramado_P":
        valor = min(valor, TRAVA_MAXIMA_P)
    if valor and tipo_estrutural == "aramado_M" and "Vestido" in categoria_peca:
        valor = min(valor, TRAVA_MAXIMA_M_VESTIDOS)
    return valor

def obter_capacidade_estimada_exibicao(tipo_estrutural, rua_nome):
    fixa = CAPACIDADE_FIXA_POR_RUA.get(rua_nome, {}).get(tipo_estrutural)
    if fixa is not None:
        return fixa
    return obter_capacidade_minima(CATEGORIA_REFERENCIA_DISPLAY, tipo_estrutural, "Verão", rua_nome)

def calcular_pecas_totais(dados_casulo):
    return sum(dados_casulo.values()) if dados_casulo else 0

def calcular_fracao_ocupada(dados_casulo, tipo_estrutural, rua_nome):
    """
    % de ocupação real do casulo, considerando o mix de categorias/estações
    guardado nele. Cada combinação consome capacidade proporcional ao seu
    próprio mínimo de faixa (fração = qtd / capacidade_mínima daquela peça).
    """
    if not dados_casulo:
        return 0.0
    fracao = 0.0
    for chave_combo, qtd in dados_casulo.items():
        categoria_peca, estacao = chave_combo.split("|", 1)
        cap_min = obter_capacidade_minima(categoria_peca, tipo_estrutural, estacao, rua_nome)
        if cap_min > 0:
            fracao += qtd / cap_min
    return fracao

def montar_html_nicho(rua_selecionada, col_num, nivel, spec, chave_lado):
    if nivel not in spec["niveis"]:
        return "<div class='nicho' style='background: transparent;'>-</div>"

    chave = obter_chave_casulo(rua_selecionada, chave_lado, col_num, nivel)
    dados_casulo = st.session_state.base_dados_cd.get(chave, {})
    pecas_atuais = calcular_pecas_totais(dados_casulo)
    capacidade_estimada = obter_capacidade_estimada_exibicao(spec["tipo_estrutural"], rua_selecionada)
    pct_ocupacao = calcular_fracao_ocupada(dados_casulo, spec["tipo_estrutural"], rua_selecionada) * 100

    status = "livre"
    if pct_ocupacao >= 100: status = "saturado"
    elif pct_ocupacao >= 81: status = "saturado"
    elif pct_ocupacao >= 50: status = "atencao"

    is_destaque = (st.session_state.busca_destaque and st.session_state.busca_destaque['rua'] == rua_selecionada and st.session_state.busca_destaque['nivel'] == nivel and st.session_state.busca_destaque['col'] == col_num)
    classe_destaque = "destaque-ativo" if is_destaque else ""

    return f"<div class='nicho {status} {classe_destaque}' title='{col_num:03d}-{nivel} | {pecas_atuais}/{capacidade_estimada} peças ({pct_ocupacao:.1f}% da capacidade)'>{pecas_atuais}/{capacidade_estimada}</div>"

def renderizar_cabecalho_colunas(lista_colunas):
    grid_header = st.columns(len(lista_colunas) + 1)
    with grid_header[0]:
        st.markdown("<div style='font-size:10px;'>&nbsp;</div>", unsafe_allow_html=True)
    for idx, col_num in enumerate(lista_colunas):
        with grid_header[idx + 1]:
            st.markdown(f"<div style='text-align:center; font-weight:bold; color:#ffcc00; font-size:10px;'>{col_num:03d}</div>", unsafe_allow_html=True)

# Inicialização do Estado
if 'base_dados_cd' not in st.session_state:
    st.session_state.base_dados_cd = {}
    for r_nome, r_cfg in ESTRUTURA_CD.items():
        if r_cfg.get("tipo") == "Inexistente":
            continue
        lista_lados = [("impar", r_cfg.get("cols_impar", [])), ("par", r_cfg.get("cols_par", []))]
        if "cols_seq" in r_cfg:
            lista_lados = [("seq", r_cfg["cols_seq"])]

        for lado, cols in lista_lados:
            for c in cols:
                l_param = "par" if r_nome == "Rua 11" else ("impar" if lado == "seq" else lado)
                spec = obter_especificacao_casulo(r_nome, c, l_param)
                for n in spec["niveis"]:
                    chave_casulo = obter_chave_casulo(r_nome, lado, c, n)
                    st.session_state.base_dados_cd[chave_casulo] = {}

if 'busca_destaque' not in st.session_state:
    st.session_state.busca_destaque = None
if 'aba_ativa_selecionada' not in st.session_state:
    st.session_state.aba_ativa_selecionada = "🏠 Tela Inicial (Geral)"

USUARIOS_PADRAO = {
    "admin": {"senha": "admin123", "papel": "gerente"}
}
if 'usuarios_cadastrados' not in st.session_state:
    st.session_state.usuarios_cadastrados = dict(USUARIOS_PADRAO)
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
if 'usuario_atual' not in st.session_state:
    st.session_state.usuario_atual = None
if 'papel_atual' not in st.session_state:
    st.session_state.papel_atual = None


# ==========================================
# BLOCO 2: INTERFACE VISUAL (FRONT-END & ESTILOS)
# ==========================================

st.markdown("""
<style>
    .stApp {
        background-color: #0b0c10;
        color: #c5c6c7;
        text-align: center;
    }
    .logo-container {
        text-align: center;
        padding: 15px 0;
        margin-bottom: 5px;
    }
    .logo-icone {
        font-size: 55px;
        margin-bottom: -10px;
        filter: drop-shadow(0 0 10px rgba(255, 204, 0, 0.6));
    }
    .logo-texto {
        font-family: 'Trebuchet MS', sans-serif;
        font-size: 40px;
        font-weight: 900;
        letter-spacing: 2px;
        color: #ffcc00;
        text-shadow: 0 0 10px rgba(255, 204, 0, 0.4);
        margin: 0;
    }
    .logo-sub {
        font-size: 12px;
        color: #8892b0;
        letter-spacing: 5px;
        text-transform: uppercase;
        margin-top: -5px;
    }
    .card-dashboard {
        background: linear-gradient(135deg, #1f2833 0%, #0b0c10 100%);
        border: 1px solid #ffcc00;
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 4px 20px rgba(255, 204, 0, 0.1);
    }
    .card-dashboard h5 {
        margin: 0;
        color: #8892b0;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .card-dashboard h2 {
        margin: 10px 0 0 0;
        color: #ffcc00;
        font-size: 26px;
        font-weight: bold;
    }
    .planta-rua-bloco {
        background: #1f2833;
        border: 1px solid #283845;
        border-radius: 8px;
        padding: 12px;
        text-align: center;
        margin-bottom: 10px;
    }
    .bar-container {
        width: 100%;
        background-color: #0b0c10;
        border-radius: 6px;
        height: 10px;
        margin-top: 5px;
        overflow: hidden;
        border: 1px solid #283845;
    }
    .bar-fill {
        height: 100%;
        border-radius: 6px;
    }
    .cor-verde { background-color: #45a29e; }
    .cor-amarelo { background-color: #ffcc00; }
    .cor-laranja { background-color: #f39c12; }
    .cor-vermelho { background-color: #e74c3c; }
    .topicos-legenda {
        background: #1f2833;
        border: 1px solid #283845;
        border-radius: 8px;
        padding: 12px 20px;
        margin: 0 auto 20px auto;
        max-width: 800px;
        text-align: left;
        font-size: 13px;
    }
    .topicos-legenda ul {
        margin: 0;
        padding-left: 20px;
        color: #c5c6c7;
    }
    .topicos-legenda li {
        margin-bottom: 4px;
        text-align: left;
    }
    .lado-container {
        background: #11161d;
        border: 1px solid #283845;
        border-radius: 8px;
        padding: 10px;
        text-align: center;
        margin-bottom: 15px;
    }
    .lado-titulo {
        font-size: 13px;
        font-weight: bold;
        color: #ffcc00;
        text-align: center;
        margin-bottom: 8px;
        border-bottom: 1px solid #283845;
        padding-bottom: 4px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .nicho {
        width: 44px;
        height: 28px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 9px;
        font-weight: bold;
        border-radius: 4px;
        color: #0b0c10;
        margin: 1.5px auto;
        text-align: center;
    }
    .livre { background-color: #45a29e; color: #fff; }
    .atencao { background-color: #ffcc00; }
    .saturado { background-color: #e74c3c; color: #fff; }
    .destaque-ativo { 
        border: 2px solid #ffffff !important; 
        transform: scale(1.15); 
        box-shadow: 0 0 12px #ffcc00; 
        z-index: 10; 
        background-color: #ffcc00 !important;
        color: #0b0c10 !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# BLOCO 1.5: PORTAL DE AUTENTICAÇÃO (LOGIN)
# ==========================================
if not st.session_state.autenticado:
    st.markdown("""
    <div class="logo-container">
        <div class="logo-icone">⚠️📦</div>
        <h1 class="logo-texto">STOCK CONTROL</h1>
        <div class="logo-sub">Gestão por Peças por Casulo</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<h3 style='text-align:center; color:#ffcc00;'>🔐 Acesso ao Sistema</h3>", unsafe_allow_html=True)

    col_login_esq, col_login_meio, col_login_dir = st.columns([1, 1.2, 1])
    with col_login_meio:
        with st.form("form_login"):
            usuario_input = st.text_input("Usuário")
            senha_input = st.text_input("Senha", type="password")
            submit_login = st.form_submit_button("Entrar", type="primary", use_container_width=True)

        if submit_login:
            dados_usuario = st.session_state.usuarios_cadastrados.get(usuario_input)
            if dados_usuario and dados_usuario["senha"] == senha_input:
                st.session_state.autenticado = True
                st.session_state.usuario_atual = usuario_input
                st.session_state.papel_atual = dados_usuario["papel"]
                st.rerun()
            else:
                st.error("⚠️ Usuário ou senha inválidos.")

        st.markdown("<p style='text-align:center; color:#8892b0; font-size:11px; margin-top:10px;'>Acesso padrão inicial: <b>admin</b> / <b>admin123</b><br>(crie os logins da equipe e troque essa senha na aba Gerenciador)</p>", unsafe_allow_html=True)

    st.stop()

# SIDEBAR: NAVEGAÇÃO
st.sidebar.markdown("<h2 style='color: #ffcc00; text-align: center;'>⚙️ NAVEGAÇÃO</h2>", unsafe_allow_html=True)

opcoes_telas = [
    "🏠 Tela Inicial (Geral)", 
    "📦 Visualizador de Casulos", 
    "🔍 Consulta Rápida de Casulos", 
    "📥 Entrada de Dados / Abastecimento"
]
if st.session_state.papel_atual == "gerente":
    opcoes_telas.append("🛠️ Gerenciador (Admin)")

if st.session_state.aba_ativa_selecionada not in opcoes_telas:
    st.session_state.aba_ativa_selecionada = "🏠 Tela Inicial (Geral)"

st.session_state.aba_ativa_selecionada = st.sidebar.radio("Selecione a Tela:", opcoes_telas, index=opcoes_telas.index(st.session_state.aba_ativa_selecionada))

st.sidebar.markdown(f"<p style='text-align:center; color:#8892b0; font-size:12px;'>👤 <b>{st.session_state.usuario_atual}</b> ({st.session_state.papel_atual.capitalize()})</p>", unsafe_allow_html=True)
if st.sidebar.button("🚪 Sair"):
    st.session_state.autenticado = False
    st.session_state.usuario_atual = None
    st.session_state.papel_atual = None
    st.rerun()

# PESQUISA GLOBAL
st.sidebar.markdown("---")
st.sidebar.markdown("<h4 style='color: #ffcc00;'>🔎 Localizador Global</h4>", unsafe_allow_html=True)
busca_input = st.sidebar.text_input("Digite o endereço:", placeholder="003-B-009...")

if st.sidebar.button("Destacar no Sistema"):
    tokens = re.findall(r'[A-Za-z0-9]+', busca_input)
    if len(tokens) >= 3:
        num_rua = int(tokens[0])
        rua_alvo = f"Rua {num_rua:02d}"
        col_buscada = int(tokens[2])
        nivel_buscado = tokens[1].upper()
        
        if rua_alvo in ESTRUTURA_CD:
            cfg = ESTRUTURA_CD[rua_alvo]
            if cfg.get("tipo") == "Inexistente":
                st.sidebar.error(f"⚠️ A {rua_alvo} é inexistente!")
            else:
                todos_da_rua = cfg.get("cols_impar", []) + cfg.get("cols_par", []) + cfg.get("cols_seq", [])
                if todos_da_rua and col_buscada not in todos_da_rua:
                    st.sidebar.error(f"⚠️ Coluna {col_buscada:03d} não existe na {rua_alvo}!")
                else:
                    st.session_state.busca_destaque = {
                        'rua': rua_alvo,
                        'nivel': nivel_buscado,
                        'col': col_buscada
                    }
                    st.session_state.aba_ativa_selecionada = "📦 Visualizador de Casulos"
                    st.sidebar.success(f"Casulo localizado!")
                    st.rerun()
        else:
            st.sidebar.error("Rua não encontrada!")
    else:
        st.sidebar.error("Formato inválido! Use ex: 003-B-009")

# BRANDING DO APP
st.markdown("""
<div class="logo-container">
    <div class="logo-icone">⚠️📦</div>
    <h1 class="logo-texto">STOCK CONTROL</h1>
    <div class="logo-sub">Gestão por Peças por Casulo</div>
</div>
""", unsafe_allow_html=True)


# ==========================================
# TELA 1: TELA INICIAL (PAINEL GERAL)
# ==========================================
if st.session_state.aba_ativa_selecionada == "🏠 Tela Inicial (Geral)":
    st.markdown("<h3 style='text-align: center; color: #ffcc00;'>📊 Painel Geral de Ocupação</h3>", unsafe_allow_html=True)

    soma_fracoes_geral = 0.0
    total_pecas_atuais = 0
    casulos_livres = 0
    total_casulos = len(st.session_state.base_dados_cd)

    for chave, dados_casulo in st.session_state.base_dados_cd.items():
        r_nome, lado, c_str, n = chave.split("|")
        l_param = "par" if r_nome == "Rua 11" else ("impar" if lado == "seq" else lado)
        spec = obter_especificacao_casulo(r_nome, int(c_str), l_param)
        pecas_casulo = calcular_pecas_totais(dados_casulo)
        soma_fracoes_geral += calcular_fracao_ocupada(dados_casulo, spec["tipo_estrutural"], r_nome)
        total_pecas_atuais += pecas_casulo
        if pecas_casulo == 0:
            casulos_livres += 1

    pct_geral = (soma_fracoes_geral / total_casulos * 100) if total_casulos > 0 else 0.0

    kcol1, kcol2, kcol3, kcol4 = st.columns(4)
    with kcol1: st.markdown(f"<div class='card-dashboard'><h5>Total Casulos</h5><h2>{total_casulos:,}</h2></div>", unsafe_allow_html=True)
    with kcol2: st.markdown(f"<div class='card-dashboard'><h5>Ocupação Média</h5><h2>{pct_geral:.1f}%</h2></div>", unsafe_allow_html=True)
    with kcol3: st.markdown(f"<div class='card-dashboard'><h5>Casulos Zerados</h5><h2>{casulos_livres:,}</h2></div>", unsafe_allow_html=True)
    with kcol4: st.markdown(f"<div class='card-dashboard'><h5>Peças Armazenadas</h5><h2>{total_pecas_atuais:,} un</h2></div>", unsafe_allow_html=True)

    st.write("---")
    st.markdown("<h4 style='text-align: center; color: #ffcc00;'>🗺️ Mapa de Calor por Rua</h4>", unsafe_allow_html=True)

    def obter_classe_cor(pct):
        if pct == 0: return "cor-verde"
        elif pct < 50: return "cor-verde"
        elif pct <= 80: return "cor-amarelo"
        elif pct < 100: return "cor-laranja"
        else: return "cor-vermelho"

    ruas_nomes = list(ESTRUTURA_CD.keys())
    bloco_cols = st.columns(3)
    dados_ranking = []

    for idx, rua in enumerate(ruas_nomes):
        col_alvo = bloco_cols[idx % 3]
        cfg_rua = ESTRUTURA_CD[rua]

        if cfg_rua.get("tipo") == "Inexistente":
            with col_alvo:
                st.markdown(f"""
                <div class="planta-rua-bloco" style="border-color: #333;">
                    <div style="font-weight: bold; font-size: 15px; color: #555;">{rua}</div>
                    <div style="font-size: 11px; margin-top: 4px; color: #e74c3c; text-transform: uppercase; letter-spacing: 1px;">Inexistente</div>
                </div>
                """, unsafe_allow_html=True)
            continue

        soma_fracoes_rua = 0.0
        contagem_rua = 0
        for chave, dados_casulo in st.session_state.base_dados_cd.items():
            r_n, lado_r, c_r, n_r = chave.split("|")
            if r_n == rua:
                l_param = "par" if rua == "Rua 11" else ("impar" if lado_r == "seq" else lado_r)
                spec_r = obter_especificacao_casulo(rua, int(c_r), l_param)
                soma_fracoes_rua += calcular_fracao_ocupada(dados_casulo, spec_r["tipo_estrutural"], rua)
                contagem_rua += 1

        pct_rua = (soma_fracoes_rua / contagem_rua * 100) if contagem_rua > 0 else 0.0
        classe_cor = obter_classe_cor(pct_rua)
        dados_ranking.append({"Rua": rua, "Ocupação (%)": round(pct_rua, 1)})

        with col_alvo:
            st.markdown(f"""
            <div class="planta-rua-bloco">
                <div style="font-weight: bold; font-size: 15px; color: #ffcc00;">{rua}</div>
                <div style="font-size: 12px; margin-top: 2px; color: #8892b0;">{pct_rua:.1f}% ocupado</div>
                <div class="bar-container">
                    <div class="bar-fill {classe_cor}" style="width: {pct_rua}%;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.write("---")
    st.markdown("<h4 style='text-align: center; color: #ffcc00;'>📈 Ranking de Ocupação por Corredor (%)</h4>", unsafe_allow_html=True)

    if dados_ranking:
        df_ranking = pd.DataFrame(dados_ranking).set_index("Rua")
        st.bar_chart(df_ranking, color="#ffcc00")

        df_ordenado = pd.DataFrame(dados_ranking).sort_values("Ocupação (%)", ascending=False)
        rua_mais_cheia = df_ordenado.iloc[0]
        rua_mais_vazia = df_ordenado.iloc[-1]

        kcol_rank1, kcol_rank2 = st.columns(2)
        with kcol_rank1:
            st.markdown(f"<div class='card-dashboard'><h5>🔥 Corredor Mais Cheio</h5><h2>{rua_mais_cheia['Rua']}</h2><p style='color:#8892b0; margin-top:4px; font-size:12px;'>{rua_mais_cheia['Ocupação (%)']:.1f}% ocupado</p></div>", unsafe_allow_html=True)
        with kcol_rank2:
            st.markdown(f"<div class='card-dashboard'><h5>🌤️ Corredor Mais Livre</h5><h2>{rua_mais_vazia['Rua']}</h2><p style='color:#8892b0; margin-top:4px; font-size:12px;'>{rua_mais_vazia['Ocupação (%)']:.1f}% ocupado</p></div>", unsafe_allow_html=True)


# ==========================================
# TELA 2: VISUALIZADOR DE CASULOS
# ==========================================
elif st.session_state.aba_ativa_selecionada == "📦 Visualizador de Casulos":
    lista_ruas = list(ESTRUTURA_CD.keys())
    rua_inicial_idx = 0
    if st.session_state.busca_destaque and st.session_state.busca_destaque['rua'] in lista_ruas:
        rua_inicial_idx = lista_ruas.index(st.session_state.busca_destaque['rua'])

    rua_selecionada = st.selectbox("Selecione a Rua para Inspeção Detalhada:", lista_ruas, index=rua_inicial_idx)

    config_rua = ESTRUTURA_CD.get(rua_selecionada, {})

    if config_rua.get("tipo") == "Inexistente":
        st.markdown(f"<h3 style='text-align: center; color: #e74c3c;'>⚠️ Corredor <b>{rua_selecionada}</b> Inexistente</h3>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #8892b0;'>Este corredor não possui estrutura física mapeada no sistema.</p>", unsafe_allow_html=True)
    else:
        st.markdown(f"<h3 style='text-align: center; color: #ffcc00;'>📍 Malha Física do Corredor: <b>{rua_selecionada}</b></h3>", unsafe_allow_html=True)

        st.markdown("""
        <div class="topicos-legenda">
            <b style="color: #ffcc00; display: block; margin-bottom: 6px; text-align: center;">📋 Legenda de Ocupação (tabela de capacidade real):</b>
            <ul>
                <li><span style="color: #45a29e; font-weight: bold;">Verde:</span> Disponível / Baixa (&lt; 50%)</li>
                <li><span style="color: #ffcc00; font-weight: bold;">Amarelo:</span> Moderado (50% a 80%)</li>
                <li><span style="color: #f39c12; font-weight: bold;">Laranja:</span> Alerta (81% a 99%)</li>
                <li><span style="color: #e74c3c; font-weight: bold;">Vermelho:</span> Saturado (100%)</li>
                <li>Dentro do casulo: <b>peças atuais / capacidade estimada</b>. A coluna aparece na linha de cabeçalho, acima da grade.</li>
                <li>⚠️ Jaquetas Pesadas/Casacos/Parkas só podem ser lançadas em casulos de <b>Metal Raso ou Madeira/Metal Profundo</b>.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

        if rua_selecionada == "Rua 14":
            st.markdown("<p style='text-align:center; color:#8892b0; font-size:13px;'>Corredor segmentado por Tipologia Estrutural (Madeira e Metal)</p>", unsafe_allow_html=True)

            blocos_r14 = [
                ("🌲 Bloco 1: Prateleiras de Madeira Gigante (Colunas 01 a 23)", list(range(1, 24))),
                ("🔩 Bloco 2: Prateleiras de Metal Profundo (Colunas 24 a 31)", list(range(24, 32))),
                ("⚙️ Bloco 3: Prateleiras de Metal Raso (Colunas 42 a 48)", list(range(42, 49)))
            ]

            for titulo_bloco, cols_bloco in blocos_r14:
                st.markdown(f"<div class='lado-container'>", unsafe_allow_html=True)
                st.markdown(f"<div class='lado-titulo'>{titulo_bloco}</div>", unsafe_allow_html=True)

                spec_ref = obter_especificacao_casulo(rua_selecionada, cols_bloco[0], "impar")
                niveis_ordenados = sorted(spec_ref["niveis"])

                renderizar_cabecalho_colunas(cols_bloco)

                for nivel in niveis_ordenados:
                    grid_bloco = st.columns(len(cols_bloco) + 1)
                    with grid_bloco[0]:
                        st.markdown(f"<div style='line-height:28px; text-align:center; font-weight:bold; color:#8892b0; font-size: 10px;'>{nivel}</div>", unsafe_allow_html=True)
                    for idx, col_num in enumerate(cols_bloco):
                        with grid_bloco[idx + 1]:
                            spec_col = obter_especificacao_casulo(rua_selecionada, col_num, "impar")
                            st.markdown(montar_html_nicho(rua_selecionada, col_num, nivel, spec_col, "seq"), unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

        elif rua_selecionada == "Rua 20":
            st.markdown("<p style='text-align:center; color:#8892b0; font-size:13px;'>Corredor Sequencial de Aramados Pequenos (Colunas Ímpares de 35 a 137)</p>", unsafe_allow_html=True)

            todas_colunas = config_rua.get("cols_seq", [])
            if not todas_colunas:
                st.warning("⚠️ Não existem colunas cadastradas para a Rua 20.")
            else:
                if len(todas_colunas) > 25:
                    tamanho_bloco = 25
                    blocos = [(f"Colunas {todas_colunas[i]:03d} até {todas_colunas[min(i+tamanho_bloco-1, len(todas_colunas)-1)]:03d}", todas_colunas[i:i+tamanho_bloco]) for i in range(0, len(todas_colunas), tamanho_bloco)]
                    opcoes_bloco = [b[0] for b in blocos]
                    bloco_escolhido_nome = st.selectbox("Selecione o Bloco de Colunas:", opcoes_bloco)
                    colunas_exemplo = next(b[1] for b in blocos if b[0] == bloco_escolhido_nome)
                else:
                    colunas_exemplo = todas_colunas

                niveis_ordenados = sorted(NIVEIS_P)

                st.markdown("<div class='lado-container'>", unsafe_allow_html=True)
                st.markdown(f"<div class='lado-titulo'>Corredor Sequencial Rua 20</div>", unsafe_allow_html=True)

                renderizar_cabecalho_colunas(colunas_exemplo)

                for nivel in niveis_ordenados:
                    grid_seq = st.columns(len(colunas_exemplo) + 1)
                    with grid_seq[0]:
                        st.markdown(f"<div style='line-height:28px; text-align:center; font-weight:bold; color:#8892b0; font-size: 10px;'>{nivel}</div>", unsafe_allow_html=True)
                    for idx, col_num in enumerate(colunas_exemplo):
                        with grid_seq[idx + 1]:
                            spec_col = obter_especificacao_casulo(rua_selecionada, col_num, "impar")
                            st.markdown(montar_html_nicho(rua_selecionada, col_num, nivel, spec_col, "seq"), unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

        elif rua_selecionada == "Rua 21":
            st.markdown("<p style='text-align:center; color:#8892b0; font-size:13px;'>Corredor Sequencial de Prateleiras de Metal (Colunas Ímpares de 01 a 77)</p>", unsafe_allow_html=True)

            todas_colunas = config_rua.get("cols_seq", [])
            if not todas_colunas:
                st.warning("⚠️ Não existem colunas cadastradas para a Rua 21.")
            else:
                if len(todas_colunas) > 25:
                    tamanho_bloco = 25
                    blocos = [(f"Colunas {todas_colunas[i]:03d} até {todas_colunas[min(i+tamanho_bloco-1, len(todas_colunas)-1)]:03d}", todas_colunas[i:i+tamanho_bloco]) for i in range(0, len(todas_colunas), tamanho_bloco)]
                    opcoes_bloco = [b[0] for b in blocos]
                    bloco_escolhido_nome = st.selectbox("Selecione o Bloco de Colunas:", opcoes_bloco)
                    colunas_exemplo = next(b[1] for b in blocos if b[0] == bloco_escolhido_nome)
                else:
                    colunas_exemplo = todas_colunas

                spec_ref = obter_especificacao_casulo(rua_selecionada, colunas_exemplo[0], "impar")
                niveis_ordenados = sorted(spec_ref["niveis"])

                st.markdown("<div class='lado-container'>", unsafe_allow_html=True)
                st.markdown(f"<div class='lado-titulo'>Corredor Sequencial Rua 21</div>", unsafe_allow_html=True)

                renderizar_cabecalho_colunas(colunas_exemplo)

                for nivel in niveis_ordenados:
                    grid_seq = st.columns(len(colunas_exemplo) + 1)
                    with grid_seq[0]:
                        st.markdown(f"<div style='line-height:28px; text-align:center; font-weight:bold; color:#8892b0; font-size: 10px;'>{nivel}</div>", unsafe_allow_html=True)
                    for idx, col_num in enumerate(colunas_exemplo):
                        with grid_seq[idx + 1]:
                            spec_col = obter_especificacao_casulo(rua_selecionada, col_num, "impar")
                            st.markdown(montar_html_nicho(rua_selecionada, col_num, nivel, spec_col, "seq"), unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

        elif "cols_seq" in config_rua or rua_selecionada == "Rua 11":
            if rua_selecionada == "Rua 11":
                todas_colunas = config_rua.get("cols_par", [])
            else:
                todas_colunas = config_rua.get("cols_seq", [])

            if not todas_colunas:
                st.warning(f"⚠️ Não existem casulos cadastrados nesta rua ({rua_selecionada}).")
            else:
                if len(todas_colunas) > 25:
                    tamanho_bloco = 25
                    blocos = [(f"Colunas {todas_colunas[i]:03d} até {todas_colunas[min(i+tamanho_bloco-1, len(todas_colunas)-1)]:03d}", todas_colunas[i:i+tamanho_bloco]) for i in range(0, len(todas_colunas), tamanho_bloco)]
                    opcoes_bloco = [b[0] for b in blocos]
                    bloco_escolhido_nome = st.selectbox("Selecione o Bloco de Colunas:", opcoes_bloco)
                    colunas_exemplo = next(b[1] for b in blocos if b[0] == bloco_escolhido_nome)
                else:
                    colunas_exemplo = todas_colunas

                l_ref = "par" if rua_selecionada == "Rua 11" else "impar"
                spec_ref = obter_especificacao_casulo(rua_selecionada, colunas_exemplo[0] if colunas_exemplo else 22, l_ref)
                niveis_ordenados = sorted(spec_ref["niveis"])

                st.markdown(f"<p style='text-align:center; color:#8892b0; font-size:12px;'>Especificação: <b>{spec_ref['tipo_desc']}</b></p>", unsafe_allow_html=True)

                st.markdown("<div class='lado-container'>", unsafe_allow_html=True)
                st.markdown(f"<div class='lado-titulo'>Corredor Sequencial / Unilateral ({rua_selecionada})</div>", unsafe_allow_html=True)

                renderizar_cabecalho_colunas(colunas_exemplo)

                for nivel in niveis_ordenados:
                    grid_seq = st.columns(len(colunas_exemplo) + 1)
                    with grid_seq[0]:
                        st.markdown(f"<div style='line-height:28px; text-align:center; font-weight:bold; color:#8892b0; font-size: 10px;'>{nivel}</div>", unsafe_allow_html=True)
                    for idx, col_num in enumerate(colunas_exemplo):
                        with grid_seq[idx + 1]:
                            l_param_col = "par" if rua_selecionada == "Rua 11" else "impar"
                            spec_col = obter_especificacao_casulo(rua_selecionada, col_num, l_param_col)
                            lado_chave = "par" if rua_selecionada == "Rua 11" else "seq"
                            st.markdown(montar_html_nicho(rua_selecionada, col_num, nivel, spec_col, lado_chave), unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

        else:
            todas_cols_impares = config_rua.get("cols_impar", [])
            todas_cols_pares = config_rua.get("cols_par", [])
            todas_colunas = sorted(list(set(todas_cols_impares + todas_cols_pares)))

            if not todas_colunas:
                st.warning(f"⚠️ Não existem casulos cadastrados nesta rua ({rua_selecionada}).")
            else:
                if len(todas_colunas) > 20:
                    tamanho_bloco = 20
                    blocos = [(f"Colunas {todas_colunas[i]:03d} até {todas_colunas[min(i+tamanho_bloco-1, len(todas_colunas)-1)]:03d}", todas_colunas[i:i+tamanho_bloco]) for i in range(0, len(todas_colunas), tamanho_bloco)]
                    opcoes_bloco = [b[0] for b in blocos]
                    bloco_escolhido_nome = st.selectbox("Selecione o Bloco de Colunas:", opcoes_bloco)
                    colunas_exemplo = next(b[1] for b in blocos if b[0] == bloco_escolhido_nome)
                else:
                    colunas_exemplo = todas_colunas

                colunas_impares = [c for c in colunas_exemplo if c in todas_cols_impares]
                colunas_pares = [c for c in colunas_exemplo if c in todas_cols_pares]

                niveis_impar_ref, tipo_desc_impar = [], ""
                niveis_par_ref, tipo_desc_par = [], ""
                if colunas_impares:
                    spec_impar = obter_especificacao_casulo(rua_selecionada, colunas_impares[0], "impar")
                    niveis_impar_ref = spec_impar["niveis"]
                    tipo_desc_impar = spec_impar["tipo_desc"]
                if colunas_pares:
                    spec_par = obter_especificacao_casulo(rua_selecionada, colunas_pares[0], "par")
                    niveis_par_ref = spec_par["niveis"]
                    tipo_desc_par = spec_par["tipo_desc"]

                niveis_ordenados = sorted(set(niveis_impar_ref) | set(niveis_par_ref))

                if tipo_desc_impar and tipo_desc_par and tipo_desc_impar != tipo_desc_par:
                    tipo_desc = f"Ímpar: {tipo_desc_impar} | Par: {tipo_desc_par}"
                else:
                    tipo_desc = tipo_desc_impar or tipo_desc_par

                st.markdown(f"<p style='text-align:center; color:#8892b0; font-size:12px;'>Especificação: <b>{tipo_desc}</b></p>", unsafe_allow_html=True)

                col_esq_layout, col_dir_layout = st.columns(2)

                with col_esq_layout:
                    st.markdown("<div class='lado-container'>", unsafe_allow_html=True)
                    st.markdown("<div class='lado-titulo'>◀ Lado Ímpar</div>", unsafe_allow_html=True)
                    if colunas_impares:
                        renderizar_cabecalho_colunas(colunas_impares)
                        for nivel in niveis_ordenados:
                            grid_impar = st.columns(len(colunas_impares) + 1)
                            with grid_impar[0]:
                                st.markdown(f"<div style='line-height:28px; text-align:center; font-weight:bold; color:#8892b0; font-size: 10px;'>{nivel}</div>", unsafe_allow_html=True)
                            for idx, col_num in enumerate(colunas_impares):
                                with grid_impar[idx + 1]:
                                    spec_col = obter_especificacao_casulo(rua_selecionada, col_num, "impar")
                                    st.markdown(montar_html_nicho(rua_selecionada, col_num, nivel, spec_col, "impar"), unsafe_allow_html=True)
                    else:
                        st.markdown("<p style='color: #8892b0; font-size: 12px; padding: 20px;'>Sem casulos neste lado.</p>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)

                with col_dir_layout:
                    st.markdown("<div class='lado-container'>", unsafe_allow_html=True)
                    st.markdown("<div class='lado-titulo'>Lado Par ▶</div>", unsafe_allow_html=True)
                    if colunas_pares:
                        renderizar_cabecalho_colunas(colunas_pares)
                        for nivel in niveis_ordenados:
                            grid_par = st.columns(len(colunas_pares) + 1)
                            with grid_par[0]:
                                st.markdown(f"<div style='line-height:28px; text-align:center; font-weight:bold; color:#8892b0; font-size: 10px;'>{nivel}</div>", unsafe_allow_html=True)
                            for idx, col_num in enumerate(colunas_pares):
                                with grid_par[idx + 1]:
                                    spec_col = obter_especificacao_casulo(rua_selecionada, col_num, "par")
                                    st.markdown(montar_html_nicho(rua_selecionada, col_num, nivel, spec_col, "par"), unsafe_allow_html=True)
                    else:
                        st.markdown("<p style='color: #8892b0; font-size: 12px; padding: 20px;'>Sem casulos neste lado.</p>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)


# ==========================================
# TELA 3: CONSULTA RÁPIDA DE CASULOS ESPECÍFICOS
# ==========================================
elif st.session_state.aba_ativa_selecionada == "🔍 Consulta Rápida de Casulos":
    st.markdown("<h3 style='text-align: center; color: #ffcc00;'>🔍 Auditoria Rápida de Múltiplos Casulos</h3>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #8892b0;'>Selecione ou insira endereços para auditar simultaneamente a ocupação.</p>", unsafe_allow_html=True)

    chaves_disponiveis = sorted(list(st.session_state.base_dados_cd.keys()))

    casulos_selecionados = st.multiselect(
        "Selecione os Casulos (Formato: Rua|Lado|Coluna|Nível):",
        options=chaves_disponiveis,
        default=chaves_disponiveis[:3] if len(chaves_disponiveis) >= 3 else chaves_disponiveis
    )

    if not casulos_selecionados:
        st.info("💡 Nenhum casulo selecionado acima. Utilize a caixa de seleção para escolher os endereços que deseja auditar.")
    else:
        st.write("---")
        st.caption("Para lançar ou ajustar quantidades, use a aba 📥 Entrada de Dados (o lançamento precisa da categoria da peça e da estação).")
        cols_cards = st.columns(3)

        for idx, chave in enumerate(casulos_selecionados):
            col_alvo_card = cols_cards[idx % 3]
            r_nome, lado_n, c_str, nivel_n = chave.split("|")
            col_num = int(c_str)

            l_param = "par" if r_nome == "Rua 11" else ("impar" if lado_n == "seq" else lado_n)
            spec = obter_especificacao_casulo(r_nome, col_num, l_param)
            dados_casulo = st.session_state.base_dados_cd.get(chave, {})
            pecas_atuais = calcular_pecas_totais(dados_casulo)
            pct = calcular_fracao_ocupada(dados_casulo, spec["tipo_estrutural"], r_nome) * 100
            capacidade_estimada = obter_capacidade_estimada_exibicao(spec["tipo_estrutural"], r_nome)

            c_cor = "cor-verde"
            if pct >= 100: c_cor = "cor-vermelho"
            elif pct >= 81: c_cor = "cor-laranja"
            elif pct >= 50: c_cor = "cor-amarelo"

            breakdown_txt = ", ".join([f"{combo.replace('|', ' - ')}: {qtd}" for combo, qtd in dados_casulo.items() if qtd > 0]) or "Vazio"

            with col_alvo_card:
                st.markdown(f"""
                <div class="card-dashboard" style="margin-bottom: 15px; text-align: left; padding: 15px;">
                    <div style="font-size: 13px; font-weight: bold; color: #ffcc00; margin-bottom: 5px;">📍 {r_nome} ({lado_n.upper()})</div>
                    <div style="font-size: 12px; color: #c5c6c7;">Coluna: <b>{col_num:03d}</b> | Nível: <b>{nivel_n}</b> | Tipo: <b>{spec['tipo_desc']}</b></div>
                    <div style="font-size: 16px; font-weight: bold; color: #fff; margin: 8px 0;">{pecas_atuais:,} / {capacidade_estimada:,} un <span style="font-size: 12px; color: #8892b0;">({pct:.1f}%)</span></div>
                    <div class="bar-container">
                        <div class="bar-fill {c_cor}" style="width: {min(pct, 100.0)}%;"></div>
                    </div>
                    <div style="font-size: 10px; color: #8892b0; margin-top: 6px;">Mix atual: {breakdown_txt}</div>
                </div>
                """, unsafe_allow_html=True)


# ==========================================
# TELA 4: ENTRADA DE DADOS / ABASTECIMENTO
# ==========================================
elif st.session_state.aba_ativa_selecionada == "📥 Entrada de Dados / Abastecimento":
    st.markdown("<h3 style='text-align: center; color: #ffcc00;'>📥 Entrada de Dados por Categoria e Estação</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='color: #8892b0; text-align: center;'>Cada lançamento marca a peça com uma categoria (do tipo Regatas/Bodys/Tops até Jaquetas Pesadas) e uma estação. Estoques de estações diferentes convivem no mesmo casulo.</p>", unsafe_allow_html=True)

    with st.expander("📋 Ver tabela de capacidade (Verão / Inverno)"):
        st.markdown("**Verão - Feminino** (peças por casulo, faixa mín-máx)")
        df_verao = pd.DataFrame([
            {"Categoria": cat, **{tipo: f"{v[0]}-{v[1]}" if v else "Proibido" for tipo, v in tipos.items()}}
            for cat, tipos in CAPACIDADE_VERAO_FEMININO.items()
        ])
        st.dataframe(df_verao, use_container_width=True, hide_index=True)

        st.markdown("**Inverno - Feminino** (peças por casulo, faixa mín-máx)")
        df_inverno = pd.DataFrame([
            {"Categoria": cat, **{tipo: f"{v[0]}-{v[1]}" if v else "Proibido" for tipo, v in tipos.items()}}
            for cat, tipos in CAPACIDADE_INVERNO_FEMININO.items()
        ])
        st.dataframe(df_inverno, use_container_width=True, hide_index=True)

        st.markdown("**Densidade fixa por rua (Masculino)** — sobrepõe a tabela de categoria")
        df_fixa = pd.DataFrame([
            {"Rua": rua, "Tipo": tipo, "Capacidade fixa": valor}
            for rua, tipos in CAPACIDADE_FIXA_POR_RUA.items()
            for tipo, valor in tipos.items()
        ])
        st.dataframe(df_fixa, use_container_width=True, hide_index=True)

        st.caption("O sistema usa sempre o valor MÍNIMO da faixa como capacidade real (ou a densidade fixa, quando existir). Meia-Estação reaproveita a tabela de Verão. Travas rígidas: P máx 6 peças, Vestidos em M máx 4 peças, em qualquer rua.")

    tab_cad1, tab_cad2 = st.tabs(["✏️ Atualização de Casulo Individual", "🧹 Ações Globais na Base"])

    with tab_cad1:
        st.markdown("#### Configurar Estoque do Casulo")
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)

        with col_f1:
            rua_cad = st.selectbox("Rua", list(ESTRUTURA_CD.keys()), key="rcad")

        cfg_r_cad = ESTRUTURA_CD.get(rua_cad, {})

        if cfg_r_cad.get("tipo") == "Inexistente":
            st.error(f"⚠️ A {rua_cad} é inexistente e não possui casulos para abastecimento.")
        else:
            with col_f2:
                if "cols_seq" in cfg_r_cad:
                    lado_cad = "seq"
                    st.selectbox("Lado", ["Sequencial Único"], key="lcad_seq_disabled", disabled=True)
                elif rua_cad == "Rua 11":
                    lado_cad = "par"
                    st.selectbox("Lado", ["par (Unilateral)"], key="lcad_r11_disabled", disabled=True)
                else:
                    lado_cad = st.selectbox("Lado", ["impar", "par"], key="lcad")

            if lado_cad == "seq":
                cols_disponiveis = cfg_r_cad.get("cols_seq", [])
            else:
                cols_disponiveis = cfg_r_cad.get("cols_impar" if lado_cad == "impar" else "cols_par", [])

            with col_f3:
                if cols_disponiveis:
                    col_cad = st.selectbox("Coluna", cols_disponiveis, key="ccad")
                else:
                    col_cad = st.selectbox("Coluna", [0], key="ccad_vazio")

            l_param_func = "par" if rua_cad == "Rua 11" else ("impar" if lado_cad == "seq" else lado_cad)
            spec_cad = obter_especificacao_casulo(rua_cad, col_cad, l_param_func)

            with col_f4:
                if spec_cad["niveis"]:
                    nivel_cad = st.selectbox("Nível", sorted(spec_cad["niveis"]), key="ncad")
                else:
                    nivel_cad = st.selectbox("Nível", ["B"], key="ncad_vazio")

            lado_chave_cad = "seq" if lado_cad == "seq" else lado_cad
            chave_alvo = obter_chave_casulo(rua_cad, lado_chave_cad, col_cad, nivel_cad)
            dados_casulo_alvo = st.session_state.base_dados_cd.get(chave_alvo, {})
            pecas_atuais_totais = calcular_pecas_totais(dados_casulo_alvo)
            pct_atual = calcular_fracao_ocupada(dados_casulo_alvo, spec_cad["tipo_estrutural"], rua_cad) * 100

            st.info(f"📦 Casulo {rua_cad} - Col {col_cad:03d} - Nível {nivel_cad} | Tipo: **{spec_cad['tipo_desc']}** | Ocupação atual: **{pecas_atuais_totais} peças ({pct_atual:.1f}%)**")

            st.markdown("##### Lançar / Ajustar peças por Categoria e Estação")
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                estacao_cad = st.selectbox("Estação (marca da peça)", ESTACOES_PECA, key="estacao_cad")
            with col_t2:
                categorias_disponiveis = obter_categorias_por_estacao(obter_genero_rua(rua_cad))[estacao_cad]
                categorias_permitidas = [c for c in categorias_disponiveis if peca_permitida(c, spec_cad["tipo_estrutural"], estacao_cad, rua_cad)]
                categoria_cad = st.selectbox("Categoria da peça", categorias_permitidas, key="categoria_cad")

            faixa_cad = obter_faixa_capacidade(categoria_cad, spec_cad["tipo_estrutural"], estacao_cad, rua_cad)

            chave_combo_cad = obter_chave_estoque(categoria_cad, estacao_cad)
            qtd_existente_combo = dados_casulo_alvo.get(chave_combo_cad, 0)

            if faixa_cad:
                if faixa_cad[0] == faixa_cad[1]:
                    st.caption(f"Densidade fixa da rua: {faixa_cad[0]} peças.")
                else:
                    st.caption(f"Faixa da tabela: {faixa_cad[0]} a {faixa_cad[1]} peças (sistema usa o mínimo: {faixa_cad[0]}).")

            nova_qtd_input = st.number_input("Quantidade", min_value=0, value=int(qtd_existente_combo), step=1, key="qtd_cad")

            categorias_bloqueadas = [c for c in categorias_disponiveis if c not in categorias_permitidas]
            if categorias_bloqueadas:
                st.caption(f"⚠️ Este casulo não aceita: {', '.join(categorias_bloqueadas)} (só cabem em Metal Raso ou Madeira/Metal Profundo).")

            if st.button("💾 Salvar Quantidade", type="primary"):
                dados_atualizados = dict(st.session_state.base_dados_cd.get(chave_alvo, {}))
                if nova_qtd_input <= 0:
                    dados_atualizados.pop(chave_combo_cad, None)
                else:
                    dados_atualizados[chave_combo_cad] = int(nova_qtd_input)
                st.session_state.base_dados_cd[chave_alvo] = dados_atualizados
                st.success(f"Casulo {rua_cad} - {col_cad:03d}-{nivel_cad} atualizado: {categoria_cad} / {estacao_cad} = {nova_qtd_input} peças!")
                st.rerun()

    with tab_cad2:
        st.markdown("#### Manutenção Geral da Base de Dados")

        if st.session_state.papel_atual != "gerente":
            st.info("🔒 Ações globais na base são funções críticas, restritas ao papel de Gerente.")
        else:
            st.warning("⚠️ Atenção: Os botões abaixo modificam permanentemente a quantidade de peças em todo o CD na memória.")

            c_A, c_B = st.columns(2)
            with c_A:
                if st.button("Zerar Todos os Casulos (0 Peças)"):
                    for k in st.session_state.base_dados_cd.keys():
                        st.session_state.base_dados_cd[k] = {}
                    st.success("Todos os casulos foram zerados com sucesso!")
                    st.rerun()
            with c_B:
                if st.button("Popular com Dados Simulados Aleatórios"):
                    np.random.seed(321)
                    for k in st.session_state.base_dados_cd.keys():
                        r_n, l_n, c_n, n_n = k.split("|")
                        l_param_pop = "par" if r_n == "Rua 11" else ("impar" if l_n == "seq" else l_n)
                        spec_pop = obter_especificacao_casulo(r_n, int(c_n), l_param_pop)

                        if np.random.rand() < 0.35:
                            st.session_state.base_dados_cd[k] = {}
                            continue

                        estacao_sorteada = np.random.choice(ESTACOES_PECA)
                        categorias_disp_pop = obter_categorias_por_estacao(obter_genero_rua(r_n))[estacao_sorteada]
                        categorias_ok_pop = [c for c in categorias_disp_pop if peca_permitida(c, spec_pop["tipo_estrutural"], estacao_sorteada, r_n)]
                        if not categorias_ok_pop:
                            st.session_state.base_dados_cd[k] = {}
                            continue
                        categoria_sorteada = np.random.choice(categorias_ok_pop)
                        cap_min_pop = obter_capacidade_minima(categoria_sorteada, spec_pop["tipo_estrutural"], estacao_sorteada, r_n)
                        qtd_sorteada = int(np.random.choice([0, int(cap_min_pop * 0.3), int(cap_min_pop * 0.7), cap_min_pop]))

                        if qtd_sorteada > 0:
                            st.session_state.base_dados_cd[k] = {obter_chave_estoque(categoria_sorteada, estacao_sorteada): qtd_sorteada}
                        else:
                            st.session_state.base_dados_cd[k] = {}
                    st.success("Base populada com dados de teste (categorias e estações variadas)!")
                    st.rerun()


# ==========================================
# TELA 5: GERENCIADOR (ADMIN)
# ==========================================
elif st.session_state.aba_ativa_selecionada == "🛠️ Gerenciador (Admin)":
    if st.session_state.papel_atual != "gerente":
        st.error("⛔ Acesso restrito a usuários com papel de Gerente.")
    else:
        st.markdown("<h3 style='text-align: center; color: #ffcc00;'>🛠️ Painel do Gerenciador</h3>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #8892b0;'>Funções críticas disponíveis apenas para o papel de Gerente.</p>", unsafe_allow_html=True)

        tab_ger1, tab_ger2 = st.tabs(["👥 Gestão de Logins", "🧾 Usuários Cadastrados"])

        with tab_ger1:
            st.markdown("#### Criar Novo Login")
            col_g1, col_g2, col_g3 = st.columns(3)
            with col_g1:
                novo_usuario = st.text_input("Novo usuário (login)", key="novo_usuario_input")
            with col_g2:
                nova_senha = st.text_input("Senha", type="password", key="nova_senha_input")
            with col_g3:
                novo_papel = st.selectbox("Papel", ["operador", "gerente"], key="novo_papel_input")

            if st.button("➕ Criar Usuário", type="primary"):
                if not novo_usuario or not nova_senha:
                    st.error("⚠️ Preencha usuário e senha.")
                elif novo_usuario in st.session_state.usuarios_cadastrados:
                    st.error(f"⚠️ O usuário '{novo_usuario}' já existe.")
                else:
                    st.session_state.usuarios_cadastrados[novo_usuario] = {"senha": nova_senha, "papel": novo_papel}
                    st.success(f"Usuário '{novo_usuario}' criado como {novo_papel}!")
                    st.rerun()

            st.markdown("---")
            st.markdown("#### Remover Usuário")
            usuarios_removiveis = [u for u in st.session_state.usuarios_cadastrados.keys() if u != st.session_state.usuario_atual]
            if usuarios_removiveis:
                usuario_remover = st.selectbox("Selecione o usuário a remover", usuarios_removiveis, key="usuario_remover_input")
                if st.button("🗑️ Remover Usuário Selecionado"):
                    total_gerentes = sum(1 for u in st.session_state.usuarios_cadastrados.values() if u["papel"] == "gerente")
                    if st.session_state.usuarios_cadastrados[usuario_remover]["papel"] == "gerente" and total_gerentes <= 1:
                        st.error("⚠️ Não é possível remover o último gerente do sistema.")
                    else:
                        del st.session_state.usuarios_cadastrados[usuario_remover]
                        st.success(f"Usuário '{usuario_remover}' removido!")
                        st.rerun()
            else:
                st.info("Não há outros usuários cadastrados para remover.")

        with tab_ger2:
            st.markdown("#### Usuários com Acesso ao Sistema")
            lista_usuarios_df = pd.DataFrame([
                {"Usuário": u, "Papel": dados["papel"].capitalize()}
                for u, dados in st.session_state.usuarios_cadastrados.items()
            ])
            st.dataframe(lista_usuarios_df, use_container_width=True, hide_index=True)
