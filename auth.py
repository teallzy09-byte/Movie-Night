import streamlit as st
import pandas as pd
from database import load_table, save_table, hash_password

def render_auth_gateway():
    """Renders a clean authorization box for signing in or creating accounts."""
    st.markdown("<div class='auth-container'>", unsafe_allow_html=True)
    st.markdown("## 🍿 Group Movie Night Login")
    
    login_tab, signup_tab = st.tabs(["🔒 Sign In", "📝 Create Account"])
    user_db = load_table("Users", ["Username", "Password"])
    
    # --- LOGIN ROUTINE ---
    with login_tab:
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
                
    # --- SIGN UP ROUTINE ---
   with signup_tab:
        with st.form("signup_form"):
            new_user = st.text_input("Choose Username").strip()
            new_pass = st.text_input("Create Password", type="password")
            confirm_pass = st.text_input("Confirm Password", type="password")
            if st.form_submit_button("Register", use_container_width=True):
                if new_pass != confirm_pass:
                    st.error("Passwords match error.")
                elif new_user in user_db["Username"].values:
                    st.error("Username already exists.")
                elif not new_user or not new_pass:
                    st.error("Credential field layout specifications require text values.")
                else:
                    new_acc = pd.DataFrame([{"Username": new_user, "Password": hash_password(new_pass)}])
                    updated_user_db = pd.concat([user_db, new_acc], ignore_index=True)
                    save_table("Users", updated_user_db)
                    st.success("Account created! You can now log in.")
                    
    st.markdown("</div>", unsafe_allow_html=True)
