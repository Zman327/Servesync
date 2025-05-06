from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify, make_response
import base64
from flask_sqlalchemy import SQLAlchemy
from fpdf import FPDF
from openpyxl import Workbook
from sqlalchemy import MetaData, Table
from datetime import datetime
import os
import csv
import io
import pytz


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


@app.route('/submit-hours', methods=['POST'])
def submit_hours():
    user = User.query.filter_by(school_id=session.get('username')).first()
    if not user:
        flash('You must be logged in to submit hours.', 'logpage-error')
        return redirect(url_for('logpage'))

    # Get form data
    date = request.form['date']
    group_name = request.form['group']
    staff_label = request.form['person_in_charge']
    activity = request.form['activity']
    activity = request.form['activity'].strip()
    if not activity or len(activity) > 30:
        flash("Activity name must not be empty or over 30 characters.", "logpage-error")
        return redirect(url_for('logpage'))
    hours = float(request.form['hours'])
    if hours <= 0 or hours > 24:
        flash("Hours must be greater than 0 and no more than 24.", "logpage-error")
        return redirect(url_for('logpage'))
    details = request.form.get('details', '')

    # Get related group and staff IDs
    group = Group.query.filter_by(name=group_name).first()
    staff_school_id = staff_label.split('(')[-1].strip(')')
    staff = User.query.filter_by(school_id=staff_school_id).first()

    if not group or not staff:
        flash("Invalid group or staff member.", "logpage-error")
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
    flash("Your hours have been submitted for review!", "logpage-success")
    return redirect(url_for('logpage'))


@app.route('/test')
def testpage():
    return render_template('test.html')


@app.route('/admin.dashboard')
def adminpage():
    # Get the New Zealand timezone
    nz_timezone = pytz.timezone('Pacific/Auckland')
    # Get the current time in New Zealand
    now = datetime.now(nz_timezone)
    # Set the greeting based on the New Zealand time
    if now.hour < 12:
        greeting = "Good Morning"
    elif now.hour < 18:
        greeting = "Good Afternoon"
    else:
        greeting = "Good Evening"

    # Get all users
    users = User.query.all()

    return render_template('admin.html', greeting=greeting, users=users)


@app.route('/student.dashboard')
def studentpage():
    # Get the New Zealand timezone
    nz_timezone = pytz.timezone('Pacific/Auckland')
    # Get the current time in New Zealand
    now = datetime.now(nz_timezone)
    # Set the greeting based on the New Zealand time
    if now.hour < 12:
        greeting = "Good Morning"
    elif now.hour < 18:
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
    # Get the New Zealand timezone
    nz_timezone = pytz.timezone('Pacific/Auckland')
    # Get the current time in New Zealand
    now = datetime.now(nz_timezone)
    # Set the greeting based on the New Zealand time
    if now.hour < 12:
        greeting = "Good Morning"
    elif now.hour < 18:
        greeting = "Good Afternoon"
    else:
        greeting = "Good Evening"

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
            # Build picture URL from BLOB or fallback to default
            if user and user.picture:
                encoded_picture = base64.b64encode(user.picture).decode('utf-8')
                picture_url = f"data:image/jpeg;base64,{encoded_picture}"
            else:
                picture_url = url_for('static', filename='default-profile.png')

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
                'formatted_log_time': log.formatted_log_time,
                'picture_url': picture_url
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


@app.route('/activity-history')
def activity_history():
    return render_template('activity.html')


# Route: /activity-history/<int:user_id>
@app.route('/activity-history/<int:user_id>')
def activity_history_user(user_id):
    user = User.query.get(user_id)
    if not user:
        flash("User not found.")
        return redirect(url_for('homepage'))

    logs = ServiceHour.query.filter_by(user_id=user.school_id).order_by(ServiceHour.date.desc()).all()

    for log in logs:
        log.group_name = Group.query.get(log.group_id).name if log.group_id else "N/A"
        try:
            log.formatted_date = datetime.strptime(log.date, "%d-%m-%Y").strftime("%b %d, %Y")
        except Exception:
            log.formatted_date = log.date
        try:
            log.formatted_log_time = datetime.strptime(log.log_time, "%d-%m-%Y %H:%M:%S").strftime("%b %d, %Y at %I:%M %p")
        except Exception:
            log.formatted_log_time = log.log_time
        log.status_label = {
            1: 'Approved',
            2: 'Pending',
            3: 'Rejected'
        }.get(log.status, 'Unknown')

    return render_template('activity.html', logs=logs, student=user)


@app.route('/submissions')
def submissions():
    staff_id = session.get('username')
    selected_status = request.args.get('status')  # Get status filter from query string

    # Get groups this staff manages
    attached_groups = Group.query.filter_by(staff=staff_id).all()
    group_ids = [group.id for group in attached_groups]

    # Get all logs from those groups only
    logs = ServiceHour.query.filter(ServiceHour.group_id.in_(group_ids)).all()

    STATUS_MAP = {
        1: 'Approved',
        2: 'Pending',
        3: 'Rejected'
    }

    submission_data = []
    accepted_count = 0
    pending_count = 0
    rejected_count = 0

    for log in logs:
        status_label = STATUS_MAP.get(log.status, 'Unknown')
        if not selected_status or status_label == selected_status:
            user = User.query.get(log.user_id)
            if user and user.picture:
                encoded_picture = base64.b64encode(user.picture).decode('utf-8')
                picture_url = f"data:image/jpeg;base64,{encoded_picture}"
            else:
                picture_url = url_for('static', filename='default-profile.png')
            student_name = f"{user.first_name} {user.last_name}" if user else "Unknown"
            group = Group.query.get(log.group_id)
            group_name = group.name if group else "N/A"
            try:
                formatted_date = datetime.strptime(log.date, "%d-%m-%Y").strftime("%b %d, %Y")
            except Exception:
                formatted_date = log.date
            try:
                formatted_log_time = (
                    datetime.strptime(log.log_time, "%d-%m-%Y %H:%M:%S").strftime("%b %d, %Y at %I:%M %p")
                    if log.log_time else "N/A"
                )
            except Exception:
                formatted_log_time = log.log_time if log.log_time else "N/A"

            submission_data.append({
                'id': log.id,
                'student_name': student_name,
                'user_id': log.user_id,
                'description': log.description,
                'hours': log.hours,
                'date': formatted_date,
                'formatted_date': formatted_date,
                'status': log.status,
                'status_label': status_label,
                'group': group_name,
                'log_time': log.log_time,
                'formatted_log_time': formatted_log_time,
                'picture_url': picture_url  # 👈 add this line
})

            # Count the status categories
            if log.status == 1:
                accepted_count += 1
            elif log.status == 2:
                pending_count += 1
            elif log.status == 3:
                rejected_count += 1

    # Sort by newest first using original log.date format
    submission_data.sort(key=lambda x: datetime.strptime(x["date"], "%b %d, %Y"), reverse=True)

    return render_template('submissions.html', submissions=submission_data, 
                           accepted_count=accepted_count, 
                           pending_count=pending_count, 
                           rejected_count=rejected_count)


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
            elif role_name.lower() == 'admin':
                return redirect(url_for('adminpage'))
            else:
                return redirect(url_for('studentpage'))
        else:
            flash('Incorrect password!')
    else:
        flash('No user found with that username!')

    return redirect(url_for('homepage'))  # Redirect back to the homepage for another attempt


@app.route('/update-log-field', methods=['POST'])
def update_log_field():
    data = request.get_json()
    log_id = data.get('log_id')
    description = data.get('description')
    hours = data.get('hours')
    date = data.get('date')

    log = ServiceHour.query.get(log_id)
    if not log:
        return jsonify({'success': False, 'error': 'Log not found'})

    log.description = description
    try:
        log.hours = float(hours)
        datetime.strptime(date, "%d-%m-%Y")  # Validate format
        log.date = date
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

    db.session.commit()
    return jsonify({'success': True})


# Route to accept a service log
@app.route('/approve-log', methods=['POST'])
def approve_log():
    log_id = request.form.get('log_id')
    if log_id:
        service_log = ServiceHour.query.get(log_id)
        if service_log:
            service_log.status = 1  # Set status to Approved
            db.session.commit()

    # Redirect back to the referrer URL or staff page if referrer is not available
    return redirect(request.referrer or url_for('staffpage'))


# Route to reject a service log
@app.route('/reject-log', methods=['POST'])
def reject_log():
    log_id = request.form.get('log_id')
    if log_id:
        service_log = ServiceHour.query.get(log_id)
        if service_log:
            service_log.status = 3  # Set status to Rejected
            db.session.commit()

    # Redirect back to the referrer URL or staff page if referrer is not available
    return redirect(request.referrer or url_for('staffpage'))


@app.route('/approve-all-pending', methods=['POST'])
def approve_all_pending():
    staff_id = session.get('username')
    if not staff_id:
        return redirect('/login')

    # Approve all pending logs for this staff
    pending_logs = ServiceHour.query.filter_by(staff=staff_id, status=2).all()
    for log in pending_logs:
        log.status = 1  # Approved
    db.session.commit()

    # Use redirect target from form if provided
    redirect_to = request.form.get('redirect_to', '/staff.dashboard')
    return redirect(redirect_to)


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
    return render_template('reports.html')


@app.route('/download/csv')
def download_csv():
    staff_id = session.get('username')
    staff = User.query.filter_by(school_id=staff_id).first()
    logs = ServiceHour.query.filter_by(staff=staff_id, status=1).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([f"Report for: {staff.first_name} {staff.last_name}"])
    writer.writerow([])
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

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=service_hours_report.csv"
    response.headers["Content-Type"] = "text/csv"
    return response


@app.route('/download/excel')
def download_excel():
    staff_id = session.get('username')
    staff = User.query.filter_by(school_id=staff_id).first()
    logs = ServiceHour.query.filter_by(staff=staff_id, status=1).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Service Hours"
    ws.append([f"Report for: {staff.first_name} {staff.last_name}"])
    ws.append([])
    ws.append(['Student', 'Activity', 'Hours', 'Date', 'Date Submitted', 'Group'])

    for log in logs:
        user = User.query.get(log.user_id)
        group = Group.query.get(log.group_id)
        ws.append([
            f"{user.first_name} {user.last_name}" if user else "Unknown",
            log.description,
            log.hours,
            log.date,
            log.log_time,
            group.name if group else "N/A"
        ])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=service_hours_report.xlsx"
    response.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return response


@app.route('/download/pdf')
def download_pdf():
    staff_id = session.get('username')
    staff = User.query.filter_by(school_id=staff_id).first()
    logs = ServiceHour.query.filter_by(staff=staff_id, status=1).all()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Report for: {staff.first_name} {staff.last_name}", ln=True, align='C')
    pdf.ln(10)

    pdf.set_font("Arial", size=10)
    for log in logs:
        user = User.query.get(log.user_id)
        group = Group.query.get(log.group_id)
        pdf.multi_cell(0, 10, txt=f"Student: {user.first_name} {user.last_name if user else 'Unknown'}\n"
                                   f"Activity: {log.description}\n"
                                   f"Hours: {log.hours}\n"
                                   f"Date: {log.date}\n"
                                   f"Submitted: {log.log_time}\n"
                                   f"Group: {group.name if group else 'N/A'}\n", border=0)
        pdf.ln(2)

    response = make_response(pdf.output(dest='S').encode('latin-1'))
    response.headers["Content-Disposition"] = "attachment; filename=service_hours_report.pdf"
    response.headers["Content-Type"] = "application/pdf"
    return response


if __name__ == "__main__":
    app.run(debug=True)