import os
import time
import pandas as pd
import yfinance as yf
import streamlit as st

# ==========================================
# Config inicial
# ==========================================
st.set_page_config(page_title="Scanner TheStrat", page_icon="📊", layout="wide")
st.title("📊 Scanner TheStrat – Lógica Colab")

# ==========================================
# Carregar base oficial
# ==========================================
def load_data():
    df = pd.read_csv("data/simbolos700.csv")
    if "Sub_Group" not in df.columns:
        df["Sub_Group"] = ""
    if "Daily" not in df.columns:
        df["Daily"] = ""
    if "Weekly" not in df.columns:
        df["Weekly"] = ""
    return df

df_master = load_data()

# ==========================================
# Função candle_type (igual Colab)
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
    for tf_name, tf_interval in {"Daily":"1d", "Weekly":"1wk"}.items():
        df = yf.download(symbol, period="1y", interval=tf_interval,
                         progress=False, auto_adjust=True)  # ⚠️ igual Colab
        if len(df) < 3:
            out[tf_name] = "N/A"
            continue
        tipo_ultima = candle_type(df.iloc[-2], df.iloc[-1])       # última comparação
        tipo_anterior = candle_type(df.iloc[-3], df.iloc[-2])     # anterior
        out[tf_name] = f"{tipo_anterior}/{tipo_ultima}"
    return out

# ==========================================
# Slider para controlar quantos símbolos atualizar
# ==========================================
st.sidebar.header("⚙️ Configurações")
update_limit = st.sidebar.slider("Qtd. símbolos para atualizar", 5, 200, 20)

# ==========================================
# Botão de atualização com barra de progresso
# ==========================================
if st.button("🔄 Atualizar dados"):
    st.info(f"⏳ Atualizando {update_limit} símbolos, aguarde...")
    progress = st.progress(0)
    total = min(update_limit, len(df_master))

    for i, sym in enumerate(df_master["Symbol"].tolist()[:update_limit]):
        try:
            pair = classify_pair(sym)
            df_master.loc[df_master["Symbol"] == sym, "Daily"] = pair["Daily"]
            df_master.loc[df_master["Symbol"] == sym, "Weekly"] = pair["Weekly"]
        except Exception:
            df_master.loc[df_master["Symbol"] == sym, "Daily"] = "—"
            df_master.loc[df_master["Symbol"] == sym, "Weekly"] = "—"

        progress.progress((i+1)/total)

    df_master.to_csv("data/simbolos700.csv", index=False)
    st.success(f"✅ Dados atualizados ({update_limit} símbolos)!")
    time.sleep(0.7)
    st.rerun()

# ==========================================
# Filtros no TOPO
# ==========================================
col1, col2, col3, col4 = st.columns([2,2,2,2])
with col1:
    etf = st.selectbox("🎯 ETF", [""] + sorted(df_master["ETF_Symbol"].unique()))
with col2:
    industry = st.selectbox("🏭 Indústria", [""] + sorted(df_master["TradingView_Industry"].unique()))
with col3:
    sub_group = st.selectbox("🔖 Sub-Grupo", [""] + sorted(df_master["Sub_Group"].dropna().unique()))
with col4:
    search_symbol = st.text_input("🔍 Buscar símbolo").upper().strip()

filtered = df_master.copy()
if etf: filtered = filtered[filtered["ETF_Symbol"] == etf]
if industry: filtered = filtered[filtered["TradingView_Industry"] == industry]
if sub_group: filtered = filtered[filtered["Sub_Group"] == sub_group]
if search_symbol: filtered = filtered[filtered["Symbol"].str.contains(search_symbol)]

# ==========================================
# Filtros de padrão (Daily / Weekly)
# ==========================================
colA, colB = st.columns(2)
with colA:
    daily_filter = st.selectbox("📅 Filtro Daily", [""] + sorted(filtered["Daily"].dropna().unique()))
with colB:
    weekly_filter = st.selectbox("📅 Filtro Weekly", [""] + sorted(filtered["Weekly"].dropna().unique()))

if daily_filter:
    filtered = filtered[filtered["Daily"].str.contains(daily_filter)]
if weekly_filter:
    filtered = filtered[filtered["Weekly"].str.contains(weekly_filter)]

st.markdown(f"**🔎 Símbolos após filtros: {len(filtered)}**")

# ==========================================
# Coloração estilo Colab (Pure Alpha)
# ==========================================
def highlight(val):
    if not isinstance(val, str): return ""
    atual = val.split("/")[-1] if "/" in val else val
    if atual == "2u": return "background-color: limegreen; color:black; font-weight:bold;"
    if atual == "2d": return "background-color: crimson; color:white; font-weight:bold;"
    if atual == "3": return "background-color: orange; color:white; font-weight:bold;"
    if atual == "1": return "background-color: mediumslateblue; color:white; font-weight:bold;"
    return ""

st.dataframe(filtered[["Symbol","Daily","Weekly","Sector_SPDR","TradingView_Industry","Sub_Group"]]
             .style.applymap(highlight, subset=["Daily","Weekly"]),
             use_container_width=True, height=600)
