import os
from flask import Flask, render_template, request, flash, send_from_directory
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from flask_basicauth import BasicAuth
from wtforms import MultipleFileField

app = Flask(__name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app.config["FLASK_ADMIN_SWATCH"] = "cerulean"
app.secret_key = os.environ.get("SECRET_KEY", "super-secret-key")

app.config["BASIC_AUTH_USERNAME"] = os.environ.get("BASIC_AUTH_USERNAME", "john")
app.config["BASIC_AUTH_PASSWORD"] = os.environ.get("BASIC_AUTH_PASSWORD", "matrix")

database_url = os.environ.get("DATABASE_URL")

if database_url:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
else:
    data_dir = os.path.join(BASE_DIR, "data")
    os.makedirs(data_dir, exist_ok=True)
    db_path = os.path.join(data_dir, "project.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

upload_folder = os.path.join(BASE_DIR, "uploads")
os.makedirs(upload_folder, exist_ok=True)
app.config["UPLOAD_FOLDER"] = upload_folder

basic_auth = BasicAuth(app)
db = SQLAlchemy(app)


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), nullable=False)


class Post(db.Model):
    __tablename__ = "posts"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    uploads = db.Column(db.Text, nullable=True)


class Document(db.Model):
    __tablename__ = "documents"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    uploads = db.Column(db.Text, nullable=True)


class Sport(db.Model):
    __tablename__ = "sporturi"
    id = db.Column(db.Integer, primary_key=True)
    nume = db.Column(db.String(100), unique=True, nullable=False)
    locuri_maxime = db.Column(db.Integer, nullable=False, default=100)


class Inscriere(db.Model):
    __tablename__ = "inscrieri"
    id = db.Column(db.Integer, primary_key=True)
    nume = db.Column(db.String(100), nullable=False)
    prenume = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    telefon = db.Column(db.String(20), nullable=False)
    sport = db.Column(db.String(100), nullable=False)


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


class MyAdminIndexView(AdminIndexView):
    @expose("/")
    @basic_auth.required
    def index(self):
        return super().index()


class MyModelView(ModelView):
    form_extra_fields = {
        "uploads": MultipleFileField("Files")
    }

    def on_model_change(self, form, model, is_created):
        if "uploads" in request.files:
            files = request.files.getlist("uploads")
            filenames = []

            for file in files:
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                    filenames.append(filename)

            if filenames:
                model.uploads = ",".join(filenames)

    def is_accessible(self):
        return basic_auth.authenticate()


admin = Admin(app, name="admin", index_view=MyAdminIndexView())
admin.add_view(MyModelView(User, db.session))
admin.add_view(MyModelView(Post, db.session))
admin.add_view(MyModelView(Document, db.session))
admin.add_view(MyModelView(Sport, db.session))
admin.add_view(MyModelView(Inscriere, db.session))


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


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

    return render_template("index.html", posts=posts, sporturi_status=sporturi_status)


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


@app.route("/inscriere/", methods=("GET", "POST"))
def inscriere():
    if request.method == "POST":
        nume = request.form["nume"].strip()
        prenume = request.form["prenume"].strip()
        email = request.form["email"].strip()
        telefon = request.form["telefon"].strip()
        sport = request.form["sport"].strip()

        if not nume:
            flash("Numele este obligatoriu!", "warning")
        elif not prenume:
            flash("Prenumele este obligatoriu!", "warning")
        elif not email:
            flash("Emailul este obligatoriu!", "warning")
        elif not telefon:
            flash("Telefonul este obligatoriu!", "warning")
        elif not sport:
            flash("Selectează un sport!", "warning")
        else:
            sport_selectat = Sport.query.filter_by(nume=sport).first()

            if not sport_selectat:
                flash("Sport invalid!", "warning")
            else:
                inscrisi_curent = Inscriere.query.filter_by(sport=sport).count()

                if inscrisi_curent >= sport_selectat.locuri_maxime:
                    flash(f"Nu mai sunt locuri disponibile la {sport}!", "warning")
                else:
                    existing = Inscriere.query.filter_by(email=email, sport=sport).first()

                    if existing:
                        flash("Există deja o înscriere cu acest email la sportul selectat!", "warning")
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
                            "inscriere.html",
                            show_modal=True,
                            nume=nume,
                            prenume=prenume,
                            sport=sport
                        )

    sporturi = Sport.query.all()
    return render_template("inscriere.html", sporturi=sporturi)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)