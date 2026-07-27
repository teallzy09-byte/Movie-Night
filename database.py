import hashlib
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

# Initialize global GSheets connection
conn = st.connection("gsheets", type=GSheetsConnection)

def hash_password(password):
    """Encrypts passwords using SHA-256."""
    return hashlib.sha256(str.encode(password)).hexdigest()

def load_table(sheet_name, fallback_cols):
    """Loads a specific worksheet tab safely, cleaning up data formats."""
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        if not df.empty:
            for col in df.columns:
                df[col] = df[col].astype(str).str.strip()
        return df
    except Exception:
        return pd.DataFrame(columns=fallback_cols)

def save_table(sheet_name, df):
    """Pushes a modified dataframe back up to the specific cloud sheet partition."""
    conn.update(worksheet=sheet_name, data=df)
