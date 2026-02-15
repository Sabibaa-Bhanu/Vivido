import streamlit as st

from utils.welcome_ui import render_welcome_page


st.set_page_config(
    page_title="Vivido - Welcome",
    page_icon="assests/logo/vivido_logo2.jpeg",
    layout="centered",
)

render_welcome_page()
