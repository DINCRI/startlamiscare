import os
from flask import Flask, render_template, request, flash, send_from_directory, redirect, url_for
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from flask_basicauth import BasicAuth
from wtforms import MultipleFileField
import re
from datetime import datetime
from flask_wtf.csrf import CSRFProtect
from sqlalchemy.exc import IntegrityError
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy.exc import IntegrityError

app = Flask(__name__)
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)
csrf = CSRFProtect(app)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app.config["FLASK_ADMIN_SWATCH"] = "cerulean"
app.secret_key = os.environ.get("SECRET_KEY", "super-secret-key")
# 🔐 Securitate cookies
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("COOKIE_SECURE", "false").lower() == "true"

app.config["REMEMBER_COOKIE_HTTPONLY"] = True
app.config["REMEMBER_COOKIE_SECURE"] = os.environ.get("COOKIE_SECURE", "false").lower() == "true"
app.config["REMEMBER_COOKIE_SAMESITE"] = "Lax"

app.config["BASIC_AUTH_USERNAME"] = os.environ.get("BASIC_AUTH_USERNAME", "john")
app.config["BASIC_AUTH_PASSWORD"] = os.environ.get("BASIC_AUTH_PASSWORD", "matrix")

database_url = os.environ.get("DATABASE_URL")

if database_url:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

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

    data_nasterii = db.Column(db.String(10), nullable=False)
    judet = db.Column(db.String(100), nullable=False)
    localitate = db.Column(db.String(100), nullable=False)
    strada = db.Column(db.String(150), nullable=False)
    numar = db.Column(db.String(20), nullable=False)
    bloc = db.Column(db.String(20), nullable=True)
    apartament = db.Column(db.String(20), nullable=True)
    serie_ci = db.Column(db.String(20), nullable=False)
    numar_ci = db.Column(db.String(20), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("email", "sport", name="uq_email_sport"),
    )
    

with app.app_context():
    db.create_all()

    sporturi_default = [
        ("Cros", 700),
        ("Tenis de câmp", 25),
        ("Haltere", 25),
        ("Volei", 25),
        ("Mini fotbal", 25),
        ("Badminton", 25),
        ("Baschet", 25),
        ("Tenis de masă", 25),
        ("Taekwondo", 25),
        ("Box", 25),
        ("Teqball", 25),
        ("Handbal", 25),
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


admin = Admin(
    app,
    name="admin",
    index_view=MyAdminIndexView(),
    url="/panou-secret"
)
admin.add_view(MyModelView(User, db.session))
admin.add_view(MyModelView(Post, db.session))
admin.add_view(MyModelView(Document, db.session))
admin.add_view(MyModelView(Sport, db.session))
admin.add_view(MyModelView(Inscriere, db.session))


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

SPORTURI_INFO = {
    "Cros": {
        "ora": "12:00–13:00",
        "tip": "Competiție",
        "descriere": "Încălzire oficială la 12:00, apoi curse pentru primar, gimnazial și liceal/open."
    },
    "Tenis de câmp": {
        "ora": "13:30",
        "tip": "Atelier + concurs",
        "descriere": "Duble cu răsucirea rachetei și lovituri forehand/backhand controlate."
    },
    "Haltere": {
        "ora": "14:30",
        "tip": "Atelier + concurs",
        "descriere": "Se evaluează execuția corectă la smuls, aruncat și îndreptări."
    },
    "Volei": {
        "ora": "13:00",
        "tip": "Atelier + concurs",
        "descriere": "Concurs de pase de sus și de jos, alternativ."
    },
    "Mini fotbal": {
        "ora": "13:30",
        "tip": "Atelier + concurs",
        "descriere": "Concurs de duble și menținerea mingii în aer prin lovituri alternative."
    },
    "Badminton": {
        "ora": "13:30",
        "tip": "Atelier + concurs",
        "descriere": "Meciuri 1 vs 1 pe teren redus, până la 6 puncte."
    },
    "Baschet": {
        "ora": "13:00",
        "tip": "Atelier + concurs",
        "descriere": "Circuitul aruncărilor: lay-up, aruncări din unghi, libere și distanță."
    },
    
    "Tenis de masă": {
        "ora": "13:30",
        "tip": "Atelier + concurs",
        "descriere": "Meciuri 1 vs 1, eliminatoriu, până la 6 puncte."
    },
    "Taekwondo": {
        "ora": "14:30",
        "tip": "Atelier + concurs",
        "descriere": "Identificarea și executarea cât mai corectă a elementelor tehnice."
    },
    "Box": {
        "ora": "14:00",
        "tip": "Atelier + concurs",
        "descriere": "Lovituri la sac pe 30 secunde și joc tehnic de poziționare."
    },
    "Teqball": {
        "ora": "13:30",
        "tip": "Atelier + concurs",
        "descriere": "Meciuri 1 vs 1, până la 6 puncte, finala în sistem cel mai bun din 3 seturi."
    },
    "Handball": {
        "ora": "13:00",
        "tip": "Atelier + concurs",
        "descriere": "Concurs de aruncări la plasă-țintă."
    },
}

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

        info = SPORTURI_INFO.get(sport.nume, {})

        sporturi_status.append({
            "nume": sport.nume,
            "locuri_maxime": sport.locuri_maxime,
            "inscrisi": inscrisi,
            "procent": procent,
            "ora": info.get("ora", "În program"),
            "tip": info.get("tip", "Sport"),
            "descriere": info.get("descriere", "")
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

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_REGEX = re.compile(r"^(\+4|4|0)7\d{8}$")
DATE_REGEX = re.compile(r"^(0[1-9]|[12][0-9]|3[01])\.(0[1-9]|1[0-2])\.\d{4}$")
SERIE_CI_REGEX = re.compile(r"^[A-Za-z]{2}$")
NUMAR_CI_REGEX = re.compile(r"^\d{6}$")

@app.route("/inscriere/", methods=("GET", "POST"))
@limiter.limit("5 per minute")
def inscriere():
    sporturi = Sport.query.order_by(Sport.nume.asc()).all()

    if request.method == "POST":
        nume = request.form.get("nume", "").strip()
        prenume = request.form.get("prenume", "").strip()
        email = request.form.get("email", "").strip().lower()
        telefon = request.form.get("telefon", "").strip()
        sport = request.form.get("sport", "").strip()

        data_nasterii = request.form.get("data_nasterii", "").strip()
        judet = request.form.get("judet", "").strip()
        localitate = request.form.get("localitate", "").strip()
        strada = request.form.get("strada", "").strip()
        numar = request.form.get("numar", "").strip()
        bloc = request.form.get("bloc", "").strip()
        apartament = request.form.get("apartament", "").strip()
        serie_ci = request.form.get("serie_ci", "").strip().upper()
        numar_ci = request.form.get("numar_ci", "").strip()

        acord_regulament = request.form.get("acord_regulament")
        acord_responsabilitate = request.form.get("acord_responsabilitate")

        errors = []

        if not nume:
            errors.append("Numele este obligatoriu.")

        if not prenume:
            errors.append("Prenumele este obligatoriu.")

        if not email:
            errors.append("Emailul este obligatoriu.")
        elif not EMAIL_REGEX.match(email):
            errors.append("Email invalid.")

        if not telefon:
            errors.append("Telefonul este obligatoriu.")
        elif not PHONE_REGEX.match(telefon):
            errors.append("Telefon invalid (ex: 07xxxxxxxx).")

        if not data_nasterii:
            errors.append("Data nașterii este obligatorie.")
        elif not DATE_REGEX.match(data_nasterii):
            errors.append("Format dată invalid (zz.ll.aaaa).")
        else:
            try:
                datetime.strptime(data_nasterii, "%d.%m.%Y")
            except ValueError:
                errors.append("Data nașterii nu este validă.")

        if not judet:
            errors.append("Județul este obligatoriu.")

        if not localitate:
            errors.append("Localitatea este obligatorie.")

        if not strada:
            errors.append("Strada este obligatorie.")

        if not numar:
            errors.append("Numărul este obligatoriu.")

        if not serie_ci:
            errors.append("Seria CI este obligatorie.")
        elif not SERIE_CI_REGEX.match(serie_ci):
            errors.append("Seria CI trebuie să aibă 2 litere.")

        if not numar_ci:
            errors.append("Numărul CI este obligatoriu.")
        elif not NUMAR_CI_REGEX.match(numar_ci):
            errors.append("Numărul CI trebuie să aibă 6 cifre.")

        if not sport:
            errors.append("Selectează un sport.")

        if not acord_regulament:
            errors.append("Trebuie să accepți regulamentul.")

        if not acord_responsabilitate:
            errors.append("Trebuie să confirmi participarea.")

        if errors:
            for err in errors:
                flash(err, "warning")
            return render_template("inscriere.html", sporturi=sporturi)

        sport_selectat = Sport.query.filter_by(nume=sport).first()

        if not sport_selectat:
            flash("Sport invalid.", "warning")
            return render_template("inscriere.html", sporturi=sporturi)

        inscrisi_curent = Inscriere.query.filter_by(sport=sport).count()

        if inscrisi_curent >= sport_selectat.locuri_maxime:
            flash(f"Nu mai sunt locuri disponibile la {sport}.", "warning")
            return render_template("inscriere.html", sporturi=sporturi)

        existing = Inscriere.query.filter_by(email=email, sport=sport).first()

        if existing:
            flash("Există deja o înscriere cu acest email la sportul selectat.", "warning")
            return render_template("inscriere.html", sporturi=sporturi)

        inscriere_noua = Inscriere(
            nume=nume,
            prenume=prenume,
            email=email,
            telefon=telefon,
            sport=sport,
            data_nasterii=data_nasterii,
            judet=judet,
            localitate=localitate,
            strada=strada,
            numar=numar,
            bloc=bloc if bloc else None,
            apartament=apartament if apartament else None,
            serie_ci=serie_ci,
            numar_ci=numar_ci
        )

        try:
            db.session.add(inscriere_noua)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Există deja o înscriere cu acest email la sportul selectat.", "warning")
            return render_template("inscriere.html", sporturi=sporturi)
        except Exception:
            db.session.rollback()
            flash("A apărut o eroare la salvarea înscrierii. Te rugăm să încerci din nou.", "warning")
            return render_template("inscriere.html", sporturi=sporturi)

        return redirect(url_for(
            "inscriere",
            success=1,
            nume=nume,
            prenume=prenume,
            sport=sport
        ))

    show_modal = request.args.get("success") == "1"
    nume = request.args.get("nume", "")
    prenume = request.args.get("prenume", "")
    sport = request.args.get("sport", "")

    return render_template(
        "inscriere.html",
        sporturi=sporturi,
        show_modal=show_modal,
        nume=nume,
        prenume=prenume,
        sport=sport
    )


@app.route("/lista-prezenta")
@basic_auth.required
def lista_prezenta():
    sport_selectat = request.args.get("sport", "").strip()

    sporturi = Sport.query.order_by(Sport.nume.asc()).all()

    query = Inscriere.query

    if sport_selectat:
        query = query.filter_by(sport=sport_selectat)

    inscrieri = query.order_by(
        Inscriere.sport.asc(),
        Inscriere.nume.asc(),
        Inscriere.prenume.asc()
    ).all()

    return render_template(
        "lista_prezenta.html",
        inscrieri=inscrieri,
        sporturi=sporturi,
        sport_selectat=sport_selectat
    )

@app.route("/dashboard-inscrieri")
@basic_auth.required
def dashboard_inscrieri():
    sport_selectat = request.args.get("sport", "").strip()
    cautare = request.args.get("q", "").strip()

    sporturi = Sport.query.order_by(Sport.nume.asc()).all()

    query = Inscriere.query

    if sport_selectat:
        query = query.filter_by(sport=sport_selectat)

    if cautare:
        termen = f"%{cautare}%"
        query = query.filter(
            db.or_(
                Inscriere.nume.ilike(termen),
                Inscriere.prenume.ilike(termen),
                Inscriere.email.ilike(termen),
                Inscriere.telefon.ilike(termen),
            )
        )

    inscrieri = query.order_by(
        Inscriere.sport.asc(),
        Inscriere.nume.asc(),
        Inscriere.prenume.asc()
    ).all()

    return render_template(
        "dashboard_inscrieri.html",
        inscrieri=inscrieri,
        sporturi=sporturi,
        sport_selectat=sport_selectat,
        cautare=cautare
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)