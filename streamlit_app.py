import os
import time
import pandas as pd
import yfinance as yf
import streamlit as st

# ==========================================
# Config inicial
# ==========================================
st.set_page_config(page_title="Scanner TheStrat", page_icon="📊", layout="wide")
st.title("📊 Scanner TheStrat – Estilo Dashboard")

# ==========================================
# Carregar base oficial
# ==========================================
@st.cache_data
def load_data():
    df = pd.read_csv("data/simbolos700.csv")  # caminho fixo
    if "Sub_Group" not in df.columns:
        df["Sub_Group"] = ""  # garante coluna extra
    return df

df_master = load_data()

# ==========================================
# Funções de candle
# ==========================================
def candle_type(prev, curr):
    prev_high, prev_low = float(prev["High"]), float(prev["Low"])
    curr_high, curr_low = float(curr["High"]), float(curr["Low"])
    if curr_high <= prev_high and curr_low >= prev_low:
        return "1"
    elif curr_high >= prev_high and curr_low <= prev_low:
        return "3"
    elif curr_high > prev_high:
        return "2u"
    elif curr_low < prev_low:
        return "2d"
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

# Filtrar
filtered = df_master.copy()
if etf: filtered = filtered[filtered["ETF_Symbol"] == etf]
if industry: filtered = filtered[filtered["TradingView_Industry"] == industry]
if sub_group: filtered = filtered[filtered["Sub_Group"] == sub_group]
if search_symbol: filtered = filtered[filtered["Symbol"].str.contains(search_symbol)]

st.markdown(f"**Total de símbolos filtrados:** {len(filtered)}")

# ==========================================
# Classificação TheStrat (limitada para não travar)
# ==========================================
rows = []
subset = filtered.head(50)  # limite inicial p/ performance
for sym in subset["Symbol"].tolist():
    try:
        pair = classify_pair(sym)
        rows.append({
            "Symbol": sym,
            "Daily": pair["Daily"],
            "Weekly": pair["Weekly"],
            "Sector": filtered.loc[filtered["Symbol"]==sym,"Sector_SPDR"].values[0],
            "Industry": filtered.loc[filtered["Symbol"]==sym,"TradingView_Industry"].values[0],
            "Sub_Group": filtered.loc[filtered["Symbol"]==sym,"Sub_Group"].values[0]
        })
    except Exception:
        rows.append({"Symbol": sym, "Daily":"—", "Weekly":"—"})

df_status = pd.DataFrame(rows)

# ==========================================
# Coloração estilo Pure Alpha
# ==========================================
def highlight(val):
    if not isinstance(val, str): return ""
    atual = val.split("/")[-1] if "/" in val else val
    if atual == "2u": return "background-color: limegreen; color:black; font-weight:bold;"
    if atual == "2d": return "background-color: crimson; color:white; font-weight:bold;"
    if atual == "3": return "background-color: orange; color:white; font-weight:bold;"
    if atual == "1": return "background-color: mediumslateblue; color:white; font-weight:bold;"
    return ""

st.dataframe(df_status.style.applymap(highlight, subset=["Daily","Weekly"]),
             use_container_width=True, height=600)

# ==========================================
# Resumo setorial (% 2u / 2d)
# ==========================================
st.subheader("📊 Resumo por Setor")

summary = []
for sector in df_master["Sector_SPDR"].unique():
    subset = df_status[df_status["Sector"] == sector]
    if len(subset) == 0: continue
    total = len(subset)
    count_2u = sum(subset["Daily"].str.endswith("2u"))
    count_2d = sum(subset["Daily"].str.endswith("2d"))
    summary.append({
        "Sector": sector,
        "Total": total,
        "%2u": round(count_2u/total*100,1),
        "%2d": round(count_2d/total*100,1),
    })

df_summary = pd.DataFrame(summary)

cols = st.columns(len(df_summary))
for i, row in df_summary.iterrows():
    with cols[i]:
        st.metric(label=row["Sector"],
                  value=f"2u {row['%2u']}% | 2d {row['%2d']}%",
                  delta=f"Total {row['Total']}")

# ==========================================
# Editor Sub_Group
# ==========================================
st.subheader("✏️ Editar Sub-Grupo")
edit_symbol = st.selectbox("Escolha um símbolo", df_master["Symbol"].tolist())
new_group = st.text_input("Novo Sub-Grupo", "")
if st.button("Salvar Sub-Grupo"):
    df_master.loc[df_master["Symbol"] == edit_symbol, "Sub_Group"] = new_group
    df_master.to_csv("data/simbolos700.csv", index=False)
    st.success(f"Sub-Grupo '{new_group}' salvo para {edit_symbol}")
    time.sleep(0.7)
    st.rerun()
