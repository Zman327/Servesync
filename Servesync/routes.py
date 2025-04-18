from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import os
from sqlalchemy import MetaData, Table
from datetime import datetime


app = Flask(__name__)
app.secret_key = 'your_secret_key'
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'ServeSync.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


with app.app_context():
    metadata = MetaData()
    users_table = Table('user', metadata, autoload_with=db.engine)

    class User(db.Model):
        __table__ = users_table

    award_table = Table('award', metadata, autoload_with=db.engine)

    class Award(db.Model):
        __table__ = award_table

    service_hours_table = Table('service_hours', metadata, autoload_with=db.engine)

    class ServiceHour(db.Model):
        __table__ = service_hours_table
    
    group_table = Table('group', metadata, autoload_with=db.engine)
    
    class Group(db.Model):
        __table__ = group_table


@app.route('/home')
def homepage():
    return render_template('index.html')


@app.route('/account')
def accountpage():
    return render_template('account.html')


@app.route('/log')
def logpage():
    return render_template('log.html')


@app.route('/test')
def testpage():
    return render_template('test.html')


@app.route('/student.dashboard')
def studentpage():
    hour = datetime.now().hour
    if hour < 12:
        greeting = "Good Morning"
    elif hour < 18:
        greeting = "Good Afternoon"
    else:
        greeting = "Good Evening"

    # Get the current logged-in user
    user = User.query.filter_by(school_id=session.get('username')).first()

    # Get user's completed hours (default to 0 if none)
    user_hours = user.hours or 0

    # Find the next award the user hasn't reached yet
    next_award = Award.query.filter(Award.threshold > user_hours).order_by(Award.threshold.asc()).first()

    # Get the next award's name and threshold
    next_award_name = next_award.name if next_award else None
    next_award_threshold = next_award.threshold if next_award else 20
    next_award_colour = next_award.colour if next_award else '#0b5e3e'

    # Fetch top 5 most recent logs for this user
    recent_logs = (
        ServiceHour.query
        .filter_by(user_id=user.school_id)
        .order_by(ServiceHour.date.desc())
        .limit(5)
        .all()
    )

    STATUS_MAP = {
        1: 'Approved',
        2: 'Pending',
        3: 'Rejected'
    }
    for log in recent_logs:
        log.status = STATUS_MAP.get(log.status, 'Unknown')
    
    # Attach group name if group_id exists
    for log in recent_logs:
        log.group_name = Group.query.get(log.group_id).name if log.group_id else None

    # Pass the next_award_threshold and recent_logs to the template
    return render_template(
        'student.html',
        greeting=greeting,
        user=user,
        next_award_name=next_award_name,
        next_award_threshold=next_award_threshold,
        next_award_colour=next_award_colour,
        recent_logs=recent_logs
    )


@app.route('/staff.dashboard')
def staffpage():
    hour = datetime.now().hour
    if hour < 12:
        greeting = "Good Morning"
    elif hour < 18:
        greeting = "Good Afternoon"
    else:
        greeting = "Good Evening"
    return render_template('staff.html', greeting=greeting)


# 404 page to display when a page is not found
# helps re-direct users back to home page
@app.errorhandler(404) # noqa:
def page_not_found(e):
    return render_template('404.html'), 404


@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']  # assuming username is the school_id
    password = request.form['password']

    print(f"Received username: {username} and password: {password}")

    # Check if user exists in the database
    user = User.query.filter_by(school_id=username).first()

    # Print the user object to verify it's being fetched correctly
    print(f"User found: {user}")  # This will print None if the user is not found

    if user:
        print(f"Stored password: {user.password}")
        print(f"Entered password: {password}")
        # Directly compare the plain-text password
        if user.password == password:
            session['username'] = user.school_id
            session['name'] = f"{user.first_name} {user.last_name}"
            # Fetch role name using a raw SQL query (since we're using reflection)
            role_name = db.session.execute(
                db.text("SELECT name FROM user_role WHERE id = :id"), {"id": user.role}
            ).scalar()
            session['role'] = role_name
            print(f"Session set: {session}")
            flash('Login successful!')
            if role_name.lower() == 'staff':
                return redirect(url_for('staffpage'))
            else:
                return redirect(url_for('studentpage'))
        else:
            flash('Incorrect password!')
    else:
        flash('No user found with that username!')

    return redirect(url_for('homepage'))  # Redirect back to the homepage for another attempt

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('homepage'))


if __name__ == "__main__":
    app.run(debug=True)
