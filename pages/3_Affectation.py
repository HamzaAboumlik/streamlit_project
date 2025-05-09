import streamlit as st
import pandas as pd
from utils.ui import render_navbar, apply_global_css
from utils.database import get_connection, fetch_data, execute_query

st.set_page_config(page_title="Affectation - Gestion Parc Informatique FedEx", layout="wide")

apply_global_css()

if "current_page" not in st.session_state:
    st.session_state.current_page = "Affectation"
if "edit_affectation_id" not in st.session_state:
    st.session_state.edit_affectation_id = None
if "delete_affectation_id" not in st.session_state:
    st.session_state.delete_affectation_id = None

render_navbar()

st.markdown('<div class="content">', unsafe_allow_html=True)

st.title("🔄 Gestion des Affectations")

tab1, tab2 = st.tabs(["Liste", "Ajouter Affectation"])

with tab1:
    conn = get_connection()
    query = """
    SELECT af.ID_Affectation, af.ID_Article_Affectation, a.Ref_Article, a.Libelle_Article, 
           af.Service_Employe_Article, af.Date_Affectation, af.Numero_Affectation,
           e.Nom_Employe + ' ' + e.Prenom_Employe AS Employe_Nom
    FROM Affectation af
    JOIN Article a ON af.ID_Article_Affectation = a.ID_Article
    LEFT JOIN Employe e ON af.Service_Employe_Article = e.Service_Employe AND e.Statut_Employe = 'Actif'
    """
    affectations = pd.read_sql(query, conn)
    conn.close()

    if affectations.empty:
        st.info("Aucune affectation trouvée.")
    else:
        st.markdown("""
        <style>
        .table-header {
            background-color: #4D148C;
            color: white;
            padding: 10px;
            font-weight: bold;
            display: flex;
            justify-content: space-between;
        }
        .table-row {
            border-bottom: 1px solid #ddd;
            padding: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .modal {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background-color: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            z-index: 1000;
            width: 400px;
            max-width: 90%;
        }
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: rgba
        }
        .stTextInput > div > input, .stSelectbox > div > select, .stDateInput > div > input {
            padding: 5px;
            font-size: 14px;
        }
        .stButton > button {
            padding: 5px 10px;
            font-size: 14px;
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown('<div class="table-header"><div>ID</div><div>Article</div><div>Service</div><div>Employé</div><div>Date</div><div>Numéro</div><div>Actions</div></div>', unsafe_allow_html=True)

        for idx, row in affectations.iterrows():
            with st.container():
                st.markdown(f'<div class="table-row"><div>{row["ID_Affectation"]}</div><div>{row["Ref_Article"]} - {row["Libelle_Article"]}</div><div>{row["Service_Employe_Article"] or "N/A"}</div><div>{row["Employe_Nom"] or "Non affecté"}</div><div>{row["Date_Affectation"]}</div><div>{row["Numero_Affectation"]}</div><div><button style="background-color:#4D148C;color:white;border:none;padding:5px 10px;border-radius:5px;" onclick="return false;">Actions</button></div></div>', unsafe_allow_html=True)
                col1, col2, col3 = st.columns([8, 1, 1])
                with col2:
                    if st.button("Modifier", key=f"edit_btn_{row['ID_Affectation']}", help="Modifier cette affectation"):
                        st.session_state.edit_affectation_id = row['ID_Affectation']
                with col3:
                    if st.button("Supprimer", key=f"delete_btn_{row['ID_Affectation']}", help="Supprimer cette affectation"):
                        st.session_state.delete_affectation_id = row['ID_Affectation']

        if st.session_state.edit_affectation_id:
            affectation_id = st.session_state.edit_affectation_id
            affectation = affectations[affectations['ID_Affectation'] == affectation_id].iloc[0]
            with st.container():
                st.markdown('<div class="modal-overlay"></div>', unsafe_allow_html=True)
                with st.form(key=f"edit_form_{affectation_id}"):
                    st.markdown('<div class="modal">', unsafe_allow_html=True)
                    st.markdown("<h3>Modifier Affectation</h3>", unsafe_allow_html=True)
                    conn = get_connection()
                    articles = fetch_data("Article", conn)
                    services = fetch_data("Service", conn)
                    conn.close()
                    article_options = {f"{row['Ref_Article']} - {row['Libelle_Article']} (ID: {row['ID_Article']})": row['ID_Article'] for _, row in articles.iterrows()}
                    current_article = next((k for k, v in article_options.items() if v == affectation['ID_Article_Affectation']), list(article_options.keys())[0])
                    selected_article = st.selectbox("Article*", options=list(article_options.keys()), index=list(article_options.keys()).index(current_article))
                    article_id = article_options[selected_article]
                    service_options = {row['Service_Service']: row['Service_Service'] for _, row in services.iterrows()}
                    service_options["Aucun"] = None
                    current_service = affectation['Service_Employe_Article'] if affectation['Service_Employe_Article'] in service_options else "Aucun"
                    selected_service = st.selectbox("Service*", options=list(service_options.keys()), index=list(service_options.keys()).index(current_service))
                    service_employe = service_options[selected_service]
                    date_affectation = st.text_input("Date d'affectation*", value=affectation['Date_Affectation'] or "", max_chars=10)
                    numero_affectation = st.number_input("Numéro d'affectation*", value=int(affectation['Numero_Affectation']) if pd.notnull(affectation['Numero_Affectation']) else 0, min_value=0)
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if st.form_submit_button("Mettre à jour"):
                            if article_id and service_employe and date_affectation and numero_affectation:
                                conn = get_connection()
                                query = """
                                UPDATE Affectation
                                SET ID_Article_Affectation = ?, Service_Employe_Article = ?, Date_Affectation = ?, Numero_Affectation = ?
                                WHERE ID_Affectation = ?
                                """
                                try:
                                    execute_query(conn, query, (article_id, service_employe, date_affectation, numero_affectation, affectation_id))
                                    conn.close()
                                    st.success("Affectation mise à jour avec succès.")
                                    st.session_state.edit_affectation_id = None
                                    st.rerun()
                                except Exception as e:
                                    conn.close()
                                    st.error(f"Erreur lors de la mise à jour. Détail : {str(e)}")
                            else:
                                st.warning("Tous les champs sont requis.")
                    with col2:
                        if st.form_submit_button("Annuler"):
                            st.session_state.edit_affectation_id = None
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state.delete_affectation_id:
            affectation_id = st.session_state.delete_affectation_id
            with st.container():
                st.markdown('<div class="modal-overlay"></div>', unsafe_allow_html=True)
                with st.form(key=f"delete_form_{affectation_id}"):
                    st.markdown('<div class="modal">', unsafe_allow_html=True)
                    st.markdown("<h3>Confirmer Suppression</h3>", unsafe_allow_html=True)
                    st.markdown("Êtes-vous sûr de vouloir supprimer cette affectation ?")
                    if st.checkbox("Confirmer la suppression", key=f"confirm_delete_{affectation_id}"):
                        if st.form_submit_button("Supprimer"):
                            conn = get_connection()
                            query = "DELETE FROM Affectation WHERE ID_Affectation = ?"
                            try:
                                execute_query(conn, query, (affectation_id,))
                                conn.close()
                                st.success("Affectation supprimée avec succès.")
                                st.session_state.delete_affectation_id = None
                                st.rerun()
                            except Exception as e:
                                conn.close()
                                st.error(f"Erreur lors de la suppression. Détail : {str(e)}")
                    if st.form_submit_button("Annuler"):
                        st.session_state.delete_affectation_id = None
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

with tab2:
    with st.form("add_affectation"):
        conn = get_connection()
        articles = fetch_data("Article", conn)
        services = fetch_data("Service", conn)
        conn.close()
        article_options = {f"{row['Ref_Article']} - {row['Libelle_Article']} (ID: {row['ID_Article']})": row['ID_Article'] for _, row in articles.iterrows()}
        selected_article = st.selectbox("Article*", options=list(article_options.keys()))
        article_id = article_options[selected_article]
        service_options = {row['Service_Service']: row['Service_Service'] for _, row in services.iterrows()}
        service_options["Aucun"] = None
        selected_service = st.selectbox("Service*", options=list(service_options.keys()), index=len(service_options)-1)
        service_employe = service_options[selected_service]
        date_affectation = st.text_input("Date d'affectation* (YYYY-MM-DD)")
        numero_affectation = st.number_input("Numéro d'affectation*", min_value=0)
        if st.form_submit_button("Affecter"):
            if article_id and service_employe and date_affectation and numero_affectation:
                conn = get_connection()
                query = """
                INSERT INTO Affectation (ID_Article_Affectation, Service_Employe_Article, Date_Affectation, Numero_Affectation)
                VALUES (?, ?, ?, ?)
                """
                try:
                    execute_query(conn, query, (article_id, service_employe, date_affectation, numero_affectation))
                    conn.close()
                    st.success("Affectation ajoutée avec succès.")
                    st.rerun()
                except Exception as e:
                    conn.close()
                    st.error(f"Erreur : Impossible d'ajouter l'affectation. Détail : {str(e)}")
            else:
                st.warning("Tous les champs sont requis.")

st.markdown('</div>', unsafe_allow_html=True)