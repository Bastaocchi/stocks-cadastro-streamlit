import pandas as pd

# Classificação TheStrat para a ÚLTIMA barra diária usando a barra anterior
# 1 = inside; 2u = rompe máxima anterior sem romper mínima; 
# 2d = rompe mínima sem romper máxima; 3 = rompe ambas

def classify_last_two_bars(df: pd.DataFrame) -> str:
    """
    Exige DataFrame com colunas: ["Open","High","Low","Close"], indexado por data crescente.
    Retorna uma das strings: "1", "2u", "2d", "3".
    """
    if df is None or df.empty or len(df) < 2:
        return "—"
    last = df.iloc[-1]
    prev = df.iloc[-2]
    broke_high = last["High"] > prev["High"]
    broke_low = last["Low"] < prev["Low"]
    inside = (last["High"] < prev["High"]) and (last["Low"] > prev["Low"])
    if inside:
        return "1"
    if broke_high and broke_low:
        return "3"
    if broke_high and not broke_low:
        return "2u"
    if broke_low and not broke_high:
        return "2d"
    return "—"
