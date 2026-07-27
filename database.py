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
        df = conn.read(worksheet=sheet_name, ttl=2)
        if not df.empty:
            for col in df.columns:
                df[col] = df[col].astype(str).str.strip()
        return df
    except Exception:
        return pd.DataFrame(columns=fallback_cols)

def save_table(sheet_name, df):
    """Pushes a modified dataframe back up to the specific cloud sheet partition."""
    conn.update(worksheet=sheet_name, data=df)

def append_review_atomic(movie_id, username, rating, comment):
    """Safely appends a single personal review row without overwriting other users."""
    # 1. Load the live table with no cache to get the absolute newest state
    review_df = conn.read(worksheet="Reviews", ttl=0)
    
    # 2. Strip out ONLY this specific user's old review for this specific movie
    review_df = review_df[~((review_df["MovieID"].astype(str) == str(movie_id)) & 
                            (review_df["Username"].astype(str) == str(username)))]
    
    # 3. Create the clean updated single row entry
    new_row = pd.DataFrame([{"MovieID": str(movie_id), "Username": str(username), "Rating": str(rating), "Comment": str(comment).strip()}])
    
    # 4. Merge and push back up instantly
    final_df = pd.concat([review_df, new_row], ignore_index=True)
    conn.update(worksheet="Reviews", data=final_df)

def update_movie_status_atomic(movie_id, new_status, new_date, new_picker):
    """Safely updates a single movie's status criteria across concurrent users."""
    movie_df = conn.read(worksheet="Movies", ttl=0)
    
    # Find the target index row matching this film choice ID
    target_mask = movie_df["MovieID"].astype(str) == str(movie_id)
    
    if target_mask.any():
        movie_df.loc[target_mask, "Status"] = str(new_status)
        movie_df.loc[target_mask, "DateWatched"] = str(new_date)
        movie_df.loc[target_mask, "Picker"] = str(new_picker)
        conn.update(worksheet="Movies", data=movie_df)

