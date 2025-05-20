from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file, Blueprint
import pyodbc
import os
from werkzeug.utils import secure_filename
import uuid
import logging
from datetime import datetime, date
from flask_bcrypt import Bcrypt
from functools import wraps
from io import BytesIO
import pandas as pd
from datetime import timedelta
# App setup
app = Flask(__name__, static_folder='static')
app.secret_key = os.urandom(24).hex()
app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'images')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=12)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
bcrypt = Bcrypt(app)

logging.basicConfig(level=logging.DEBUG, filename='app.log', filemode='a',
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


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


def get_server_timestamp():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT CURRENT_TIMESTAMP")
        timestamp = cursor.fetchone()[0]
        conn.close()
        return timestamp
    except pyodbc.Error as e:
        logger.error(f"Error fetching server timestamp: {str(e)}")
        return datetime.now()


def update_article_status(article_id, conn, cursor):
    """Update Statut_Article based on active affectations."""
    today = date.today().strftime('%Y-%m-%d')
    cursor.execute("""
                   SELECT COUNT(*)
                   FROM Affectation
                   WHERE ID_Article_Affectation = ?
                     AND (Date_Restitution_Affectation IS NULL OR Date_Restitution_Affectation > ?)
                   """, (article_id, today))
    active_affectations = cursor.fetchone()[0]

    new_status = 'AFFECTE' if active_affectations > 0 else 'NON AFFECTE'
    cursor.execute("""
                   UPDATE Article
                   SET Statut_Article = ?
                   WHERE ID_Article = ?
                   """, (new_status, article_id))


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Veuillez vous connecter pour accéder à cette page.', 'danger')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Accès réservé aux administrateurs.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)

    return decorated_function


# Routes
@app.route('/')
def index():
    logger.debug("Accessed index route")
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    logger.debug(f"Accessed login route, method: {request.method}")
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            flash('Email et mot de passe requis.', 'danger')
            logger.warning("Login attempt with missing email or password")
            return render_template('login.html')

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT ID_User, Email, Password, Role FROM [User] WHERE Email = ?", (email,))
            user = cursor.fetchone()
            conn.close()

            if user and bcrypt.check_password_hash(user.Password, password):
                session['user_id'] = user.ID_User
                session['email'] = user.Email
                session['role'] = user.Role
                logger.info(f"User {email} logged in successfully")
                next_page = request.args.get('next')
                return redirect(next_page or url_for('index'))
            else:
                flash('Email ou mot de passe incorrect.', 'danger')
                logger.warning(f"Failed login attempt for {email}")
                return render_template('login.html')
        except pyodbc.Error as e:
            logger.error(f"Database error during login: {str(e)}")
            flash('Erreur de connexion à la base de données.', 'danger')
            return render_template('login.html')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logger.debug("Accessed logout route")
    session.pop('user_id', None)
    session.pop('email', None)
    session.pop('role', None)
    flash('Vous avez été déconnecté.', 'success')
    logger.info("User logged out")
    return redirect(url_for('login'))


@app.route('/admin/users')
@admin_required
def admin_users():
    logger.debug("Accessed admin_users route")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ID_User, Email, Role FROM [User]")
        users = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        users_list = [dict(zip(columns, user)) for user in users]
        conn.close()
        return render_template('admin_users.html', users=users_list)
    except pyodbc.Error as e:
        logger.error(f"Database error in admin_users: {str(e)}")
        flash(f'Erreur de base de données : {str(e)}', 'danger')
        return render_template('admin_users.html', users=[])


@app.route('/admin/users/add', methods=['GET', 'POST'])
@admin_required
def admin_add_user():
    logger.debug(f"Accessed admin_add_user route, method: {request.method}")
    try:
        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')
            password_confirm = request.form.get('password_confirm')
            role = request.form.get('role')

            if not email or not password or not role:
                flash('Email, mot de passe et rôle sont requis.', 'danger')
                return redirect(request.url)
            if password != password_confirm:
                flash('Les mots de passe ne correspondent pas.', 'danger')
                return redirect(request.url)
            if len(password) < 8:
                flash('Le mot de passe doit contenir au moins 8 caractères.', 'danger')
                return redirect(request.url)
            if role not in ['user', 'admin']:
                flash('Rôle invalide.', 'danger')
                return redirect(request.url)

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM [User] WHERE Email = ?", (email,))
            if cursor.fetchone()[0] > 0:
                conn.close()
                flash('Cet email est déjà utilisé.', 'danger')
                return redirect(request.url)

            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            cursor.execute("INSERT INTO [User] (Email, Password, Role) VALUES (?, ?, ?)",
                           (email, hashed_password, role))
            conn.commit()
            conn.close()
            flash('Utilisateur ajouté avec succès.', 'success')
            logger.info(f"Admin added user: {email}, role: {role}")
            return redirect(url_for('admin_users'))

        return render_template('admin_add_user.html')
    except pyodbc.Error as e:
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        logger.error(f"Database error in admin_add_user: {str(e)}")
        flash(f'Erreur de base de données : {str(e)}', 'danger')
        return redirect(request.url)


@app.route('/admin/users/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_user(id):
    logger.debug(f"Accessed admin_edit_user route for ID: {id}, method: {request.method}")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ID_User, Email, Role FROM [User] WHERE ID_User = ?", (id,))
        user = cursor.fetchone()
        if not user:
            conn.close()
            flash('Utilisateur non trouvé.', 'danger')
            return redirect(url_for('admin_users'))

        user_dict = {'ID_User': user[0], 'Email': user[1], 'Role': user[2]}

        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')
            password_confirm = request.form.get('password_confirm')
            role = request.form.get('role')

            if not email or not role:
                flash('Email et rôle sont requis.', 'danger')
                return redirect(request.url)
            if password and password != password_confirm:
                flash('Les mots de passe ne correspondent pas.', 'danger')
                return redirect(request.url)
            if password and len(password) < 8:
                flash('Le mot de passe doit contenir au moins 8 caractères.', 'danger')
                return redirect(request.url)
            if role not in ['user', 'admin']:
                flash('Rôle invalide.', 'danger')
                return redirect(request.url)

            cursor.execute("SELECT COUNT(*) FROM [User] WHERE Email = ? AND ID_User != ?", (email, id))
            if cursor.fetchone()[0] > 0:
                conn.close()
                flash('Cet email est déjà utilisé.', 'danger')
                return redirect(request.url)

            if password:
                hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
                cursor.execute("UPDATE [User] SET Email = ?, Password = ?, Role = ? WHERE ID_User = ?",
                               (email, hashed_password, role, id))
            else:
                cursor.execute("UPDATE [User] SET Email = ?, Role = ? WHERE ID_User = ?",
                               (email, role, id))
            conn.commit()
            conn.close()
            flash('Utilisateur mis à jour avec succès.', 'success')
            logger.info(f"Admin updated user ID: {id}, email: {email}, role: {role}")
            return redirect(url_for('admin_users'))

        conn.close()
        return render_template('admin_edit_user.html', user=user_dict)
    except pyodbc.Error as e:
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        logger.error(f"Database error in admin_edit_user: {str(e)}")
        flash(f'Erreur de base de données : {str(e)}', 'danger')
        return redirect(request.url)


@app.route('/admin/users/delete/<int:id>', methods=['POST'])
@admin_required
def admin_delete_user(id):
    logger.debug(f"Accessed admin_delete_user route for ID: {id}")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT Email FROM [User] WHERE ID_User = ?", (id,))
        user = cursor.fetchone()
        if not user:
            conn.close()
            flash('Utilisateur non trouvé.', 'danger')
            return redirect(url_for('admin_users'))

        cursor.execute("DELETE FROM [User] WHERE ID_User = ?", (id,))
        conn.commit()
        conn.close()
        flash('Utilisateur supprimé avec succès.', 'success')
        logger.info(f"Admin deleted user ID: {id}, email: {user[0]}")
        return redirect(url_for('admin_users'))
    except pyodbc.Error as e:
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        logger.error(f"Database error in admin_delete_user: {str(e)}")
        flash(f'Erreur de base de données : {str(e)}', 'danger')
        return redirect(url_for('admin_users'))


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    logger.debug(f"Accessed profile route, method: {request.method}")
    try:
        if request.method == 'POST':
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            password_confirm = request.form.get('password_confirm')

            if not current_password or not new_password:
                flash('Mot de passe actuel et nouveau mot de passe requis.', 'danger')
                return redirect(request.url)
            if new_password != password_confirm:
                flash('Les nouveaux mots de passe ne correspondent pas.', 'danger')
                return redirect(request.url)
            if len(new_password) < 8:
                flash('Le nouveau mot de passe doit contenir au moins 8 caractères.', 'danger')
                return redirect(request.url)

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT Password FROM [User] WHERE ID_User = ?", (session['user_id'],))
            user = cursor.fetchone()
            if not user or not bcrypt.check_password_hash(user[0], current_password):
                conn.close()
                flash('Mot de passe actuel incorrect.', 'danger')
                return redirect(request.url)

            hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
            cursor.execute("UPDATE [User] SET Password = ? WHERE ID_User = ?",
                           (hashed_password, session['user_id']))
            conn.commit()
            conn.close()
            flash('Mot de passe mis à jour avec succès.', 'success')
            logger.info(f"User {session['email']} updated password")
            return redirect(url_for('profile'))

        return render_template('profile.html', email=session['email'])
    except pyodbc.Error as e:
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        logger.error(f"Database error in profile: {str(e)}")
        flash(f'Erreur de base de données : {str(e)}', 'danger')
        return redirect(request.url)


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Veuillez vous connecter pour accéder au tableau de bord.', 'warning')
        return redirect(url_for('login'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Total employees
        cursor.execute("SELECT COUNT(*) FROM Employe")
        total_employes = cursor.fetchone()[0]

        # Total articles
        cursor.execute("SELECT COUNT(*) FROM Article")
        total_articles = cursor.fetchone()[0]

        # Affected articles
        cursor.execute("""
            SELECT COUNT(DISTINCT af.ID_Article_Affectation)
            FROM Affectation af
            WHERE (af.Date_Restitution_Affectation IS NULL OR af.Date_Restitution_Affectation > GETDATE())
        """)
        articles_affectes = cursor.fetchone()[0]

        # Non-affected articles
        cursor.execute("""
            SELECT COUNT(*) 
            FROM Article ar
            LEFT JOIN Affectation af ON ar.ID_Article = af.ID_Article_Affectation
            WHERE af.ID_Article_Affectation IS NULL
            OR (af.Date_Restitution_Affectation IS NOT NULL AND af.Date_Restitution_Affectation <= GETDATE())
        """)
        articles_non_affectes = cursor.fetchone()[0]

        # Articles by type
        cursor.execute("""
            SELECT Type_Article, COUNT(*) 
            FROM Article 
            GROUP BY Type_Article
        """)
        repartition_types = cursor.fetchall()

        # Articles by service
        cursor.execute("""
            SELECT COALESCE(af.Service_Employe_Article, 'N/A'), COUNT(*) 
            FROM Article ar
            INNER JOIN Affectation af ON ar.ID_Article = af.ID_Article_Affectation
            WHERE (af.Date_Restitution_Affectation IS NULL OR af.Date_Restitution_Affectation > GETDATE())
            GROUP BY COALESCE(af.Service_Employe_Article, 'N/A')
        """)
        repartition_services = cursor.fetchall()

        # Employees by direction and service
        cursor.execute("""
            SELECT COALESCE(Direction_Employe, 'N/A') AS Direction_Employe, 
                   COALESCE(Service_Employe, 'N/A') AS Service_Employe, 
                   COUNT(*) AS Nombre_Employes
            FROM Employe
            GROUP BY COALESCE(Direction_Employe, 'N/A'), COALESCE(Service_Employe, 'N/A')
        """)
        repartition_employes = cursor.fetchall()

        # Materials by direction and service
        cursor.execute("""
            -- Directions
            SELECT 
                af.Service_Employe_Article AS Direction_Employe,
                'N/A' AS Service_Employe,
                COUNT(*) AS Affectes
            FROM Article ar
            INNER JOIN Affectation af ON ar.ID_Article = af.ID_Article_Affectation
            INNER JOIN Employe e ON af.Service_Employe_Article = e.Direction_Employe
            WHERE ar.Statut_Article = 'AFFECTE'
            AND (af.Date_Restitution_Affectation IS NULL OR af.Date_Restitution_Affectation > GETDATE())
            AND af.Service_Employe_Article IS NOT NULL
            GROUP BY af.Service_Employe_Article
            UNION ALL
            -- Services
            SELECT 
                'N/A' AS Direction_Employe,
                af.Service_Employe_Article AS Service_Employe,
                COUNT(*) AS Affectes
            FROM Article ar
            INNER JOIN Affectation af ON ar.ID_Article = af.ID_Article_Affectation
            INNER JOIN Employe e ON af.Service_Employe_Article = e.Service_Employe
            WHERE ar.Statut_Article = 'AFFECTE'
            AND (af.Date_Restitution_Affectation IS NULL OR af.Date_Restitution_Affectation > GETDATE())
            AND af.Service_Employe_Article IS NOT NULL
            GROUP BY af.Service_Employe_Article
        """)
        repartition_materiel_direction_service = cursor.fetchall()

        # Log data for debugging
        logger.debug(f"Total employés: {total_employes}")
        logger.debug(f"Total articles: {total_articles}")
        logger.debug(f"Articles affectés: {articles_affectes}")
        logger.debug(f"Articles non affectés: {articles_non_affectes}")
        logger.debug(f"Répartition types: {[(row[0], row[1]) for row in repartition_types]}")
        logger.debug(f"Répartition services: {[(row[0], row[1]) for row in repartition_services]}")
        logger.debug(f"Répartition employés: {[(row[0], row[1], row[2]) for row in repartition_employes]}")
        logger.debug(f"Répartition matériel direction/service: {[(row[0], row[1], row[2]) for row in repartition_materiel_direction_service]}")

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

    except Exception as e:
        logger.error(f"Erreur dans le tableau de bord: {str(e)}")
        flash('Une erreur est survenue lors du chargement du tableau de bord.', 'danger')
        return render_template('dashboard.html',
                              total_employes=0,
                              total_articles=0,
                              articles_affectes=0,
                              articles_non_affectes=0,
                              repartition_types=[],
                              repartition_services=[],
                              repartition_employes=[],
                              repartition_materiel_direction_service=[])
inventaire_bp = Blueprint('inventaire', __name__)


@inventaire_bp.route('/liste_inventaire')
@login_required
def liste_inventaire():
    logger.debug("Accessed liste_inventaire route")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
                       SELECT a.ID_Article,
                              a.Libelle_Article,
                              a.Statut_Article,
                              a.Date_Achat_Article,
                              af.Service_Employe_Article,
                              e.Direction_Employe AS Direction_Employe_Article,
                              af.Affecter_au_Article,
                              af.Date_Affectation,
                              af.Date_Restitution_Affectation,
                              e.Nom_Employe,
                              e.Prenom_Employe
                       FROM Article a
                                LEFT JOIN Affectation af ON a.ID_Article = af.ID_Article_Affectation
                                LEFT JOIN Employe e ON af.Affecter_au_Article = e.Code_Employe
                       """)
        inventaire_raw = cursor.fetchall()

        cursor.execute("SELECT DISTINCT Direction_Employe FROM Employe WHERE Direction_Employe IS NOT NULL")
        directions_list = [row.Direction_Employe for row in cursor.fetchall()]

        today = date.today().strftime('%Y-%m-%d')
        inventaire = []
        for item in inventaire_raw:
            if item.Date_Restitution_Affectation and item.Date_Restitution_Affectation <= today:
                status_display = 'Non affecté'
                status_color = 'secondary'
            else:
                status_display = 'Active' if item.Statut_Article == 'AFFECTE' else 'Non affecté'
                status_color = 'success' if item.Statut_Article == 'AFFECTE' else 'secondary'
            inventaire.append({
                'ID_Article': item.ID_Article,
                'Libelle_Article': item.Libelle_Article,
                'Statut_Article': item.Statut_Article,
                'Date_Achat_Article': item.Date_Achat_Article,
                'Service_Employe_Article': item.Service_Employe_Article,
                'Direction_Employe_Article': item.Direction_Employe_Article,
                'Affecter_au_Article': item.Affecter_au_Article,
                'Date_Affectation': item.Date_Affectation,
                'Date_Restitution_Affectation': item.Date_Restitution_Affectation,
                'Nom_Employe': item.Nom_Employe,
                'Prenom_Employe': item.Prenom_Employe,
                'Status_Display': status_display,
                'Status_Color': status_color
            })

        conn.close()
        return render_template('liste_inventaire.html',
                               inventaire=inventaire,
                               directions_list=directions_list)
    except pyodbc.Error as e:
        logger.error(f"Database error in liste_inventaire: {str(e)}")
        flash(f'Erreur de base de données : {str(e)}', 'danger')
        return render_template('liste_inventaire.html', inventaire=[], directions_list=[])


@inventaire_bp.route('/export_inventaire')
@login_required
def export_inventaire():
    logger.debug("Accessed export_inventaire route")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                a.Libelle_Article AS 'Libellé',
                a.Statut_Article AS 'Statut',
                a.Date_Achat_Article AS 'Date Achat',
                CASE 
                    WHEN af.Service_Employe_Article IN (
                        SELECT DISTINCT Direction_Employe 
                        FROM Employe 
                        WHERE Direction_Employe IS NOT NULL
                    ) THEN NULL 
                    ELSE af.Service_Employe_Article 
                END AS 'Service',
                CASE 
                    WHEN af.Service_Employe_Article IN (
                        SELECT DISTINCT Direction_Employe 
                        FROM Employe 
                        WHERE Direction_Employe IS NOT NULL
                    ) THEN af.Service_Employe_Article 
                    ELSE NULL 
                END AS 'Direction',
                CASE 
                    WHEN af.Affecter_au_Article IS NOT NULL THEN 
                        CONCAT(e.Nom_Employe, ' ', e.Prenom_Employe, ' (Employé)')
                    WHEN af.Service_Employe_Article IN (
                        SELECT DISTINCT Direction_Employe 
                        FROM Employe 
                        WHERE Direction_Employe IS NOT NULL
                    ) THEN CONCAT(af.Service_Employe_Article, ' (Direction)')
                    ELSE COALESCE(af.Service_Employe_Article, 'N/A') + ' (Service)'
                END AS 'Affecté à',
                af.Date_Affectation AS 'Date Affectation',
                af.Date_Restitution_Affectation AS 'Date Restitution'
            FROM Article a
            LEFT JOIN Affectation af ON a.ID_Article = af.ID_Article_Affectation
                AND (af.Date_Restitution_Affectation IS NULL OR af.Date_Restitution_Affectation > ?)
            LEFT JOIN Employe e ON af.Affecter_au_Article = e.Code_Employe
        """, (date.today().strftime('%Y-%m-%d'),))
        rows = cursor.fetchall()

        columns = ['Libellé', 'Statut', 'Date Achat', 'Service', 'Direction', 'Affecté à', 'Date Affectation', 'Date Restitution']
        df = pd.DataFrame([tuple(row) for row in rows], columns=columns)
        df.fillna('-', inplace=True)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Inventaire')
        output.seek(0)

        conn.close()
        return send_file(
            output,
            download_name=f"inventaire_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            as_attachment=True,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except pyodbc.Error as e:
        logger.error(f"Database error in export_inventaire: {str(e)}")
        flash(f'Erreur de base de données : {str(e)}', 'danger')
        return redirect(url_for('inventaire.liste_inventaire'))

app.register_blueprint(inventaire_bp)


@app.route('/utilisateurs')
@login_required
def utilisateurs():
    logger.debug("Accessed utilisateurs route")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
                       SELECT ID_Employe,
                              Code_Employe,
                              Nom_Employe,
                              Prenom_Employe,
                              CIN_Employe,
                              Service_Employe,
                              Direction_Employe,
                              Statut_Employe
                       FROM Employe
                       """)
        employes = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        employes_list = [dict(zip(columns, employe)) for employe in employes]
        logger.debug(f"Total employes fetched: {len(employes_list)}")

        cursor.execute("""
                       SELECT DISTINCT Service_Employe
                       FROM Employe
                       WHERE Service_Employe IS NOT NULL
                         AND Service_Employe <> ''
                       ORDER BY Service_Employe
                       """)
        services = [row.Service_Employe for row in cursor.fetchall()]
        logger.debug(f"Services fetched: {services}")

        cursor.execute("""
                       SELECT DISTINCT Direction_Employe
                       FROM Employe
                       WHERE Direction_Employe IS NOT NULL
                         AND Direction_Employe <> ''
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
@login_required
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
                                                Fonction_Employe, Service_Employe, Direction_Employe,
                                                Affectation_Employe,
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
        directions = [row[0] for row in cursor.fetchall()]
        cursor.execute("SELECT Service_Service FROM Service")
        services = [row[0] for row in cursor.fetchall()]
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
@login_required
def editer_utilisateur(id):
    logger.debug(f"Accessed editer_utilisateur route for ID: {id}, method: {request.method}")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

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

            for form_field, db_field in field_mapping.items():
                if form_field in data and data[form_field] != '':
                    new_value = data[form_field] if data[form_field] else None
                    if new_value != employe_dict[db_field]:
                        if form_field in ['code', 'badge', 'cin']:
                            cursor.execute(f"SELECT COUNT(*) FROM Employe WHERE {db_field} = ? AND ID_Employe != ?",
                                           (new_value, id))
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
        directions = [row[0] for row in cursor.fetchall()]
        cursor.execute("SELECT Service_Service FROM Service")
        services = [row[0] for row in cursor.fetchall()]
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
@login_required
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
@login_required
def materiel():
    logger.debug("Accessed materiel route")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch articles with affectation details
        cursor.execute("""
                       SELECT a.ID_Article,
                              a.Ref_Article,
                              a.Libelle_Article,
                              a.Type_Article,
                              a.Marque_Article,
                              a.Etat_Article,
                              a.Statut_Article,
                              a.Affecter_au_Article,
                              a.Image_Path,
                              af.Service_Employe_Article,
                              e.Nom_Employe,
                              e.Prenom_Employe
                       FROM Article a
                                LEFT JOIN Affectation af ON a.ID_Article = af.ID_Article_Affectation
                           AND (af.Date_Restitution_Affectation IS NULL OR af.Date_Restitution_Affectation > ?)
                                LEFT JOIN Employe e ON a.Affecter_au_Article = e.Code_Employe
                       """, (date.today().strftime('%Y-%m-%d'),))
        articles = cursor.fetchall()
        article_columns = [column[0] for column in cursor.description]
        articles_list = []
        today = date.today().strftime('%Y-%m-%d')
        for article in articles:
            article_dict = dict(zip(article_columns, article))
            # Determine affectation display
            if article.Affecter_au_Article and article.Nom_Employe:
                article_dict['Affectation_Display'] = f"{article.Nom_Employe} {article.Prenom_Employe} (Employé)"
            elif article.Service_Employe_Article:
                # Check if Service_Employe_Article is a direction
                cursor.execute("SELECT COUNT(*) FROM Employe WHERE Direction_Employe = ?",
                               (article.Service_Employe_Article,))
                is_direction = cursor.fetchone()[0] > 0
                article_dict['Affectation_Display'] = (f"{article.Service_Employe_Article} "
                                                       f"({'Direction' if is_direction else 'Service'})")
            else:
                article_dict['Affectation_Display'] = "Non affecté"
            articles_list.append(article_dict)

        # Fetch employees for filters and details
        cursor.execute("SELECT Code_Employe, Nom_Employe, Prenom_Employe FROM Employe")
        employes = cursor.fetchall()
        employe_columns = [column[0] for column in cursor.description]
        employes_list = [dict(zip(employe_columns, employe)) for employe in employes]

        # Fetch types, states, brands, and statuses
        cursor.execute("""
                       SELECT DISTINCT Type_Article
                       FROM Article
                       WHERE Type_Article IS NOT NULL
                         AND Type_Article <> ''
                       ORDER BY Type_Article
                       """)
        types = [row.Type_Article for row in cursor.fetchall()]

        cursor.execute("""
                       SELECT DISTINCT Etat_Article
                       FROM Article
                       WHERE Etat_Article IS NOT NULL
                         AND Etat_Article <> ''
                       ORDER BY Etat_Article
                       """)
        etats = [row.Etat_Article for row in cursor.fetchall()]

        cursor.execute("""
                       SELECT DISTINCT Marque_Article
                       FROM Article
                       WHERE Marque_Article IS NOT NULL
                         AND Marque_Article <> ''
                       ORDER BY Marque_Article
                       """)
        marques = [row.Marque_Article for row in cursor.fetchall()]

        cursor.execute("""
                       SELECT DISTINCT Statut_Article
                       FROM Article
                       WHERE Statut_Article IS NOT NULL
                         AND Statut_Article <> ''
                       ORDER BY Statut_Article
                       """)
        statuts = [row.Statut_Article for row in cursor.fetchall()]

        # Fetch services and directions for filter dropdown
        cursor.execute("""
                       SELECT DISTINCT Service_Employe
                       FROM Employe
                       WHERE Service_Employe IS NOT NULL
                         AND Service_Employe <> ''
                       ORDER BY Service_Employe
                       """)
        services = [row.Service_Employe for row in cursor.fetchall()]

        cursor.execute("""
                       SELECT DISTINCT Direction_Employe
                       FROM Employe
                       WHERE Direction_Employe IS NOT NULL
                         AND Direction_Employe <> ''
                       ORDER BY Direction_Employe
                       """)
        directions = [row.Direction_Employe for row in cursor.fetchall()]

        conn.close()
        return render_template('materiel.html',
                               articles=articles_list,
                               employes=employes_list,
                               employes_liste=employes_list,
                               types=types,
                               etats=etats,
                               marques=marques,
                               statuts=statuts,
                               services=services,
                               directions=directions)
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
                               statuts=[],
                               services=[],
                               directions=[])
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
                               statuts=[],
                               services=[],
                               directions=[])

@app.route('/ajouter_materiel', methods=['GET', 'POST'])
@login_required
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
            date_achat = request.form.get('date_achat') or None
            affecte_a_id = request.form.get('affecter_au') or None

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

            cursor.execute("""
                           INSERT INTO Article (Ref_Article,
                                                Libelle_Article,
                                                Type_Article,
                                                Marque_Article,
                                                Etat_Article,
                                                Statut_Article,
                                                Affecter_au_Article,
                                                Image_Path,
                                                Date_Achat_Article)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                           """, (
                               ref,
                               libelle,
                               type_article,
                               marque,
                               etat,
                               'NON AFFECTE',  # Initial status, updated by affectation if needed
                               None,  # Affecter_au_Article set via affectation
                               image_path_db,
                               date_achat
                           ))
            article_id = cursor.execute("SELECT @@IDENTITY").fetchone()[0]

            if affecte_a_id:
                server_time = get_server_timestamp()
                numero_affectation = f"AUTO_{server_time.strftime('%Y%m%d%H%M%S')}"
                cursor.execute("""
                               INSERT INTO Affectation (ID_Article_Affectation,
                                                        Service_Employe_Article,
                                                        Date_Affectation,
                                                        Affecter_au_Article,
                                                        Numero_Affectation)
                               VALUES (?, ?, ?, ?, ?)
                               """, (
                                   article_id,
                                   cursor.execute("SELECT Service_Employe FROM Employe WHERE Code_Employe = ?",
                                                  (affecte_a_id,)).fetchone()[0] or "Inconnu",
                                   date.today().strftime('%Y-%m-%d'),
                                   affecte_a_id,
                                   numero_affectation
                               ))
                update_article_status(article_id, conn, cursor)

            conn.commit()
            flash('Matériel ajouté avec succès', 'success')
            logger.info(f"Added material: {ref}, Image_Path: {image_path_db}, Date_Achat: {date_achat}")
            conn.close()
            return redirect(url_for('materiel'))

        conn.close()
        return render_template('ajouter_materiel.html',
                               types=types,
                               etats=etats,
                               categories=categories,
                               locations=locations,
                               employes=employes)
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
@login_required
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
            affecte_a_id = request.form.get('affecte_a') or None

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

            cursor.execute("""
                           UPDATE Article
                           SET Ref_Article         = ?,
                               Libelle_Article     = ?,
                               Type_Article        = ?,
                               Marque_Article      = ?,
                               Etat_Article        = ?,
                               Affecter_au_Article = ?,
                               Image_Path          = ?
                           WHERE ID_Article = ?
                           """, (ref, libelle, type_article, marque, etat, affecte_a_id, image_path_db, id))

            if affecte_a_id and article_dict.get('Affecter_au_Article') != affecte_a_id:
                cursor.execute(
                    "DELETE FROM Affectation WHERE ID_Article_Affectation = ? AND Date_Restitution_Affectation IS NULL",
                    (id,))
                server_time = get_server_timestamp()
                numero_affectation = f"AUTO_{server_time.strftime('%Y%m%d%H%M%S')}"
                cursor.execute("""
                               INSERT INTO Affectation (ID_Article_Affectation,
                                                        Service_Employe_Article,
                                                        Date_Affectation,
                                                        Affecter_au_Article,
                                                        Numero_Affectation)
                               VALUES (?, ?, ?, ?, ?)
                               """, (
                                   id,
                                   cursor.execute("SELECT Service_Employe FROM Employe WHERE Code_Employe = ?",
                                                  (affecte_a_id,)).fetchone()[0] or "Inconnu",
                                   date.today().strftime('%Y-%m-%d'),
                                   affecte_a_id,
                                   numero_affectation
                               ))
            elif not affecte_a_id and article_dict.get('Affecter_au_Article'):
                cursor.execute(
                    "UPDATE Affectation SET Date_Restitution_Affectation = ? WHERE ID_Article_Affectation = ? AND Date_Restitution_Affectation IS NULL",
                    (date.today().strftime('%Y-%m-%d'), id))

            update_article_status(id, conn, cursor)
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
@login_required
def supprimer_materiel(id):
    logger.debug(f"Accessed supprimer_materiel route for ID: {id}")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Affectation WHERE ID_Article_Affectation = ?", (id,))
        cursor.execute("DELETE FROM Article WHERE ID_Article = ?", (id,))
        conn.commit()
        flash('Matériel supprimé', 'success')
        logger.info(f"Deleted material ID: {id}")
        conn.close()
        return redirect(url_for('materiel'))
    except pyodbc.IntegrityError as e:
        conn.rollback()
        logger.error(f"Integrity error in supprimer_materiel: {str(e)}")
        flash('Erreur : Impossible de supprimer, matériel lié à des données.', 'danger')
        return redirect(url_for('materiel'))
    except pyodbc.Error as e:
        conn.rollback()
        logger.error(f"Database error in supprimer_materiel: {str(e)}")
        flash(f'Erreur de base de données : {str(e)}', 'danger')
        return redirect(url_for('materiel'))


@app.route('/affectations')
@login_required
def affectations():
    logger.debug("Accessed affectations route")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
                       SELECT a.ID_Affectation,
                              ar.Libelle_Article,
                              e.Nom_Employe,
                              e.Prenom_Employe,
                              a.Date_Affectation,
                              a.Date_Restitution_Affectation,
                              a.Service_Employe_Article,
                              a.Affecter_au_Article
                       FROM Affectation a
                                LEFT JOIN Article ar ON a.ID_Article_Affectation = ar.ID_Article
                                LEFT JOIN Employe e ON a.Affecter_au_Article = e.Code_Employe
                       """)
        affectations_raw = cursor.fetchall()

        today = date.today().strftime('%Y-%m-%d')
        affectations = []
        for aff in affectations_raw:
            if aff.Date_Restitution_Affectation and aff.Date_Restitution_Affectation <= today:
                status_display = 'Terminée'
                status_color = 'secondary'
            else:
                status_display = 'Active'
                status_color = 'success'
            affectations.append({
                'ID_Affectation': aff.ID_Affectation,
                'Libelle_Article': aff.Libelle_Article,
                'Nom_Employe': aff.Nom_Employe,
                'Prenom_Employe': aff.Prenom_Employe,
                'Date_Affectation': aff.Date_Affectation,
                'Date_Restitution_Affectation': aff.Date_Restitution_Affectation,
                'Service_Employe_Article': aff.Service_Employe_Article,
                'Affecter_au_Article': aff.Affecter_au_Article,
                'Status_Display': status_display,
                'Status_Color': status_color
            })

        cursor.execute("SELECT ID_Article, Libelle_Article FROM Article WHERE Statut_Article = 'NON AFFECTE'")
        articles = cursor.fetchall()
        cursor.execute("SELECT Code_Employe, Nom_Employe, Prenom_Employe FROM Employe")
        employes = cursor.fetchall()
        cursor.execute(
            "SELECT DISTINCT Service_Employe FROM Employe WHERE Service_Employe IS NOT NULL AND Service_Employe <> ''")
        services = cursor.fetchall()
        cursor.execute(
            "SELECT DISTINCT Direction_Employe FROM Employe WHERE Direction_Employe IS NOT NULL AND Direction_Employe <> ''")
        directions = cursor.fetchall()
        directions_list = [d.Direction_Employe for d in directions]

        conn.close()
        return render_template('affectation.html', affectations=affectations,
                               articles=articles, employes=employes, services=services,
                               directions=directions, directions_list=directions_list,
                               current_date=today)
    except pyodbc.Error as e:
        logger.error(f"Database error in affectations: {str(e)}")
        flash(f'Erreur de base de données : {str(e)}', 'danger')
        return render_template('affectation.html', affectations=[], articles=[], employes=[],
                               services=[], directions=[], directions_list=[],
                               current_date=date.today().strftime('%Y-%m-%d'))


@app.route('/affectation/ajouter', methods=['POST'])
@login_required
def ajouter_affectation():
    logger.debug("Accessed ajouter_affectation route")
    try:
        data = request.form
        conn = get_db_connection()
        cursor = conn.cursor()

        article_id = int(data.get('article')) if data.get('article') else None
        affectation_type = data.get('affectation_type')
        employe_code = data.get('employe') if affectation_type == 'EMPLOYEE' else None
        service = data.get('service') if affectation_type == 'SERVICE' else None
        direction = data.get('direction') if affectation_type == 'DIRECTION' else None
        date_affectation = data.get('date_affectation')
        date_restitution = data.get('date_restitution') or None
        server_time = get_server_timestamp()
        numero_affectation = data.get('numero_affectation') or f"AUTO_{server_time.strftime('%Y%m%d%H%M%S')}"

        if not article_id or not date_affectation or (affectation_type == 'EMPLOYEE' and not employe_code) or \
                (affectation_type == 'SERVICE' and not service) or (affectation_type == 'DIRECTION' and not direction):
            raise ValueError("Champs obligatoires manquants.")

        cursor.execute("SELECT Statut_Article FROM Article WHERE ID_Article = ?", (article_id,))
        article = cursor.fetchone()
        if not article or article[0] == 'AFFECTE':
            raise ValueError("Matériel invalide ou déjà affecté.")

        if affectation_type == 'EMPLOYEE':
            cursor.execute("SELECT Service_Employe FROM Employe WHERE Code_Employe = ?", (employe_code,))
            employe = cursor.fetchone()
            if not employe:
                raise ValueError("Employé non trouvé.")
            service_employe_article = employe[0] or "Inconnu"
            affecter_au_article = employe_code
        elif affectation_type == 'SERVICE':
            service_employe_article = service
            affecter_au_article = None
        elif affectation_type == 'DIRECTION':
            service_employe_article = direction
            affecter_au_article = None
        else:
            raise ValueError("Type d'affectation invalide.")

        date_affectation_str = datetime.strptime(date_affectation, '%Y-%m-%d').strftime('%Y-%m-%d')
        date_restitution_str = datetime.strptime(date_restitution, '%Y-%m-%d').strftime(
            '%Y-%m-%d') if date_restitution else None

        cursor.execute("""
                       INSERT INTO Affectation (ID_Article_Affectation,
                                                Service_Employe_Article,
                                                Date_Affectation,
                                                Date_Restitution_Affectation,
                                                Affecter_au_Article,
                                                Numero_Affectation)
                       VALUES (?, ?, ?, ?, ?, ?)
                       """, (
                           article_id,
                           service_employe_article,
                           date_affectation_str,
                           date_restitution_str,
                           affecter_au_article,
                           numero_affectation
                       ))

        cursor.execute("""
                       UPDATE Article
                       SET Statut_Article      = ?,
                           Affecter_au_Article = ?
                       WHERE ID_Article = ?
                       """, (
                           'AFFECTE' if not date_restitution_str or date_restitution_str > date.today().strftime(
                               '%Y-%m-%d') else 'NON AFFECTE',
                           affecter_au_article,
                           article_id
                       ))

        conn.commit()
        flash('Affectation ajoutée avec succès', 'success')
        logger.info(
            f"Added affectation: Article {article_id}, Type {affectation_type}, Target {affecter_au_article or service_employe_article}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error in ajouter_affectation: {str(e)}")
        flash(f'Erreur: {str(e)}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('affectations'))


@app.route('/affectation/terminer/<int:id>', methods=['POST'])
@login_required
def terminer_affectation(id):
    logger.debug(f"Accessed terminer_affectation route for ID: {id}")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
                       SELECT a.ID_Affectation, ar.Libelle_Article, a.ID_Article_Affectation
                       FROM Affectation a
                                LEFT JOIN Article ar ON a.ID_Article_Affectation = ar.ID_Article
                       WHERE a.ID_Affectation = ?
                       """, (id,))
        affectation = cursor.fetchone()
        if not affectation:
            raise ValueError("Affectation non trouvée.")

        date_restitution = request.form.get('date_restitution')
        if not date_restitution:
            flash('Date de restitution requise.', 'danger')
            return redirect(url_for('affectations'))

        try:
            date_restitution_str = datetime.strptime(date_restitution, '%Y-%m-%d').strftime('%Y-%m-%d')
        except ValueError:
            flash('Format de date invalide.', 'danger')
            return redirect(url_for('affectations'))

        cursor.execute("""
                       UPDATE Affectation
                       SET Date_Restitution_Affectation = ?
                       WHERE ID_Affectation = ?
                       """, (date_restitution_str, id))

        cursor.execute("""
                       UPDATE Article
                       SET Statut_Article      = ?,
                           Affecter_au_Article = NULL
                       WHERE ID_Article = ?
                       """, (
                           'NON AFFECTE' if date_restitution_str <= date.today().strftime('%Y-%m-%d') else 'AFFECTE',
                           affectation.ID_Article_Affectation
                       ))

        conn.commit()
        flash('Affectation terminée avec succès', 'success')
        logger.info(f"Terminated affectation ID: {id} with restitution date: {date_restitution_str}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error in terminer_affectation: {str(e)}")
        flash(f'Erreur: {str(e)}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('affectations'))


@app.route('/affectation/supprimer/<int:id>', methods=['POST'])
@login_required
def supprimer_affectation(id):
    logger.debug(f"Accessed supprimer_affectation route for ID: {id}")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ID_Article_Affectation FROM Affectation WHERE ID_Affectation = ?", (id,))
        result = cursor.fetchone()
        if not result:
            raise ValueError("Affectation non trouvée.")

        article_id = result[0]
        cursor.execute("DELETE FROM Affectation WHERE ID_Affectation = ?", (id,))
        update_article_status(article_id, conn, cursor)
        conn.commit()
        flash('Affectation supprimée avec succès', 'success')
        logger.info(f"Deleted affectation ID: {id}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error in supprimer_affectation: {str(e)}")
        flash(f'Erreur: {str(e)}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('affectations'))


@app.route('/api/stats')
@login_required
def api_stats():
    logger.debug("Accessed api_stats route")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
                       SELECT SUM(CASE WHEN Statut_Article = 'AFFECTE' THEN 1 ELSE 0 END)     as affectes,
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


if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)