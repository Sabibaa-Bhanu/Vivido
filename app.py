import streamlit as st

from backend.database import create_tables
from utils.welcome_ui import render_welcome_page

create_tables()

st.set_page_config(page_title="Vivido", page_icon="assests/logo/vivido_logo2.jpeg", layout="centered")

render_welcome_page()
