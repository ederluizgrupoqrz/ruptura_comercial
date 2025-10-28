import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import re

# === CONFIGURAÇÕES ===
SHEET_ID = "1Ss4PCyVcDiXMDRglyg6u7Vqux0gJ_amZn06GdVh7PQo"
SHEET_NAME = "RUPTURAS LOJAS"
LOGO_PATH = "qrz_grupo_queiroz_logo.png"

TRATATIVAS = [
    "Nenhuma",
    "Problema no Agendamento",
    "Ruptura da Industria",
    "Será feito pedido",
    "Pendente Entrega",
    "Mudança de Gramatura",
    "Descontinuado",
    "Solicitar Transferencia",
    "Chegou Recente",
    "Verificar Estoque (Divergência)",
    "Saiu do Mix da Loja",
    "Indeferido"
]

# === CONECTAR AO GOOGLE SHEETS ===
def conectar_planilha():
    escopos = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("projeto-ruptura-33518d57fb06.json", escopos)
    cliente = gspread.authorize(creds)
    planilha = cliente.open_by_key(SHEET_ID)
    aba = planilha.worksheet(SHEET_NAME)
    return aba

# === CARREGAR DADOS ===
@st.cache_data(ttl=60)
def carregar_dados():
    aba = conectar_planilha()
    dados = aba.get_all_records()
    df = pd.DataFrame(dados)

    # Converter a coluna de data/hora do formulário para datetime
    if "Carimbo de data/hora" in df.columns:
        df["Data"] = df["Carimbo de data/hora"].apply(lambda x: str(x).split(" ")[0])  # extrai apenas a data
        try:
            df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y").dt.date
        except Exception:
            df["Data"] = pd.NaT
    return df

# === SALVAR TRATATIVA ===
def salvar_tratativa(df, id_linha, tratativa):
    aba = conectar_planilha()
    linhas = aba.get_all_values()
    header = linhas[0]

    if "Tratativa Comercial" not in header or "IDOK" not in header:
        st.error("Colunas 'IDOK' ou 'Tratativa Comercial' não encontradas na planilha.")
        return

    idx_tratativa = header.index("Tratativa Comercial")
    idx_id = header.index("IDOK")
    id_alvo = str(id_linha).strip()

    for i, row in enumerate(linhas[1:], start=2):
        id_planilha = str(row[idx_id]).strip()
        if id_planilha == id_alvo:
            valor = "" if tratativa == "Nenhuma" else tratativa
            aba.update_cell(i, idx_tratativa + 1, valor)
            st.success(f"✅ Tratativa atualizada para '{valor or 'Nenhuma'}'")
            return

    st.warning(f"⚠️ Registro não encontrado para ID {id_linha} — verifique se está igual na planilha.")

# === INTERFACE STREAMLIT ===
st.set_page_config(page_title="Tratativas Comerciais", layout="wide")

# === CSS PARA TEMA CLARO/ESCURO ===
st.markdown("""
<style>
@media (prefers-color-scheme: dark) {
    :root {
        --bg-color: #121212;
        --text-color: #f5f5f5;
        --sidebar-bg: #1c1c1c;
        --input-bg: #2a2a2a;
        --card-pendente: #3a1f1f;
        --card-tratado: #1f3a2a;
    }

    body, .stApp {
        background-color: var(--bg-color);
        color: var(--text-color);
    }

    div[data-testid="stSidebar"] {
        background-color: var(--sidebar-bg) !important;
        color: var(--text-color) !important;
    }

    h1, h2, h3, h4, h5, h6, p, label, span, div, button, input, select {
        color: var(--text-color) !important;
    }

    .stSelectbox, .stTextInput, .stRadio, .stDateInput, .stButton > button {
        background-color: var(--input-bg) !important;
        color: var(--text-color) !important;
        border: 1px solid #333 !important;
    }

    .stButton > button {
        background-color: #333 !important;
        color: var(--text-color) !important;
        border-radius: 8px;
    }
}

@media (prefers-color-scheme: light) {
    :root {
        --bg-color: #ffffff;
        --text-color: #000000;
        --sidebar-bg: #f0f2f6;
        --input-bg: #ffffff;
        --card-pendente: #FDECEA;
        --card-tratado: #E8F5E9;
    }

    body, .stApp {
        background-color: var(--bg-color);
        color: var(--text-color);
    }

    div[data-testid="stSidebar"] {
        background-color: var(--sidebar-bg) !important;
        color: var(--text-color) !important;
    }
}
</style>
""", unsafe_allow_html=True)

# === CABEÇALHO ===
col1, col2 = st.columns([1, 5])
with col1:
    st.image(LOGO_PATH, width=220)
with col2:
    st.title("Sistema de Tratativas Comerciais")

df = carregar_dados()
if df.empty:
    st.error("Nenhum dado encontrado na planilha.")
    st.stop()

# === MENU LATERAL ===
st.sidebar.header("Menu Principal")

# Filtro comprador
compradores = sorted(df["Comprador"].dropna().unique())
comprador = st.sidebar.selectbox("👤 Selecione o comprador:", compradores)

if not comprador:
    st.info("Selecione um comprador no menu lateral.")
    st.stop()

# Filtro de data
datas_disponiveis = sorted(df["Data"].dropna().unique())
data_selecionada = st.sidebar.date_input("📅 Filtrar por data:", value=None, min_value=min(datas_disponiveis), max_value=max(datas_disponiveis))

# === FILTRAR DADOS ===
dados_filtrados = df[df["Comprador"] == comprador]

if data_selecionada:
    dados_filtrados = dados_filtrados[dados_filtrados["Data"] == data_selecionada]

if dados_filtrados.empty:
    st.warning("Nenhum registro encontrado para os filtros selecionados.")
    st.stop()

# === CONTADORES ===
pendentes = dados_filtrados[dados_filtrados["Tratativa Comercial"] == ""]
tratados = dados_filtrados[dados_filtrados["Tratativa Comercial"] != ""]

opcao = st.sidebar.radio(
    "Escolha a visualização:",
    (
        f"📍 Produtos sem tratativa ({len(pendentes)})",
        f"✅ Produtos com tratativa ({len(tratados)})"
    )
)

if st.sidebar.button("🔄 Atualizar dados"):
    st.cache_data.clear()
    st.rerun()

# === EXIBIÇÃO ===
dados_exibir = pendentes if "sem" in opcao else tratados
st.subheader(opcao)

for _, row in dados_exibir.iterrows():
    id_linha = str(row["IDOK"]).strip()
    loja = row["Informe a loja da ruptura"]
    produto = row["Informe o produto em ruptura"]
    codigo = row.get("Informe o código do produto em ruptura", "")
    tempo = row.get("A quanto tempo esse produto está em ruptura?", "")
    datahora = row.get("Carimbo de data/hora", "")
    tratativa_atual = row.get("Tratativa Comercial", "")

    cor_var = "var(--card-pendente)" if tratativa_atual == "" else "var(--card-tratado)"

    with st.container():
        st.markdown(
            f"""
            <div style='background-color:{cor_var}; padding:15px; border-radius:10px; margin-bottom:10px'>
            <b>🏬 Loja:</b> {loja}<br>
            <b>🧾 Produto:</b> {produto}<br>
            <b>🧾 ID:</b> {id_linha}<br>
            <b>🔢 Código:</b> {codigo or '-'}<br>
            <b>⏱ Tempo de ruptura:</b> {tempo or '-'}<br>
            <b>🕒 Data/Hora:</b> {datahora or '-'}<br>
            </div>
            """,
            unsafe_allow_html=True
        )

        nova_tratativa = st.selectbox(
            "Selecione a tratativa:",
            TRATATIVAS,
            index=TRATATIVAS.index(tratativa_atual) if tratativa_atual in TRATATIVAS else 0,
            key=f"{id_linha}_select"
        )

        if st.button("💾 Salvar", key=f"{id_linha}_btn"):
            salvar_tratativa(df, id_linha, nova_tratativa)
            st.cache_data.clear()
            st.rerun()

st.sidebar.markdown("---")
st.sidebar.info("📌 Dica: Use 'Nenhuma' para remover uma tratativa e voltar o item para pendentes.")
