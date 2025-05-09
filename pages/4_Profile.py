import streamlit as st
import pandas as pd
import base64
from utils.ui import render_navbar, apply_global_css
from utils.database import get_connection, fetch_data, execute_query

# Page config
st.set_page_config(page_title="Profile - Gestion Parc Informatique FedEx", layout="wide")

# Apply global CSS
apply_global_css()
if "current_page" not in st.session_state:
    st.session_state.current_page = "Profile"

# Navbar with logo
render_navbar()

# Content wrapper to avoid overlap with fixed navbar
st.markdown('<div class="content">', unsafe_allow_html=True)

# Content