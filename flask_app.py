from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import pyodbc
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
import pyodbc
from datetime import datetime
import logging

logging.basicConfig(level=logging.DEBUG, filename='app.log', filemode='a',
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
app = Flask(__name__)
app.secret_key = 'votre_cle_secrete'


# Configuration de la connexion à la base de données
def get_db_connection():
    conn_str = (
        "DRIVER={SQL Server};"
        "SERVER=localhost\\TEST;"
        "DATABASE=gestion_parc_informatique;"
        "Trusted_Connection=yes;"
    )
    return pyodbc.connect(conn_str)


# Routes principales
@app.route('/')
def index():
    return render_template('index.html')


# Gestion des utilisateurs
@app.route('/utilisateurs')
def utilisateurs():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Employe")
    employes = cursor.fetchall()
    conn.close()
    return render_template('utilisateurs.html', employes=employes)


@app.route('/utilisateur/ajouter', methods=['GET', 'POST'])
def ajouter_utilisateur():
    if request.method == 'POST':
        # Récupérer les données du formulaire
        data = request.form

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
                       INSERT INTO Employe (Code_Employe, Badge_Employe, CIN_Employe, Nom_Employe, Prenom_Employe,
                                            Fonction_Employe, Service_Employe, Direction_Employe, Affectation_Employe,
                                            Statut_Employe, Date_Sortie_Employe)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                       """, (
                           data['code'], data['badge'], data['cin'], data['nom'], data['prenom'],
                           data['fonction'], data['service'], data['direction'], data['affectation'],
                           data['statut'], data['date_sortie']
                       ))
        conn.commit()
        conn.close()
        flash('Utilisateur ajouté avec succès', 'success')
        return redirect(url_for('utilisateurs'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Direction")
    directions = cursor.fetchall()
    cursor.execute("SELECT * FROM Service")
    services = cursor.fetchall()
    conn.close()
    return render_template('ajouter_utilisateur.html', directions=directions, services=services)


@app.route('/utilisateur/editer/<int:id>', methods=['GET', 'POST'])
def editer_utilisateur(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        data = request.form
        cursor.execute("""
                       UPDATE Employe
                       SET Code_Employe        = ?,
                           Badge_Employe       = ?,
                           CIN_Employe         = ?,
                           Nom_Employe         = ?,
                           Prenom_Employe      = ?,
                           Fonction_Employe    = ?,
                           Service_Employe     = ?,
                           Direction_Employe   = ?,
                           Affectation_Employe = ?,
                           Statut_Employe      = ?,
                           Date_Sortie_Employe = ?
                       WHERE ID_Employe = ?
                       """, (
                           data['code'], data['badge'], data['cin'], data['nom'], data['prenom'],
                           data['fonction'], data['service'], data['direction'], data['affectation'],
                           data['statut'], data['date_sortie'], id
                       ))
        conn.commit()
        conn.close()
        flash('Utilisateur mis à jour avec succès', 'success')
        return redirect(url_for('utilisateurs'))

    cursor.execute("SELECT * FROM Employe WHERE ID_Employe = ?", (id,))
    employe = cursor.fetchone()
    cursor.execute("SELECT * FROM Direction")
    directions = cursor.fetchall()
    cursor.execute("SELECT * FROM Service")
    services = cursor.fetchall()
    conn.close()

    if employe:
        return render_template('edit_utilisateur.html', employe=employe, directions=directions, services=services)
    else:
        flash('Utilisateur non trouvé', 'danger')
        return redirect(url_for('utilisateurs'))

@app.route('/utilisateur/supprimer/<int:id>', methods=['POST'])
def supprimer_utilisateur(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Employe WHERE ID_Employe = ?", (id,))
    conn.commit()
    conn.close()
    flash('Utilisateur supprimé avec succès', 'success')
    return redirect(url_for('utilisateurs'))
# Gestion du matériel
@app.route('/materiel')
def materiel():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Article")
    articles = cursor.fetchall()
    conn.close()
    return render_template('materiel.html', articles=articles)


from flask import Flask, render_template, request, redirect, url_for, flash
import pyodbc
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, filename='app.log', filemode='a',
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ... (other imports and app setup)

@app.route('/materiel/ajouter', methods=['GET', 'POST'])
def ajouter_materiel():
    # Predefined lists for Statut_Article and Etat_Article
    statuts = ['affecté', 'non affecté']
    etats = ['disponible', 'non disponible', 'en maintenance', 'occupé']
    types = ['ordinateur', 'imprimante', 'scanner', 'autre']  # Example types
    categories = ['informatique', 'bureautique', 'réseau']  # Example categories
    locations = ['bureau 1', 'bureau 2', 'entrepôt', 'autre']  # Example locations

    if request.method == 'POST':
        data = request.form
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # Validate required fields
            required_fields = ['ref', 'libelle', 'type', 'categorie', 'marque', 'etat', 'statut']
            for field in required_fields:
                if not data.get(field) or data.get(field).strip() == '':
                    raise ValueError(f"Le champ {field} est requis.")

            # Get column lengths for all VARCHAR columns
            varchar_columns = [
                'Ref_Article', 'Libelle_Article', 'Type_Article', 'Categorie_Article',
                'Marque_Article', 'Description_Article', 'Etat_Article', 'Statut_Article',
                'Location_Article', 'Affecter_au_Article', 'Service_Employe_Article',
                'Agence_Article', 'Compte_Comptable_Article', 'modifier_o',
                'Achete_Par_Article', 'Affecte_A_Article', 'Numero_Affectation'
            ]
            column_lengths = {}
            for col in varchar_columns:
                cursor.execute("""
                    SELECT CHARACTER_MAXIMUM_LENGTH
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_NAME = 'Article' AND COLUMN_NAME = ?
                """, (col,))
                length = cursor.fetchone()
                column_lengths[col] = length[0] if length and length[0] is not None else 50  # Default to 50 if unknown

            # Prepare form data with dynamic truncation
            ref = data.get('ref', '')[:column_lengths['Ref_Article']]
            libelle = data.get('libelle', '')[:column_lengths['Libelle_Article']]
            type_article = data.get('type', '')[:column_lengths['Type_Article']]
            categorie = data.get('categorie', '')[:column_lengths['Categorie_Article']]
            marque = data.get('marque', '')[:column_lengths['Marque_Article']]
            description = data.get('description', '')[:column_lengths['Description_Article']]
            etat = data.get('etat', '')[:column_lengths['Etat_Article']]
            statut = data.get('statut', '')[:column_lengths['Statut_Article']]
            location = data.get('location', '')[:column_lengths['Location_Article']]
            affecter_au = data.get('affecter_au', '')[:column_lengths['Affecter_au_Article']]
            service_employe = data.get('service_employe', '')[:column_lengths['Service_Employe_Article']]
            agence = data.get('agence', '')[:column_lengths['Agence_Article']]
            compte_comptable = data.get('compte_comptable', '')[:column_lengths['Compte_Comptable_Article']]
            modifier_o = data.get('modifier_o', '')[:column_lengths['modifier_o']]
            achete_par = data.get('achete_par', '')[:column_lengths['Achete_Par_Article']]
            affecte_a = data.get('affecte_a', '')[:column_lengths['Affecte_A_Article']]
            numero_affectation = data.get('numero_affectation', '')[:column_lengths['Numero_Affectation']]

            # Log all string values to identify truncation issues
            logger.debug(f"Insert values: ref={ref} (len={len(ref)}), libelle={libelle} (len={len(libelle)}), "
                        f"type={type_article} (len={len(type_article)}), categorie={categorie} (len={len(categorie)}), "
                        f"marque={marque} (len={len(marque)}), description={description} (len={len(description)}), "
                        f"etat={etat} (len={len(etat)}), statut={statut} (len={len(statut)}), "
                        f"location={location} (len={len(location)}), affecter_au={affecter_au} (len={len(affecter_au)}), "
                        f"service_employe={service_employe} (len={len(service_employe)}), agence={agence} (len={len(agence)}), "
                        f"compte_comptable={compte_comptable} (len={len(compte_comptable)}), "
                        f"modifier_o={modifier_o} (len={len(modifier_o)}), achete_par={achete_par} (len={len(achete_par)}), "
                        f"affecte_a={affecte_a} (len={len(affecte_a)}), numero_affectation={numero_affectation} (len={len(numero_affectation)})")

            # Validate Statut_Article and Etat_Article
            if not statut or statut not in statuts:
                raise ValueError(f"Statut invalide. Choisissez parmi : {', '.join(statuts)}")
            if not etat or etat not in etats:
                raise ValueError(f"État invalide. Choisissez parmi : {', '.join(etats)}")

            # Validate dates
            date_achat = data.get('date_achat') or None
            date_echeance = data.get('date_echeance') or None
            date_affectation = data.get('date_affectation') or None
            date_restitution = data.get('date_restitution') or None
            if date_achat and date_achat.strip():
                try:
                    date_achat = datetime.strptime(date_achat, '%Y-%m-%d').strftime('%Y-%m-%d')
                except ValueError:
                    raise ValueError("Format de date d'achat invalide (utilisez AAAA-MM-JJ).")
            if date_echeance and date_echeance.strip():
                try:
                    date_echeance = datetime.strptime(date_echeance, '%Y-%m-%d').strftime('%Y-%m-%d')
                except ValueError:
                    raise ValueError("Format de date d'échéance invalide (utilisez AAAA-MM-JJ).")
            if date_affectation and date_affectation.strip():
                try:
                    date_affectation = datetime.strptime(date_affectation, '%Y-%m-%d').strftime('%Y-%m-%d')
                except ValueError:
                    raise ValueError("Format de date d'affectation invalide (utilisez AAAA-MM-JJ).")
            if date_restitution and date_restitution.strip():
                try:
                    date_restitution = datetime.strptime(date_restitution, '%Y-%m-%d').strftime('%Y-%m-%d')
                except ValueError:
                    raise ValueError("Format de date de restitution invalide (utilisez AAAA-MM-JJ).")

            # Log parameters
            logger.debug(f"Adding article: ref={ref}, libelle={libelle}, statut={statut}, etat={etat}, location={location}")

            # Insert into Article
            cursor.execute("""
                INSERT INTO Article (Ref_Article, Libelle_Article, Type_Article, Categorie_Article,
                                    Marque_Article, Description_Article, Date_Achat_Article,
                                    Date_Echeance_Article, Etat_Article, Statut_Article, Location_Article,
                                    Affecter_au_Article, Service_Employe_Article, Agence_Article,
                                    Date_Affectation_Article, Date_Restitution_Article,
                                    Compte_Comptable_Article, modifier_o, Achete_Par_Article,
                                    Affecte_A_Article, Numero_Affectation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (ref, libelle, type_article, categorie, marque, description, date_achat,
                  date_echeance, etat, statut, location, affecter_au, service_employe, agence,
                  date_affectation, date_restitution, compte_comptable, modifier_o,
                  achete_par, affecte_a, numero_affectation))

            conn.commit()
            flash('Matériel ajouté avec succès', 'success')
            return redirect(url_for('materiel'))

        except ValueError as ve:
            conn.rollback()
            flash(str(ve), 'danger')
        except pyodbc.DataError as de:
            conn.rollback()
            error_msg = str(de)
            logger.error(f"Data error: {error_msg}")
            if '22001' in error_msg:
                flash('Erreur : Une valeur saisie est trop longue pour une colonne de la base de données. Vérifiez les longueurs des champs.', 'danger')
            else:
                flash(f'Erreur lors de l\'ajout du matériel : {error_msg}', 'danger')
        except Exception as e:
            conn.rollback()
            logger.error(f"Error adding materiel: {str(e)}")
            flash(f'Erreur lors de l\'ajout du matériel : {str(e)}', 'danger')
        finally:
            conn.close()

    return render_template('ajouter_materiel.html', statuts=statuts, etats=etats, types=types,
                           categories=categories, locations=locations)
@app.route('/materiel/editer/<int:id>', methods=['GET', 'POST'])
def editer_materiel(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        data = request.form
        # Fetch current article data
        cursor.execute("SELECT * FROM Article WHERE ID_Article = ?", (id,))
        article = cursor.fetchone()
        # Map tuple to dictionary for easier access (assuming row_factory isn’t set)
        columns = [desc[0] for desc in cursor.description]
        article_dict = dict(zip(columns, article))

        # Use form data or fallback to current values
        ref = data.get('ref', article_dict['Ref_Article'])
        libelle = data.get('libelle', article_dict['Libelle_Article'])
        type_article = data.get('type', article_dict['Type_Article'])
        categorie = data.get('categorie', article_dict['Categorie_Article'])
        marque = data.get('marque', article_dict['Marque_Article'])
        description = data.get('description', article_dict['Description_Article'])
        date_achat = data.get('date_achat', article_dict['Date_Achat_Article'])
        date_echeance = data.get('date_echeance', article_dict['Date_Echeance_Article'])
        etat = data.get('etat', article_dict['Etat_Article'])
        statut = data.get('statut', article_dict['Statut_Article'])
        location = data.get('location', article_dict['Location_Article'])
        affecter_au = data.get('affecter_au', article_dict['Affecter_au_Article'])
        service_employe = data.get('service_employe', article_dict['Service_Employe_Article'])
        agence = data.get('agence', article_dict['Agence_Article'])
        date_affectation = data.get('date_affectation', article_dict['Date_Affectation_Article'])
        date_restitution = data.get('date_restitution', article_dict['Date_Restitution_Article'])
        compte_comptable = data.get('compte_comptable', article_dict['Compte_Comptable_Article'])
        modifier_o = data.get('modifier_o', article_dict['modifier_o'])
        achete_par = data.get('achete_par', article_dict['Achete_Par_Article'])
        affecte_a = data.get('affecte_a', article_dict['Affecte_A_Article'])
        numero_affectation = data.get('numero_affectation', article_dict['Numero_Affectation'])

        cursor.execute("""
                       UPDATE Article
                       SET Ref_Article              = ?,
                           Libelle_Article          = ?,
                           Type_Article             = ?,
                           Categorie_Article        = ?,
                           Marque_Article           = ?,
                           Description_Article      = ?,
                           Date_Achat_Article       = ?,
                           Date_Echeance_Article    = ?,
                           Etat_Article             = ?,
                           Statut_Article           = ?,
                           Location_Article         = ?,
                           Affecter_au_Article      = ?,
                           Service_Employe_Article  = ?,
                           Agence_Article           = ?,
                           Date_Affectation_Article = ?,
                           Date_Restitution_Article = ?,
                           Compte_Comptable_Article = ?,
                           modifier_o               = ?,
                           Achete_Par_Article       = ?,
                           Affecte_A_Article        = ?,
                           Numero_Affectation       = ?
                       WHERE ID_Article = ?
                       """, (
                           ref, libelle, type_article, categorie, marque, description, date_achat,
                           date_echeance, etat, statut, location, affecter_au, service_employe, agence,
                           date_affectation, date_restitution, compte_comptable, modifier_o, achete_par,
                           affecte_a, numero_affectation, id
                       ))
        conn.commit()
        conn.close()
        flash('Matériel mis à jour avec succès', 'success')
        return redirect(url_for('materiel'))

    cursor.execute("SELECT * FROM Article WHERE ID_Article = ?", (id,))
    article = cursor.fetchone()
    conn.close()

    if article:
        return render_template('edit_materiel.html', article=article)
    else:
        flash('Matériel non trouvé', 'danger')
        return redirect(url_for('materiel'))

@app.route('/materiel/supprimer/<int:id>', methods=['POST'])
def supprimer_materiel(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Article WHERE ID_Article = ?", (id,))
    conn.commit()
    conn.close()
    flash('Matériel supprimé avec succès', 'success')
    return redirect(url_for('materiel'))
# Gestion des affectations
@app.route('/affectations')
def affectations():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Récupérer les affectations avec les détails du matériel et de l'employé
    cursor.execute("""
                   SELECT a.ID_Affectation,
                          ar.Libelle_Article,
                          e.Nom_Employe,
                          e.Prenom_Employe,
                          a.Date_Affectation,
                          a.Date_Restitution_Affectation,
                          a.Service_Employe_Article
                   FROM Affectation a
                            LEFT JOIN Article ar ON a.ID_Article_Affectation = ar.ID_Article
                            LEFT JOIN Employe e ON a.Affecter_au_Article = e.Code_Employe
                   """)
    affectations = cursor.fetchall()

    # Récupérer la liste des matériels disponibles
    cursor.execute("SELECT ID_Article, Libelle_Article FROM Article WHERE Statut_Article = 'NON AFFECTE'")
    articles = cursor.fetchall()

    # Récupérer la liste des employés
    cursor.execute("SELECT Code_Employe, Nom_Employe, Prenom_Employe FROM Employe")
    employes = cursor.fetchall()

    conn.close()

    return render_template('affectation.html', affectations=affectations, articles=articles, employes=employes)


from flask import Flask, render_template, request, redirect, url_for, flash
import pyodbc
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# ... (other imports and app setup)

from flask import Flask, render_template, request, redirect, url_for, flash
import pyodbc
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, filename='app.log', filemode='a',
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ... (other imports and app setup)

@app.route('/affectation/ajouter', methods=['POST'])
def ajouter_affectation():
    data = request.form
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Validate and convert inputs
        article_id = int(data.get('article')) if data.get('article') else None
        employe_code = data.get('employe')
        date_affectation = data.get('date_affectation')
        date_restitution = data.get('date_restitution') or None
        numero_affectation = data.get('numero_affectation') or "AUTO_" + datetime.now().strftime('%Y%m%d%H%M%S')

        if not article_id:
            raise ValueError("Matériel non sélectionné.")
        if not employe_code:
            raise ValueError("Employé non sélectionné.")
        if not date_affectation:
            raise ValueError("Date d'affectation requise.")

        # Validate article
        cursor.execute("SELECT Statut_Article FROM Article WHERE ID_Article = ?", (article_id,))
        article = cursor.fetchone()
        if not article:
            raise ValueError("Matériel non trouvé.")
        if article[0] == 'AFFECTE':
            raise ValueError("Ce matériel est déjà affecté.")

        # Validate employee and get service
        cursor.execute("SELECT Service_Employe FROM Employe WHERE Code_Employe = ?", (employe_code,))
        employe = cursor.fetchone()
        if not employe:
            raise ValueError("Employé non trouvé.")
        service = employe[0] or "Inconnu"

        # Get column lengths from database
        cursor.execute("SELECT CHARACTER_MAXIMUM_LENGTH FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'Affectation' AND COLUMN_NAME = 'Service_Employe_Article'")
        service_max_length = cursor.fetchone()[0] or 50
        cursor.execute("SELECT CHARACTER_MAXIMUM_LENGTH FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'Affectation' AND COLUMN_NAME = 'Numero_Affectation'")
        numero_max_length = cursor.fetchone()[0] or 20
        cursor.execute("SELECT CHARACTER_MAXIMUM_LENGTH FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'Affectation' AND COLUMN_NAME = 'Affecter_au_Article'")
        employe_code_max_length = cursor.fetchone()[0] or 50

        # Truncate strings to fit column lengths
        if len(service) > service_max_length:
            service = service[:service_max_length]
        if len(numero_affectation) > numero_max_length:
            numero_affectation = numero_affectation[:numero_max_length]
        if len(employe_code) > employe_code_max_length:
            employe_code = employe_code[:employe_code_max_length]

        # Convert and validate dates as strings
        try:
            date_affectation_str = datetime.strptime(date_affectation, '%Y-%m-%d').strftime('%Y-%m-%d')
            if datetime.strptime(date_affectation, '%Y-%m-%d').date() > datetime.now().date():
                raise ValueError("La date d'affectation ne peut pas être future.")
        except ValueError as ve:
            raise ValueError("Format de date d'affectation invalide (utilisez AAAA-MM-JJ).")

        date_restitution_str = None
        if date_restitution and date_restitution.strip():
            try:
                date_restitution_str = datetime.strptime(date_restitution, '%Y-%m-%d').strftime('%Y-%m-%d')
                if datetime.strptime(date_restitution, '%Y-%m-%d').date() < datetime.strptime(date_affectation, '%Y-%m-%d').date():
                    raise ValueError("La date de restitution doit être après la date d'affectation.")
            except ValueError as ve:
                raise ValueError("Format de date de restitution invalide (utilisez AAAA-MM-JJ).")

        # Validate numero_affectation uniqueness
        cursor.execute("SELECT COUNT(*) FROM Affectation WHERE Numero_Affectation = ?", (numero_affectation,))
        if cursor.fetchone()[0] > 0:
            raise ValueError("Numéro d'affectation déjà utilisé.")

        # Log parameters for debugging
        logger.debug(f"Parameters: article_id={article_id}, service={service} (len={len(service)}), "
                     f"date_affectation={date_affectation_str}, date_restitution={date_restitution_str}, "
                     f"employe_code={employe_code} (len={len(employe_code)}), numero_affectation={numero_affectation} (len={len(numero_affectation)})")

        # Insert into Affectation
        cursor.execute("""
            INSERT INTO Affectation (ID_Article_Affectation, Service_Employe_Article, Date_Affectation,
                                    Date_Restitution_Affectation, Affecter_au_Article, Numero_Affectation)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (article_id, service, date_affectation_str, date_restitution_str, employe_code, numero_affectation))

        # Update Article
        cursor.execute("""
            UPDATE Article
            SET Statut_Article = 'AFFECTE',
                Affecter_au_Article = ?,
                Service_Employe_Article = ?,
                Date_Affectation_Article = ?,
                Date_Restitution_Article = ?,
                Numero_Affectation = ?
            WHERE ID_Article = ?
        """, (employe_code, service, date_affectation_str, date_restitution_str, numero_affectation, article_id))

        conn.commit()
        flash('Affectation ajoutée avec succès', 'success')
    except ValueError as ve:
        conn.rollback()
        flash(str(ve), 'danger')
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error: {str(e)}")
        flash(f'Erreur lors de l\'affectation : {str(e)}', 'danger')
    finally:
        conn.close()

    return redirect(url_for('affectations'))
@app.route('/affectation/terminer/<int:id>', methods=['POST'])
def terminer_affectation(id):
    date_restitution = datetime.now().strftime('%Y-%m-%d')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Récupérer l'ID de l'article concerné
        cursor.execute("SELECT ID_Article_Affectation FROM Affectation WHERE ID_Affectation = ?", (id,))
        id_article = cursor.fetchone()[0]

        # Terminer l'affectation
        cursor.execute("""
                       UPDATE Affectation
                       SET Date_Restitution_Affectation = ?
                       WHERE ID_Affectation = ?
                       """, (date_restitution, id))

        # Mettre à jour le statut de l'article
        cursor.execute("""
                       UPDATE Article
                       SET Statut_Article           = 'NON AFFECTE',
                           Affecter_au_Article      = NULL,
                           Service_Employe_Article  = NULL,
                           Date_Restitution_Article = ?,
                           Numero_Affectation       = NULL
                       WHERE ID_Article = ?
                       """, (date_restitution, id_article))

        conn.commit()
        flash('Affectation terminée avec succès', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Erreur lors de la terminaison de l\'affectation: {str(e)}', 'danger')
    finally:
        conn.close()

    return redirect(url_for('affectations'))


# Tableau de bord statistiques
@app.route('/dashboard')
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Statistiques générales
    cursor.execute("SELECT COUNT(*) FROM Employe")
    total_employes = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Article")
    total_articles = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Article WHERE Statut_Article = 'AFFECTE'")
    articles_affectes = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Article WHERE Statut_Article = 'NON AFFECTE'")
    articles_non_affectes = cursor.fetchone()[0]

    # Répartition par type d'article
    cursor.execute("SELECT Type_Article, COUNT(*) FROM Article GROUP BY Type_Article")
    repartition_types = cursor.fetchall()

    # Répartition par service
    cursor.execute(
        "SELECT Service_Employe_Article, COUNT(*) FROM Article WHERE Service_Employe_Article IS NOT NULL GROUP BY Service_Employe_Article")
    repartition_services = cursor.fetchall()

    conn.close()

    return render_template('dashboard.html',
                           total_employes=total_employes,
                           total_articles=total_articles,
                           articles_affectes=articles_affectes,
                           articles_non_affectes=articles_non_affectes,
                           repartition_types=repartition_types,
                           repartition_services=repartition_services)


# API pour les graphiques
@app.route('/api/stats')
def api_stats():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Données pour le graphique de répartition des articles
    cursor.execute("""
                   SELECT SUM(CASE WHEN Statut_Article = 'AFFECTE' THEN 1 ELSE 0 END)     as affectes,
                          SUM(CASE WHEN Statut_Article = 'NON AFFECTE' THEN 1 ELSE 0 END) as non_affectes
                   FROM Article
                   """)
    statut_articles = cursor.fetchone()

    # Données pour le graphique des types d'articles
    cursor.execute("SELECT Type_Article, COUNT(*) FROM Article GROUP BY Type_Article")
    types_articles = [{'type': row[0], 'count': row[1]} for row in cursor.fetchall()]

    conn.close()

    return jsonify({
        'statut_articles': {
            'affectes': statut_articles[0],
            'non_affectes': statut_articles[1]
        },
        'types_articles': types_articles
    })

@app.route('/profile')
def profile():
    user_id = session.get('user_id')


    # Connexion à la base de données
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Employe WHERE ID_Employe = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    if user:
        columns = [desc[0] for desc in cursor.description]
        user_dict = dict(zip(columns, user))
        return render_template('profile.html', user=user_dict)
    else:
        flash('Utilisateur non trouvé.', 'danger')
        return redirect(url_for('index'))
if __name__ == '__main__':
    app.run(debug=True)