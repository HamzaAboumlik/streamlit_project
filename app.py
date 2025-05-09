import streamlit as st
import pandas as pd
from utils.ui import render_navbar, apply_global_css
from utils.database import get_connection, fetch_data

st.set_page_config(page_title="Dashboard - Gestion Parc Informatique FedEx", layout="wide")

apply_global_css()

if "current_page" not in st.session_state:
    st.session_state.current_page = "Dashboard"

render_navbar()

st.title("📊 Tableau de bord")

conn = get_connection()
query_employes = "SELECT * FROM Employe"
query_articles = "SELECT * FROM Article"
query_affectations = "SELECT * FROM Affectation"
employes = pd.read_sql(query_employes, conn)
articles = pd.read_sql(query_articles, conn)
affectations = pd.read_sql(query_affectations, conn)
conn.close()

col1, col2, col3 = st.columns(3)
col1.metric("Employés", len(employes))
col2.metric("Articles", len(articles))
col3.metric("Affectations", len(affectations))

st.subheader("Répartition des articles par statut")
if not articles.empty:
    st.bar_chart(articles["Statut_Article"].value_counts())

st.subheader("Répartition des employés par service")
if not employes.empty:
    st.bar_chart(employes["Service_Employe"].value_counts())