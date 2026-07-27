import streamlit as st

st.title("🚀 Streamlit Online Test App")


user_name = st.text_input("Enter your name:", placeholder="Type here...")


age = st.slider("Select your age:", min_value=0, max_value=100, value=25)

if st.button("Submit Profile"):
    if user_name:
        st.success(f"Hello {user_name}! Your profile is ready.")
        st.write(f"You are **{age}** years old.")
        st.balloons()
    else:
        st.warning("Please enter a name before submitting.")
