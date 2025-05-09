import pyodbc
import pandas as pd
import streamlit as st

def get_connection():
    """Établit une connexion à la base de données SQL Server"""
    return pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=localhost\\TEST;'
        'DATABASE=gestion_parc_informatique;'
        'Trusted_Connection=yes;'
    )

def fetch_data(table_name, conn):
    """Récupère toutes les données d'une table"""
    query = f"SELECT * FROM {table_name}"
    return pd.read_sql(query, conn)

def execute_query(conn, query, params=None):
    """Exécute une requête SQL avec des paramètres optionnels"""
    cursor = conn.cursor()
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Erreur lors de l'exécution de la requête: {str(e)}")
        return False