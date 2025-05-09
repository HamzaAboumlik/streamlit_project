import streamlit as st
import pandas as pd
from utils.ui import render_navbar, apply_global_css
from utils.database import get_connection, fetch_data

st.set_page_config(page_title="Dashboard", layout="wide")

apply_global_css()

if "current_page" not in st.session_state:
    st.session_state.current_page = "Dashboard"

render_navbar()

st.title("📊 Tableau de bord")

conn = get_connection()
users = fetch_data("utilisateur", conn)
materiel = fetch_data("materiel", conn)
conn.close()

col1, col2 = st.columns(2)
col1.metric("Utilisateurs", len(users))
col2.metric("Matériels", len(materiel))

st.subheader("Répartition du matériel par statut")
if not materiel.empty:
    st.bar_chart(materiel["statut"].value_counts())