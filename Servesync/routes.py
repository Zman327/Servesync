from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
import os
import csv
from sqlalchemy import MetaData, Table
from datetime import datetime


app = Flask(__name__, template_folder='templates')
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
    return render_template('Index.html')


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

    # Find the highest award
    max_award = Award.query.order_by(Award.threshold.desc()).first()
    max_award_name = max_award.name if max_award else "Platinum"
    max_award_colour = max_award.colour if max_award else "#e5c100"
    max_award_threshold = max_award.threshold if max_award else 40

    # Whether the user has achieved the maximum award
    has_achieved_max = user_hours >= max_award_threshold

    from collections import defaultdict

    # Calculate hours per group for the current user
    group_hours = defaultdict(float)
    for log in approved_logs:
        if log.group_id:
            group = Group.query.get(log.group_id)
            if group:
                group_hours[group.name] += log.hours

    # Sort groups by total hours descending and take top 5
    top_groups = sorted(group_hours.items(), key=lambda item: item[1], reverse=True)[:3]

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
        recent_logs=recent_logs,
        top_groups=top_groups,
        max_award_name=max_award_name,
        max_award_colour=max_award_colour,
        max_award_threshold=max_award_threshold,
        has_achieved_max=has_achieved_max
    )


@app.route('/staff.dashboard')
def staffpage():
    hour = datetime.now().hour
    greeting = "Good Morning" if hour < 12 else "Good Afternoon" if hour < 18 else "Good Evening"

    staff_id = session.get('username')
    selected_status = request.args.get('status')  # Get status filter from query string

    # Fetch all service logs for the current staff
    logs = ServiceHour.query.filter_by(staff=staff_id).all()
    # Fetch the groups attached to this staff member
    attached_groups = Group.query.filter_by(staff=staff_id).all()

    pending_count = sum(1 for log in logs if log.status == 2)

    # Calculate total approved hours this year
    current_year = datetime.now().year
    approved_hours_this_year = sum(
        log.hours for log in logs
        if log.status == 1 and datetime.strptime(log.date, "%d-%m-%Y").year == current_year
    )

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
            try:
                log.formatted_log_time = datetime.strptime(log.log_time, "%d-%m-%Y %H:%M:%S").strftime("%b %d, %Y at %I:%M %p")
            except Exception:
                log.formatted_log_time = log.log_time
            user = User.query.get(log.user_id)
            student_name = f"{user.first_name} {user.last_name}" if user else "Unknown"
            filtered_logs.append({
                'id': log.id,
                'user_id': log.user_id,
                'student_name': student_name,
                'description': log.description,
                'hours': log.hours,
                'date': log.date,
                'formatted_date': log.formatted_date,
                'status': log.status,
                'status_label': log.status_label,
                'group': log.group_name,
                'log_time': log.log_time,
                'formatted_log_time': log.formatted_log_time
            })

    # Sort and limit to 5 most recent logs
    filtered_logs.sort(key=lambda log: datetime.strptime(log["date"], "%d-%m-%Y"), reverse=True)
    recent_logs = filtered_logs[:5]

    return render_template(
        'staff.html',
        greeting=greeting,
        recent_submissions=recent_logs,
        pending_count=pending_count,
        attached_groups=attached_groups,
        approved_hours_this_year=approved_hours_this_year
    )


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
    flash("Your hours have been submitted for review!", "success")
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


# Route to handle editing a service log
@app.route('/edit-log', methods=['POST'])
def edit_log():
    log_id = request.form.get('log_id')
    description = request.form.get('description')
    hours = request.form.get('hours')
    date = request.form.get('date')

    # Validate and check if hours is provided, if not set it to 0 or a default value
    if not hours:
        hours = 0.0  # or any default value you prefer

    try:
        hours = float(hours)  # Ensure it's converted to a float
    except ValueError:
        # Handle invalid input for hours
        flash('Invalid value for hours. Please enter a valid number.')
        return redirect(url_for('staffpage'))

    # Handle the date parsing to avoid passing None to strptime
    if date:
        try:
            formatted_date = datetime.strptime(date, "%d-%m-%Y")
        except ValueError:
            flash('Invalid date format. Please enter the date in DD-MM-YYYY format.')
            return redirect(url_for('staffpage'))
    else:
        formatted_date = None  # or a default date if needed

    # Now update the log entry in the database
    log = ServiceHour.query.get(log_id)

    if log:
        log.description = description
        log.hours = hours  # Valid float value
        log.date = formatted_date.strftime("%d-%m-%Y") if formatted_date else None

        # Commit the changes to the database
        db.session.commit()

        flash('Log updated successfully!')
        return redirect(url_for('staffpage'))
    else:
        flash('Log not found')
        return redirect(url_for('staffpage'))


@app.route('/approve-all-pending', methods=['POST'])
def approve_all_pending():
    staff_id = session.get('username')
    if not staff_id:
        return redirect('/login')

    # Find all pending logs for this staff
    pending_logs = ServiceHour.query.filter_by(staff=staff_id, status=2).all()

    for log in pending_logs:
        log.status = 1  # 1 = Approved

    db.session.commit()

    return redirect('/staff.dashboard')


@app.route('/api/groups')
def search_groups():
    query = request.args.get('q', '')
    groups = Group.query.filter(Group.name.ilike(f'%{query}%')).limit(10).all()
    return jsonify([group.name for group in groups])


# Route to get staff for a given group
@app.route('/api/staff-for-group')
def get_staff_for_group():
    group_name = request.args.get('group', '')
    group = Group.query.filter_by(name=group_name).first()
    if group:
        staff = User.query.filter_by(school_id=group.staff).first()
        if staff:
            return jsonify({
                'label': f"{staff.first_name} {staff.last_name} ({staff.school_id})",
                'value': f"{staff.first_name} {staff.last_name} ({staff.school_id})"
            })
    return jsonify(None), 404


@app.route('/api/all-staff')
def get_all_staff():
    staff_members = User.query.filter_by(role='2').all()  # Ensure this matches the correct column and value
    staff_list = [{'value': f"{staff.first_name} {staff.last_name} ({staff.school_id})", 
                   'label': f"{staff.first_name} {staff.last_name} ({staff.school_id})"} for staff in staff_members]
    return jsonify(staff_list)


@app.route('/reports')
def download_reports():
    import io
    staff_id = session.get('username')

    # Fetch staff user
    staff = User.query.filter_by(school_id=staff_id).first()

    # Fetch all approved logs for the current staff
    logs = ServiceHour.query.filter_by(staff=staff_id, status=1).all()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([f"Report for: {staff.first_name} {staff.last_name}"])
    writer.writerow([])  # Empty row for spacing
    writer.writerow(['Student', 'Activity', 'Hours', 'Date', 'Date Submitted', 'Group'])

    for log in logs:
        user = User.query.get(log.user_id)
        group = Group.query.get(log.group_id)
        writer.writerow([
            f"{user.first_name} {user.last_name}" if user else "Unknown",
            log.description,
            log.hours,
            log.date,
            log.log_time,
            group.name if group else "N/A"
        ])

    # Return CSV as downloadable file
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=service_hours_report.csv"
    response.headers["Content-Type"] = "text/csv"
    return response


if __name__ == "__main__":
    app.run(debug=True)
