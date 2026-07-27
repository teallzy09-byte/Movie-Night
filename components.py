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
    """Generates the 4-column movie grid with click-to-edit review sheets and clean line streams."""
    movie_db = load_table("Movies", ["MovieID", "Title", "Poster", "Year", "Status"])
    review_db = load_table("Reviews", ["MovieID", "Username", "Rating", "Comment"])
    
    columns_per_row = 4
    for i in range(0, len(display_movies), columns_per_row):
        row_slice = display_movies.iloc[i : i + columns_per_row]
        cols = st.columns(columns_per_row)
        
        for idx, (_, row) in enumerate(row_slice.iterrows()):
            m_id = row["MovieID"]
            
            with cols[idx]:
                # 1. Base card visual presentation
                st.markdown(f"""
                <div class='movie-card'>
                    <div>
                        <img class='movie-poster' src='{row['Poster']}'>
                        <div style='font-weight: 700; font-size: 1.15rem; color: #1a202c; margin-bottom: 4px;'>{row['Title']}</div>
                        <div class='movie-meta' style='margin-bottom: 8px;'>📅 {row['Year']}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # 2. Universal Group Status selector
                status_options = ["Plan to Watch", "Watched"]
                global_status = row["Status"] if row["Status"] in status_options else "Plan to Watch"
                s_idx = status_options.index(global_status)
                new_status = st.selectbox("Group Movie Status", status_options, index=s_idx, key=f"status_{m_id}")
                
                if new_status != row["Status"]:
                    movie_db.loc[movie_db["MovieID"] == m_id, "Status"] = new_status
                    save_table("Movies", movie_db)
                    st.rerun()
                
                # 3. POPUP WINDOW LAYOUT USING ST.POPOVER (Appears when clicked to edit review)
                if new_status == "Watched":
                    with st.popover("✍️ Write / Edit Your Review", use_container_width=True):
                        st.markdown(f"### Reviewing: *{row['Title']}*")
                        
                        user_rev = review_db[(review_db["MovieID"] == m_id) & (review_db["Username"] == current_user)]
                        
                        # Extract previous states safely if they exist
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
                        
                        rating_options = [f"{x}/10" for x in range(1, 11)]
                        r_idx = rating_options.index(current_rating) if current_rating in rating_options else 6
                        
                        new_rating = st.selectbox("Your Score", rating_options, index=r_idx, key=f"rating_{m_id}_{current_user}")
                        new_comment = st.text_area("Your Notes/Comments", value=current_comment, key=f"comm_{m_id}_{current_user}")
                        
                        if st.button("💾 Save Review Updates", key=f"save_btn_{m_id}_{current_user}", use_container_width=True, type="primary"):
                            # Delete existing record entry for safety
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
                
                # 4. CLEAN STREAM FEED DESIGN: Renders clean single text lines directly inside the frame
                all_group_reviews = review_db[review_db["MovieID"] == m_id]
                if not all_group_reviews.empty:
                    st.markdown("<div style='margin-top: 10px; font-size: 0.85rem; border-top: 1px solid #e2e8f0; padding-top: 8px;'>", unsafe_allow_html=True)
                    for _, rev in all_group_reviews.iterrows():
                        comment_str = f" - {rev['Comment']}" if rev['Comment'] and str(rev['Comment']) != "nan" and str(rev['Comment']).strip() != "" else ""
                        # Outputs as a clean, standardized, borderless text row element
                        st.markdown(f"👤 {rev['Username']}: {rev['Rating']}{comment_str}")
                    st.markdown("</div>", unsafe_allow_html=True)
                st.write("")
