import streamlit as st
import pandas as pd
from utils.ui import render_navbar, apply_global_css
from utils.database import get_connection, fetch_data, execute_query

st.set_page_config(page_title="Matériel - Gestion Parc Informatique FedEx", layout="wide")

apply_global_css()

if "current_page" not in st.session_state:
    st.session_state.current_page = "Matériel"
if "edit_material_id" not in st.session_state:
    st.session_state.edit_material_id = None
if "delete_material_id" not in st.session_state:
    st.session_state.delete_material_id = None

render_navbar()

st.markdown('<div class="content">', unsafe_allow_html=True)

st.title("💻 Gestion du Matériel")

tab1, tab2 = st.tabs(["Inventaire", "Ajouter Article"])

with tab1:
    conn = get_connection()
    query = """
    SELECT a.ID_Article, a.Ref_Article, a.Libelle_Article, a.Type_Article, a.Marque_Article, a.Statut_Article, 
           a.Service_Employe_Article, a.Date_Affectation_Article, 
           e.Nom_Employe + ' ' + e.Prenom_Employe AS Employe_Nom
    FROM Article a
    LEFT JOIN Affectation af ON a.ID_Article = af.ID_Article_Affectation
    LEFT JOIN Employe e ON a.Service_Employe_Article = e.Service_Employe AND e.Statut_Employe = 'Actif'
    """
    data = pd.read_sql(query, conn)
    conn.close()

    if not data.empty:
        type_filter = st.selectbox("Filtrer par type", ["Tous"] + sorted(data["Type_Article"].dropna().unique()))
        filtered_data = data if type_filter == "Tous" else data[data["Type_Article"] == type_filter]

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
            background-color: rgba(0,0,0,0.5);
            z-index: 999;
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

        st.markdown('<div class="table-header"><div>ID</div><div>Référence</div><div>Libellé</div><div>Type</div><div>Marque</div><div>Statut</div><div>Service</div><div>Employé</div><div>Actions</div></div>', unsafe_allow_html=True)

        for idx, row in filtered_data.iterrows():
            with st.container():
                st.markdown(f'<div class="table-row"><div>{row["ID_Article"]}</div><div>{row["Ref_Article"]}</div><div>{row["Libelle_Article"]}</div><div>{row["Type_Article"]}</div><div>{row["Marque_Article"]}</div><div>{row["Statut_Article"]}</div><div>{row["Service_Employe_Article"] or "N/A"}</div><div>{row["Employe_Nom"] or "Non affecté"}</div><div><button style="background-color:#4D148C;color:white;border:none;padding:5px 10px;border-radius:5px;" onclick="return false;">Actions</button></div></div>', unsafe_allow_html=True)
                col1, col2, col3 = st.columns([8, 1, 1])
                with col2:
                    if st.button("Modifier", key=f"edit_btn_{row['ID_Article']}", help="Modifier cet article"):
                        st.session_state.edit_material_id = row['ID_Article']
                with col3:
                    if st.button("Supprimer", key=f"delete_btn_{row['ID_Article']}", help="Supprimer cet article"):
                        st.session_state.delete_material_id = row['ID_Article']

        if st.session_state.edit_material_id:
            article_id = st.session_state.edit_material_id
            article = filtered_data[filtered_data['ID_Article'] == article_id].iloc[0]
            with st.container():
                st.markdown('<div class="modal-overlay"></div>', unsafe_allow_html=True)
                with st.form(key=f"edit_form_{article_id}"):
                    st.markdown('<div class="modal">', unsafe_allow_html=True)
                    st.markdown("<h3>Modifier Article</h3>", unsafe_allow_html=True)
                    ref = st.text_input("Référence*", value=article['Ref_Article'] or "", max_chars=20)
                    libelle = st.text_input("Libellé*", value=article['Libelle_Article'] or "", max_chars=50)
                    type_article = st.text_input("Type*", value=article['Type_Article'] or "", max_chars=50)
                    marque = st.text_input("Marque*", value=article['Marque_Article'] or "", max_chars=40)
                    statut = st.selectbox("Statut*", ["NON AFFECTE", "AFFECTE", "EN MAINTENANCE"], index=["NON AFFECTE", "AFFECTE", "EN MAINTENANCE"].index(article['Statut_Article']) if article['Statut_Article'] in ["NON AFFECTE", "AFFECTE", "EN MAINTENANCE"] else 0)
                    conn = get_connection()
                    services = fetch_data("Service", conn)
                    service_options = {row['Service_Service']: row['Service_Service'] for _, row in services.iterrows()}
                    service_options["Aucun"] = None
                    current_service = article['Service_Employe_Article'] if article['Service_Employe_Article'] in service_options else "Aucun"
                    selected_service = st.selectbox("Service", options=list(service_options.keys()), index=list(service_options.keys()).index(current_service))
                    service_employe = service_options[selected_service]
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if st.form_submit_button("Mettre à jour"):
                            if ref and libelle and type_article and marque:
                                conn = get_connection()
                                query = """
                                UPDATE Article
                                SET Ref_Article = ?, Libelle_Article = ?, Type_Article = ?, Marque_Article = ?, Statut_Article = ?, Service_Employe_Article = ?
                                WHERE ID_Article = ?
                                """
                                try:
                                    execute_query(conn, query, (ref, libelle, type_article, marque, statut, service_employe, article_id))
                                    conn.close()
                                    st.success("Article mis à jour avec succès.")
                                    st.session_state.edit_material_id = None
                                    st.rerun()
                                except Exception as e:
                                    conn.close()
                                    st.error(f"Erreur lors de la mise à jour. Détail : {str(e)}")
                            else:
                                st.warning("Les champs Référence, Libellé, Type et Marque sont requis.")
                    with col2:
                        if st.form_submit_button("Annuler"):
                            st.session_state.edit_material_id = None
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state.delete_material_id:
            article_id = st.session_state.delete_material_id
            with st.container():
                st.markdown('<div class="modal-overlay"></div>', unsafe_allow_html=True)
                with st.form(key=f"delete_form_{article_id}"):
                    st.markdown('<div class="modal">', unsafe_allow_html=True)
                    st.markdown("<h3>Confirmer Suppression</h3>", unsafe_allow_html=True)
                    st.markdown("Êtes-vous sûr de vouloir supprimer cet article ?")
                    if st.checkbox("Confirmer la suppression", key=f"confirm_delete_{article_id}"):
                        if st.form_submit_button("Supprimer"):
                            conn = get_connection()
                            query = "DELETE FROM Affectation WHERE ID_Article_Affectation = ?"
                            execute_query(conn, query, (article_id,))
                            query = "DELETE FROM Article WHERE ID_Article = ?"
                            try:
                                execute_query(conn, query, (article_id,))
                                conn.close()
                                st.success("Article supprimé avec succès.")
                                st.session_state.delete_material_id = None
                                st.rerun()
                            except Exception as e:
                                conn.close()
                                st.error(f"Erreur lors de la suppression. Détail : {str(e)}")
                    if st.form_submit_button("Annuler"):
                        st.session_state.delete_material_id = None
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

    else:
        st.info("Aucun article trouvé.")

with tab2:
    with st.form("add_article", clear_on_submit=True):
        ref = st.text_input("Référence*")
        libelle = st.text_input("Libellé*")
        type_article = st.text_input("Type*")
        marque = st.text_input("Marque*")
        statut = st.selectbox("Statut*", ["NON AFFECTE", "AFFECTE", "EN MAINTENANCE"])
        conn = get_connection()
        services = fetch_data("Service", conn)
        conn.close()
        service_options = {row['Service_Service']: row['Service_Service'] for _, row in services.iterrows()}
        service_options["Aucun"] = None
        selected_service = st.selectbox("Service", options=list(service_options.keys()), index=len(service_options)-1)
        service_employe = service_options[selected_service]
        if st.form_submit_button("Ajouter"):
            if ref and libelle and type_article and marque:
                conn = get_connection()
                query = """
                INSERT INTO Article (Ref_Article, Libelle_Article, Type_Article, Marque_Article, Statut_Article, Service_Employe_Article)
                VALUES (?, ?, ?, ?, ?, ?)
                """
                try:
                    execute_query(conn, query, (ref, libelle, type_article, marque, statut, service_employe))
                    conn.close()
                    st.success("Article ajouté avec succès.")
                    st.rerun()
                except Exception as e:
                    conn.close()
                    st.error(f"Erreur : Impossible d'ajouter l'article. Détail : {str(e)}")
            else:
                st.warning("Les champs Référence, Libellé, Type et Marque sont requis.")

st.markdown('</div>', unsafe_allow_html=True)