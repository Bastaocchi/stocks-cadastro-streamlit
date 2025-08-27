import os
import time
import streamlit as st
import pandas as pd
import yfinance as yf

from lib.db import read_tickers, upsert_ticker, delete_ticker

st.set_page_config(page_title="Cadastro de Ações EUA", page_icon="📈", layout="wide")
st.title("📈 Cadastro de Ações (EUA) – TheStrat Classificação")

# ==========================================
# Funções de classificação
# ==========================================
def candle_type(prev, curr):
    prev_high = float(prev['High'])
    prev_low  = float(prev['Low'])
    curr_high = float(curr['High'])
    curr_low  = float(curr['Low'])
    if curr_high <= prev_high and curr_low >= prev_low:
        return "1"
    elif curr_high >= prev_high and curr_low <= prev_low:
        return "3"
    elif curr_high > prev_high:
        return "2u"
    elif curr_low < prev_low:
        return "2d"
    else:
        return "2"

def classify_pair(symbol):
    out = {}
    for tf_name, tf_interval in {"Daily": "1d", "Weekly": "1wk"}.items():
        df = yf.download(symbol, period="1y", interval=tf_interval,
                         progress=False, auto_adjust=True)
        if len(df) < 3:
            out[tf_name] = "N/A"
            continue
        tipo_ultima = candle_type(df.iloc[-2], df.iloc[-1])
        tipo_anterior = candle_type(df.iloc[-3], df.iloc[-2])
        out[tf_name] = f"{tipo_anterior}/{tipo_ultima}"
    return out

# ==========================================
# Sidebar: cadastro de tickers
# ==========================================
with st.sidebar:
    st.header("Cadastrar/Editar Ticker")
    with st.form("cadastro"):
        symbol = st.text_input("Símbolo (ex.: AAPL, MSFT)").upper().strip()
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Nome", placeholder="Apple Inc.")
            sector = st.text_input("Setor", placeholder="Technology")
        with col2:
            industry = st.text_input("Indústria", placeholder="Consumer Electronics")
            is_active = st.checkbox("Ativo", value=True)
        submitted = st.form_submit_button("Salvar/Atualizar")
    if submitted and symbol:
        upsert_ticker(symbol, name, sector, industry, is_active)
        st.success(f"Ticker {symbol} salvo!")
        time.sleep(0.7)
        st.rerun()

    # --------------------------------------
    # Cadastro em Massa
    # --------------------------------------
    st.markdown("---")
    st.header("📋 Cadastro em Massa")

    bulk_input = st.text_area("Cole tickers (um por linha ou separados por vírgula)")
    default_sector = st.text_input("Setor padrão (opcional)", "")
    default_industry = st.text_input("Indústria padrão (opcional)", "")

    if st.button("Cadastrar lista"):
        tickers_bulk = [t.strip().upper() for t in bulk_input.replace(",", "\n").splitlines() if t.strip()]
        if tickers_bulk:
            for t in tickers_bulk:
                upsert_ticker(t, sector=default_sector, industry=default_industry, is_active=True)
            st.success(f"{len(tickers_bulk)} tickers cadastrados!")
            time.sleep(0.7)
            st.rerun()
        else:
            st.warning("Nenhum ticker válido informado.")

# ==========================================
# Carregar lista de tickers cadastrados
# ==========================================
df_tickers = read_tickers()

st.subheader("🔎 Lista de Tickers")
st.dataframe(df_tickers.sort_values("symbol"), use_container_width=True, height=250)

# ==========================================
# Opção de apagar ticker
# ==========================================
if not df_tickers.empty:
    st.subheader("🗑️ Remover Ticker")
    to_delete = st.selectbox("Escolha um ticker para apagar",
                             options=df_tickers["symbol"].tolist())
    if st.button("Apagar ticker selecionado"):
        delete_ticker(to_delete)
        st.success(f"Ticker {to_delete} removido!")
        time.sleep(0.7)
        st.rerun()

st.divider()

# ==========================================
# Classificação TheStrat Daily + Weekly
# ==========================================
st.subheader("📊 Classificação TheStrat (Daily + Weekly)")

sel = st.multiselect(
    "Selecione alguns tickers (ou deixe vazio para usar os 20 primeiros ativos)",
    options=df_tickers[df_tickers["is_active"]==True]["symbol"].tolist(),
)

universe = sel if sel else df_tickers[df_tickers["is_active"]==True]["symbol"].head(20).tolist()

rows = []
for sym in universe:
    try:
        pair = classify_pair(sym)
        rows.append({"Ticker": sym, "Daily": pair["Daily"], "Weekly": pair["Weekly"]})
    except Exception:
        rows.append({"Ticker": sym, "Daily": "—", "Weekly": "—"})

df_status = pd.DataFrame(rows)

# Garante que as colunas existam
for col in ["Daily", "Weekly"]:
    if col not in df_status.columns:
        df_status[col] = "—"

# ==========================================
# Coloração estilo Excel
# ==========================================
def highlight(val):
    if not isinstance(val, str): return ""
    if "/" in val:
        atual = val.split("/")[1]
    else:
        atual = val
    if atual == "2u": return "background-color: lightgreen; color:black;"
    if atual == "2d": return "background-color: tomato; color:black;"
    if atual == "3": return "background-color: orange; color:white;"
    if atual == "1": return "background-color: violet; color:white;"
    return ""

st.write("**Classificação (anterior/atual)**")
if {"Daily","Weekly"}.issubset(df_status.columns):
    st.dataframe(
        df_status.style.applymap(highlight, subset=["Daily","Weekly"]),
        use_container_width=True, height=400
    )
else:
    st.dataframe(df_status, use_container_width=True, height=400)

st.caption("Versão MVP com cadastro individual + em massa, edição, exclusão e classificação Daily/Weekly.")
