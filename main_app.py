import hashlib
import pandas as pd
import requests
import streamlit as st
from streamlit_gsheets import GSheetsConnection

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
# 2. CRYPTO SECURITY IMPLEMENTATION
# ----------------------------------------------------
def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()


# ----------------------------------------------------
# 3. DATABASE MANAGEMENT
# ----------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

def load_table(sheet_name, fallback_cols):
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        if not df.empty:
            for col in df.columns:
                df[col] = df[col].astype(str).str.strip()
        return df
    except Exception:
        return pd.DataFrame(columns=fallback_cols)

# Load global data tables
user_db = load_table("Users", ["Username", "Password"])
movie_db = load_table("Movies", ["MovieID", "Title", "Poster", "Year", "Status"])
review_db = load_table("Reviews", ["MovieID", "Username", "Rating", "Comment"])

def save_table(sheet_name, df):
    conn.update(worksheet=sheet_name, data=df)

# ----------------------------------------------------
# 4. USER PORTAL GATEWAY (AUTH)
# ----------------------------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

if not st.session_state.logged_in:
    st.markdown("<div class='auth-container'>", unsafe_allow_html=True)
    st.markdown("## 🍿 Group Movie Night Login")
    auth_mode = st.tabs(["🔒 Sign In", "📝 Create Account"])
    
    with auth_mode:
        with st.form("login_form"):
            login_user = st.text_input("Username").strip()
            login_pass = st.text_input("Password", type="password")
            if st.form_submit_button("Log In", use_container_width=True):
                if login_user in user_db["Username"].values:
                    stored_hash = user_db.loc[user_db["Username"] == login_user, "Password"].values
                    if hash_password(login_pass) == stored_hash:
                        st.session_state.logged_in = True
                        st.session_state.username = login_user
                        st.rerun()
                st.error("Invalid username or password configuration.")
                
    with auth_mode:
        with st.form("signup_form"):
            new_user = st.text_input("Username").strip()
            new_pass = st.text_input("Password", type="password")
            confirm_pass = st.text_input("Confirm Password", type="password")
            if st.form_submit_button("Register", use_container_width=True):
                if new_pass != confirm_pass:
                    st.error("Passwords match error.")
                elif new_user in user_db["Username"].values:
                    st.error("Username already exists.")
                else:
                    new_acc = pd.DataFrame([{"Username": new_user, "Password": hash_password(new_pass)}])
                    user_db = pd.concat([user_db, new_acc], ignore_index=True)
                    save_table("Users", user_db)
                    st.success("Account created! You can now log in.")
                    
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

current_user = st.session_state.username



# ----------------------------------------------------
# MODAL POPUP: OMDb MOVIE SEARCH
# ----------------------------------------------------
@st.dialog("🎬 Add Item to Watchlist")
def add_item_dialog():
    st.write("Search Movie Below")
    search_query = st.text_input("Search Movie Title", key="search", placeholder="e.g. Lala Land, Barbarian, Other Movies...")
    
    if search_query.strip():
        search_url = f"https://omdbapi.com/?s={search_query.strip()}&apikey={OMDB_API_KEY}"
        
        try:
            response = requests.get(search_url, timeout=5)
            if response.status_code != 200:
                st.error(f"OMDb request failed with status code {response.status_code}.")
                return
            
            data = response.json()
            if data.get("Response") == "True":
                st.markdown("---")
                for item in data.get("Search", []):
                    if item["Type"] in ["movie", "series", "episode"]:
                        col_img, col_info = st.columns([1, 2])
                        
                        with col_img:
                            poster_url = item["Poster"] if item["Poster"] != "N/A" else "https://blocks.astratic.com/img/general-img-landscape.png"
                            st.image(poster_url, use_container_width=True)
                            
                        with col_info:
                            st.markdown(f"#### {item['Title']}")
                            st.caption(f"📅 Year: {item['Year']} | 🏷️ Type: {item['Type'].capitalize()}")
                            
                            btn_id = f"add_{item['imdbID']}"
                            if st.button("➕ Select & Add", key=btn_id, use_container_width=True):
                                global existing_data
                                titles_in_db = existing_data["Title"].dropna().astype(str).str.lower().values
                                if item['Title'].strip().lower() in titles_in_db:
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
                st.warning(f"OMDb Message: {data.get('Error', 'Unknown error')}")
        except requests.exceptions.RequestException as exc:
            st.error(f"Could not reach OMDb API servers. Check network routing. ({exc.__class__.__name__})")
        except ValueError:
            st.error("OMDb returned an unexpected response format.")

# ----------------------------------------------------
# VIEW LAYOUT COMPOSITION
# ----------------------------------------------------

col_title, col_space, col_add = st.columns([4, 4, 2])
with col_title:
    st.markdown("## 🎞️ Movie Night")
    with col_prof:
        st.markdown(f"👋 Active Session: **{current_user}**")
        if st.button("🚪 Logout", size="small"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.rerun()
    with col_btn:
        if st.button("➕ Add New Movie", use_container_width=True, type="primary"):
            add_item_dialog()
    
# ----------------------------------------------------
# 7. UNIVERSAL FILTER CONTROLS 
# ----------------------------------------------------
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

# Filter execution layout assignment
if active_filter != "All":
    display_movies = movie_db[movie_db["Status"] == active_filter]
else:
    display_movies = movie_db

# ----------------------------------------------------
# GROUP DYNAMIC RENDER GRID (CONTINUED)
# ----------------------------------------------------
if not display_movies.empty:
    columns_per_row = 4
    for i in range(0, len(display_movies), columns_per_row):
        row_slice = display_movies.iloc[i : i + columns_per_row]
        cols = st.columns(columns_per_row)
        
        for idx, (_, row) in enumerate(row_slice.iterrows()):
            m_id = row["MovieID"]
            
            with cols[idx]:
                # 1. Base card markup design
                st.markdown(f"""
                <div class='movie-card'>
                    <div>
                        <img class='movie-poster' src='{row['Poster']}'>
                        <div class='movie-title'>{row['Title']}</div>
                        <div class='movie-meta'>📅 {row['Year']}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # 2. UNIVERSAL STATUS SELECTBOX (Saves straight to 'Movies' sheet)
                status_options = ["Plan to Watch", "Watched"]
                global_status = row["Status"] if row["Status"] in status_options else "Plan to Watch"
                s_idx = status_options.index(global_status)
                
                new_status = st.selectbox("Group Movie Status", status_options, index=s_idx, key=f"status_{m_id}")
                
                if new_status != row["Status"]:
                    # Find matching exact target row inside global dataframe
                    target_idx = movie_db[movie_db["MovieID"] == m_id].index
                    movie_db.at[target_idx, "Status"] = new_status
                    save_table("Movies", movie_db)
                    st.rerun()
                
                # 3. CHOOSE PERSONAL REVIEW LOGIC (Runs only if movie is Watched)
                if new_status == "Watched":
                    st.markdown("---")
                    st.caption("✍️ Your Review:")
                    
                    # Fetch active user's existing review criteria
                    user_rev = review_db[(review_db["MovieID"] == m_id) & (review_db["Username"] == current_user)]
                    current_rating = user_rev["Rating"].values[0] if not user_rev.empty else "⭐⭐⭐"
                    current_comment = user_rev["Comment"].values[0] if not user_rev.empty else ""
                    
                    # Dropdown rating + clear comment submission box layout elements
                    rating_options = ["⭐", "⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐"]
                    r_idx = rating_options.index(current_rating) if current_rating in rating_options else 2
                    
                    new_rating = st.selectbox("Your Rating", rating_options, index=r_idx, key=f"rating_{m_id}_{current_user}")
                    new_comment = st.text_input("Comment/Notes", value=current_comment, key=f"comm_{m_id}_{current_user}")
                    
                    # Save personal edits instantly if form values deviate from DB state values
                    if new_rating != current_rating or new_comment != current_comment:
                        # Clear old row pairing
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
                
                # 4. GROUP INSIGHTS PANEL: Render reviews left by friends
                all_group_reviews = review_db[(review_db["MovieID"] == m_id)]
                if not all_group_reviews.empty:
                    st.markdown("**Group Discussion & Ratings:**")
                    for _, rev in all_group_reviews.iterrows():
                        comment_str = f" - *\"{rev['Comment']}\"*" if rev['Comment'] and str(rev['Comment']) != "nan" else ""
                        st.markdown(f"<div class='review-box'>👤 **{rev['Username']}**: {rev['Rating']}{comment_str}</div>", unsafe_allow_html=True)
                
                st.write("") 
else:
    st.info("No items match this viewing state matrix filter criteria.")
