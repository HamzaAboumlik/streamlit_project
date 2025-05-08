import streamlit as st
import pyodbc
import pandas as pd



def get_connection():
    return pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=localhost\\TEST;'
        'DATABASE=gestion_parc;'
        'Trusted_Connection=yes;'
    )


def fetch_users(conn):
    query = "SELECT * FROM utilisateur"
    return pd.read_sql(query, conn)

def add_user(conn, nom, prenom, adresse):
    cursor = conn.cursor()
    cursor.execute("INSERT INTO utilisateur (nom, prenom, adresse) VALUES (?, ?, ?)", (nom, prenom, adresse))
    conn.commit()

def delete_user(conn, user_id):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM utilisateur WHERE id = ?", (user_id,))
    conn.commit()

def update_user(conn, user_id, nom, prenom, adresse):
    cursor = conn.cursor()
    cursor.execute("UPDATE utilisateur SET nom=?, prenom=?, adresse=? WHERE id=?", (nom, prenom, adresse, user_id))
    conn.commit()


menu = [" Afficher", " Ajouter"]
choice = st.sidebar.radio("Navigation", menu)

conn = get_connection()
users = fetch_users(conn)


if choice == " Afficher":
    st.subheader(" Liste des utilisateurs")

    search_term = st.text_input("🔍 Rechercher par nom ou prénom")
    if search_term:
        users = users[
            users['nom'].str.contains(search_term, case=False) |
            users['prenom'].str.contains(search_term, case=False)
        ]

    if users.empty:
        st.info("Aucun utilisateur trouvé.")
    else:
        st.data_editor(
            users,
            column_config={
                "id": st.column_config.NumberColumn("ID", width="small"),
                "nom": st.column_config.TextColumn("Nom"),
                "prenom": st.column_config.TextColumn("Prénom"),
                "adresse": st.column_config.TextColumn("Adresse")
            },
            use_container_width=True,
            hide_index=True,
            disabled=True
        )

        st.markdown("---")
        st.subheader(" Modifier ou  Supprimer un utilisateur")
        selected_id = st.selectbox("Sélectionnez un ID", users['id'])

        selected_user = users[users['id'] == selected_id].iloc[0]
        col1, col2 = st.columns(2)
        with col1:
            nom = st.text_input("Nom", selected_user['nom'])
            prenom = st.text_input("Prénom", selected_user['prenom'])
        with col2:
            adresse = st.text_input("Adresse", selected_user['adresse'])

        if st.button("Mettre à jour"):
            update_user(conn, selected_id, nom, prenom, adresse)
            st.success(" Utilisateur mis à jour")
            st.rerun()

        if st.button("Supprimer", type="primary"):
            delete_user(conn, selected_id)
            st.success("️ Utilisateur supprimé")
            st.rerun()


elif choice == " Ajouter":
    st.subheader(" Ajouter un nouvel utilisateur")
    col1, col2 = st.columns(2)
    with col1:
        nom = st.text_input("Nom")
        prenom = st.text_input("Prénom")
    with col2:
        adresse = st.text_input("Adresse")

    if st.button("Ajouter"):
        if nom and prenom and adresse:
            add_user(conn, nom, prenom, adresse)
            st.success("✅ Utilisateur ajouté")
        else:
            st.warning("⚠️ Veuillez remplir tous les champs.")
