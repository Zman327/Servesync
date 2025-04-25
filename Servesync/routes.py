from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify
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

    user_role_table = Table('user_role', metadata, autoload_with=db.engine)

    class UserRole(db.Model):
        __table__ = user_role_table


@app.route('/home')
def homepage():
    return render_template('index.html')


@app.route('/account')
def accountpage():
    return render_template('account.html')


@app.route('/log')
def logpage():
    # Get all users who have the 'staff' role (role = 2)
    staff_members = User.query.filter_by(role=2).all()

    # Get all groups from the group table
    groups = Group.query.all()

    return render_template('log.html', staff_members=staff_members, groups=groups)


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

    # Get user's approved hours (sum of approved logs)
    approved_logs = ServiceHour.query.filter_by(user_id=user.school_id, status=1).all()
    user_hours = sum(log.hours for log in approved_logs) if approved_logs else 0

    # Find the next award the user hasn't reached yet
    next_award = Award.query.filter(Award.threshold > user_hours).order_by(Award.threshold.asc()).first()

    # Get the next award's name and threshold
    next_award_name = next_award.name if next_award else None
    next_award_threshold = next_award.threshold if next_award else 20
    next_award_colour = next_award.colour if next_award else '#0b5e3e'

    # Fetch top 5 most recent logs for this user
    recent_logs = sorted(
        ServiceHour.query
            .filter_by(user_id=user.school_id)
            .all(),
        key=lambda log: datetime.strptime(log.date, "%d-%m-%Y"),
        reverse=True
    )[:5]

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

    for log in recent_logs:
        try:
            log.formatted_date = datetime.strptime(log.date, "%d-%m-%Y").strftime("%b %d").upper()
        except Exception:
            log.formatted_date = str(log.date)

    # Pass the next_award_threshold and recent_logs to the template
    return render_template(
        'student.html',
        greeting=greeting,
        user=user,
        user_hours=user_hours,
        next_award_name=next_award_name,
        next_award_threshold=next_award_threshold,
        next_award_colour=next_award_colour,
        recent_logs=recent_logs
    )


@app.route('/staff.dashboard')
def staffpage():
    hour = datetime.now().hour
    greeting = "Good Morning" if hour < 12 else "Good Afternoon" if hour < 18 else "Good Evening"

    staff_id = session.get('username')
    selected_status = request.args.get('status')  # Get status filter from query string

    # Fetch all service logs for the current staff
    logs = ServiceHour.query.filter_by(staff=staff_id).all()

    STATUS_MAP = {
        1: 'Approved',
        2: 'Pending',
        3: 'Rejected'
    }

    filtered_logs = []

    for log in logs:
        log.status_label = STATUS_MAP.get(log.status, 'Unknown')
        if not selected_status or log.status_label == selected_status:
            log.group_name = Group.query.get(log.group_id).name if log.group_id else "N/A"
            try:
                log.formatted_date = datetime.strptime(log.date, "%d-%m-%Y").strftime("%b %d, %Y")
            except Exception:
                log.formatted_date = log.date
            filtered_logs.append({
                'id': log.id,
                'user_id': log.user_id,
                'description': log.description,
                'hours': log.hours,
                'date': log.date,
                'formatted_date': log.formatted_date,
                'status': log.status,
                'status_label': log.status_label,
                'group': log.group_name,
            })

    # Sort and limit to 5 most recent logs
    filtered_logs.sort(key=lambda log: datetime.strptime(log["date"], "%d-%m-%Y"), reverse=True)
    recent_logs = filtered_logs[:5]

    return render_template('staff.html', greeting=greeting, recent_submissions=recent_logs)


# 404 page to display when a page is not found
# helps re-direct users back to home page
@app.errorhandler(404) # noqa:
def page_not_found(e):
    return render_template('404.html'), 404


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
        # Directly compare the plain-text password
        if user.password == password:
            session['username'] = user.school_id
            session['name'] = f"{user.first_name} {user.last_name}"
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


@app.route('/submit-hours', methods=['POST'])
def submit_hours():
    user = User.query.filter_by(school_id=session.get('username')).first()
    if not user:
        flash('You must be logged in to submit hours.')
        return redirect(url_for('logpage'))

    # Get form data
    date = request.form['date']
    group_name = request.form['group']
    staff_label = request.form['person_in_charge']
    activity = request.form['activity']
    hours = float(request.form['hours'])
    details = request.form.get('details', '')

    # Get related group and staff IDs
    group = Group.query.filter_by(name=group_name).first()
    staff_school_id = staff_label.split('(')[-1].strip(')')
    staff = User.query.filter_by(school_id=staff_school_id).first()

    if not group or not staff:
        flash("Invalid group or staff member.")
        return redirect(url_for('logpage'))

    # Create a new service hour record
    new_log = ServiceHour(
        user_id=user.school_id,
        group_id=group.id,
        hours=hours,
        date=datetime.strptime(date, "%Y-%m-%d").strftime("%d-%m-%Y"),
        description=details or activity,
        time=hours,
        status=2,  # 2 = Pending
        log_time=datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
        staff=staff.school_id
    )

    db.session.add(new_log)
    db.session.commit()
    session['success'] = True
    return redirect(url_for('logpage'))


# Route to accept a service log
@app.route('/approve-log', methods=['POST'])
def approve_log():
    log_id = request.form.get('log_id')
    if log_id:
        service_log = ServiceHour.query.get(log_id)
        if service_log:
            service_log.status = 1  # Set status to Approved
            db.session.commit()
    return redirect(url_for('staffpage'))

# Route to reject a service log
@app.route('/reject-log', methods=['POST'])
def reject_log():
    log_id = request.form.get('log_id')
    if log_id:
        service_log = ServiceHour.query.get(log_id)
        if service_log:
            service_log.status = 3  # Set status to Rejected
            db.session.commit()
    return redirect(url_for('staffpage'))


if __name__ == "__main__":
    app.run(debug=True)
