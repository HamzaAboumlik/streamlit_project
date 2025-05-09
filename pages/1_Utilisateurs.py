import streamlit as st
import pandas as pd
from utils.ui import render_navbar, apply_global_css
from utils.database import get_connection, fetch_data, execute_query

st.set_page_config(page_title="Utilisateurs - Gestion Parc Informatique FedEx", layout="wide")

apply_global_css()

if "current_page" not in st.session_state:
    st.session_state.current_page = "Utilisateurs"

render_navbar()

st.markdown('<div class="content">', unsafe_allow_html=True)

st.title("👤 Gestion des Employés")

tab1, tab2, tab3 = st.tabs(["Liste", "Ajouter", "Statistiques"])

with tab1:
    conn = get_connection()
    query = """
    SELECT e.ID_Employe, e.Code_Employe, e.Nom_Employe, e.Prenom_Employe, e.Service_Employe, e.Direction_Employe, e.Statut_Employe
    FROM Employe e
    """
    try:
        users = pd.read_sql(query, conn)
    except Exception as e:
        st.error(f"Erreur lors du chargement des employés : {str(e)}")
        users = pd.DataFrame()
    conn.close()

    search = st.text_input("🔍 Rechercher", key="search_users")
    if search:
        users = users[users.apply(lambda row: search.lower() in str(row).lower(), axis=1)]

    if users.empty:
        st.info("Aucun employé trouvé.")
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
        .st-expander {
            background-color: #f8f9fa;
            border: 1px solid #ddd;
            border-radius: 5px;
            margin: 5px 0;
        }
        .st-expander > div > div {
            padding: 10px;
        }
        .stTextInput > div > input, .stSelectbox > div > select {
            padding: 5px;
            font-size: 14px;
        }
        .stButton>button {
            background-color: #4D148C !important;
            color: white !important;
            border: none !important;
            border-radius: 5px !important;
            padding: 5px 10px !important;
            font-size: 14px !important;
            margin: 0 2px !important;
        }
        .stButton>button:hover {
            background-color: #3A0D6B !important;
        }
        .stButton>button:nth-child(2) {
            background-color: #FF6600 !important;
        }
        .stButton>button:nth-child(2):hover {
            background-color: #E55A00 !important;
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown('<div class="table-header"><div>ID</div><div>Code</div><div>Nom</div><div>Prénom</div><div>Service</div><div>Direction</div><div>Statut</div><div>Actions</div></div>', unsafe_allow_html=True)

        for idx, row in users.iterrows():
            with st.container():
                col1, col2, col3, col4, col5, col6, col7, col8 = st.columns([1, 1, 2, 2, 2, 2, 1, 1])
                with col1: st.write(row["ID_Employe"])
                with col2: st.write(row["Code_Employe"])
                with col3: st.write(row["Nom_Employe"])
                with col4: st.write(row["Prenom_Employe"])
                with col5: st.write(row["Service_Employe"] or "N/A")
                with col6: st.write(row["Direction_Employe"] or "N/A")
                with col7: st.write(row["Statut_Employe"])
                with col8:
                    if st.button("Modifier", key=f"edit_btn_{row['ID_Employe']}", help="Modifier cet employé"):
                        st.session_state[f"action_{row['ID_Employe']}"] = "edit"
                    if st.button("Supprimer", key=f"delete_btn_{row['ID_Employe']}", help="Supprimer cet employé"):
                        st.session_state[f"action_{row['ID_Employe']}"] = "delete"

                action_key = f"action_{row['ID_Employe']}"
                if action_key in st.session_state:
                    if st.session_state[action_key] == "edit":
                        with st.expander("Modifier Employé", expanded=True):
                            with st.form(key=f"edit_form_{row['ID_Employe']}"):
                                code = st.text_input("Code*", value=row['Code_Employe'] or "", max_chars=10)
                                nom = st.text_input("Nom*", value=row['Nom_Employe'] or "", max_chars=40)
                                prenom = st.text_input("Prénom*", value=row['Prenom_Employe'] or "", max_chars=40)
                                conn = get_connection()
                                try:
                                    services = fetch_data("Service", conn)
                                    directions = fetch_data("Direction", conn)
                                except Exception as e:
                                    st.error(f"Erreur lors du chargement des services/directions : {str(e)}")
                                    services = pd.DataFrame()
                                    directions = pd.DataFrame()
                                conn.close()
                                service_options = {row['Service_Service']: row['Service_Service'] for _, row in services.iterrows()}
                                service_options["Aucun"] = None
                                current_service = row['Service_Employe'] if row['Service_Employe'] in service_options else "Aucun"
                                selected_service = st.selectbox("Service", options=list(service_options.keys()), index=list(service_options.keys()).index(current_service), key=f"service_{row['ID_Employe']}")
                                service_employe = service_options[selected_service]
                                direction_options = {row['Direction_Direction']: row['Direction_Direction'] for _, row in directions.iterrows()}
                                direction_options["Aucun"] = None
                                current_direction = row['Direction_Employe'] if row['Direction_Employe'] in direction_options else "Aucun"
                                selected_direction = st.selectbox("Direction", options=list(direction_options.keys()), index=list(direction_options.keys()).index(current_direction), key=f"direction_{row['ID_Employe']}")
                                direction_employe = direction_options[selected_direction]
                                statut = st.selectbox("Statut*", ["Actif", "Inactif"], index=["Actif", "Inactif"].index(row['Statut_Employe']) if row['Statut_Employe'] in ["Actif", "Inactif"] else 0, key=f"statut_{row['ID_Employe']}")
                                col1, col2 = st.columns([1, 1])
                                with col1:
                                    if st.form_submit_button("Mettre à jour"):
                                        if code and nom and prenom:
                                            conn = get_connection()
                                            query = """
                                            UPDATE Employe
                                            SET Code_Employe = ?, Nom_Employe = ?, Prenom_Employe = ?, Service_Employe = ?, Direction_Employe = ?, Statut_Employe = ?
                                            WHERE ID_Employe = ?
                                            """
                                            try:
                                                execute_query(conn, query, (code, nom, prenom, service_employe, direction_employe, statut, row['ID_Employe']))
                                                conn.close()
                                                st.success("Employé mis à jour avec succès.")
                                                del st.session_state[action_key]
                                                st.rerun()
                                            except Exception as e:
                                                conn.close()
                                                st.error(f"Erreur lors de la mise à jour : {str(e)}")
                                        else:
                                            st.warning("Les champs Code, Nom et Prénom sont requis.")
                                with col2:
                                    if st.form_submit_button("Annuler"):
                                        del st.session_state[action_key]
                                        st.rerun()
                    elif st.session_state[action_key] == "delete":
                        with st.expander("Confirmer Suppression", expanded=True):
                            with st.form(key=f"delete_form_{row['ID_Employe']}"):
                                st.markdown(f"Êtes-vous sûr de vouloir supprimer l'employé {row['Nom_Employe']} {row['Prenom_Employe']} ?")
                                confirm = st.checkbox("Confirmer la suppression", key=f"confirm_delete_{row['ID_Employe']}")
                                col1, col2 = st.columns([1, 1])
                                with col1:
                                    submit_button = st.form_submit_button("Supprimer", disabled=not confirm)
                                    if submit_button:
                                        conn = get_connection()
                                        try:
                                            query_check = "SELECT COUNT(*) FROM Affectation WHERE Employe_ID = ?"  # Placeholder; confirm column name
                                            cursor = conn.cursor()
                                            cursor.execute(query_check, (row['ID_Employe'],))
                                            count = cursor.fetchone()[0]
                                            if count > 0:
                                                st.error("Impossible de supprimer : cet employé est lié à des affectations.")
                                            else:
                                                query = "DELETE FROM Employe WHERE ID_Employe = ?"
                                                execute_query(conn, query, (row['ID_Employe'],))
                                                st.success("Employé supprimé avec succès.")
                                                del st.session_state[action_key]
                                                st.rerun()
                                        except Exception as e:
                                            st.error(f"Erreur lors de la suppression : {str(e)}")
                                            if "Invalid column name" in str(e):
                                                st.warning("Vérifiez le nom de la colonne dans la table Affectation ou Employe. Utilisez 'SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME IN ('Employe', 'Affectation');' pour confirmer.")
                                        finally:
                                            conn.close()
                                with col2:
                                    if st.form_submit_button("Annuler"):
                                        del st.session_state[action_key]
                                        st.rerun()

with tab2:
    with st.form("add_user"):
        code = st.text_input("Code*")
        nom = st.text_input("Nom*")
        prenom = st.text_input("Prénom*")
        conn = get_connection()
        try:
            services = fetch_data("Service", conn)
            directions = fetch_data("Direction", conn)
        except Exception as e:
            st.error(f"Erreur lors du chargement des services/directions : {str(e)}")
            services = pd.DataFrame()
            directions = pd.DataFrame()
        conn.close()
        service_options = {row['Service_Service']: row['Service_Service'] for _, row in services.iterrows()}
        service_options["Aucun"] = None
        selected_service = st.selectbox("Service", options=list(service_options.keys()), index=len(service_options)-1)
        service_employe = service_options[selected_service]
        direction_options = {row['Direction_Direction']: row['Direction_Direction'] for _, row in directions.iterrows()}
        direction_options["Aucun"] = None
        selected_direction = st.selectbox("Direction", options=list(direction_options.keys()), index=len(direction_options)-1)
        direction_employe = direction_options[selected_direction]
        statut = st.selectbox("Statut*", ["Actif", "Inactif"])
        if st.form_submit_button("Ajouter"):
            if code and nom and prenom:
                conn = get_connection()
                query = """
                INSERT INTO Employe (Code_Employe, Nom_Employe, Prenom_Employe, Service_Employe, Direction_Employe, Statut_Employe)
                VALUES (?, ?, ?, ?, ?, ?)
                """
                try:
                    execute_query(conn, query, (code, nom, prenom, service_employe, direction_employe, statut))
                    conn.close()
                    st.success("Employé ajouté avec succès.")
                    st.rerun()
                except Exception as e:
                    conn.close()
                    st.error(f"Erreur : Impossible d'ajouter l'employé : {str(e)}")
            else:
                st.warning("Les champs Code, Nom et Prénom sont requis.")

with tab3:
    conn = get_connection()
    query = """
    SELECT e.ID_Employe, e.Nom_Employe, e.Prenom_Employe, e.Service_Employe, e.Direction_Employe, e.Statut_Employe
    FROM Employe e
    """
    try:
        users = pd.read_sql(query, conn)
    except Exception as e:
        st.error(f"Erreur lors du chargement des employés : {str(e)}")
        users = pd.DataFrame()
    conn.close()

    st.metric("Nombre d'employés", len(users))
    if not users.empty:
        users['initial'] = users['Nom_Employe'].str[0].str.upper()
        st.bar_chart(users['initial'].value_counts())

st.markdown('</div>', unsafe_allow_html=True)