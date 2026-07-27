import streamlit as st
from database import load_table
from auth import render_auth_gateway
from components import add_item_dialog, render_movie_grid

# Setup page layout configuration parameters
st.set_page_config(page_title="Movie Night", layout="wide", initial_sidebar_state="collapsed")

# Core Style Sheets injection
st.markdown("""
<style>
    .auth-container { max-width: 450px; margin: 50px auto; padding: 30px; background-color: #ffffff; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); border: 1px solid #e2e8f0; }
    .movie-card {
        background-color: #ffffff; border-radius: 10px; padding: 14px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05); border: 1px solid #e2e8f0;
        margin-bottom: 12px; text-align: left; height: 100%; display: flex; flex-direction: column; justify-content: space-between;
    }
    .movie-poster { width: 100%; border-radius: 8px; object-fit: cover; aspect-ratio: 2/3; margin-bottom: 12px; }
    .movie-title { font-weight: 700; font-size: 1.15rem; color: #1a202c; margin-bottom: 4px; min-height: 55px; }
    .movie-meta { font-size: 0.85rem; color: #718096; margin-bottom: 12px; }
    .review-box { background-color: #f7fafc; padding: 8px; border-radius: 6px; border-left: 3px solid #3182ce; font-size: 0.85rem; margin-top: 6px; margin-bottom: 6px;}
</style>
""", unsafe_allow_html=True)

# Initialize system state engines
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

# Security Interception Firewall Gateway check
if not st.session_state.logged_in:
    render_auth_gateway()
    st.stop()

current_user = st.session_state.username

# --- MAIN SCREEN HEADER NAVIGATION ASSEMBLY ---
col_hdr, col_prof, col_btn = st.columns([5, 3, 2])
with col_hdr:
    st.markdown("## 🎞️ Shared Movie Board")
with col_prof:
    st.markdown(f"👋 Active Session: **{current_user}**")
    if st.button("🚪 Logout", size="small"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()
with col_btn:
    if st.button("➕ Add New Movie", use_container_width=True, type="primary"):
        add_item_dialog()

# Load movies dataset table to compute reactive top horizontal filter rows counters
movie_db = load_table("Movies", ["MovieID", "Title", "Poster", "Year", "Status"])

active_filter = st.session_state.get("current_filter", "All")
all_c = len(movie_db)
plan_c = len(movie_db[movie_db["Status"] == "Plan to Watch"])
watch_c = len(movie_db[movie_db["Status"] == "Watched"])

f_col1, f_col2, f_col3, _ = st.columns([1, 1.3, 1.1, 6])
with f_col1:
    if st.button(f"All ({all_c})", type="primary" if active_filter == "All" else "secondary", use_container_width=True):
        st.session_state.current_filter = "All"; st.rerun()
with f_col2:
    if st.button(f"Plan to Watch ({plan_c})", type="primary" if active_filter == "Plan to Watch" else "secondary", use_container_width=True):
        st.session_state.current_filter = "Plan to Watch"; st.rerun()
with f_col3:
    if st.button(f"Watched ({watch_c})", type="primary" if active_filter == "Watched" else "secondary", use_container_width=True):
        st.session_state.current_filter = "Watched"; st.rerun()

st.markdown("---")

# Filter execution logic matching active parameters selection matrix
if active_filter != "All":
    display_movies = movie_db[movie_db["Status"] == active_filter]
else:
    display_movies = movie_db

# Execute UI grid construction
if not display_movies.empty:
    render_movie_grid(display_movies, current_user)
else:
    st.info("No items match this viewing state matrix filter criteria.")
