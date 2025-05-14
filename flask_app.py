from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import pyodbc
import os
from werkzeug.utils import secure_filename
import uuid
import logging
from datetime import datetime

# App setup
app = Flask(__name__, static_folder='static')
app.secret_key = 'hamza'
app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'images')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Configure logging
logging.basicConfig(level=logging.DEBUG, filename='app.log', filemode='a',
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Helper functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    conn_str = (
        "DRIVER={SQL Server};"
        "SERVER=localhost\\TEST;"
        "DATABASE=gestion_parc_informatique;"
        "Trusted_Connection=yes;"
    )
    return pyodbc.connect(conn_str)

# Routes
@app.route('/')
def index():
    logger.debug("Accessed index route")
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    logger.debug("Accessed dashboard route")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Total employees
        cursor.execute("SELECT COUNT(*) FROM Employe")
        total_employes = cursor.fetchone()[0]

        # Total equipment
        cursor.execute("SELECT COUNT(*) FROM Article")
        total_articles = cursor.fetchone()[0]

        # Assigned equipment
        cursor.execute("SELECT COUNT(*) FROM Article WHERE Affecter_au_Article IS NOT NULL")
        articles_affectes = cursor.fetchone()[0]

        # Non-assigned equipment
        cursor.execute("SELECT COUNT(*) FROM Article WHERE Affecter_au_Article IS NULL")
        articles_non_affectes = cursor.fetchone()[0]

        # Equipment by type
        cursor.execute("SELECT Type_Article, COUNT(*) FROM Article GROUP BY Type_Article")
        repartition_types = cursor.fetchall()

        # Equipment by service (exclude unassigned)
        cursor.execute("""
            SELECT e.Service_Employe, COUNT(a.ID_Article)
            FROM Article a
            INNER JOIN Employe e ON TRY_CAST(a.Affecter_au_Article AS varchar) = e.Code_Employe
            WHERE e.Service_Employe IS NOT NULL
            GROUP BY e.Service_Employe
        """)
        repartition_services = cursor.fetchall()

        # Employees by direction and service
        cursor.execute("""
            SELECT ISNULL(e.Direction_Employe, 'Non spécifié') AS Direction_Employe,
                   ISNULL(e.Service_Employe, 'Non spécifié') AS Service_Employe,
                   COUNT(e.ID_Employe) AS Nombre_Employes
            FROM Employe e
            GROUP BY e.Direction_Employe, e.Service_Employe
            ORDER BY e.Direction_Employe, e.Service_Employe
        """)
        repartition_employes = cursor.fetchall()

        # Equipment assigned and unassigned by direction and service
        cursor.execute("""
            SELECT ISNULL(e.Direction_Employe, 'Non spécifié') AS Direction_Employe,
                   ISNULL(e.Service_Employe, 'Non spécifié') AS Service_Employe,
                   SUM(CASE WHEN a.Statut_Article = 'AFFECTE' THEN 1 ELSE 0 END) AS Affectes,
                   SUM(CASE WHEN a.Affecter_au_Article IS NULL THEN 1 ELSE 0 END) AS Non_Affectes
            FROM Article a
            LEFT JOIN Employe e ON TRY_CAST(a.Affecter_au_Article AS varchar) = e.Code_Employe
            GROUP BY e.Direction_Employe, e.Service_Employe
            ORDER BY e.Direction_Employe, e.Service_Employe
        """)
        repartition_materiel_direction_service = cursor.fetchall()

        conn.close()
        return render_template('dashboard.html',
                             total_employes=total_employes,
                             total_articles=total_articles,
                             articles_affectes=articles_affectes,
                             articles_non_affectes=articles_non_affectes,
                             repartition_types=repartition_types,
                             repartition_services=repartition_services,
                             repartition_employes=repartition_employes,
                             repartition_materiel_direction_service=repartition_materiel_direction_service)
    except pyodbc.Error as e:
        logger.error(f"Database error in dashboard: {str(e)}")
        flash(f'Erreur de base de données : {str(e)}', 'danger')
        return render_template('dashboard.html', total_employes=0, total_articles=0,
                             articles_affectes=0, articles_non_affectes=0,
                             repartition_types=[], repartition_services=[],
                             repartition_employes=[], repartition_materiel_direction_service=[])

@app.route('/utilisateurs')
def utilisateurs():
    logger.debug("Accessed utilisateurs route")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch all employees
        cursor.execute("""
            SELECT ID_Employe, Code_Employe, Nom_Employe, Prenom_Employe, 
                   CIN_Employe, Service_Employe, Direction_Employe, Statut_Employe
            FROM Employe
        """)
        employes = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        employes_list = [dict(zip(columns, employe)) for employe in employes]
        logger.debug(f"Total employes fetched: {len(employes_list)}")

        # Fetch distinct services (exclude NULL and empty)
        cursor.execute("""
            SELECT DISTINCT Service_Employe
            FROM Employe
            WHERE Service_Employe IS NOT NULL AND Service_Employe <> ''
            ORDER BY Service_Employe
        """)
        services = [row.Service_Employe for row in cursor.fetchall()]
        logger.debug(f"Services fetched: {services}")

        # Fetch distinct directions (exclude NULL and empty)
        cursor.execute("""
            SELECT DISTINCT Direction_Employe
            FROM Employe
            WHERE Direction_Employe IS NOT NULL AND Direction_Employe <> ''
            ORDER BY Direction_Employe
        """)
        directions = [row.Direction_Employe for row in cursor.fetchall()]
        logger.debug(f"Directions fetched: {directions}")

        conn.close()
        return render_template('utilisateurs.html', employes=employes_list, services=services, directions=directions)
    except pyodbc.Error as e:
        logger.error(f"Database error in utilisateurs: {str(e)}")
        flash(f'Erreur de base de données : {str(e)}', 'danger')
        return render_template('utilisateurs.html', employes=[], services=[], directions=[])
    except Exception as e:
        logger.error(f"Error in utilisateurs: {str(e)}")
        flash(f'Erreur : {str(e)}', 'danger')
        return render_template('utilisateurs.html', employes=[], services=[], directions=[])

@app.route('/utilisateur/ajouter', methods=['GET', 'POST'])
def ajouter_utilisateur():
    logger.debug(f"Accessed ajouter_utilisateur route, method: {request.method}")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if request.method == 'POST':
            data = request.form
            date_sortie = data['date_sortie'] if data['date_sortie'] else None
            cursor.execute("""
                INSERT INTO Employe (Code_Employe, Badge_Employe, CIN_Employe, Nom_Employe, Prenom_Employe,
                                    Fonction_Employe, Service_Employe, Direction_Employe, Affectation_Employe,
                                    Statut_Employe, Date_Sortie_Employe)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data['code'], data['badge'], data['cin'], data['nom'], data['prenom'],
                data['fonction'], data['service'] or None, data['direction'] or None,
                data['affectation'], data['statut'], date_sortie
            ))
            conn.commit()
            flash('Utilisateur ajouté avec succès', 'success')
            logger.info(f"Added user: {data['code']}")
            conn.close()
            return redirect(url_for('utilisateurs'))

        cursor.execute("SELECT Direction_Direction FROM Direction")
        directions = cursor.fetchall()
        cursor.execute("SELECT Service_Service FROM Service")
        services = cursor.fetchall()
        statuts = ['Actif', 'Non Actif']
        conn.close()
        return render_template('ajouter_utilisateur.html', directions=directions, services=services, statuts=statuts)
    except pyodbc.IntegrityError as e:
        conn.rollback()
        logger.error(f"Integrity error in ajouter_utilisateur: {str(e)}")
        flash('Erreur : Code, badge ou CIN déjà utilisé.', 'danger')
        return redirect(request.url)
    except pyodbc.Error as e:
        conn.rollback()
        logger.error(f"Database error in ajouter_utilisateur: {str(e)}")
        flash(f'Erreur de base de données : {str(e)}', 'danger')
        return redirect(request.url)
    except KeyError as e:
        conn.rollback()
        logger.error(f"Form field missing in ajouter_utilisateur: {str(e)}")
        flash(f'Erreur : Champ de formulaire manquant ({str(e)}).', 'danger')
        return redirect(request.url)

@app.route('/utilisateur/editer/<int:id>', methods=['GET', 'POST'])
def editer_utilisateur(id):
    logger.debug(f"Accessed editer_utilisateur route for ID: {id}, method: {request.method}")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch current employee data
        cursor.execute("SELECT * FROM Employe WHERE ID_Employe = ?", (id,))
        employe = cursor.fetchone()
        if not employe:
            conn.close()
            flash('Utilisateur non trouvé', 'danger')
            logger.warning(f"User not found: ID {id}")
            return redirect(url_for('utilisateurs'))

        columns = [column[0] for column in cursor.description]
        employe_dict = dict(zip(columns, employe))

        if request.method == 'POST':
            data = request.form.to_dict()
            update_fields = {}
            params = []

            # Map form fields to database columns
            field_mapping = {
                'code': 'Code_Employe',
                'badge': 'Badge_Employe',
                'cin': 'CIN_Employe',
                'nom': 'Nom_Employe',
                'prenom': 'Prenom_Employe',
                'fonction': 'Fonction_Employe',
                'service': 'Service_Employe',
                'direction': 'Direction_Employe',
                'affectation': 'Affectation_Employe',
                'statut': 'Statut_Employe',
                'date_sortie': 'Date_Sortie_Employe'
            }

            # Check unique constraints for changed fields
            for form_field, db_field in field_mapping.items():
                if form_field in data and data[form_field] != '':
                    new_value = data[form_field] if data[form_field] else None
                    if new_value != employe_dict[db_field]:
                        # Validate unique fields
                        if form_field in ['code', 'badge', 'cin']:
                            cursor.execute(f"SELECT COUNT(*) FROM Employe WHERE {db_field} = ? AND ID_Employe != ?", (new_value, id))
                            if cursor.fetchone()[0] > 0:
                                conn.close()
                                flash(f'Erreur : {form_field.capitalize()} déjà utilisé.', 'danger')
                                return redirect(request.url)
                        update_fields[db_field] = new_value
                        params.append(new_value)

            if not update_fields:
                conn.close()
                flash('Aucune modification détectée.', 'info')
                return redirect(url_for('utilisateurs'))

            # Build dynamic UPDATE query
            set_clause = ', '.join(f"{field} = ?" for field in update_fields.keys())
            query = f"UPDATE Employe SET {set_clause} WHERE ID_Employe = ?"
            params.append(id)

            cursor.execute(query, params)
            conn.commit()
            flash('Utilisateur mis à jour avec succès', 'success')
            logger.info(f"Updated user ID: {id}, fields: {list(update_fields.keys())}")
            conn.close()
            return redirect(url_for('utilisateurs'))

        cursor.execute("SELECT Direction_Direction FROM Direction")
        directions = cursor.fetchall()
        cursor.execute("SELECT Service_Service FROM Service")
        services = cursor.fetchall()
        statuts = ['Actif', 'Non Actif']
        conn.close()
        return render_template('edit_utilisateur.html', employe=employe_dict,
                             directions=directions, services=services, statuts=statuts)
    except pyodbc.IntegrityError as e:
        conn.rollback()
        logger.error(f"Integrity error in editer_utilisateur: {str(e)}")
        flash('Erreur : Code, badge ou CIN déjà utilisé.', 'danger')
        return redirect(request.url)
    except pyodbc.Error as e:
        conn.rollback()
        logger.error(f"Database error in editer_utilisateur: {str(e)}")
        flash(f'Erreur de base de données : {str(e)}', 'danger')
        return redirect(request.url)
    except KeyError as e:
        conn.rollback()
        logger.error(f"Form field missing in editer_utilisateur: {str(e)}")
        flash(f'Erreur : Champ de formulaire manquant ({str(e)}).', 'danger')
        return redirect(request.url)

@app.route('/utilisateur/supprimer/<int:id>', methods=['POST'])
def supprimer_utilisateur(id):
    logger.debug(f"Accessed supprimer_utilisateur route for ID: {id}")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Employe WHERE ID_Employe = ?", (id,))
        conn.commit()
        flash('Utilisateur supprimé avec succès', 'success')
        logger.info(f"Deleted user ID: {id}")
        conn.close()
        return redirect(url_for('utilisateurs'))
    except pyodbc.IntegrityError as e:
        conn.rollback()
        logger.error(f"Integrity error in supprimer_utilisateur: {str(e)}")
        flash('Erreur : Impossible de supprimer, utilisateur lié à des données.', 'danger')
        return redirect(url_for('utilisateurs'))
    except pyodbc.Error as e:
        conn.rollback()
        logger.error(f"Database error in supprimer_utilisateur: {str(e)}")
        flash(f'Erreur de base de données : {str(e)}', 'danger')
        return redirect(url_for('utilisateurs'))


@app.route('/materiel')
def materiel():
    logger.debug("Accessed materiel route")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch all articles
        cursor.execute("""
                       SELECT ID_Article,
                              Ref_Article,
                              Libelle_Article,
                              Type_Article,
                              Marque_Article,
                              Etat_Article,
                              Statut_Article,
                              Affecter_au_Article,
                              Image_Path
                       FROM Article
                       """)
        articles = cursor.fetchall()
        article_columns = [column[0] for column in cursor.description]
        logger.debug(f"Article table columns: {article_columns}")
        if 'Image_Path' not in article_columns:
            logger.error("Image_Path column missing from Article table")
        articles_list = [dict(zip(article_columns, article)) for article in articles]
        logger.debug(f"Total articles fetched: {len(articles_list)}")
        for article in articles_list:
            logger.debug(
                f"Article: Ref={article.get('Ref_Article', 'N/A')}, Image_Path={article.get('Image_Path', 'None')}")

        # Fetch all employees
        cursor.execute("""
                       SELECT Code_Employe, Nom_Employe, Prenom_Employe
                       FROM Employe
                       """)
        employes = cursor.fetchall()
        employe_columns = [column[0] for column in cursor.description]
        employes_list = [dict(zip(employe_columns, employe)) for employe in employes]
        logger.debug(f"Total employes fetched: {len(employes_list)}")

        # Fetch distinct types
        cursor.execute("""
                       SELECT DISTINCT Type_Article
                       FROM Article
                       WHERE Type_Article IS NOT NULL
                         AND Type_Article <> ''
                       ORDER BY Type_Article
                       """)
        types = [row.Type_Article for row in cursor.fetchall()]
        logger.debug(f"Types fetched: {types}")

        # Fetch distinct etats
        cursor.execute("""
                       SELECT DISTINCT Etat_Article
                       FROM Article
                       WHERE Etat_Article IS NOT NULL
                         AND Etat_Article <> ''
                       ORDER BY Etat_Article
                       """)
        etats = [row.Etat_Article for row in cursor.fetchall()]
        logger.debug(f"Etats fetched: {etats}")

        # Fetch distinct marques
        cursor.execute("""
                       SELECT DISTINCT Marque_Article
                       FROM Article
                       WHERE Marque_Article IS NOT NULL
                         AND Marque_Article <> ''
                       ORDER BY Marque_Article
                       """)
        marques = [row.Marque_Article for row in cursor.fetchall()]
        logger.debug(f"Marques fetched: {marques}")

        # Fetch distinct statuts
        cursor.execute("""
                       SELECT DISTINCT Statut_Article
                       FROM Article
                       WHERE Statut_Article IS NOT NULL
                         AND Statut_Article <> ''
                       ORDER BY Statut_Article
                       """)
        statuts = [row.Statut_Article for row in cursor.fetchall()]
        logger.debug(f"Statuts fetched: {statuts}")

        conn.close()
        return render_template('materiel.html',
                               articles=articles_list,
                               employes=employes_list,
                               employes_liste=employes_list,
                               types=types,
                               etats=etats,
                               marques=marques,
                               statuts=statuts)
    except pyodbc.Error as e:
        logger.error(f"Database error in materiel: {str(e)}")
        flash(f'Erreur de base de données : {str(e)}', 'danger')
        return render_template('materiel.html',
                               articles=[],
                               employes=[],
                               employes_liste=[],
                               types=[],
                               etats=[],
                               marques=[],
                               statuts=[])
    except Exception as e:
        logger.error(f"Error in materiel: {str(e)}")
        flash(f'Erreur : {str(e)}', 'danger')
        return render_template('materiel.html',
                               articles=[],
                               employes=[],
                               employes_liste=[],
                               types=[],
                               etats=[],
                               marques=[],
                               statuts=[])
@app.route('/ajouter_materiel', methods=['GET', 'POST'])
def ajouter_materiel():
    logger.debug(f"Accessed ajouter_materiel route, method: {request.method}")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        types = ['ordinateur', 'imprimante', 'scanner', 'autre']
        etats = ['dispo', 'en maintenance', 'non disponible']
        categories = ['électronique', 'mobilier', 'autre']
        locations = ['bureau 1', 'bureau 2', 'entrepôt']
        cursor.execute("SELECT Code_Employe, Nom_Employe, Prenom_Employe FROM Employe")
        employes = cursor.fetchall()

        if request.method == 'POST':
            ref = request.form['ref']
            libelle = request.form['libelle']
            type_article = request.form['type']
            marque = request.form['marque']
            etat = request.form['etat']
            affecte_a_id = request.form.get('affecte_a')

            image_path_db = None
            if 'image' in request.files:
                image = request.files['image']
                if image and allowed_file(image.filename):
                    filename = secure_filename(f"{uuid.uuid4().hex}_{image.filename}")
                    image_path_db = filename
                    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    logger.debug(f"Saving image to: {image_path}, DB path: {image_path_db}")
                    if len(image_path_db) > 255:
                        flash('Nom du fichier image trop long.', 'danger')
                        return redirect(request.url)
                    image.save(image_path)
                    if not os.path.exists(image_path):
                        logger.error(f"Image not saved: {image_path}")
                        flash('Erreur : Image non enregistrée.', 'danger')
                        return redirect(request.url)
                    logger.info(f"Image saved successfully: {image_path_db}")
                elif image.filename != '':
                    flash('Format d\'image non valide. Utilisez PNG, JPG ou JPEG.', 'danger')
                    return redirect(request.url)

            statut = 'AFFECTE' if affecte_a_id else 'NON AFFECTE'



            cursor.execute("""
                INSERT INTO Article (Ref_Article, Libelle_Article, Type_Article, Marque_Article, 
                                    Etat_Article, Statut_Article, Affecter_au_Article, Image_Path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (ref, libelle, type_article, marque, etat, statut, affecte_a_id, image_path_db))
            conn.commit()
            flash('Matériel ajouté avec succès', 'success')
            logger.info(f"Added material: {ref}, Image_Path: {image_path_db}")
            conn.close()
            return redirect(url_for('materiel'))

        conn.close()
        return render_template('ajouter_materiel.html', types=types, etats=etats,
                             categories=categories, locations=locations, employes=employes)
    except pyodbc.DataError as e:
        conn.rollback()
        logger.error(f"Data error in ajouter_materiel: {str(e)}")
        flash(f'Erreur de base de données : {str(e)}', 'danger')
        return redirect(request.url)
    except pyodbc.Error as e:
        conn.rollback()
        logger.error(f"Database error in ajouter_materiel: {str(e)}")
        flash(f'Erreur de base de données : {str(e)}', 'danger')
        return redirect(request.url)
    except KeyError as e:
        conn.rollback()
        logger.error(f"Form field missing in ajouter_materiel: {str(e)}")
        flash(f'Erreur : Champ de formulaire manquant ({str(e)}).', 'danger')
        return redirect(request.url)

@app.route('/editer_materiel/<int:id>', methods=['GET', 'POST'])
def editer_materiel(id):
    logger.debug(f"Accessed editer_materiel route for ID: {id}, method: {request.method}")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        types = ['ordinateur', 'imprimante', 'scanner', 'autre']
        etats = ['dispo', 'en maintenance', 'non disponible']
        categories = ['électronique', 'mobilier', 'autre']
        locations = ['bureau 1', 'bureau 2', 'entrepôt']

        cursor.execute("SELECT * FROM Article WHERE ID_Article = ?", (id,))
        article = cursor.fetchone()
        if article:
            columns = [column[0] for column in cursor.description]
            article_dict = dict(zip(columns, article))
        else:
            flash('Matériel non trouvé', 'danger')
            logger.warning(f"Material not found: ID {id}")
            return redirect(url_for('materiel'))

        cursor.execute("SELECT Code_Employe, Nom_Employe, Prenom_Employe FROM Employe")
        employes = cursor.fetchall()

        if request.method == 'POST':
            ref = request.form['ref']
            libelle = request.form['libelle']
            type_article = request.form['type']
            marque = request.form['marque']
            etat = request.form['etat']
            affecte_a_id = request.form.get('affecte_a')

            image_path_db = article_dict.get('Image_Path')
            remove_image = 'remove_image' in request.form
            if remove_image:
                image_path_db = None
                logger.info(f"Image removed for article ID: {id}")
            if 'image' in request.files:
                image = request.files['image']
                if image and allowed_file(image.filename):
                    filename = secure_filename(f"{uuid.uuid4().hex}_{image.filename}")
                    image_path_db = filename
                    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    logger.debug(f"Saving image to: {image_path}, DB path: {image_path_db}")
                    if len(image_path_db) > 255:
                        flash('Nom du fichier image trop long.', 'danger')
                        return redirect(request.url)
                    image.save(image_path)
                    if not os.path.exists(image_path):
                        logger.error(f"Image not saved: {image_path}")
                        flash('Erreur : Image non enregistrée.', 'danger')
                        return redirect(request.url)
                    logger.info(f"Image updated for article ID: {id}, Image_Path: {image_path_db}")
                elif image.filename != '':
                    flash('Format d\'image non valide. Utilisez PNG, JPG ou JPEG.', 'danger')
                    return redirect(request.url)

            statut = 'AFFECTE' if affecte_a_id else 'NON AFFECTE'


            cursor.execute("""
                UPDATE Article
                SET Ref_Article = ?, Libelle_Article = ?, Type_Article = ?, Marque_Article = ?,
                    Etat_Article = ?, Statut_Article = ?, Affecter_au_Article = ?, Image_Path = ?
                WHERE ID_Article = ?
            """, (ref, libelle, type_article, marque, etat, statut, affecte_a_id, image_path_db, id))
            conn.commit()
            flash('Matériel mis à jour', 'success')
            logger.info(f"Updated material ID: {id}, Image_Path: {image_path_db}")
            conn.close()
            return redirect(url_for('materiel'))

        conn.close()
        return render_template('edit_materiel.html', article=article_dict, types=types,
                             etats=etats, categories=categories, locations=locations, employes=employes)
    except pyodbc.DataError as e:
        conn.rollback()
        logger.error(f"Data error in editer_materiel: {str(e)}")
        flash(f'Erreur de base de données : {str(e)}', 'danger')
        return redirect(request.url)
    except pyodbc.Error as e:
        conn.rollback()
        logger.error(f"Database error in editer_materiel: {str(e)}")
        flash(f'Erreur de base de données : {str(e)}', 'danger')
        return redirect(request.url)
    except KeyError as e:
        conn.rollback()
        logger.error(f"Form field missing in editer_materiel: {str(e)}")
        flash(f'Erreur : Champ de formulaire manquant ({str(e)}).', 'danger')
        return redirect(request.url)

@app.route('/supprimer_materiel/<int:id>', methods=['POST'])
def supprimer_materiel(id):
    logger.debug(f"Accessed supprimer_materiel route for ID: {id}")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Article WHERE ID_Article = ?", (id,))
        conn.commit()
        flash('Matériel supprimé', 'success')
        logger.info(f"Deleted material ID: {id}")
        conn.close()
        return redirect(url_for('materiel'))
    except pyodbc.IntegrityError as e:
        conn.rollback()
        logger.error(f"Integrity error in supprimer_materiel: {str(e)}")
        flash('Erreur : Impossible de supprimer, matériel lié à des affectations.', 'danger')
        return redirect(url_for('materiel'))
    except pyodbc.Error as e:
        conn.rollback()
        logger.error(f"Database error in supprimer_materiel: {str(e)}")
        flash(f'Erreur de base de données : {str(e)}', 'danger')
        return redirect(url_for('materiel'))

@app.route('/affectations')
def affectations():
    logger.debug("Accessed affectations route")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.ID_Affectation, ar.Libelle_Article, e.Nom_Employe, e.Prenom_Employe,
                   a.Date_Affectation, a.Date_Restitution_Affectation, a.Service_Employe_Article
            FROM Affectation a
            LEFT JOIN Article ar ON a.ID_Article_Affectation = ar.ID_Article
            LEFT JOIN Employe e ON a.Affecter_au_Article = e.Code_Employe
        """)
        affectations = cursor.fetchall()
        cursor.execute("SELECT ID_Article, Libelle_Article FROM Article WHERE Statut_Article = 'NON AFFECTE'")
        articles = cursor.fetchall()
        cursor.execute("SELECT Code_Employe, Nom_Employe, Prenom_Employe FROM Employe")
        employes = cursor.fetchall()
        conn.close()
        return render_template('affectation.html', affectations=affectations,
                             articles=articles, employes=employes)
    except pyodbc.Error as e:
        logger.error(f"Database error in affectations: {str(e)}")
        flash(f'Erreur de base de données : {str(e)}', 'danger')
        return render_template('affectation.html', affectations=[], articles=[], employes=[])

@app.route('/affectation/ajouter', methods=['POST'])
def ajouter_affectation():
    logger.debug("Accessed ajouter_affectation route")
    try:
        data = request.form
        conn = get_db_connection()
        cursor = conn.cursor()

        article_id = int(data.get('article')) if data.get('article') else None
        employe_code = data.get('employe')
        date_affectation = data.get('date_affectation')
        date_restitution = data.get('date_restitution') or None
        numero_affectation = data.get('numero_affectation') or "AUTO_" + datetime.now().strftime('%Y%m%d%H%M%S')

        if not article_id or not employe_code or not date_affectation:
            raise ValueError("Champs obligatoires manquants.")

        cursor.execute("SELECT Statut_Article FROM Article WHERE ID_Article = ?", (article_id,))
        article = cursor.fetchone()
        if not article or article[0] == 'AFFECTE':
            raise ValueError("Matériel invalide ou déjà affecté.")

        cursor.execute("SELECT Service_Employe FROM Employe WHERE Code_Employe = ?", (employe_code,))
        employe = cursor.fetchone()
        if not employe:
            raise ValueError("Employé non trouvé.")
        service = employe[0] or "Inconnu"

        date_affectation_str = datetime.strptime(date_affectation, '%Y-%m-%d').strftime('%Y-%m-%d')
        date_restitution_str = datetime.strptime(date_restitution, '%Y-%m-%d').strftime('%Y-%m-%d') if date_restitution else None

        cursor.execute("""
            INSERT INTO Affectation (ID_Article_Affectation, Service_Employe_Article, Date_Affectation,
                                    Date_Restitution_Affectation, Affecter_au_Article, Numero_Affectation)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (article_id, service, date_affectation_str, date_restitution_str, employe_code, numero_affectation))

        cursor.execute("""
            UPDATE Article
            SET Statut_Article = 'AFFECTE', Affecter_au_Article = ?, Service_Employe_Article = ?,
                Date_Affectation_Article = ?, Date_Restitution_Article = ?, Numero_Affectation = ?
            WHERE ID_Article = ?
        """, (employe_code, service, date_affectation_str, date_restitution_str, numero_affectation, article_id))

        conn.commit()
        flash('Affectation ajoutée avec succès', 'success')
        logger.info(f"Added affectation: Article {article_id}, Employe {employe_code}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error in ajouter_affectation: {str(e)}")
        flash(f'Erreur: {str(e)}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('affectations'))

@app.route('/affectation/terminer/<int:id>', methods=['POST'])
def terminer_affectation(id):
    logger.debug(f"Accessed terminer_affectation route for ID: {id}")
    date_restitution = datetime.now().strftime('%Y-%m-%d')
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ID_Article_Affectation FROM Affectation WHERE ID_Affectation = ?", (id,))
        id_article = cursor.fetchone()
        if not id_article:
            raise ValueError("Affectation non trouvée.")
        id_article = id_article[0]

        cursor.execute("""
            UPDATE Affectation
            SET Date_Restitution_Affectation = ?
            WHERE ID_Affectation = ?
        """, (date_restitution, id))
        cursor.execute("""
            UPDATE Article
            SET Statut_Article = 'NON AFFECTE', Affecter_au_Article = NULL, Service_Employe_Article = NULL,
                Date_Restitution_Article = ?, Numero_Affectation = NULL
            WHERE ID_Article = ?
        """, (date_restitution, id_article))
        conn.commit()
        flash('Affectation terminée avec succès', 'success')
        logger.info(f"Terminated affectation ID: {id}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error in terminer_affectation: {str(e)}")
        flash(f'Erreur: {str(e)}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('affectations'))

@app.route('/api/stats')
def api_stats():
    logger.debug("Accessed api_stats route")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT SUM(CASE WHEN Statut_Article = 'AFFECTE' THEN 1 ELSE 0 END) as affectes,
                   SUM(CASE WHEN Statut_Article = 'NON AFFECTE' THEN 1 ELSE 0 END) as non_affectes
            FROM Article
        """)
        statut_articles = cursor.fetchone()
        cursor.execute("SELECT Type_Article, COUNT(*) FROM Article GROUP BY Type_Article")
        types_articles = [{'type': row[0], 'count': row[1]} for row in cursor.fetchall()]
        conn.close()
        return jsonify({
            'statut_articles': {'affectes': statut_articles[0] or 0, 'non_affectes': statut_articles[1] or 0},
            'types_articles': types_articles
        })
    except pyodbc.Error as e:
        logger.error(f"Database error in api_stats: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/profile')
def profile():
    logger.debug("Accessed profile route")
    try:
        user_id = session.get('user_id')
        if not user_id:
            flash('Veuillez vous connecter.', 'danger')
            logger.warning("Profile accessed without user_id in session")
            return redirect(url_for('index'))

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Employe WHERE ID_Employe = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        if user:
            columns = [desc[0] for desc in cursor.description]
            user_dict = dict(zip(columns, user))
            return render_template('profile.html', user=user_dict)
        flash('Utilisateur non trouvé.', 'danger')
        logger.warning(f"User not found: ID {user_id}")
        return redirect(url_for('index'))
    except pyodbc.Error as e:
        logger.error(f"Database error in profile: {str(e)}")
        flash(f'Erreur de base de données : {str(e)}', 'danger')
        return redirect(url_for('index'))

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)