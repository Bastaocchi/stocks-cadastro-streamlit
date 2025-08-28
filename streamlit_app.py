import streamlit as st
import pandas as pd
import yfinance as yf
import time

# ==========================================
# Configuração inicial
# ==========================================
st.set_page_config(page_title="Scanner TheStrat", page_icon="📈", layout="wide")
st.title("📈 Scanner TheStrat – Base 700 Símbolos")

# ==========================================
# Carregar base oficial CSV
# ==========================================
@st.cache_data
def load_data():
    df = pd.read_csv("simbolos700.csv")
    if "Sub_Group" not in df.columns:
        df["Sub_Group"] = ""  # coluna livre
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
# Filtros
# ==========================================
st.sidebar.header("Filtros")
etf = st.sidebar.selectbox("🎯 ETF (XLK, XLY...)", [""] + sorted(df_master["ETF_Symbol"].unique()))
industry = st.sidebar.selectbox("🏭 Indústria", [""] + sorted(df_master["TradingView_Industry"].unique()))
sub_group = st.sidebar.selectbox("🔖 Sub-Grupo", [""] + sorted(df_master["Sub_Group"].dropna().unique()))

filtered = df_master.copy()
if etf: filtered = filtered[filtered["ETF_Symbol"] == etf]
if industry: filtered = filtered[filtered["TradingView_Industry"] == industry]
if sub_group: filtered = filtered[filtered["Sub_Group"] == sub_group]

st.write(f"### 🎯 Total de símbolos filtrados: {len(filtered)}")

# ==========================================
# Classificação TheStrat para subset
# ==========================================
rows = []
subset = filtered.head(50)  # limite inicial p/ não travar
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
# Coloração estilo Excel
# ==========================================
def highlight(val):
    if not isinstance(val, str): return ""
    atual = val.split("/")[-1] if "/" in val else val
    if atual == "2u": return "background-color: lightgreen; color:black;"
    if atual == "2d": return "background-color: tomato; color:black;"
    if atual == "3": return "background-color: orange; color:white;"
    if atual == "1": return "background-color: violet; color:white;"
    return ""

st.dataframe(df_status.style.applymap(highlight, subset=["Daily","Weekly"]),
             use_container_width=True, height=600)

# ==========================================
# Editor Sub_Group
# ==========================================
st.subheader("✏️ Editar Sub-Grupo")
edit_symbol = st.selectbox("Escolha um símbolo", df_master["Symbol"].tolist())
new_group = st.text_input("Novo Sub-Grupo", "")
if st.button("Salvar Sub-Grupo"):
    df_master.loc[df_master["Symbol"] == edit_symbol, "Sub_Group"] = new_group
    df_master.to_csv("simbolos700.csv", index=False)
    st.success(f"Sub-Grupo '{new_group}' salvo para {edit_symbol}")
    time.sleep(0.7)
    st.rerun()
