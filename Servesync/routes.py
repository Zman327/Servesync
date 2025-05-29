from flask import Flask, render_template, session, url_for
import base64
import os
from flask_dance.contrib.google import make_google_blueprint
from Servesync.student import student_bp
from Servesync.staff import staff_bp
from Servesync.admin import admin_bp
from Servesync.auth import auth_bp
from models import init_models, User


app = Flask(__name__, template_folder='templates')
app.secret_key = 'your_secret_key'


# Dictionary to track last time a staff member was notified
last_notified = {}

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # Allow HTTP for local dev

google_bp = make_google_blueprint(
    client_id="26915404481-5bcada6j7otusedjet7p5g93pn08rp69.apps.googleusercontent.com", # noqa
    client_secret="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",
    redirect_url="http://127.0.0.1:5000/google_login/callback",  # when live use https://zeyad327.pythonanywhere.com/google_login/callback # noqa
    scope=[
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile"
    ]
)

app.register_blueprint(google_bp, url_prefix="/google_login")
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'ServeSync.db') # noqa
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


init_models(app)


@app.context_processor
def inject_profile_image():
    def get_profile_image():
        if 'username' in session:
            user = User.query.filter_by(school_id=session['username']).first()
            if user and user.picture:
                encoded = base64.b64encode(user.picture).decode('utf-8')
                return f"data:image/jpeg;base64,{encoded}"
        return url_for('static', filename='Images/Profile/deafult.jpg')

    return dict(profile_image=get_profile_image())


@app.route('/home')
def homepage():
    return render_template('Index.html')


@app.route('/')
def homepage1():
    return render_template('Index.html')


app.register_blueprint(student_bp)
app.register_blueprint(staff_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(auth_bp)


@app.route("/some_route")
def some_route():
    user = User.query.filter_by(school_id=session.get('username')).first()
    if user and user.picture:
        image_data = base64.b64encode(user.picture).decode('utf-8')
        profile_image = f"data:image/jpeg;base64,{image_data}"
    else:
        profile_image = url_for('static', filename='Images/Profile/deafult.jpg') # noqa

    return render_template("some_template.html", profile_image=profile_image)


@app.route('/account')
def accountpage():
    return render_template('account.html')


@app.route('/test')
def testpage():
    return render_template('test.html')


@app.route('/about')
def aboutpage():
    return render_template('layout/about.html')


@app.route('/privacy_policy')
def privacypage():
    return render_template('layout/privacy_policy.html')


@app.route('/terms')
def termspage():
    return render_template('layout/terms.html')


# 404 page to display when a page is not found
# helps re-direct users back to home page
@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('errors/500.html'), 500


@app.errorhandler(403)
def forbidden(e):
    return render_template('errors/403.html'), 403


@app.errorhandler(405)
def method_not_allowed(e):
    return render_template('errors/405.html'), 405
