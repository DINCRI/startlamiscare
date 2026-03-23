import os
from flask import Flask, render_template, request, abort
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

basic_auth = BasicAuth(app)
db = SQLAlchemy(app)

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

with app.app_context():
    db.create_all()

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
            model.uploads = ','.join(filenames)

    def is_accessible(self):
        return basic_auth.authenticate()

admin = Admin(app, name='admin', index_view=MyAdminIndexView())
admin.add_view(MyModelView(User, db.session))
admin.add_view(MyModelView(Post, db.session))
admin.add_view(MyModelView(Document, db.session))

@app.route("/")
def index():
    return render_template("index.html", posts=Post.query.all())

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

if __name__ == "__main__":
    app.run()