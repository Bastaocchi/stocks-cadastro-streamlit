import os
import streamlit as st
import pandas as pd

# ==========================================
# Carregar base oficial CSV
# ==========================================
@st.cache_data
def load_data():
    path1 = "data/simbolos700.csv"   # opção preferida (pasta data/)
    path2 = "simbolos700.csv"        # fallback (raiz do projeto)

    if os.path.exists(path1):
        df = pd.read_csv(path1)
    elif os.path.exists(path2):
        df = pd.read_csv(path2)
    else:
        st.error("⚠️ Arquivo `simbolos700.csv` não encontrado no repositório. "
                 "Suba o arquivo em `data/` ou na raiz do projeto no GitHub.")
        st.stop()

    # Garante a coluna Sub_Group
    if "Sub_Group" not in df.columns:
        df["Sub_Group"] = ""

    return df

df_master = load_data()
