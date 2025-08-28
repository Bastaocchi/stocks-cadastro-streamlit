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
def load_data():
    df = pd.read_csv("data/simbolos700.csv")
    if "Sub_Group" not in df.columns:
        df["Sub_Group"] = ""  # garante coluna extra
    if "Daily" not in df.columns:
        df["Daily"] = ""
    if "Weekly" not in df.columns:
        df["Weekly"] = ""
    return df

df_master = load_data()

# ==========================================
# Função de classificação TheStrat
# ==========================================
def candle_type(prev, curr):
    prev_high, prev_low = float(prev["High"]), float(prev["Low"])
    curr_high, curr_low = float(curr["High"]), float(curr["Low"])

    # Inside bar
    if curr_high <= prev_high and curr_low >= prev_low:
        return "1"
    # Outside bar
    if curr_high >= prev_high and curr_low <= prev_low:
        return "3"
    # 2u: rompeu apenas a máxima
    if curr_high > prev_high and curr_low >= prev_low:
        return "2u"
    # 2d: rompeu apenas a mínima
    if curr_low < prev_low and curr_high <= prev_high:
        return "2d"
    return "2"

def classify_pair(symbol):
    out = {}
    for tf_name, tf_interval in {"Daily":"1d", "Weekly":"1wk"}.items():
        df = yf.download(symbol, period="1y", interval=tf_interval,
                         progress=False, auto_adjust=False)
        if len(df) < 4:
            out[tf_name] = "N/A"
            continue
        # pega os dois últimos fechados (ignora candle em formação)
        tipo_ultima = candle_type(df.iloc[-3], df.iloc[-2])
        tipo_anterior = candle_type(df.iloc[-4], df.iloc[-3])
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

        # Atualiza barra
        progress.progress((i+1)/total)

    # Salva resultados
    df_master.to_csv("data/simbolos700.csv", index=False)
    st.success(f"✅ Dados atualizados e salvos no CSV ({update_limit} símbolos)!")
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

# Aplicar filtros
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

st.dataframe(filtered[["Symbol","Daily","Weekly","Sector_SPDR","TradingView_Industry","Sub_Group"]]
             .style.applymap(highlight, subset=["Daily","Weekly"]),
             use_container_width=True, height=600)

# ==========================================
# Resumo setorial (% 2u / 2d)
# ==========================================
st.subheader("📊 Resumo por Setor")

summary = []
for sector in df_master["Sector_SPDR"].unique():
    subset_sec = filtered[filtered["Sector_SPDR"] == sector]
    if len(subset_sec) == 0: continue
    total = len(subset_sec)
    count_2u = sum(subset_sec["Daily"].str.endswith("2u"))
    count_2d = sum(subset_sec["Daily"].str.endswith("2d"))
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
