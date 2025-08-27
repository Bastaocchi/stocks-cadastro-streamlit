import os
import time
import streamlit as st
import pandas as pd
import yfinance as yf

from lib.db import read_tickers, upsert_ticker
from lib.strat import classify_last_two_bars

st.set_page_config(page_title="Cadastro de Ações EUA", page_icon="📈", layout="wide")
st.title("📈 Cadastro de Ações (EUA) – MVP")

# Sidebar: Formulário de cadastro
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

# Carregar lista
df_tickers = read_tickers()

# Filtros
st.subheader("🔎 Lista de Tickers")
colf1, colf2, colf3 = st.columns([2,2,1])
with colf1:
    f_sector = st.text_input("Filtrar por Setor")
with colf2:
    f_industry = st.text_input("Filtrar por Indústria")
with colf3:
    f_active = st.selectbox("Ativo?", ("Todos","Somente ativos","Somente inativos"), index=1)

f = df_tickers.copy()
if f_sector:
    f = f[f["sector"].fillna("").str.contains(f_sector, case=False, na=False)]
if f_industry:
    f = f[f["industry"].fillna("").str.contains(f_industry, case=False, na=False)]
if f_active == "Somente ativos":
    f = f[f["is_active"] == True]
elif f_active == "Somente inativos":
    f = f[f["is_active"] == False]

st.dataframe(f.sort_values("symbol"), use_container_width=True, height=320)

st.divider()

# Classificação TheStrat diária + Relatório por setor
st.subheader("📊 Classificação TheStrat (D1) e Relatório por Setor")

# Seleção de universo para cálculo (evitar chamadas excessivas)
sel = st.multiselect(
    "Selecione alguns tickers para calcular agora (deixe vazio para usar os 20 primeiros ativos)",
    options=f[f["is_active"]==True]["symbol"].tolist(),
)

universe = sel if sel else f[f["is_active"]==True]["symbol"].head(20).tolist()

@st.cache_data(ttl=3600)
def fetch_ohlc(symbol: str, period: str = "3mo") -> pd.DataFrame:
    data = yf.download(symbol, period=period, interval="1d", auto_adjust=False, progress=False)
    if data is None or data.empty:
        return pd.DataFrame()
    data = data.rename(columns={"Open":"Open","High":"High","Low":"Low","Close":"Close","Volume":"Volume"})
    return data[["Open","High","Low","Close","Volume"]]

rows = []
for sym in universe:
    try:
        ohlc = fetch_ohlc(sym)
        status = classify_last_two_bars(ohlc)
        rows.append({"symbol": sym, "the_strat": status})
    except Exception:
        rows.append({"symbol": sym, "the_strat": "—"})

df_status = pd.DataFrame(rows)

# Tabela de status
st.write("**Status diário (D1) – últimos 2 candles**")
st.dataframe(df_status, use_container_width=True, height=300)

# Relatório por setor (% 2u / % 2d)
if not f.empty:
    merged = f.merge(df_status, on="symbol", how="left")
    merged = merged[merged["is_active"] == True]
    sector_grp = merged.groupby(merged["sector"].fillna("(Sem setor)"))
    rep = sector_grp.apply(lambda g: pd.Series({
        "tickers": len(g),
        "% 2u": round((g["the_strat"] == "2u").mean()*100, 1),
        "% 2d": round((g["the_strat"] == "2d").mean()*100, 1),
    })).reset_index().rename(columns={"sector":"Setor"})
    st.write("**Relatório por setor** (considera apenas o conjunto calculado acima)")
    st.dataframe(rep.sort_values("Setor"), use_container_width=True)
else:
    st.info("Cadastre tickers para ver o relatório por setor.")

st.caption("MVP – para produção, configure uma API de mercado e Supabase.")
