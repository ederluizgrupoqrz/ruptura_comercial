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
    "Nenhuma",  # para permitir remover a tratativa
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

# === CSS PARA TEMA ESCURO / CLARO ===
st.markdown("""
<style>
[data-testid="stSidebar"] {
    background-color: var(--background-color);
    color: var(--text-color);
}
:root {
    --background-color: white;
    --text-color: black;
}
@media (prefers-color-scheme: dark) {
    :root {
        --background-color: #0E1117;
        --text-color: white;
    }
    [data-testid="stSidebar"], [data-testid="stAppViewContainer"] {
        background-color: #0E1117 !important;
        color: white !important;
    }
    h1, h2, h3, h4, h5, h6, p, label, div, span {
        color: white !important;
    }
    .stSelectbox, .stButton, .stRadio, .stDateInput {
        color: white !important;
    }
}
</style>
""", unsafe_allow_html=True)

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
    return pd.DataFrame(dados)

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
compradores = sorted(df["Comprador"].dropna().unique())
comprador = st.sidebar.selectbox("👤 Selecione o comprador:", compradores)

# === FILTRO DE DATA ===
st.sidebar.markdown("### 📅 Filtro de Data")

# Converte a coluna de data
df["Carimbo de data/hora"] = pd.to_datetime(df["Carimbo de data/hora"], errors="coerce", format="%d/%m/%Y %H:%M:%S")

data_min = df["Carimbo de data/hora"].min().date() if not df.empty else datetime.today().date()
data_max = df["Carimbo de data/hora"].max().date() if not df.empty else datetime.today().date()

col_data1, col_data2 = st.sidebar.columns(2)
data_inicio = col_data1.date_input("Início", data_min)
data_fim = col_data2.date_input("Fim", data_max)

if data_inicio > data_fim:
    st.sidebar.error("⚠️ A data inicial não pode ser maior que a final.")
    st.stop()

# === BOTÃO DE ATUALIZAR ===
if st.sidebar.button("🔄 Atualizar dados"):
    st.cache_data.clear()
    st.rerun()

# === FILTROS PRINCIPAIS ===
if not comprador:
    st.info("Selecione um comprador no menu lateral.")
    st.stop()

dados_filtrados = df[
    (df["Comprador"] == comprador) &
    (df["Carimbo de data/hora"].dt.date >= data_inicio) &
    (df["Carimbo de data/hora"].dt.date <= data_fim)
]

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

# === EXIBIR PRODUTOS ===
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

    cor = "#FDECEA" if tratativa_atual == "" else "#E8F5E9"

    with st.container():
        st.markdown(
            f"""
            <div style='background-color:{cor}; padding:15px; border-radius:10px; margin-bottom:10px'>
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
