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

def render_movie_grid(display_movies, current_user):
    """Generates the 4-column aesthetic movie matrix layout framework grid."""
    movie_db = load_table("Movies", ["MovieID", "Title", "Poster", "Year", "Status"])
    review_db = load_table("Reviews", ["MovieID", "Username", "Rating", "Comment"])
    
    columns_per_row = 4
    for i in range(0, len(display_movies), columns_per_row):
        row_slice = display_movies.iloc[i : i + columns_per_row]
        cols = st.columns(columns_per_row)
        
        for idx, (_, row) in enumerate(row_slice.iterrows()):
            m_id = row["MovieID"]
            
            with cols[idx]:
                st.markdown(f"""
                <div class='movie-card'>
                    <div>
                        <img class='movie-poster' src='{row['Poster']}'>
                        <div class='movie-title'>{row['Title']}</div>
                        <div class='movie-meta'>📅 {row['Year']}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Universal Group Status selector
                status_options = ["Plan to Watch", "Watched"]
                global_status = row["Status"] if row["Status"] in status_options else "Plan to Watch"
                s_idx = status_options.index(global_status)
                new_status = st.selectbox("Group Movie Status", status_options, index=s_idx, key=f"status_{m_id}")
                
                if new_status != row["Status"]:
                    movie_db.loc[movie_db["MovieID"] == m_id, "Status"] = new_status
                    save_table("Movies", movie_db)
                    st.rerun()
                
                # Isolated Personal Review inputs
                if new_status == "Watched":
                    st.markdown("---")
                    st.caption("✍️ Your Review:")
                    
                    user_rev = review_db[(review_db["MovieID"] == m_id) & (review_db["Username"] == current_user)]
                    current_rating = str(user_rev["Rating"].values[0]) if not user_rev.empty else "⭐⭐⭐"
                    current_comment = str(user_rev["Comment"].values[0]) if not user_rev.empty else ""
                    if current_comment == "nan":
                        current_comment = ""
                    
                    rating_options = ["⭐", "⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐"]
                    r_idx = rating_options.index(current_rating) if current_rating in rating_options else 2
                    
                    new_rating = st.selectbox("Your Rating", rating_options, index=r_idx, key=f"rating_{m_id}_{current_user}")
                    new_comment = st.text_input("Comment/Notes", value=current_comment, key=f"comm_{m_id}_{current_user}")
                    
                    if new_rating != current_rating or new_comment != current_comment:
                        review_db = review_db[~((review_db["MovieID"] == m_id) & (review_db["Username"] == current_user))]
                        updated_review = pd.DataFrame([{
                            "MovieID": m_id,
                            "Username": current_user,
                            "Rating": new_rating,
                            "Comment": new_comment.strip()
                        }])
                        review_db = pd.concat([review_db, updated_review], ignore_index=True)
                        save_table("Reviews", review_db)
                        st.rerun()
                
                # Display friend discussion board feed
                all_group_reviews = review_db[review_db["MovieID"] == m_id]
                if not all_group_reviews.empty:
                    st.markdown("**Group Discussion & Ratings:**")
                    for _, rev in all_group_reviews.iterrows():
                        comment_str = f" - \{rev['Comment']}\" if rev['Comment'] and str(rev['Comment']) != "nan" else ""
                        st.markdown(f"<div class='review-box'>👤 {rev['Username']}: {rev['Rating']}{comment_str}</div>", unsafe_allow_html=True)
                st.write("")
