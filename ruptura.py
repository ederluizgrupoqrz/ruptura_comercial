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

    # garante que temos as colunas certas
    if "Tratativa Comercial" not in header or "ID" not in header:
        st.error("Colunas 'ID' ou 'Tratativa Comercial' não encontradas na planilha.")
        return

    idx_tratativa = header.index("Tratativa Comercial")
    idx_id = header.index("ID")

    # converte o ID do formulário e da planilha em string (texto puro)
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

# === CABEÇALHO COM LOGO ===
col1, col2 = st.columns([1, 5])
with col1:
    st.image(LOGO_PATH, width=220)
with col2:
    st.title(" Sistema de Tratativas Comerciais")

df = carregar_dados()

if df.empty:
    st.error("Nenhum dado encontrado na planilha.")
    st.stop()

# === MENU PRINCIPAL ===
st.sidebar.header("Menu Principal")
compradores = sorted(df["Comprador"].dropna().unique())
comprador = st.sidebar.selectbox("👤 Selecione o comprador:", compradores)

if not comprador:
    st.info("Selecione um comprador no menu lateral.")
    st.stop()

# === FILTRAR POR COMPRADOR ===
dados_comprador = df[df["Comprador"] == comprador]

# === CONTADORES ===
pendentes = dados_comprador[dados_comprador["Tratativa Comercial"] == ""]
tratados = dados_comprador[dados_comprador["Tratativa Comercial"] != ""]

opcao = st.sidebar.radio(
    "Escolha a visualização:",
    (
        f"📍 Produtos sem tratativa ({len(pendentes)})",
        f"✅ Produtos com tratativa ({len(tratados)})"
    )
)

# === BOTÃO DE ATUALIZAR ===
if st.sidebar.button("🔄 Atualizar dados"):
    st.cache_data.clear()
    st.rerun()

# === EXIBIR PRODUTOS ===
dados_exibir = pendentes if "sem" in opcao else tratados

st.subheader(opcao)

for _, row in dados_exibir.iterrows():
    id_linha = row["ID"]
    loja = row["Informe a loja da ruptura"]
    produto = row["Informe o produto em ruptura"]
    codigo = row.get("Informe o código do produto em ruptura", "")
    tempo = row.get("A quanto tempo esse produto está em ruptura?", "")
    datahora = row.get("Carimbo de data/hora", "")
    tratativa_atual = row.get("Tratativa Comercial", "")

    # cor de fundo
    cor = "#FDECEA" if tratativa_atual == "" else "#E8F5E9"

    with st.container():
        st.markdown(
            f"""
            <div style='background-color:{cor}; padding:15px; border-radius:10px; margin-bottom:10px'>
            <b>🏬 Loja:</b> {loja}<br>
            <b>🧾 Produto:</b> {produto}<br>
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
