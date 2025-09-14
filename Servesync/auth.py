# Import function to check and notify staff/admin of pending submissions
from .staff import check_and_notify_pending_submissions
# Flask imports for web routing, session management, and user messaging
from flask import Blueprint, request, session, redirect, url_for, flash # noqa
# For securely checking hashed passwords
from werkzeug.security import check_password_hash
# For Google OAuth authentication
from flask_dance.contrib.google import google
# Import User model for database queries
from models import User
# For case-insensitive filtering in SQL queries
from sqlalchemy import func


# Create a Flask Blueprint for authentication-related routes
auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
def login():
    # Get username and password from submitted login form
    username = request.form['username']
    password = request.form['password']
    # Query the database for a user with matching (case-insensitive) school_id
    user = User.query.filter(func.lower(User.school_id) == username.lower()).first() # noqa

    if user:
        # Check if password is hashed (pbkdf2) and verify it securely
        if user.password.startswith('pbkdf2') and check_password_hash(user.password, password): # noqa
            # Store user information in session for authentication
            session['username'] = user.school_id
            session['name'] = f"{user.first_name} {user.last_name}"
            session['role'] = user.user_role.name
            # Notify staff/admin of pending submissions upon login
            if user.user_role.name in ['Staff', 'Admin']:
                check_and_notify_pending_submissions()
            # Redirect to the user's dashboard page based on their role
            return redirect(url_for(f"{user.user_role.name.lower()}.{user.user_role.name.lower()}page")) # noqa
        # For legacy support: check if password is stored in plaintext
        elif user.password == password:
            session['username'] = user.school_id
            session['name'] = f"{user.first_name} {user.last_name}"
            session['role'] = user.user_role.name
            if user.user_role.name in ['Staff', 'Admin']:
                check_and_notify_pending_submissions()
            return redirect(url_for(f"{user.user_role.name.lower()}.{user.user_role.name.lower()}page")) # noqa
        else:
            # Password did not match
            flash('Incorrect password!', 'login')
    else:
        # No user found with that username
        flash('No user found with that username!', 'login')

    # Redirect back to homepage (login failed)
    return redirect(url_for('homepage'))


@auth_bp.route('/logout')
def logout():
    # Clear all session data to log user out
    session.clear()
    # Redirect to homepage after logout
    return redirect(url_for('homepage'))


@auth_bp.route("/google_login/callback")
def google_login_callback():
    # Ensure the user is authorized via Google OAuth
    if not google.authorized:
        # If not authorized, redirect to Google login
        return redirect(url_for("google.login"))

    # Fetch user information from Google
    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        # If the request failed, notify user and redirect home
        flash("Failed to fetch user info from Google.", 'login')
        return redirect(url_for("homepage"))

    # Parse user info from Google response
    user_info = resp.json()
    email = user_info["email"]

    # Attempt to find a user in the database with the Google account's email
    user = User.query.filter_by(email=email).first()
    if user:
        # Store user info in session for authentication
        session['username'] = user.school_id
        session['name'] = f"{user.first_name} {user.last_name}"
        session['role'] = user.user_role.name
        # Notify staff/admin of pending submissions upon login
        if user.user_role.name in ['Staff', 'Admin']:
            check_and_notify_pending_submissions()
        # Redirect to the user's dashboard page based on their role
        return redirect(url_for(f"{user.user_role.name.lower()}.{user.user_role.name.lower()}page")) # noqa
    else:
        # No user account associated with this Google account
        flash("No account found for this Google account.", 'login')
        return redirect(url_for("homepage"))
