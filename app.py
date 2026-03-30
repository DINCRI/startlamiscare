import os
from flask import Flask, render_template, request, abort, flash
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from flask_basicauth import BasicAuth
from wtforms import MultipleFileField

app = Flask(__name__)

app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'
app.secret_key = "super secret key"

app.config['BASIC_AUTH_USERNAME'] = 'john'
app.config['BASIC_AUTH_PASSWORD'] = 'matrix'

app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///project.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

basic_auth = BasicAuth(app)
db = SQLAlchemy(app)


# ------------------------
# MODELE
# ------------------------

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), nullable=False)


class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    uploads = db.Column(db.Text, nullable=True)


class Document(db.Model):
    __tablename__ = 'documents'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    uploads = db.Column(db.Text, nullable=True)


class Sport(db.Model):
    __tablename__ = 'sporturi'
    id = db.Column(db.Integer, primary_key=True)
    nume = db.Column(db.String(100), unique=True, nullable=False)
    locuri_maxime = db.Column(db.Integer, nullable=False, default=100)


class Inscriere(db.Model):
    __tablename__ = 'inscrieri'
    id = db.Column(db.Integer, primary_key=True)
    nume = db.Column(db.String(100), nullable=False)
    prenume = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    telefon = db.Column(db.String(20), nullable=False)
    sport = db.Column(db.String(100), nullable=False)


# ------------------------
# INITIALIZARE DB
# ------------------------

with app.app_context():
    db.create_all()

    sporturi_default = [
        ("Cros", 100),
        ("Tenis de câmp", 50),
        ("Haltere", 100),
        ("Volei", 80),
        ("Mini fotbal", 120),
        ("Badminton", 60),
        ("Baschet", 100),
        ("Flowerstick", 40),
        ("Diabolo", 40),
        ("Tenis de masă", 70),
        ("Taekwondo", 50),
        ("Box", 50),
        ("Teqball", 40),
        ("Handball", 90),
    ]

    for nume_sport, locuri in sporturi_default:
        exista = Sport.query.filter_by(nume=nume_sport).first()
        if not exista:
            db.session.add(Sport(nume=nume_sport, locuri_maxime=locuri))

    db.session.commit()


# ------------------------
# SECURITATE ADMIN
# ------------------------

ALLOWED_IP = '127.0.0.1'


@app.before_request
def limit_remote_addr():
    if request.remote_addr != ALLOWED_IP and request.path.startswith('/admin'):
        abort(403)


class MyAdminIndexView(AdminIndexView):
    @expose('/')
    @basic_auth.required
    def index(self):
        return super(MyAdminIndexView, self).index()


class MyModelView(ModelView):
    form_extra_fields = {
        'uploads': MultipleFileField('Files')
    }

    def on_model_change(self, form, model, is_created):
        if 'uploads' in request.files:
            files = request.files.getlist("uploads")
            filenames = []

            for file in files:
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    filenames.append(filename)

            if filenames:
                model.uploads = ','.join(filenames)

    def is_accessible(self):
        return basic_auth.authenticate()


admin = Admin(app, name='admin', index_view=MyAdminIndexView())
admin.add_view(MyModelView(User, db.session))
admin.add_view(MyModelView(Post, db.session))
admin.add_view(MyModelView(Document, db.session))
admin.add_view(MyModelView(Sport, db.session))
admin.add_view(MyModelView(Inscriere, db.session))


# ------------------------
# RUTE SITE
# ------------------------

@app.route("/")
def index():
    posts = Post.query.all()
    sporturi = Sport.query.all()

    sporturi_status = []

    for sport in sporturi:
        inscrisi = Inscriere.query.filter_by(sport=sport.nume).count()

        procent = 0
        if sport.locuri_maxime > 0:
            procent = round((inscrisi / sport.locuri_maxime) * 100)

        if procent > 100:
            procent = 100

        sporturi_status.append({
            "nume": sport.nume,
            "locuri_maxime": sport.locuri_maxime,
            "inscrisi": inscrisi,
            "procent": procent
        })

    return render_template(
        "index.html",
        posts=posts,
        sporturi_status=sporturi_status
    )


@app.route("/anunturi")
def anunturi():
    return render_template("anunturi.html", posts=Post.query.all())


@app.route("/post/<int:post_id>")
def post_detail(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template("post_detail.html", post=post)


@app.route("/utile")
def utile():
    return render_template("utile.html", documents=Document.query.all())


@app.route("/despre-noi")
def despre_noi():
    return render_template("despre_noi.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


# ------------------------
# INSCRIERE
# ------------------------

@app.route('/inscriere/', methods=('GET', 'POST'))
def inscriere():
    if request.method == 'POST':
        nume = request.form['nume'].strip()
        prenume = request.form['prenume'].strip()
        email = request.form['email'].strip()
        telefon = request.form['telefon'].strip()
        sport = request.form['sport'].strip()

        if not nume:
            flash('Numele este obligatoriu!', 'warning')
        elif not prenume:
            flash('Prenumele este obligatoriu!', 'warning')
        elif not email:
            flash('Emailul este obligatoriu!', 'warning')
        elif not telefon:
            flash('Telefonul este obligatoriu!', 'warning')
        elif not sport:
            flash('Selectează un sport!', 'warning')
        else:
            sport_selectat = Sport.query.filter_by(nume=sport).first()

            if not sport_selectat:
                flash('Sport invalid!', 'warning')
            else:
                inscrisi_curent = Inscriere.query.filter_by(sport=sport).count()

                if inscrisi_curent >= sport_selectat.locuri_maxime:
                    flash(f'Nu mai sunt locuri disponibile la {sport}!', 'warning')
                else:
                    existing = Inscriere.query.filter_by(email=email, sport=sport).first()

                    if existing:
                        flash('Există deja o înscriere cu acest email la sportul selectat!', 'warning')
                    else:
                        inscriere_noua = Inscriere(
                            nume=nume,
                            prenume=prenume,
                            email=email,
                            telefon=telefon,
                            sport=sport
                        )

                        db.session.add(inscriere_noua)
                        db.session.commit()

                        return render_template(
                            'inscriere.html',
                            show_modal=True,
                            nume=nume,
                            prenume=prenume,
                            sport=sport
                        )

    sporturi = Sport.query.all()
    return render_template('inscriere.html', sporturi=sporturi)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)