with tab2:
    st.subheader("📊 Relatório por Setor (Daily)")

    df_rel = df_master.copy()
    df_rel["Atual"] = df_rel["Daily"].astype(str).apply(lambda x: x.split("/")[-1] if "/" in x else x)

    # Agrupar por setor
    resumo = df_rel.groupby("Sector_SPDR")["Atual"].value_counts(normalize=True).unstack(fill_value=0) * 100
    resumo["Total Tickers"] = df_rel.groupby("Sector_SPDR")["Symbol"].count()
    resumo = resumo.round(1)

    # ✅ Garantir que colunas 2u e 2d existem
    for col in ["2u", "2d"]:
        if col not in resumo.columns:
            resumo[col] = 0

    # Função para destacar >=50%
    def color_pct(val, label):
        if label == "2u" and val >= 50:
            return "background-color: darkgreen; color:white; font-weight:bold;"
        if label == "2d" and val >= 50:
            return "background-color: darkred; color:white; font-weight:bold;"
        return ""

    styled = resumo.style.applymap(lambda v: color_pct(v, "2u"), subset=["2u"]) \
                         .applymap(lambda v: color_pct(v, "2d"), subset=["2d"])

    st.dataframe(styled, use_container_width=True, height=600)
