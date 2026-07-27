import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import requests

# ----------------------------------------------------
# 1. INITIAL API CONFIG & THEME TUNING
# ----------------------------------------------------
OMDB_API_KEY = "43ac7081" 

st.set_page_config(page_title="Movie Night", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS directly injected to build clean, independent card modules
st.markdown("""
<style>
    /* Top horizontal navigation filter row */
    .filter-bar { display: flex; gap: 10px; margin-bottom: 25px; overflow-x: auto; }
    .filter-btn { background:#edf2f7; color:#4a5568; padding:6px 14px; border-radius:20px; font-size:13px; font-weight:500; }
    .filter-btn.active { background:#3182ce; color:white; }
    
    /* Movie Card layout frame styling */
    .movie-card {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 14px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        border: 1px solid #e2e8f0;
        margin-bottom: 12px;
        text-align: left;
    }
    .movie-poster { 
        width: 100%; 
        border-radius: 8px; 
        object-fit: cover; 
        aspect-ratio: 2/3; 
        margin-bottom: 12px; 
    }
    .movie-title { font-weight: 700; font-size: 1.2rem; color: #1a202c; margin-bottom: 4px; }
    .movie-meta { font-size: 0.85rem; color: #718096; margin-bottom: 12px; }
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------
# 2. STARTUP OMDb HEALTH CHECK
# ----------------------------------------------------
@st.cache_resource(ttl=3600)
def verify_omdb_connection(api_key):
    """Pings OMDb backend once on startup to ensure API and network routes work."""
    test_url = f"https://omdbapi.com{api_key}"
    try:
        response = requests.get(test_url, timeout=4)
        if response.status_code == 200 and response.json().get("Response") == "True":
            return True, "Connected"
        return False, f"OMDb API Error: {response.json().get('Error', 'Invalid configuration.')}"
    except Exception as e:
        return False, f"Network Failure: {str(e)}"

omdb_healthy, omdb_msg = verify_omdb_connection(OMDB_API_KEY)


# ----------------------------------------------------
# 3. DATABASE MANAGEMENT
# ----------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    existing_data = conn.read(ttl=0)
    # Safely clean trailing whitespace from key identification fields
    if not existing_data.empty:
        existing_data["Title"] = existing_data["Title"].astype(str).str.strip()
except Exception:
    existing_data = pd.DataFrame(columns=["Title", "Poster", "Status", "Rating", "Year"])

def save_data(df):
    conn.update(data=df)
    st.rerun()

# ----------------------------------------------------
# 4. MODAL POPUP: OMDb MOVIE SEARCH
# ----------------------------------------------------
@st.dialog("🎬 Add Item to Watchlist")
def add_item_dialog():
    st.write("Type a title below to fetch live, structured movie details from OMDb:")
    search_query = st.text_input("Search Movie Title", key="omdb_search_bar", placeholder="e.g. Primer, Barbarian...")
    
    if search_query.strip():
        # FIXED: Added the required 'www.', '?', and 's=' search query structures
        search_url = f"https://omdbapi.com{search_query.strip()}&apikey={OMDB_API_KEY}"
        
        try:
            response = requests.get(search_url, timeout=5).json()
            
            if response.get("Response") == "True":
                st.markdown("---")
                for item in response.get("Search", []):
                    if item["Type"] in ["movie", "series", "episode"]:
                        col_img, col_info = st.columns([1, 2])
                        
                        with col_img:
                            # FIXED: Changed placeholder link to a stable UI placeholder generator
                            poster_url = item["Poster"] if item["Poster"] != "N/A" else "https://ui-avatars.com"
                            st.image(poster_url, use_container_width=True)
                            
                        with col_info:
                            st.markdown(f"#### {item['Title']}")
                            st.caption(f"📅 Year: {item['Year']} | 🏷️ Type: {item['Type'].capitalize()}")
                            
                            btn_id = f"add_{item['imdbID']}"
                            if st.button("➕ Select & Add", key=btn_id, use_container_width=True):
                                global existing_data
                                if item['Title'].strip().lower() in existing_data['Title'].str.lower().values:
                                    st.error(f"'{item['Title']}' is already in your database!")
                                else:
                                    new_row = pd.DataFrame([{
                                        "Title": item['Title'].strip(),
                                        "Poster": poster_url,
                                        "Status": "Plan to Watch",
                                        "Rating": "Not Set",
                                        "Year": item['Year']
                                    }])
                                    updated_df = pd.concat([existing_data, new_row], ignore_index=True)
                                    save_data(updated_df)
            else:
                st.warning(f"OMDb Message: {response.get('Error')}")
        except Exception:
            st.error("Could not reach OMDb API servers. Check network routing.")

# ----------------------------------------------------
# 5. VIEW LAYOUT COMPOSITION
# ----------------------------------------------------

# Banner notification error callout if connection is broken
if not omdb_healthy:
    st.error(f"⚠️ **OMDb Server Connection Failure:** {omdb_msg}")

col_title, col_space, col_add = st.columns([4, 4, 2])
with col_title:
    st.markdown("## 🎞️ Movie Night")
with col_add:
    # Disable button dynamically if startup check failed
    if st.button("➕ Add Item", key="main_add_btn", type="primary", use_container_width=True, disabled=not omdb_healthy):
        add_item_dialog()

# Compute filter counts dynamically
all_count = len(existing_data)
plan_count = len(existing_data[existing_data['Status'] == 'Plan to Watch']) if not existing_data.empty else 0
watched_count = len(existing_data[existing_data['Status'] == 'Watched']) if not existing_data.empty else 0

# Interactive Filter Bar using safe session_state dictionary fallback logic
col_f1, col_f2, col_f3, col_spacer = st.columns([1, 1.3, 1.1, 6])

# Safely extract the filter using .get() to prevent unexpected AttributeError crashes
active_filter = st.session_state.get("current_filter", "All")

with col_f1:
    if st.button(f"All ({all_count})", type="primary" if active_filter == "All" else "secondary", use_container_width=True):
        st.session_state.current_filter = "All"
        st.rerun()
with col_f2:
    if st.button(f"Plan to Watch ({plan_count})", type="primary" if active_filter == "Plan to Watch" else "secondary", use_container_width=True):
        st.session_state.current_filter = "Plan to Watch"
        st.rerun()
with col_f3:
    if st.button(f"Watched ({watched_count})", type="primary" if active_filter == "Watched" else "secondary", use_container_width=True):
        st.session_state.current_filter = "Watched"
        st.rerun()

st.markdown("---")

# Filter down dataset before building rows using the verified safe variable
display_data = existing_data.copy()
if not display_data.empty and active_filter != "All":
    display_data = display_data[display_data["Status"] == active_filter]

# Grid Card Canvas Renderer logic
if not display_data.empty:
    cards_layout_limit = 4
    for i in range(0, len(display_data), cards_layout_limit):
        row_slice = display_data.iloc[i : i + cards_layout_limit]
        cols = st.columns(cards_layout_limit)
        
        for idx, (df_idx, row) in enumerate(row_slice.iterrows()):
            with cols[idx]:
                st.markdown(f"""
                <div class='movie-card'>
                    <img class='movie-poster' src='{row['Poster']}'>
                    <div class='movie-title'>{row['Title']}</div>
                    <div class='movie-meta'>📅 {row['Year']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                status_choices = ["Plan to Watch", "Watched"]
                current_status_idx = status_choices.index(row["Status"]) if row["Status"] in status_choices else 0
                
                updated_status = st.selectbox("Status", status_choices, index=current_status_idx, key=f"status_select_{df_idx}")
                
                if updated_status != row["Status"]:
                    existing_data.at[df_idx, "Status"] = updated_status
                    if updated_status == "Plan to Watch":
                        existing_data.at[df_idx, "Rating"] = "Not Set"
                    save_data(existing_data)
else:
    st.info("No movie items match the selected filter category.")
