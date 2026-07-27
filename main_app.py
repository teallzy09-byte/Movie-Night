import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import requests

# ----------------------------------------------------
# 1. INITIAL API CONFIG & THEME TUNING
# ----------------------------------------------------
OMDB_API_KEY = "http://www.omdbapi.com/?i=tt3896198&apikey=43ac7081" 

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
# 2. DATABASE MANAGEMENT
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
# 3. MODAL POPUP: OMDb MOVIE SEARCH
# ----------------------------------------------------
@st.dialog("🎬 Add Item to Watchlist")
def add_item_dialog():
    st.write("Type a title below to fetch live, structured movie details from OMDb:")
    
    # Text input triggers the request instantly on enter
    search_query = st.text_input("Search Movie Title", key="omdb_search_bar", placeholder="e.g. Primer, Barbarian, Inception...")
    
    if search_query.strip():
        # Querying the OMDb Search ('s') endpoint
        search_url = f"https://omdbapi.com{search_query.strip()}&apikey={OMDB_API_KEY}"
        
        try:
            response = requests.get(search_url).json()
            
            if response.get("Response") == "True":
                st.markdown("---")
                results_list = response.get("Search", [])
                
                for item in results_list:
                    # Target films, series, or documentaries 
                    if item["Type"] in ["movie", "series", "episode"]:
                        col_img, col_info = st.columns([1, 2])
                        
                        with col_img:
                            # Use placeholder if poster url value returns blank/empty
                            poster_url = item["Poster"] if item["Poster"] != "N/A" else "https://placeholder.com"
                            st.image(poster_url, use_container_width=True)
                            
                        with col_info:
                            st.markdown(f"#### {item['Title']}")
                            st.caption(f"📅 Year: {item['Year']} | 🏷️ Type: {item['Type'].capitalize()}")
                            
                            # Clean index binding tracking
                            btn_id = f"add_{item['imdbID']}"
                            if st.button("➕ Select & Add", key=btn_id, use_container_width=True):
                                global existing_data
                                
                                # Duplicate verification check
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
                                    st.success(f"Added {item['Title']} successfully!")
                        st.markdown("<br>", unsafe_allow_html=True)
            else:
                error_msg = response.get("Error", "No matching titles found.")
                st.warning(f"OMDb Message: {error_msg}")
                
        except Exception as e:
            st.error("Could not reach OMDb API servers. Please check your network connection or API Key configuration.")

# ----------------------------------------------------
# 4. VIEW LAYOUT COMPOSITION
# ----------------------------------------------------

# Row Structure matching GroupPick layout header
col_title, col_space, col_add = st.columns([4, 4, 2])
with col_title:
    st.markdown("## 🎞️ Movie Night")
with col_add:
    if st.button("➕ Add Item", key="main_add_btn", type="primary", use_container_width=True):
        add_item_dialog()

# Inline Header Counter Bar Layout
st.markdown(f"""
<div class='filter-bar'>
    <div class='filter-btn active'>All ({len(existing_data)})</div>
    <div class='filter-btn'>Plan to Watch ({len(existing_data[existing_data['Status']=='Plan to Watch']) if not existing_data.empty else 0})</div>
    <div class='filter-btn'>Watched ({len(existing_data[existing_data['Status']=='Watched']) if not existing_data.empty else 0})</div>
</div>
""", unsafe_allow_html=True)

# Grid Card Canvas Renderer logic
if not existing_data.empty:
    cards_layout_limit = 4  # Display up to 4 parallel columns
    
    for i in range(0, len(existing_data), cards_layout_limit):
        row_slice = existing_data.iloc[i : i + cards_layout_limit]
        cols = st.columns(cards_layout_limit)
        
        for idx, (df_idx, row) in enumerate(row_slice.iterrows()):
            with cols[idx]:
                # 1. Custom Visual HTML Card Box Wrap
                st.markdown(f"""
                <div class='movie-card'>
                    <img class='movie-poster' src='{row['Poster']}'>
                    <div class='movie-title'>{row['Title']}</div>
                    <div class='movie-meta'>📅 {row['Year']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # 2. Interactive Widget Inputs
                status_choices = ["Plan to Watch", "Watched"]
                current_status_idx = status_choices.index(row["Status"]) if row["Status"] in status_choices else 0
                
                updated_status = st.selectbox(
                    "Status", 
                    status_choices, 
                    index=current_status_idx, 
                    key=f"status_select_{df_idx}"
                )
                
                # Check status changes and trigger save
                if updated_status != row["Status"]:
                    existing_data.at[df_idx, "Status"] = updated_status
                    # If changed back to plan to watch, clear out values
                    if updated_status == "Plan to Watch":
                        existing_data.at[df_idx, "Rating"] = "Not Set"
                    save_data(existing_data)
                
                # Star Rating Input
                if updated_status == "Watched":
                    rating_options = ["⭐ 10/10", "⭐ 9/10", "⭐ 8/10", "⭐ 7/10", "⭐ 6/10", "⭐ 5/10", "👎 Poor"]
                    current_rating_str = str(row["Rating"])
                    
                    # Deduce default fallback configuration tracking indices
                    default_rating_idx = 2  # default 8/10
                    for op_idx, val in enumerate(rating_options):
                        if current_rating_str in val:
                            default_rating_idx = op_idx
                            
                    selected_rating = st.selectbox(
                        "Rating", 
                        rating_options, 
                        index=default_rating_idx, 
                        key=f"rating_select_{df_idx}"
                    )
                    
                    extracted_rating_value = selected_rating.split(" ")[-1]
                    if extracted_rating_value != current_rating_str:
                        existing_data.at[df_idx, "Rating"] = extracted_rating_value
                        save_data(existing_data)
else:
    st.info("No movie listings are populated in your sheet. Click 'Add Item' above to open your OMDb connection window!")
