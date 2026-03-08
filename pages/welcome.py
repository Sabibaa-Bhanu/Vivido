import streamlit as st

from utils.welcome_ui import render_welcome_page


st.set_page_config(
    page_title="Vivido - Welcome",
    page_icon="assests/logo/vivido_logo2.jpeg",
    layout="centered",
)

if (
    st.session_state.get("logged_in")
    or (
        st.session_state.get("user_id")
        and st.session_state.get("current_user")
    )
):
    st.session_state["logged_in"] = True
    st.switch_page("pages/dashboard.py")

render_welcome_page()
