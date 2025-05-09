import pyodbc
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DateField, SelectField
from wtforms.validators import DataRequired, Optional
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'


# Database connection function
def get_db_connection():
    conn_str = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=localhost\\TEST;"
        "DATABASE=gestion_parc_informatique;"
        "Trusted_Connection=yes;"
    )
    return pyodbc.connect(conn_str)


class UserForm(FlaskForm):
    code_employe = StringField('Code Employé', validators=[DataRequired()])
    badge_employe = StringField('Badge Employé', validators=[Optional()])
    cin_employe = StringField('CIN Employé', validators=[DataRequired()])
    nom_employe = StringField('Nom', validators=[DataRequired()])
    prenom_employe = StringField('Prénom', validators=[DataRequired()])
    fonction_employe = StringField('Fonction', validators=[Optional()])
    service_employe = SelectField('Service', coerce=int, validators=[Optional()])
    direction_employe = SelectField('Direction', coerce=int, validators=[Optional()])
    affectation_employe = StringField('Affectation', validators=[Optional()])
    statut_employe = SelectField('Statut', choices=[('Actif', 'Actif'), ('Inactif', 'Inactif')],
                                 validators=[DataRequired()])
    date_sortie_employe = DateField('Date de Sortie', format='%Y-%m-%d', validators=[Optional()])
    submit = SubmitField('Ajouter')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/utilisateurs', methods=['GET', 'POST'])
def utilisateurs():
    form = UserForm()
    search_query = request.form.get('search', '')

    # Populate dropdowns
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get services for dropdown
    cursor.execute("SELECT ID_Service, Service_Service FROM Service")
    services = cursor.fetchall()
    form.service_employe.choices = [(s.ID_Service, s.Service_Service) for s in services]

    # Get directions for dropdown
    cursor.execute("SELECT ID_Direction, Direction_Direction FROM Direction")
    directions = cursor.fetchall()
    form.direction_employe.choices = [(d.ID_Direction, d.Direction_Direction) for d in directions]

    if request.method == 'POST':
        # Handle search
        if 'search' in request.form:
            search_query = request.form['search']
            cursor.execute("""
                           SELECT *
                           FROM Employe
                           WHERE Nom_Employe LIKE ?
                              OR Prenom_Employe LIKE ?
                           ORDER BY Nom_Employe
                           """, (f'%{search_query}%', f'%{search_query}%'))
            users = cursor.fetchall()
            conn.close()
            return render_template('utilisateurs.html', users=users, form=form, search_query=search_query)

        # Handle form submission
        if form.validate_on_submit():
            try:
                cursor.execute("""
                               INSERT INTO Employe (Code_Employe, Badge_Employe, CIN_Employe, Nom_Employe,
                                                    Prenom_Employe,
                                                    Fonction_Employe, Service_Employe, Direction_Employe,
                                                    Affectation_Employe,
                                                    Statut_Employe, Date_Sortie_Employe)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                               """, (
                                   form.code_employe.data,
                                   form.badge_employe.data,
                                   form.cin_employe.data,
                                   form.nom_employe.data,
                                   form.prenom_employe.data,
                                   form.fonction_employe.data,
                                   form.service_employe.data,
                                   form.direction_employe.data,
                                   form.affectation_employe.data,
                                   form.statut_employe.data,
                                   form.date_sortie_employe.data.strftime(
                                       '%Y-%m-%d') if form.date_sortie_employe.data else None
                               ))
                conn.commit()
                flash('Utilisateur ajouté avec succès', 'success')
            except Exception as e:
                conn.rollback()
                flash(f'Erreur: {str(e)}', 'error')
            finally:
                conn.close()
                return redirect(url_for('utilisateurs'))

    # GET request - load all users
    cursor.execute("SELECT * FROM Employe ORDER BY Nom_Employe")
    users = cursor.fetchall()
    conn.close()

    return render_template('utilisateurs.html', users=users, form=form, search_query=search_query)


@app.route('/utilisateurs/search')
def search_utilisateurs():
    query = request.args.get('query', '')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
                   SELECT *
                   FROM Employe
                   WHERE Nom_Employe LIKE ?
                      OR Prenom_Employe LIKE ?
                   """, (f'%{query}%', f'%{query}%'))
    users = cursor.fetchall()
    conn.close()
    # Convert rows to dict for JSON
    user_list = [dict(zip([column[0] for column in cursor.description], user)) for user in users]
    return jsonify(user_list)


@app.route('/utilisateurs/filter')
def filter_utilisateurs():
    status = request.args.get('status', 'all')
    conn = get_db_connection()
    cursor = conn.cursor()
    if status == 'all':
        cursor.execute("SELECT * FROM Employe")
    else:
        cursor.execute("SELECT * FROM Employe WHERE Statut_Employe = ?", (status.capitalize(),))
    users = cursor.fetchall()
    conn.close()
    user_list = [dict(zip([column[0] for column in cursor.description], user)) for user in users]
    return jsonify(user_list)


@app.route('/utilisateurs/quick-add', methods=['POST'])
def quick_add_utilisateur():
    data = request.get_json()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
                       INSERT INTO Employe (Code_Employe, CIN_Employe, Nom_Employe, Prenom_Employe, Statut_Employe)
                       VALUES (?, ?, ?, ?, ?)
                       """, (data['code_employe'], data['cin_employe'], data['nom_employe'], data['prenom_employe'],
                             data['statut_employe']))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)})
    finally:
        conn.close()


@app.route('/edit-utilisateur/<int:id>', methods=['GET', 'POST'])
def edit_utilisateur(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get user data
    cursor.execute("SELECT * FROM Employe WHERE ID_Employe = ?", (id,))
    user = cursor.fetchone()

    if not user:
        conn.close()
        flash('Utilisateur non trouvé', 'error')
        return redirect(url_for('utilisateurs'))

    # Populate dropdowns
    cursor.execute("SELECT ID_Service, Service_Service FROM Service")
    services = cursor.fetchall()

    cursor.execute("SELECT ID_Direction, Direction_Direction FROM Direction")
    directions = cursor.fetchall()

    form = UserForm(
        code_employe=user.Code_Employe,
        badge_employe=user.Badge_Employe,
        cin_employe=user.CIN_Employe,
        nom_employe=user.Nom_Employe,
        prenom_employe=user.Prenom_Employe,
        fonction_employe=user.Fonction_Employe,
        service_employe=user.Service_Employe,
        direction_employe=user.Direction_Employe,
        affectation_employe=user.Affectation_Employe,
        statut_employe=user.Statut_Employe,
        date_sortie_employe=user.Date_Sortie_Employe
    )

    form.service_employe.choices = [(s.ID_Service, s.Service_Service) for s in services]
    form.direction_employe.choices = [(d.ID_Direction, d.Direction_Direction) for d in directions]

    if request.method == 'POST' and form.validate_on_submit():
        try:
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
                               form.code_employe.data,
                               form.badge_employe.data,
                               form.cin_employe.data,
                               form.nom_employe.data,
                               form.prenom_employe.data,
                               form.fonction_employe.data,
                               form.service_employe.data,
                               form.direction_employe.data,
                               form.affectation_employe.data,
                               form.statut_employe.data,
                               form.date_sortie_employe.data.strftime(
                                   '%Y-%m-%d') if form.date_sortie_employe.data else None,
                               id
                           ))
            conn.commit()
            flash('Utilisateur modifié avec succès', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Erreur: {str(e)}', 'error')
        finally:
            conn.close()
            return redirect(url_for('utilisateurs'))

    conn.close()
    return render_template('edit_utilisateur.html', form=form, user=user)


@app.route('/delete-utilisateur/<int:id>', methods=['POST'])
def delete_utilisateur(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM Employe WHERE ID_Employe = ?", (id,))
        conn.commit()
        flash('Utilisateur supprimé avec succès', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Erreur: {str(e)}', 'error')
    finally:
        conn.close()
        return redirect(url_for('utilisateurs'))


class ArticleForm(FlaskForm):
    ref_article = StringField('Référence', validators=[DataRequired()])
    libelle_article = StringField('Libellé', validators=[DataRequired()])
    type_article = StringField('Type', validators=[DataRequired()])
    categorie_article = StringField('Catégorie')
    marque_article = StringField('Marque')
    description_article = StringField('Description')
    date_achat_article = DateField('Date Achat', format='%Y-%m-%d', validators=[Optional()])
    date_echeance_article = DateField('Date Échéance', format='%Y-%m-%d', validators=[Optional()])
    etat_article = StringField('État')
    statut_article = SelectField('Statut', choices=[('NON AFFECTE', 'Non Affecté'), ('AFFECTE', 'Affecté')],
                                 validators=[DataRequired()])
    location_article = StringField('Localisation')
    affecter_au_article = StringField('Affecté à')
    service_employe_article = SelectField('Service', coerce=int, validators=[Optional()])
    agence_article = StringField('Agence')
    date_affectation_article = DateField('Date Affectation', format='%Y-%m-%d', validators=[Optional()])
    date_restitution_article = DateField('Date Restitution', format='%Y-%m-%d', validators=[Optional()])
    compte_comptable_article = StringField('Compte Comptable')
    modifier_o = StringField('Modifier')
    achete_par_article = StringField('Acheté par')
    affecte_a_article = StringField('Affecté à (Nom)')
    numero_affectation = StringField('Numéro Affectation')
    image_path_article = StringField('Chemin de l\'Image', validators=[Optional()])
    submit = SubmitField('Ajouter')


@app.route('/materiel', methods=['GET', 'POST'])
def materiel():
    form = ArticleForm()
    search_query = request.form.get('search', '')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Populate services dropdown
    cursor.execute("SELECT ID_Service, Service_Service FROM Service")
    services = cursor.fetchall()
    form.service_employe_article.choices = [(s.ID_Service, s.Service_Service) for s in services]

    if request.method == 'POST':
        if 'search' in request.form:
            search_query = request.form['search']
            cursor.execute("""
                           SELECT *
                           FROM Article
                           WHERE Libelle_Article LIKE ?
                              OR Ref_Article LIKE ?
                           ORDER BY Libelle_Article
                           """, (f'%{search_query}%', f'%{search_query}%'))
            items = cursor.fetchall()
            conn.close()
            return render_template('materiel.html', items=items, form=form, search_query=search_query)

        if form.validate_on_submit():
            try:
                cursor.execute("""
                               INSERT INTO Article (Ref_Article, Libelle_Article, Type_Article, Categorie_Article,
                                                    Marque_Article,
                                                    Description_Article, Date_Achat_Article, Date_Echeance_Article,
                                                    Etat_Article,
                                                    Statut_Article, Location_Article, Affecter_au_Article,
                                                    Service_Employe_Article,
                                                    Agence_Article, Date_Affectation_Article, Date_Restitution_Article,
                                                    Compte_Comptable_Article, modifier_o, Achete_Par_Article,
                                                    Affecte_A_Article,
                                                    Numero_Affectation, Image_Path)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                               """, (
                                   form.ref_article.data,
                                   form.libelle_article.data,
                                   form.type_article.data,
                                   form.categorie_article.data,
                                   form.marque_article.data,
                                   form.description_article.data,
                                   form.date_achat_article.data.strftime(
                                       '%Y-%m-%d') if form.date_achat_article.data else None,
                                   form.date_echeance_article.data.strftime(
                                       '%Y-%m-%d') if form.date_echeance_article.data else None,
                                   form.etat_article.data,
                                   form.statut_article.data,
                                   form.location_article.data,
                                   form.affecter_au_article.data,
                                   form.service_employe_article.data,
                                   form.agence_article.data,
                                   form.date_affectation_article.data.strftime(
                                       '%Y-%m-%d') if form.date_affectation_article.data else None,
                                   form.date_restitution_article.data.strftime(
                                       '%Y-%m-%d') if form.date_restitution_article.data else None,
                                   form.compte_comptable_article.data,
                                   form.modifier_o.data,
                                   form.achete_par_article.data,
                                   form.affecte_a_article.data,
                                   form.numero_affectation.data,
                                   form.image_path_article.data
                               ))
                conn.commit()
                flash('Article ajouté avec succès', 'success')
            except Exception as e:
                conn.rollback()
                flash(f'Erreur: {str(e)}', 'error')
            finally:
                conn.close()
                return redirect(url_for('materiel'))

    # GET request - load all articles
    cursor.execute("SELECT * FROM Article ORDER BY Libelle_Article")
    items = cursor.fetchall()
    conn.close()

    return render_template('materiel.html', items=items, form=form, search_query=search_query)


@app.route('/materiel/edit/<int:id>', methods=['GET', 'POST'])
def edit_materiel(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get article data
    cursor.execute("SELECT * FROM Article WHERE ID_Article = ?", (id,))
    item = cursor.fetchone()

    if not item:
        conn.close()
        flash('Article non trouvé', 'error')
        return redirect(url_for('materiel'))

    # Populate services dropdown
    cursor.execute("SELECT ID_Service, Service_Service FROM Service")
    services = cursor.fetchall()

    form = ArticleForm(
        ref_article=item.Ref_Article,
        libelle_article=item.Libelle_Article,
        type_article=item.Type_Article,
        categorie_article=item.Categorie_Article,
        marque_article=item.Marque_Article,
        description_article=item.Description_Article,
        date_achat_article=datetime.strptime(item.Date_Achat_Article, '%Y-%m-%d') if item.Date_Achat_Article else None,
        date_echeance_article=datetime.strptime(item.Date_Echeance_Article,
                                                '%Y-%m-%d') if item.Date_Echeance_Article else None,
        etat_article=item.Etat_Article,
        statut_article=item.Statut_Article,
        location_article=item.Location_Article,
        affecter_au_article=item.Affecter_au_Article,
        service_employe_article=item.Service_Employe_Article,
        agence_article=item.Agence_Article,
        date_affectation_article=datetime.strptime(item.Date_Affectation_Article,
                                                   '%Y-%m-%d') if item.Date_Affectation_Article else None,
        date_restitution_article=datetime.strptime(item.Date_Restitution_Article,
                                                   '%Y-%m-%d') if item.Date_Restitution_Article else None,
        compte_comptable_article=item.Compte_Comptable_Article,
        modifier_o=item.modifier_o,
        achete_par_article=item.Achete_Par_Article,
        affecte_a_article=item.Affecte_A_Article,
        numero_affectation=item.Numero_Affectation,
        image_path_article=item.Image_Path
    )

    form.service_employe_article.choices = [(s.ID_Service, s.Service_Service) for s in services]

    if request.method == 'POST' and form.validate_on_submit():
        try:
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
                               Numero_Affectation       = ?,
                               Image_Path               = ?
                           WHERE ID_Article = ?
                           """, (
                               form.ref_article.data,
                               form.libelle_article.data,
                               form.type_article.data,
                               form.categorie_article.data,
                               form.marque_article.data,
                               form.description_article.data,
                               form.date_achat_article.data.strftime(
                                   '%Y-%m-%d') if form.date_achat_article.data else None,
                               form.date_echeance_article.data.strftime(
                                   '%Y-%m-%d') if form.date_echeance_article.data else None,
                               form.etat_article.data,
                               form.statut_article.data,
                               form.location_article.data,
                               form.affecter_au_article.data,
                               form.service_employe_article.data,
                               form.agence_article.data,
                               form.date_affectation_article.data.strftime(
                                   '%Y-%m-%d') if form.date_affectation_article.data else None,
                               form.date_restitution_article.data.strftime(
                                   '%Y-%m-%d') if form.date_restitution_article.data else None,
                               form.compte_comptable_article.data,
                               form.modifier_o.data,
                               form.achete_par_article.data,
                               form.affecte_a_article.data,
                               form.numero_affectation.data,
                               form.image_path_article.data,
                               id
                           ))
            conn.commit()
            flash('Article modifié avec succès', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Erreur: {str(e)}', 'error')
        finally:
            conn.close()
            return redirect(url_for('materiel'))

    conn.close()
    return render_template('edit_materiel.html', form=form, id=id)


@app.route('/materiel/delete/<int:id>', methods=['POST'])
def delete_materiel(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM Article WHERE ID_Article = ?", (id,))
        conn.commit()
        flash('Article supprimé avec succès', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Erreur: {str(e)}', 'error')
    finally:
        conn.close()
        return redirect(url_for('materiel'))


class AffectationForm(FlaskForm):
    id_article_affectation = SelectField('Article', coerce=int, validators=[DataRequired()])
    service_employe_article = SelectField('Service', coerce=int, validators=[Optional()])
    date_affectation = DateField('Date Affectation', format='%Y-%m-%d', validators=[DataRequired()])
    date_restitution_affectation = DateField('Date Restitution', format='%Y-%m-%d', validators=[Optional()])
    affecter_au_article = StringField('Affecté à')
    numero_affectation = StringField('Numéro Affectation')
    submit = SubmitField('Affecter')


@app.route('/affectation', methods=['GET', 'POST'])
def affectation():
    form = AffectationForm()
    search_query = request.form.get('search', '')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Populate dropdowns
    cursor.execute("SELECT ID_Service, Service_Service FROM Service")
    services = cursor.fetchall()
    form.service_employe_article.choices = [(s.ID_Service, s.Service_Service) for s in services]

    cursor.execute("SELECT ID_Article, Libelle_Article FROM Article")
    articles = cursor.fetchall()
    form.id_article_affectation.choices = [(a.ID_Article, a.Libelle_Article) for a in articles]

    if request.method == 'POST':
        if 'search' in request.form:
            search_query = request.form['search']
            cursor.execute("""
                           SELECT a.*, ar.Libelle_Article
                           FROM Affectation a
                                    JOIN Article ar ON a.ID_Article_Affectation = ar.ID_Article
                           WHERE ar.Libelle_Article LIKE ?
                              OR a.Service_Employe_Article LIKE ?
                           """, (f'%{search_query}%', f'%{search_query}%'))
            affectations = cursor.fetchall()
            conn.close()
            return render_template('affectation.html', affectations=affectations, form=form, search_query=search_query)

        if form.validate_on_submit():
            try:
                cursor.execute("""
                               INSERT INTO Affectation (ID_Article_Affectation, Service_Employe_Article,
                                                        Date_Affectation,
                                                        Date_Restitution_Affectation, Affecter_au_Article,
                                                        Numero_Affectation)
                               VALUES (?, ?, ?, ?, ?, ?)
                               """, (
                                   form.id_article_affectation.data,
                                   form.service_employe_article.data,
                                   form.date_affectation.data.strftime('%Y-%m-%d'),
                                   form.date_restitution_affectation.data.strftime(
                                       '%Y-%m-%d') if form.date_restitution_affectation.data else None,
                                   form.affecter_au_article.data,
                                   form.numero_affectation.data
                               ))
                conn.commit()
                flash('Affectation ajoutée avec succès', 'success')
            except Exception as e:
                conn.rollback()
                flash(f'Erreur: {str(e)}', 'error')
            finally:
                conn.close()
                return redirect(url_for('affectation'))

    # GET request - load all affectations
    cursor.execute("""
                   SELECT a.*, ar.Libelle_Article
                   FROM Affectation a
                            JOIN Article ar ON a.ID_Article_Affectation = ar.ID_Article
                   """)
    affectations = cursor.fetchall()
    conn.close()

    return render_template('affectation.html', affectations=affectations, form=form, search_query=search_query)


@app.route('/affectation/delete/<int:id>', methods=['POST'])
def delete_affectation(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM Affectation WHERE ID_Affectation = ?", (id,))
        conn.commit()
        flash('Affectation supprimée avec succès', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Erreur: {str(e)}', 'error')
    finally:
        conn.close()
        return redirect(url_for('affectation'))


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if request.method == 'POST':
        username = request.form.get('username', 'Utilisateur')
        email = request.form.get('email', 'utilisateur@fedex.com')
        return render_template('profile.html', username=username, email=email)
    return render_template('profile.html', username='Utilisateur', email='utilisateur@fedex.com')




@app.route('/materiel/search')
def search_materiel():
    query = request.args.get('query', '')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM Article 
        WHERE Libelle_Article LIKE ? OR Ref_Article LIKE ?
    """, (f'%{query}%', f'%{query}%'))
    items = cursor.fetchall()
    conn.close()
    item_list = [dict(zip([column[0] for column in cursor.description], item)) for item in items]
    return jsonify(item_list)

@app.route('/materiel/filter')
def filter_materiel():
    status = request.args.get('status', 'all')
    conn = get_db_connection()
    cursor = conn.cursor()
    if status == 'all':
        cursor.execute("SELECT * FROM Article")
    else:
        cursor.execute("SELECT * FROM Article WHERE Statut_Article = ?", (status,))
    items = cursor.fetchall()
    conn.close()
    item_list = [dict(zip([column[0] for column in cursor.description], item)) for item in items]
    return jsonify(item_list)

@app.route('/materiel/quick-add', methods=['POST'])
def quick_add_materiel():
    data = request.get_json()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO Article (Ref_Article, Libelle_Article, Type_Article, Statut_Article)
            VALUES (?, ?, ?, ?)
        """, (data['ref_article'], data['libelle_article'], data['type_article'], data['statut_article']))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)})
    finally:
        conn.close()
if __name__ == '__main__':
    app.run(debug=True)