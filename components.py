import streamlit as st
import pandas as pd
import requests
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
                movie_db = load_table("Movies", ["MovieID", "Title", "Poster", "Year", "Status"])
                
                for item in response.get("Search", []):
                    if item["Type"] in ["movie", "series"]:
                        col_img, col_info = st.columns([1, 2])
                        with col_img:
                            p_url = item["Poster"] if item["Poster"] != "N/A" else "https://astratic.com"
                            st.image(p_url, use_container_width=True)
                        with col_info:
                            st.markdown(f"#### {item['Title']}")
                            st.caption(f"📅 {item['Year']}")
                            if st.button("➕ Add to Group List", key=f"add_{item['imdbID']}", use_container_width=True):
                                if item['imdbID'] in movie_db["MovieID"].values:
                                    st.error("This movie is already on the group dashboard!")
                                else:
                                    new_movie = pd.DataFrame([{
                                        "MovieID": item['imdbID'],
                                        "Title": item['Title'].strip(),
                                        "Poster": p_url,
                                        "Year": item['Year'],
                                        "Status": "Plan to Watch"
                                    }])
                                    updated_movies = pd.concat([movie_db, new_movie], ignore_index=True)
                                    save_table("Movies", updated_movies)
                                    st.rerun()
            else:
                st.warning(response.get("Error"))
        except Exception as e:
            st.error(f"Search API Error: {e}")

@st.dialog("🎬 Movie Details & Settings", width="large")
def movie_details_dialog(m_id, current_user, row_title):
    """Centered pop-up overlay modal rendering metadata and status settings."""
    movie_db = load_table("Movies", ["MovieID", "Title", "Poster", "Year", "Status"])
    review_db = load_table("Reviews", ["MovieID", "Username", "Rating", "Comment"])
    
    # Locate targets inside current data matrices
    m_row = movie_db[movie_db["MovieID"] == m_id].iloc[0]
    global_status = m_row["Status"] if m_row["Status"] in ["Plan to Watch", "Watched"] else "Plan to Watch"
    
    # Fetch rich extended metadata asynchronously using OMDb API mapping
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

    # --- POP-UP MODAL UI COMPOSITION ---
    col_poster, col_meta = st.columns([1, 1.8])
    with col_poster:
        st.image(m_row["Poster"], use_container_width=True)
    with col_meta:
        st.markdown(f"## {m_row['Title']}")
        st.markdown(f"🗓️ **Release Year:** {m_row['Year']}")
        st.markdown(f"🎬 **Director:** {director}")
        st.markdown(f"🏷️ **Genres:** {genre}")
        st.markdown(f"👥 **Cast:** {actors}")
        st.markdown(f"📝 **Plot Summary:** {plot}")
        
    st.markdown("---")
    st.markdown("### ⚙️ Group Management")
    
    # Universal Status configuration utilizing Group Radio selectors at the bottom
    status_options = ["Plan to Watch", "Watched"]
    r_status_idx = status_options.index(global_status)
    new_status = st.radio("Group Movie Status", status_options, index=r_status_idx, key=f"radio_status_{m_id}")
    
    if st.button("💾 Save Group Status", key=f"save_status_{m_id}", use_container_width=True, type="primary"):
        if new_status != m_row["Status"]:
            movie_db.loc[movie_db["MovieID"] == m_id, "Status"] = new_status
            save_table("Movies", movie_db)
            
            # Clean orphans if changed back to Plan to Watch
            if new_status == "Plan to Watch":
                review_db = review_db[review_db["MovieID"] != m_id]
                save_table("Reviews", review_db)
                
            st.success("Group status synchronized!")
            st.rerun()

@st.dialog("✍️ Write/Edit Your Review")
def edit_review_dialog(m_id, current_user, movie_title):
    """Dedicated modal for adding or updating user-specific reviews."""
    review_db = load_table("Reviews", ["MovieID", "Username", "Rating", "Comment"])
    user_rev = review_db[(review_db["MovieID"] == m_id) & (review_db["Username"] == current_user)]
    
    if not user_rev.empty:
        raw_rating = user_rev["Rating"].iloc[0]
        raw_comment = user_rev["Comment"].iloc[0]
        current_rating = str(raw_rating) if pd.notna(raw_rating) else "7/10"
        current_comment = str(raw_comment) if pd.notna(raw_comment) else ""
    else:
        current_rating = "7/10"
        current_comment = ""
        
    if current_comment == "nan":
        current_comment = ""
        
    st.markdown(f"### Reviewing: *{movie_title}*")
    rating_options = [f"{x}/10" for x in range(1, 11)]
    r_idx = rating_options.index(current_rating) if current_rating in rating_options else 6
    
    new_rating = st.selectbox("Your Score", rating_options, index=r_idx, key=f"rating_{m_id}_{current_user}")
    new_comment = st.text_area("Your Notes/Comments", value=current_comment, key=f"comm_{m_id}_{current_user}")
    
    if st.button("💾 Save Review Updates", use_container_width=True, type="primary"):
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
    """Generates the 4-column movie grid with poster trigger modals and standalone review buttons."""
    movie_db = load_table("Movies", ["MovieID", "Title", "Poster", "Year", "Status"])
    review_db = load_table("Reviews", ["MovieID", "Username", "Rating", "Comment"])
    
    # Standard CSS Injector to hide the text layer inside the poster-button wrapper container
    st.markdown("""
    <style>
        div.stButton > button.poster-btn-wrapper {
            border: none !important; padding: 0 !important; background: transparent !important;
            box-shadow: none !important; width: 100% !important; transition: transform 0.2s;
        }
        div.stButton > button.poster-btn-wrapper:hover { transform: scale(1.02); background: transparent !important; }
        div.stButton > button.poster-btn-wrapper p { display: none !important; }
    </style>
    """, unsafe_allow_html=True)
    
    columns_per_row = 4
    for i in range(0, len(display_movies), columns_per_row):
        row_slice = display_movies.iloc[i : i + columns_per_row]
        cols = st.columns(columns_per_row)
        
        for idx, (_, row) in enumerate(row_slice.iterrows()):
            m_id = row["MovieID"]
            global_status = row["Status"] if row["Status"] in ["Plan to Watch", "Watched"] else "Plan to Watch"
            
            with cols[idx]:
                # Custom Movie HTML Content Container Box
                st.markdown(f"""
                <div class='movie-card'>
                    <div style='font-weight: 700; font-size: 1.15rem; color: #1a202c; margin-bottom: 6px;'>{row['Title']}</div>
                    <div class='movie-meta' style='margin-bottom: 12px;'>📅 {row['Year']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # FIX: Poster Container wrapped inside a styling-isolated image execution button trigger
                if st.button("", key=f"poster_click_{m_id}", use_container_width=True, help="Click poster for details"):
                    movie_details_dialog(m_id, current_user, row["Title"])
                
                # Inject visual image container inside the button structure block coordinates
                st.markdown(f"<style>button[key='poster_click_{m_id}'] {{ background-image: url('{row['Poster']}'); background-size: cover; background-position: center; aspect-ratio: 2/3; width: 100%; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom:12px; }}</style>", unsafe_allow_html=True)
                
                # Display status indicator text line
                status_color = "#3182ce" if global_status == "Plan to Watch" else "#38a169"
                st.markdown(f"📌 Status: <span style='color:{status_color}; font-weight:700;'>{global_status}</span>", unsafe_allow_html=True)
                
                if global_status == "Watched":
                    if st.button("✍️ Edit Your Review", key=f"edit_rev_trigger_{m_id}", use_container_width=True):
                        edit_review_dialog(m_id, current_user, row["Title"])
                else:
                    st.caption("🔒 Reviews unlocked once marked Watched")
                
                # Clean Stream group data activity display feed
                all_group_reviews = review_db[review_db["MovieID"] == m_id]
                if not all_group_reviews.empty and global_status == "Watched":
                    st.markdown("<div style='margin-top: 10px; font-size: 0.85rem; border-top: 1px solid #e2e8f0; padding-top: 8px;'>", unsafe_allow_html=True)
                    for _, rev in all_group_reviews.iterrows():
                        comment_str = f" - {rev['Comment']}" if rev['Comment'] and str(rev['Comment']) != "nan" and str(rev['Comment']).strip() != "" else ""
                        st.markdown(f"👤 {rev['Username']}: {rev['Rating']}{comment_str}")
                    st.markdown("</div>", unsafe_allow_html=True)
                st.write("")
