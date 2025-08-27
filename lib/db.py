import os
import pandas as pd
from pathlib import Path

# === MODO ARQUIVO (padrão) ===
DATA_DIR = Path(".data")
DATA_DIR.mkdir(exist_ok=True)
CSV_PATH = DATA_DIR / "tickers.csv"

CSV_COLUMNS = ["symbol", "name", "sector", "industry", "is_active"]

def load_csv() -> pd.DataFrame:
    if CSV_PATH.exists():
        df = pd.read_csv(CSV_PATH)
        for c in CSV_COLUMNS:
            if c not in df.columns:
                df[c] = None
        df = df[CSV_COLUMNS]
    else:
        df = pd.DataFrame(columns=CSV_COLUMNS)
    if not df.empty:
        df["symbol"] = df["symbol"].astype(str).str.upper().str.strip()
        if "is_active" in df:
            df["is_active"] = df["is_active"].fillna(True).astype(bool)
    return df

def save_csv(df: pd.DataFrame) -> None:
    df.to_csv(CSV_PATH, index=False)

# === SUPABASE (opcional) ===
_supabase_client = None

def get_supabase_client():
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client
    try:
        from supabase import create_client
        import streamlit as st
        url = st.secrets.get("supabase_url")
        key = st.secrets.get("supabase_key")
        if url and key:
            _supabase_client = create_client(url, key)
            return _supabase_client
    except Exception:
        pass
    return None

def read_tickers() -> pd.DataFrame:
    sb = get_supabase_client()
    if sb:
        table = os.environ.get("SUPABASE_TABLE", "tickers")
        res = sb.table(table).select("symbol,name,sector,industry,is_active").execute()
        data = res.data or []
        df = pd.DataFrame(data, columns=["symbol","name","sector","industry","is_active"])
        if not df.empty:
            df["symbol"] = df["symbol"].astype(str).str.upper().str.strip()
            df["is_active"] = df["is_active"].fillna(True).astype(bool)
        return df
    return load_csv()

def upsert_ticker(symbol: str, name: str = "", sector: str = "", industry: str = "", is_active: bool = True) -> None:
    symbol = (symbol or "").upper().strip()
    if not symbol:
        return
    sb = get_supabase_client()
    if sb:
        table = os.environ.get("SUPABASE_TABLE", "tickers")
        payload = {
            "symbol": symbol,
            "name": name,
            "sector": sector,
            "industry": industry,
            "is_active": is_active,
        }
        sb.table(table).upsert(payload, on_conflict="symbol").execute()
    else:
        df = load_csv()
        if symbol in df["symbol"].values:
            df.loc[df["symbol"] == symbol, ["name","sector","industry","is_active"]] = [name, sector, industry, is_active]
        else:
            df = pd.concat([df, pd.DataFrame([{
                "symbol":symbol, "name":name, "sector":sector, "industry":industry, "is_active":is_active
            }])], ignore_index=True)
        save_csv(df)
def delete_ticker(symbol: str) -> None:
    symbol = (symbol or "").upper().strip()
    if not symbol:
        return
    sb = get_supabase_client()
    if sb:
        table = os.environ.get("SUPABASE_TABLE", "tickers")
        sb.table(table).delete().eq("symbol", symbol).execute()
    else:
        df = load_csv()
        df = df[df["symbol"] != symbol]
        save_csv(df)
