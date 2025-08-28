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
                         progress=False, auto_adjust=True)
        if len(df) < 3:
            out[tf_name] = "N/A"
            continue
        tipo_ultima = candle_type(df.iloc[-2], df.iloc[-1])
        tipo_anterior = candle_type(df.iloc[-3], df.iloc[-2])
        out[tf_name] = f"{tipo_anterior}/{tipo_ultima}"
    return out

# ==========================================
# Barra lateral - configs
# ==========================================
st.sidebar.header("⚙️ Configurações")
update_limit = st.sidebar.slider("Qtd. símbolos para atualizar", 5, 200, 20)

# Criar abas
tab1, tab2 = st.tabs(["📋 Scanner", "📊 Relatório por Setor"])

# ==========================================
# TAB 1 - SCANNER
# ==========================================
with tab1:
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

    # ==== Filtros ====
    col1, col2, col3, col4 = st.columns([2,2,2,2])
    with col1:
        etf = st.selectbox("🎯 ETF", [""] + sorted(df_master["ETF_Symbol"].dropna().unique()))
    with col2:
        industry = st.selectbox("🏭 Indústria", [""] + sorted(df_master["TradingView_Industry"].dropna().unique()))
    with col3:
        sub_group = st.selectbox("🔖 Sub-Grupo", [""] + sorted(df_master["Sub_Group"].dropna().unique()))
    with col4:
        search_symbol = st.text_input("🔍 Buscar símbolo").upper().strip()

    filtered = df_master.copy()
    if etf: filtered = filtered[filtered["ETF_Symbol"] == etf]
    if industry: filtered = filtered[filtered["TradingView_Industry"] == industry]
    if sub_group: filtered = filtered[filtered["Sub_Group"] == sub_group]
    if search_symbol: filtered = filtered[filtered["Symbol"].str.contains(search_symbol)]

    # ==== Filtros Daily/Weekly (corrigidos) ====
    colA, colB = st.columns(2)
    with colA:
        daily_filter = st.selectbox("📅 Filtro Daily", [""] + sorted(filtered["Daily"].dropna().unique()))
    with colB:
        weekly_filter = st.selectbox("📅 Filtro Weekly", [""] + sorted(filtered["Weekly"].dropna().unique()))

    if daily_filter:
        filtered = filtered[filtered["Daily"].astype(str).str.contains(daily_filter, na=False)]
    if weekly_filter:
        filtered = filtered[filtered["Weekly"].astype(str).str.contains(weekly_filter, na=False)]

    st.markdown(f"**🔎 Símbolos após filtros: {len(filtered)}**")

    # ==== Coloração ====
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

# ==========================================
# TAB 2 - RELATÓRIO POR SETOR
# ==========================================
with tab2:
    st.subheader("📊 Relatório por Setor")

    def make_report(df, col_name, title):
        df_rel = df.copy()
        df_rel["Atual"] = df_rel[col_name].astype(str).apply(lambda x: x.split("/")[-1] if "/" in x else x)

        resumo = df_rel.groupby("Sector_SPDR")["Atual"].value_counts(normalize=True).unstack(fill_value=0) * 100
        resumo["Total Tickers"] = df_rel.groupby("Sector_SPDR")["Symbol"].count()
        resumo = resumo.round(1)

        # garantir colunas
        for col in ["2u", "2d"]:
            if col not in resumo.columns:
                resumo[col] = 0

        # função cor
        def color_pct(val, label):
            if label == "2u" and val >= 50:
                return "background-color: darkgreen; color:white; font-weight:bold;"
            if label == "2d" and val >= 50:
                return "background-color: darkred; color:white; font-weight:bold;"
            return ""

        styled = resumo.style.applymap(lambda v: color_pct(v, "2u"), subset=["2u"]) \
                             .applymap(lambda v: color_pct(v, "2d"), subset=["2d"])

        st.markdown(f"### {title}")
        st.dataframe(styled, use_container_width=True, height=500)

    colL, colR = st.columns(2)
    with colL:
        make_report(df_master, "Daily", "📅 Daily")
    with colR:
        make_report(df_master, "Weekly", "📅 Weekly")
