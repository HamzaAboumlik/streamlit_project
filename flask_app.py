from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, Response
import pyodbc
import os
from werkzeug.utils import secure_filename
import uuid
import logging
from datetime import datetime
from flask_bcrypt import Bcrypt
from functools import wraps
import json
import csv
import pandas as pd

# App setup
app = Flask(__name__, static_folder='static')
app.secret_key = os.urandom(24).hex()  # Secure random key
app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'images')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Initialize Bcrypt
bcrypt = Bcrypt(app)

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


def get_server_timestamp():
    """Fetch the current timestamp from SQL Server."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT CURRENT_TIMESTAMP")
        timestamp = cursor.fetchone()[0]
        conn.close()
        return timestamp
    except pyodbc.Error as e:
        logger.error(f"Error fetching server timestamp: {str(e)}")
        return datetime.now()  # Fallback to local time if DB fails


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

            # Validate inputs
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

            # Check email uniqueness
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM [User] WHERE Email = ?", (email,))
            if cursor.fetchone()[0] > 0:
                conn.close()
                flash('Cet email est déjà utilisé.', 'danger')
                return redirect(request.url)

            # Hash password
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

            # Insert user
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

            # Validate inputs
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

            # Check email uniqueness
            cursor.execute("SELECT COUNT(*) FROM [User] WHERE Email = ? AND ID_User != ?", (email, id))
            if cursor.fetchone()[0] > 0:
                conn.close()
                flash('Cet email est déjà utilisé.', 'danger')
                return redirect(request.url)

            # Update user
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

            # Validate inputs
            if not current_password or not new_password:
                flash('Mot de passe actuel et nouveau mot de passe requis.', 'danger')
                return redirect(request.url)
            if new_password != password_confirm:
                flash('Les nouveaux mots de passe ne correspondent pas.', 'danger')
                return redirect(request.url)
            if len(new_password) < 8:
                flash('Le nouveau mot de passe doit contenir au moins 8 caractères.', 'danger')
                return redirect(request.url)

            # Verify current password
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT Password FROM [User] WHERE ID_User = ?", (session['user_id'],))
            user = cursor.fetchone()
            if not user or not bcrypt.check_password_hash(user[0], current_password):
                conn.close()
                flash('Mot de passe actuel incorrect.', 'danger')
                return redirect(request.url)

            # Update password
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
@login_required
def dashboard():
    logger.debug("Accessed dashboard route")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Total employees
        cursor.execute("SELECT COUNT(*) FROM Employe")
        total_employes = cursor.fetchone()[0]
        logger.debug(f"Total employes: {total_employes}")

        # Total articles
        cursor.execute("SELECT COUNT(*) FROM Article")
        total_articles = cursor.fetchone()[0]
        logger.debug(f"Total articles: {total_articles}")

        # Articles affectés (Statut_Article = 'AFFECTE')
        cursor.execute("SELECT COUNT(*) FROM Article WHERE Statut_Article = 'AFFECTE'")
        articles_affectes = cursor.fetchone()[0]
        logger.debug(f"Articles affectés: {articles_affectes}")

        # Articles non affectés (Statut_Article = 'NON AFFECTE')
        cursor.execute("SELECT COUNT(*) FROM Article WHERE Statut_Article = 'NON AFFECTE'")
        articles_non_affectes = cursor.fetchone()[0]
        logger.debug(f"Articles non affectés: {articles_non_affectes}")

        # Répartition des matériels par statut
        cursor.execute("""
                       SELECT Statut_Article, COUNT(*) as count
                       FROM Article
                       WHERE Statut_Article IS NOT NULL AND Statut_Article <> ''
                       GROUP BY Statut_Article
                       """)
        repartition_statuts = cursor.fetchall()
        logger.debug(f"Répartition statuts: {[(row[0], row[1]) for row in repartition_statuts]}")

        # Répartition des matériels par type
        cursor.execute("""
                       SELECT Type_Article, COUNT(*) as count
                       FROM Article
                       WHERE Type_Article IS NOT NULL AND Type_Article <> ''
                       GROUP BY Type_Article
                       """)
        repartition_types = cursor.fetchall()
        logger.debug(f"Répartition types: {[(row[0], row[1]) for row in repartition_types]}")

        # Répartition des matériels par service
        cursor.execute("""
                       SELECT e.Service_Employe, COUNT(a.ID_Article) as count
                       FROM Employe e
                           LEFT JOIN Article a
                       ON e.Code_Employe = a.Affecter_au_Article
                       WHERE e.Service_Employe IS NOT NULL AND e.Service_Employe <> ''
                       GROUP BY e.Service_Employe
                       """)
        repartition_services = cursor.fetchall()
        logger.debug(f"Répartition services: {[(row[0], row[1]) for row in repartition_services]}")

        # Répartition des employés par direction et service
        cursor.execute("""
                       SELECT Direction_Employe, Service_Employe, COUNT(*) as Nombre_Employes
                       FROM Employe
                       WHERE Direction_Employe IS NOT NULL
                         AND Service_Employe IS NOT NULL
                       GROUP BY Direction_Employe, Service_Employe
                       """)
        repartition_employes = cursor.fetchall()
        logger.debug(f"Répartition employés: {[(row[0], row[1], row[2]) for row in repartition_employes]}")

        # Répartition des matériels affectés et non affectés par direction et service
        cursor.execute("""
                       SELECT e.Direction_Employe,
                              e.Service_Employe,
                              SUM(CASE WHEN a.Statut_Article = 'AFFECTE' THEN 1 ELSE 0 END)     as Affectes,
                              SUM(CASE WHEN a.Statut_Article = 'NON AFFECTE' THEN 1 ELSE 0 END) as Non_Affectes
                       FROM Employe e
                                LEFT JOIN Article a ON e.Code_Employe = a.Affecter_au_Article
                       WHERE e.Direction_Employe IS NOT NULL
                         AND e.Service_Employe IS NOT NULL
                       GROUP BY e.Direction_Employe, e.Service_Employe
                       """)
        repartition_materiel_direction_service = cursor.fetchall()
        logger.debug(
            f"Répartition matériel direction/service: {[(row[0], row[1], row[2], row[3]) for row in repartition_materiel_direction_service]}")

        conn.close()
        return render_template('dashboard.html',
                               total_employes=total_employes,
                               total_articles=total_articles,
                               articles_affectes=articles_affectes,
                               articles_non_affectes=articles_non_affectes,
                               repartition_statuts=repartition_statuts,
                               repartition_types=repartition_types,
                               repartition_services=repartition_services,
                               repartition_employes=repartition_employes,
                               repartition_materiel_direction_service=repartition_materiel_direction_service)
    except pyodbc.Error as e:
        logger.error(f"Database error in dashboard: {str(e)}")
        flash(f'Erreur de base de données : {str(e)}', 'danger')
        return render_template('dashboard.html',
                               total_employes=0,
                               total_articles=0,
                               articles_affectes=0,
                               articles_non_affectes=0,
                               repartition_statuts=[],
                               repartition_types=[],
                               repartition_services=[],
                               repartition_employes=[],
                               repartition_materiel_direction_service=[])
    except Exception as e:
        logger.error(f"Error in dashboard: {str(e)}")
        flash(f'Erreur : {str(e)}', 'danger')
        return render_template('dashboard.html',
                               total_employes=0,
                               total_articles=0,
                               articles_affectes=0,
                               articles_non_affectes=0,
                               repartition_statuts=[],
                               repartition_types=[],
                               repartition_services=[],
                               repartition_employes=[],
                               repartition_materiel_direction_service=[])


@app.route('/export_stats', methods=['POST'])
@login_required
def export_stats():
    logger.debug("Accessed export_stats route")
    try:
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        export_format = request.form.get('format')

        if not start_date or not end_date or not export_format:
            raise ValueError("Missing required fields")

        conn = get_db_connection()
        cursor = conn.cursor()

        # Collect data
        cursor.execute("SELECT COUNT(*) FROM Employe")
        total_employes = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM Article")
        total_articles = cursor.fetchone()[0]

        cursor.execute("""
                       SELECT COUNT(*)
                       FROM Article a
                                JOIN Affectation af ON a.ID_Article = af.ID_Article_Affectation
                       WHERE af.Date_Affectation BETWEEN ? AND ?
                         AND (af.Date_Restitution_Affectation IS NULL OR af.Date_Restitution_Affectation > ?)
                       """, (start_date, end_date, end_date))
        articles_affectes = cursor.fetchone()[0]

        cursor.execute("""
                       SELECT COUNT(*)
                       FROM Article
                       WHERE ID_Article NOT IN (SELECT ID_Article_Affectation
                                                FROM Affectation
                                                WHERE Date_Affectation BETWEEN ? AND ?
                                                  AND (Date_Restitution_Affectation IS NULL OR Date_Restitution_Affectation > ?))
                       """, (start_date, end_date, end_date))
        articles_non_affectes = cursor.fetchone()[0]

        cursor.execute("SELECT Type_Article, COUNT(*) FROM Article GROUP BY Type_Article")
        repartition_types = cursor.fetchall()

        cursor.execute("""
                       SELECT af.Service_Employe_Article, COUNT(*)
                       FROM Affectation af
                       WHERE af.Date_Affectation BETWEEN ? AND ?
                         AND (af.Date_Restitution_Affectation IS NULL OR af.Date_Restitution_Affectation > ?)
                       GROUP BY af.Service_Employe_Article
                       """, (start_date, end_date, end_date))
        repartition_services = cursor.fetchall()

        cursor.execute("""
                       SELECT Direction_Employe, Service_Employe, COUNT(*) as Nombre_Employes
                       FROM Employe
                       GROUP BY Direction_Employe, Service_Employe
                       """)
        repartition_employes = cursor.fetchall()

        cursor.execute("""
                       SELECT e.Direction_Employe,
                              e.Service_Employe,
                              SUM(CASE
                                      WHEN a.Statut_Article = 'AFFECTE'
                                          AND af.Date_Affectation BETWEEN ? AND ?
                                          AND (af.Date_Restitution_Affectation IS NULL OR
                                               af.Date_Restitution_Affectation > ?)
                                          THEN 1
                                      ELSE 0 END)                                               as Affectes,
                              SUM(CASE WHEN a.Statut_Article = 'NON AFFECTE' THEN 1 ELSE 0 END) as Non_Affectes
                       FROM Employe e
                                LEFT JOIN Affectation af ON e.Service_Employe = af.Service_Employe_Article
                                LEFT JOIN Article a ON af.ID_Article_Affectation = a.ID_Article
                       GROUP BY e.Direction_Employe, e.Service_Employe
                       """, (start_date, end_date, end_date))
        repartition_materiel_direction_service = cursor.fetchall()

        conn.close()

        # Prepare data structure
        data = {
            'summary': {
                'total_employes': total_employes,
                'total_articles': total_articles,
                'articles_affectes': articles_affectes,
                'articles_non_affectes': articles_non_affectes,
                'date_range': f'{start_date} to {end_date}'
            },
            'articles_by_status': [
                {'status': 'Affectés', 'count': articles_affectes,
                 'percentage': round((articles_affectes / (articles_affectes + articles_non_affectes)) * 100, 1) if (
                                                                                                                                articles_affectes + articles_non_affectes) > 0 else 0},
                {'status': 'Non affectés', 'count': articles_non_affectes,
                 'percentage': round((articles_non_affectes / (articles_affectes + articles_non_affectes)) * 100,
                                     1) if (articles_affectes + articles_non_affectes) > 0 else 0}
            ],
            'articles_by_type': [
                {'type': row[0] or 'N/A', 'count': row[1]} for row in repartition_types
            ],
            'articles_by_service': [
                {'service': row[0] or 'N/A', 'count': row[1]} for row in repartition_services
            ],
            'employees_by_direction_service': [
                {'direction': row[0] or 'N/A', 'service': row[1] or 'N/A', 'count': row[2]} for row in
                repartition_employes
            ],
            'articles_by_direction_service': [
                {'direction': row[0] or 'N/A', 'service': row[1] or 'N/A', 'affectes': row[2], 'non_affectes': row[3]}
                for row in repartition_materiel_direction_service
            ]
        }

        if export_format == 'csv':
            output = io.StringIO()
            writer = csv.writer(output)

            writer.writerow(['Dashboard Statistics'])
            writer.writerow([f'Date Range: {start_date} to {end_date}'])
            writer.writerow([])

            writer.writerow(['Summary'])
            writer.writerow(['Metric', 'Value'])
            for key, value in data['summary'].items():
                writer.writerow([key.replace('_', ' ').title(), value])
            writer.writerow([])

            writer.writerow(['Articles by Status'])
            writer.writerow(['Status', 'Count', 'Percentage'])
            for item in data['articles_by_status']:
                writer.writerow([item['status'], item['count'], f"{item['percentage']}%"])
            writer.writerow([])

            writer.writerow(['Articles by Type'])
            writer.writerow(['Type', 'Count'])
            for item in data['articles_by_type']:
                writer.writerow([item['type'], item['count']])
            writer.writerow([])

            writer.writerow(['Articles by Service'])
            writer.writerow(['Service', 'Count'])
            for item in data['articles_by_service']:
                writer.writerow([item['service'], item['count']])
            writer.writerow([])

            writer.writerow(['Employees by Direction and Service'])
            writer.writerow(['Direction', 'Service', 'Count'])
            for item in data['employees_by_direction_service']:
                writer.writerow([item['direction'], item['service'], item['count']])
            writer.writerow([])

            writer.writerow(['Articles by Direction and Service'])
            writer.writerow(['Direction', 'Service', 'Affectes', 'Non Affectes'])
            for item in data['articles_by_direction_service']:
                writer.writerow([item['direction'], item['service'], item['affectes'], item['non_affectes']])

            filename = f'dashboard_stats_{start_date}_to_{end_date}.csv'
            return Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={'Content-Disposition': f'attachment;filename={filename}'}
            )

        elif export_format == 'json':
            filename = f'dashboard_stats_{start_date}_to_{end_date}.json'
            return Response(
                json.dumps(data, indent=2, ensure_ascii=False),
                mimetype='application/json',
                headers={'Content-Disposition': f'attachment;filename={filename}'}
            )

        elif export_format == 'excel':
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                pd.DataFrame([
                    {'Metric': key.replace('_', ' ').title(), 'Value': value}
                    for key, value in data['summary'].items()
                ]).to_excel(writer, sheet_name='Summary', index=False)
                pd.DataFrame(data['articles_by_status']).to_excel(writer, sheet_name='Articles_by_Status', index=False)
                pd.DataFrame(data['articles_by_type']).to_excel(writer, sheet_name='Articles_by_Type', index=False)
                pd.DataFrame(data['articles_by_service']).to_excel(writer, sheet_name='Articles_by_Service',
                                                                   index=False)
                pd.DataFrame(data['employees_by_direction_service']).to_excel(writer,
                                                                              sheet_name='Employees_by_Dir_Service',
                                                                              index=False)
                pd.DataFrame(data['articles_by_direction_service']).to_excel(writer,
                                                                             sheet_name='Articles_by_Dir_Service',
                                                                             index=False)

            output.seek(0)
            filename = f'dashboard_stats_{start_date}_to_{end_date}.xlsx'
            return Response(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={'Content-Disposition': f'attachment;filename={filename}'}
            )

        else:
            raise ValueError("Invalid export format")

    except Exception as e:
        logger.error(f"Error in export_stats: {str(e)}")
        flash(f'Erreur lors de l\'exportation : {str(e)}', 'danger')
        return redirect(url_for('dashboard'))


@app.route('/utilisateurs')
@login_required
def utilisateurs():
    logger.debug("Accessed utilisateurs route")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch all employees
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

        # Fetch distinct services (exclude NULL and empty)
        cursor.execute("""
                       SELECT DISTINCT Service_Employe
                       FROM Employe
                       WHERE Service_Employe IS NOT NULL
                         AND Service_Employe <> ''
                       ORDER BY Service_Employe
                       """)
        services = [row.Service_Employe for row in cursor.fetchall()]
        logger.debug(f"Services fetched: {services}")

        # Fetch distinct directions (exclude NULL and empty)
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
                           SET Ref_Article         = ?,
                               Libelle_Article     = ?,
                               Type_Article        = ?,
                               Marque_Article      = ?,
                               Etat_Article        = ?,
                               Statut_Article      = ?,
                               Affecter_au_Article = ?,
                               Image_Path          = ?
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
@login_required
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
        affectations = cursor.fetchall()
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
                               current_date=get_server_timestamp().strftime('%Y-%m-%d'))
    except pyodbc.Error as e:
        logger.error(f"Database error in affectations: {str(e)}")
        flash(f'Erreur de base de données : {str(e)}', 'danger')
        return render_template('affectation.html', affectations=[], articles=[], employes=[],
                               services=[], directions=[], directions_list=[],
                               current_date=get_server_timestamp().strftime('%Y-%m-%d'))


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
        # Use server timestamp for numero_affectation
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
                       INSERT INTO Affectation (ID_Article_Affectation, Service_Employe_Article, Date_Affectation,
                                                Date_Restitution_Affectation, Affecter_au_Article, Numero_Affectation)
                       VALUES (?, ?, ?, ?, ?, ?)
                       """, (article_id, service_employe_article, date_affectation_str, date_restitution_str,
                             affecter_au_article, numero_affectation))

        cursor.execute("""
                       UPDATE Article
                       SET Statut_Article           = 'AFFECTE',
                           Affecter_au_Article      = ?,
                           Service_Employe_Article  = ?,
                           Date_Affectation_Article = ?,
                           Date_Restitution_Article = ?,
                           Numero_Affectation       = ?
                       WHERE ID_Article = ?
                       """, (affecter_au_article, service_employe_article, date_affectation_str, date_restitution_str,
                             numero_affectation, article_id))

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


@app.route('/affectation/terminer/<int:id>', methods=['GET', 'POST'])
@login_required
def terminer_affectation(id):
    logger.debug(f"Accessed terminer_affectation route for ID: {id}, method: {request.method}")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
                       SELECT a.ID_Affectation, ar.Libelle_Article
                       FROM Affectation a
                                LEFT JOIN Article ar ON a.ID_Article_Affectation = ar.ID_Article
                       WHERE a.ID_Affectation = ?
                       """, (id,))
        affectation = cursor.fetchone()
        if not affectation:
            conn.close()
            raise ValueError("Affectation non trouvée.")

        affectation_dict = {'ID_Affectation': affectation[0], 'Libelle_Article': affectation[1]}

        if request.method == 'POST':
            date_restitution = request.form.get('date_restitution')
            if not date_restitution:
                conn.close()
                flash('Date de restitution requise.', 'danger')
                return redirect(request.url)

            # Validate date format
            try:
                date_restitution_str = datetime.strptime(date_restitution, '%Y-%m-%d').strftime('%Y-%m-%d')
            except ValueError:
                conn.close()
                flash('Format de date invalide.', 'danger')
                return redirect(request.url)

            cursor.execute("SELECT ID_Article_Affectation FROM Affectation WHERE ID_Affectation = ?", (id,))
            id_article = cursor.fetchone()[0]

            cursor.execute("""
                           UPDATE Affectation
                           SET Date_Restitution_Affectation = ?
                           WHERE ID_Affectation = ?
                           """, (date_restitution_str, id))
            cursor.execute("""
                           UPDATE Article
                           SET Statut_Article           = 'NON AFFECTE',
                               Affecter_au_Article      = NULL,
                               Service_Employe_Article  = NULL,
                               Date_Restitution_Article = ?,
                               Numero_Affectation       = NULL
                           WHERE ID_Article = ?
                           """, (date_restitution_str, id_article))
            conn.commit()
            flash('Affectation terminée avec succès', 'success')
            logger.info(f"Terminated affectation ID: {id} with restitution date: {date_restitution_str}")
            conn.close()
            return redirect(url_for('affectations'))

        conn.close()
        return render_template('terminer_affectation.html', affectation=affectation_dict,
                               current_date=get_server_timestamp().strftime('%Y-%m-%d'))
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        logger.error(f"Error in terminer_affectation: {str(e)}")
        flash(f'Erreur: {str(e)}', 'danger')
        return redirect(url_for('affectations'))


@app.route('/affectation/supprimer/<int:id>', methods=['POST'])
@login_required
def supprimer_affectation(id):
    logger.debug(f"Accessed supprimer_affectation route for ID: {id}")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ID_Article_Affectation FROM Affectation WHERE ID_Affectation = ?", (id,))
        id_article = cursor.fetchone()
        if not id_article:
            raise ValueError("Affectation non trouvée.")
        id_article = id_article[0]

        cursor.execute("DELETE FROM Affectation WHERE ID_Affectation = ?", (id,))
        cursor.execute("""
                       UPDATE Article
                       SET Statut_Article           = 'NON AFFECTE',
                           Affecter_au_Article      = NULL,
                           Service_Employe_Article  = NULL,
                           Date_Affectation_Article = NULL,
                           Date_Restitution_Article = NULL,
                           Numero_Affectation       = NULL
                       WHERE ID_Article = ?
                       """, (id_article,))
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
