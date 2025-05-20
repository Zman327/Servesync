from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify, make_response
import base64
from flask_sqlalchemy import SQLAlchemy
from fpdf import FPDF
from openpyxl import Workbook
from sqlalchemy import MetaData, Table, func
from datetime import datetime, timedelta
from collections import defaultdict
import os
import csv
import io
import pytz
import json
from werkzeug.security import generate_password_hash, check_password_hash
from flask_dance.contrib.google import make_google_blueprint, google
import pandas as pd
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from Servesync.student import student_bp
from Servesync.staff import staff_bp
from Servesync.admin import admin_bp
from models import init_models, User, Award, ServiceHour, Group, UserRole, db


app = Flask(__name__, template_folder='templates')
app.secret_key = 'your_secret_key'


# Dictionary to track last time a staff member was notified
last_notified = {}

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # Allow HTTP for local dev

google_bp = make_google_blueprint(
    client_id="26915404481-5bcada6j7otusedjet7p5g93pn08rp69.apps.googleusercontent.com",
    client_secret="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",
    redirect_url="http://127.0.0.1:5000/google_login/callback",  # when live use https://zeyad327.pythonanywhere.com/google_login/callback
    scope=[
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile"
    ]
)

app.register_blueprint(google_bp, url_prefix="/google_login")
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'ServeSync.db')
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


@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    print(f"Received username: {username} and password: {password}")

    # Check if user exists in the database
    user = User.query.filter_by(school_id=username).first()

    # Print the user object to verify it's being fetched correctly
    print(f"User found: {user}")  # This will print None if the user is not found

    if user:
        print(f"Stored password: {user.password}")
        print(f"Entered password: {password}")

        # If password is hashed, check with check_password_hash
        # If it's plain text, check directly
        if user.password.startswith('pbkdf2') and check_password_hash(user.password, password):
            session['username'] = user.school_id
            session['name'] = f"{user.first_name} {user.last_name}"
            role_name = db.session.execute(
                db.text("SELECT name FROM user_role WHERE id = :id"), {"id": user.role}
            ).scalar()
            session['role'] = role_name
            print(f"Session set: {session}")
            if role_name.lower() == 'staff':
                return redirect(url_for('staff.staffpage'))
            elif role_name.lower() == 'admin':
                return redirect(url_for('admin.adminpage'))
            else:
                return redirect(url_for('student.studentpage'))
        # If password is not hashed, compare directly
        elif user.password == password:
            session['username'] = user.school_id
            session['name'] = f"{user.first_name} {user.last_name}"
            role_name = db.session.execute(
                db.text("SELECT name FROM user_role WHERE id = :id"), {"id": user.role}
            ).scalar()
            session['role'] = role_name
            print(f"Session set: {session}")
            if role_name.lower() == 'staff':
                return redirect(url_for('staff.staffpage'))
            elif role_name.lower() == 'admin':
                return redirect(url_for('admin.adminpage'))
            else:
                return redirect(url_for('student.studentpage'))
        else:
            flash('Incorrect password!')
    else:
        flash('No user found with that username!')

    return redirect(url_for('homepage'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('homepage'))


@app.route("/some_route")
def some_route():
    user = User.query.filter_by(school_id=session.get('username')).first()
    if user and user.picture:
        image_data = base64.b64encode(user.picture).decode('utf-8')
        profile_image = f"data:image/jpeg;base64,{image_data}"
    else:
        profile_image = url_for('static', filename='Images/Profile/deafult.jpg')

    return render_template("some_template.html", profile_image=profile_image)


@app.route("/google_login/callback")
def google_login_callback():
    if not google.authorized:
        return redirect(url_for("google.login"))

    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        flash("Failed to fetch user info from Google.")
        return redirect(url_for("homepage"))

    user_info = resp.json()
    email = user_info["email"]
    name = user_info["name"]

    user = User.query.filter_by(email=email).first()

    if user:
        session['username'] = user.school_id
        session['name'] = f"{user.first_name} {user.last_name}"
        role_name = db.session.execute(
            db.text("SELECT name FROM user_role WHERE id = :id"), {"id": user.role}
        ).scalar()
        session['role'] = role_name
        if role_name.lower() == 'staff':
            return redirect(url_for('staff.staffpage'))
        elif role_name.lower() == 'admin':
            return redirect(url_for('admin.adminpage'))
        else:
            return redirect(url_for('student.studentpage'))
    else:
        flash("No account found for this Google email.")
        return redirect(url_for("homepage"))


@app.route('/account')
def accountpage():
    return render_template('account.html')


@app.route('/test')
def testpage():
    return render_template('test.html')


@app.route('/about')
def aboutpage():
    return render_template('about.html')


# 404 page to display when a page is not found
# helps re-direct users back to home page
@app.errorhandler(404) # noqa:
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500) # noqa:
def internal_server_error(e):
    return render_template('500.html'), 500
