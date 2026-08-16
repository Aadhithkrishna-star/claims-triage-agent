import streamlit as st

st.title("Test")
name = st.text_input("Your name")

if st.button("Say Hello"):
    st.write(f"Hello {name}!")