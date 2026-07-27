import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from database import load_table, save_table

OMDB_API_KEY = "43ac7081"

@st.dialog("🎬 Add Movie to Group Board")
def add_item_dialog():
    """Popup modal searching OMDb API directory."""
    search_query = st.text_input("Search Movie Title", placeholder="e.g. Inception...")
    if search_query.strip():
        search_url = f"https://omdbapi.com/?s={search_query.strip()}&apikey={OMDB_API_KEY}"
        try:
            response = requests.get(search_url, timeout=5).json()
            if response.get("Response") == "True":
                st.markdown("---")
                movie_db = load_table("Movies", ["MovieID", "Title", "Poster", "Year", "Status", "DateWatched"])
                
                for item in response.get("Search", []):
                    if item["Type"] in ["movie", "series"]:
                        col_img, col_info = st.columns()
                        with col_img:
                            p_url = item["Poster"] if item["Poster"] != "N/A" else "https://astratic.com"
                            st.image(p_url, use_container_width=True)
                        with col_info:
                            st.markdown(f"#### {item['Title']}")
                            st.caption(f"Year: {item['Year']}")
                            if st.button("Add to Group List", key=f"add_{item['imdbID']}", use_container_width=True):
                                if item['imdbID'] in movie_db["MovieID"].values:
                                    st.error("This movie is already on the group dashboard!")
                                else:
                                    new_movie = pd.DataFrame([{
                                        "MovieID": item['imdbID'],
                                        "Title": item['Title'].strip(),
                                        "Poster": p_url,
                                        "Year": item['Year'],
                                        "Status": "Plan to Watch",
                                        "DateWatched": "" # Initializes empty field structure
                                    }])
                                    updated_movies = pd.concat([movie_db, new_movie], ignore_index=True)
                                    save_table("Movies", updated_movies)
                                    st.rerun()
            else:
                st.warning(response.get("Error"))
        except Exception as e:
            st.error(f"Search API Error: {e}")

@st.dialog("Movie Details and Settings", width="large")
def movie_details_dialog(m_id):
    """Centered large pop-up overlay modal rendering metadata, status, and watch date."""
    movie_db = load_table("Movies", ["MovieID", "Title", "Poster", "Year", "Status", "DateWatched"])
    review_db = load_table("Reviews", ["MovieID", "Username", "Rating", "Comment"])
    
    m_row = movie_db[movie_db["MovieID"] == m_id].iloc[0]
    global_status = m_row["Status"] if m_row["Status"] in ["Plan to Watch", "Watched"] else "Plan to Watch"
    
    # Safely manage previous date state strings
    existing_date_str = str(m_row["DateWatched"]).strip() if "DateWatched" in m_row else ""
    try:
        if existing_date_str and existing_date_str != "nan" and existing_date_str != "":
            default_date = datetime.strptime(existing_date_str, "%Y-%m-%d").date()
        else:
            default_date = datetime.today().date()
    except Exception:
        default_date = datetime.today().date()
    
    detail_url = f"https://omdbapi.com{m_id}&apikey={OMDB_API_KEY}"
    director, genre, actors, plot = "N/A", "N/A", "N/A", "No plot description available."
    
    try:
        res = requests.get(detail_url, timeout=5).json()
        if res.get("Response") == "True":
            director = res.get("Director", "N/A")
            genre = res.get("Genre", "N/A")
            actors = res.get("Actors", "N/A")
            plot = res.get("Plot", "No plot description available.")
    except Exception:
        pass

    col_poster, col_meta = st.columns([1, 1.8])
    with col_poster:
        st.image(m_row["Poster"], use_container_width=True)
    with col_meta:
        st.markdown(f"## {m_row['Title']}")
        st.markdown(f"**Release Year:** {m_row['Year']}")
        st.markdown(f"**Director:** {director}")
        st.markdown(f"**Genres:** {genre}")
        st.markdown(f"**Cast:** {actors}")
        st.markdown(f"**Plot Summary:** {plot}")
        
    st.markdown("---")
    st.markdown("### Group Management")
    
    status_options = ["Plan to Watch", "Watched"]
    r_status_idx = status_options.index(global_status)
    new_status = st.radio("Group Movie Status", status_options, index=r_status_idx, key=f"radio_status_{m_id}")
    
    # Conditional date watch entry picker appears when Watched radio evaluates True
    new_date_str = ""
    if new_status == "Watched":
        selected_date = st.date_input("Date Watched", value=default_date, key=f"date_pick_{m_id}")
        new_date_str = selected_date.strftime("%Y-%m-%d")
    
    if st.button("Save Group Status", key=f"save_status_{m_id}", use_container_width=True, type="primary"):
        target_idx = movie_db[movie_db["MovieID"] == m_id].index
        
        # Save both Universal Status and Universal watch date to sheet rows
        movie_db.loc[target_idx, "Status"] = new_status
        movie_db.loc[target_idx, "DateWatched"] = new_date_str if new_status == "Watched" else ""
        save_table("Movies", movie_db)
        
        # Clean up orphan individual reviews if moved back to plan list
        if new_status == "Plan to Watch":
            review_db = review_db[review_db["MovieID"] != m_id]
            save_table("Reviews", review_db)
            
        st.success("Group settings synchronized!")
        st.rerun()

@st.dialog("Write or Edit Your Review")
def edit_review_dialog(m_id, current_user, movie_title):
    """Dedicated modal for adding or updating user-specific reviews."""
    review_db = load_table("Reviews", ["MovieID", "Username", "Rating", "Comment"])
    user_rev = review_db[(review_db["MovieID"] == m_id) & (review_db["Username"] == current_user)]
    
    if not user_rev.empty:
        current_rating = str(user_rev["Rating"].values[0])
        current_comment = str(user_rev["Comment"].values[0])
    else:
        current_rating = "7/10"
        current_comment = ""
        
    if current_comment == "nan":
        current_comment = ""
        
    st.markdown(f"### Reviewing: *{movie_title}*")
    rating_options = [f"{x}/10" for x in range(1, 11)]
    r_idx = rating_options.index(current_rating) if current_rating in rating_options else 6
    
    new_rating = st.selectbox("Your Score", rating_options, index=r_idx, key=f"rating_{m_id}_{current_user}")
    new_comment = st.text_area("Your Notes or Comments", value=current_comment, key=f"comm_{m_id}_{current_user}")
    
    if st.button("Save Review Updates", use_container_width=True, type="primary"):
        review_db = review_db[~((review_db["MovieID"] == m_id) & (review_db["Username"] == current_user))]
        updated_review = pd.DataFrame([{
            "MovieID": m_id,
            "Username": current_user,
            "Rating": new_rating,
            "Comment": new_comment.strip()
        }])
        review_db = pd.concat([review_db, updated_review], ignore_index=True)
        save_table("Reviews", review_db)
        st.success("Review logged!")
        st.rerun()

def render_movie_grid(display_movies, current_user):
    """Generates the 4-column movie grid with reactive text lines inside container frames."""
    movie_db = load_table("Movies", ["MovieID", "Title", "Poster", "Year", "Status", "DateWatched"])
    review_db = load_table("Reviews", ["MovieID", "Username", "Rating", "Comment"])
    
    columns_per_row = 4
    for i in range(0, len(display_movies), columns_per_row):
        row_slice = display_movies.iloc[i : i + columns_per_row]
        cols = st.columns(columns_per_row)
        
        for idx, (_, row) in enumerate(row_slice.iterrows()):
            m_id = row["MovieID"]
            global_status = row["Status"] if row["Status"] in ["Plan to Watch", "Watched"] else "Plan to Watch"
            
            with cols[idx]:
                with st.container(border=True):
                    st.markdown(f"""
                    <div style='text-align: left;'>
                        <div style='font-weight: 700; font-size: 1.15rem; color: #1a202c; margin-bottom: 2px;'>{row['Title']}</div>
                        <div style='font-size: 0.85rem; color: #718096; margin-bottom: 8px;'>Year: {row['Year']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.image(row["Poster"], use_container_width=True)
                    
                    if st.button("Info", key=f"info_text_{m_id}", use_container_width=True, type="secondary"):
                        movie_details_dialog(m_id)
                    
                    # Status Indicator Line
                    status_color = "#3182ce" if global_status == "Plan to Watch" else "#38a169"
                    st.markdown(f"<div style='font-size: 0.9rem; margin-top: 6px; margin-bottom: 4px;'>📌 Status: <span style='color:{status_color}; font-weight:700;'>{global_status}</span></div>", unsafe_allow_html=True)
                    
                    # Watch Date clean stream text row (Only shows if Status is Watched)
                    if global_status == "Watched" and "DateWatched" in row and str(row["DateWatched"]).strip() != "" and str(row["DateWatched"]).strip() != "nan":
                        st.markdown(f"<div style='font-size: 0.85rem; color: #4a5568; margin-bottom: 6px;'>Watched on: {row['DateWatched']}</div>", unsafe_allow_html=True)
                    elif global_status == "Watched":
                        st.markdown("<div style='font-size: 0.85rem; color: #a0aec0; margin-bottom: 6px; font-style: italic;'>No watch date log set</div>", unsafe_allow_html=True)
                    
                    if global_status == "Watched":
                        if st.button("✍️ Edit Your Review", key=f"edit_rev_trigger_{m_id}", use_container_width=True, type="primary"):
                            edit_review_dialog(m_id, current_user, row["Title"])
                    else:
                        st.caption("Reviews unlocked once marked Watched")
                    
                    all_group_reviews = review_db[review_db["MovieID"] == m_id]
                    if not all_group_reviews.empty and global_status == "Watched":
                        st.markdown("<div style='margin-top: 10px; font-size: 0.85rem; border-top: 1px solid #e2e8f0; padding-top: 8px;'>", unsafe_allow_html=True)
                        for _, rev in all_group_reviews.iterrows():
                            comment_str = f" - {rev['Comment']}" if rev['Comment'] and str(rev['Comment']) != "nan" and str(rev['Comment']).strip() != "" else ""
                            st.markdown(f"👤{rev['Username']}: {rev['Rating']}{comment_str}")
                        st.markdown("</div>", unsafe_allow_html=True)
