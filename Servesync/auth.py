from flask import Blueprint, request, session, redirect, url_for, flash, render_template # noqa
from werkzeug.security import check_password_hash
from flask_dance.contrib.google import google
from models import User, db

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    user = User.query.filter_by(school_id=username).first()

    if user:
        if user.password.startswith('pbkdf2') and check_password_hash(user.password, password): # noqa
            session['username'] = user.school_id
            session['name'] = f"{user.first_name} {user.last_name}"
            role_name = db.session.execute(
                db.text("SELECT name FROM user_role WHERE id = :id"), {"id": user.role} # noqa
            ).scalar()
            session['role'] = role_name
            return redirect(url_for(f"{role_name.lower()}.{role_name.lower()}page")) # noqa
        elif user.password == password:
            session['username'] = user.school_id
            session['name'] = f"{user.first_name} {user.last_name}"
            role_name = db.session.execute(
                db.text("SELECT name FROM user_role WHERE id = :id"), {"id": user.role} # noqa
            ).scalar()
            session['role'] = role_name
            return redirect(url_for(f"{role_name.lower()}.{role_name.lower()}page")) # noqa
        else:
            flash('Incorrect password!')
    else:
        flash('No user found with that username!')

    return redirect(url_for('homepage'))


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('homepage'))


@auth_bp.route("/google_login/callback")
def google_login_callback():
    if not google.authorized:
        return redirect(url_for("google.login"))

    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        flash("Failed to fetch user info from Google.")
        return redirect(url_for("homepage"))

    user_info = resp.json()
    email = user_info["email"]

    user = User.query.filter_by(email=email).first()
    if user:
        session['username'] = user.school_id
        session['name'] = f"{user.first_name} {user.last_name}"
        role_name = db.session.execute(
            db.text("SELECT name FROM user_role WHERE id = :id"), {"id": user.role} # noqa
        ).scalar()
        session['role'] = role_name
        return redirect(url_for(f"{role_name.lower()}.{role_name.lower()}page")) # noqa
    else:
        flash("No account found for this Google email.")
        return redirect(url_for("homepage"))
