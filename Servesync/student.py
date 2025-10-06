from flask import Blueprint
from flask import render_template, request, redirect, session, url_for, flash, jsonify, abort  # noqa
from functools import wraps
from models import db, User, Group, ServiceHour, Award
from sqlalchemy import case
from datetime import datetime
import pytz
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


student_bp = Blueprint('student', __name__)


@student_bp.route('/student.dashboard')
def studentpage():
    if session.get('role') != 'Student':
        abort(403)
    # Get the New Zealand timezone to ensure all time-based greetings and logs
    # are in local NZ time
    nz_timezone = pytz.timezone('Pacific/Auckland')
    # Get the current time in New Zealand to customize greeting based on time
    # of day
    now = datetime.now(nz_timezone)
    # Set the greeting based on the New Zealand time to provide a personalized
    # user experience
    if now.hour < 12:
        greeting = "Good Morning"
    elif now.hour < 18:
        greeting = "Good Afternoon"
    else:
        greeting = "Good Evening"

    # Get the current logged-in user from the database using session username
    user = User.query.filter_by(school_id=session.get('username')).first()

    # Retrieve all approved service hour logs for the user to calculate total
    # hours
    approved_logs = ServiceHour.query.filter_by(user_id=user.school_id, status=1).all() # noqa
    user_hours = sum(log.hours for log in approved_logs) if approved_logs else 0 # noqa
    # Update the user's total hours to keep the database in sync with approved
    # logs
    # --- Milestone Email Logic ---
    previous_hours = getattr(user, "hours", 0)
    user.hours = user_hours
    db.session.commit()

    milestones = [
        {"hours": 2, "name": "Service for Graduation", "colour": "#084231"},
        {"hours": 20, "name": "Silver", "colour": "#C0C0C0"},
        {"hours": 30, "name": "Gold", "colour": "#F4B942"},
        {"hours": 40, "name": "Platinum", "colour": "#164580"}
    ]

    for milestone in milestones:
        if previous_hours < milestone["hours"] <= user_hours:
            send_award_email(user, milestone)
            break

    # Find the highest award in the system to display max award info and check
    # if user has achieved it
    max_award = Award.query.order_by(Award.threshold.desc()).first()
    max_award_name = max_award.name if max_award else "Platinum"
    max_award_colour = max_award.colour if max_award else "#e5c100"
    max_award_threshold = max_award.threshold if max_award else 40

    # Determine if the user has reached or exceeded the highest award threshold
    has_achieved_max = user_hours >= max_award_threshold

    from collections import defaultdict

    # Calculate total approved hours per group for the current user to show
    # top contributing groups
    group_hours = defaultdict(float)
    for log in approved_logs:
        if log.group_id:
            group = Group.query.get(log.group_id)
            if group:
                group_hours[group.name] += log.hours

    # Sort groups by total hours descending and take top 3 to highlight user's
    # main volunteer groups
    top_groups = sorted(group_hours.items(), key=lambda item: item[1], reverse=True)[:3] # noqa

    # Find the next award the user hasn't reached yet to motivate further
    # participation
    next_award = Award.query.filter(Award.threshold > user_hours).order_by(Award.threshold.asc()).first() # noqa

    # Get the next award's name, threshold, and colour for display purposes
    next_award_name = next_award.name if next_award else None
    next_award_threshold = next_award.threshold if next_award else 20
    next_award_colour = next_award.colour if next_award else '#0b5e3e'

    # Fetch top 5 most recent logs for this user
    recent_logs = sorted(
        ServiceHour.query.filter_by(user_id=user.school_id).all(),
        key=lambda log: datetime.strptime(log.date, "%d-%m-%Y"),
        reverse=True
    )[:5]

    STATUS_MAP = {
        1: 'Approved',
        2: 'Pending',
        3: 'Rejected'
    }
    # Map numeric status codes to human-readable labels for display
    for log in recent_logs:
        log.status = STATUS_MAP.get(log.status, 'Unknown')

    # Attach group name if group_id exists to provide context in recent logs
    for log in recent_logs:
        log.group_name = Group.query.get(log.group_id).name if log.group_id else None # noqa

    # Format the date in a user-friendly way for display in the dashboard
    for log in recent_logs:
        try:
            log.formatted_date = datetime.strptime(log.date, "%d-%m-%Y").strftime("%b %d").upper() # noqa
        except Exception:
            log.formatted_date = str(log.date)

    # Pass all calculated data to the template for rendering the student
    # dashboard
    return render_template(
        'student/student.html',
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


@student_bp.route('/activity-history')
@login_required
def activity_history():
    if session.get('role') != 'Student':
        abort(403)

    # Get current user from session to fetch their activity logs
    user = User.query.filter_by(school_id=session.get('username')).first()
    if not user:
        flash("User not found.")
        return redirect(url_for('auth.login'))

    status_filter = request.args.get("status")

    query = ServiceHour.query.filter_by(user_id=user.school_id)
    if status_filter:
        # Map human-readable status filter to internal status codes
        status_map = {
            "Approved": 1,
            "Pending": 2,
            "Rejected": 3
        }
        mapped_status = status_map.get(status_filter)
        if mapped_status:
            query = query.filter(ServiceHour.status == mapped_status)

    # Order logs by date descending to show most recent first
    logs = query.order_by(ServiceHour.date.desc()).all()

    # Fetch all logs for this user without status filter to calculate counts
    # for each status
    all_logs = ServiceHour.query.filter_by(user_id=user.school_id).all()

    # Enrich each log with group name, teacher name, and formatted dates for
    # display purposes
    for log in logs:
        log.group_name = Group.query.get(log.group_id).name if log.group_id else "N/A" # noqa
        staff = User.query.filter_by(school_id=log.staff).first()
        log.teacher_name = f"{staff.first_name} {staff.last_name}" if staff else "N/A" # noqa
        try:
            log.formatted_date = datetime.strptime(log.date, "%d-%m-%Y").strftime("%b %d, %Y") # noqa
        except Exception:
            log.formatted_date = log.date
        try:
            log.formatted_log_time = datetime.strptime(log.log_time, "%d-%m-%Y %H:%M:%S").strftime("%b %d, %Y at %I:%M %p") # noqa
        except Exception:
            log.formatted_log_time = log.log_time
        log.status_label = {
            1: 'Approved',
            2: 'Pending',
            3: 'Rejected'
        }.get(log.status, 'Unknown')

    # Count totals from all_logs to display summary statistics on the page
    accepted_count = sum(1 for l in all_logs if l.status == 1) # noqa
    pending_count = sum(1 for l in all_logs if l.status == 2) # noqa
    rejected_count = sum(1 for l in all_logs if l.status == 3) # noqa

    return render_template(
        'student/activity.html',
        submissions=logs,
        accepted_count=accepted_count,
        pending_count=pending_count,
        rejected_count=rejected_count
    )


# Route: /activity-history/<int:user_id>
@student_bp.route('/activity-history/<int:user_id>')
def activity_history_user(user_id):
    user = User.query.get(user_id)
    if not user:
        flash("User not found.")
        return redirect(url_for('homepage'))

    # Fetch logs for the specified user ordered by date descending
    logs = ServiceHour.query.filter_by(user_id=user.school_id).order_by(ServiceHour.date.desc()).all() # noqa

    # Enrich logs with group names, staff names, and human-readable date
    # formats
    for log in logs:
        log.group_name = Group.query.get(log.group_id).name if log.group_id else "N/A" # noqa
        staff = User.query.filter_by(school_id=log.staff).first()
        log.teacher_name = f"{staff.first_name} {staff.last_name}" if staff else "N/A" # noqa
        try:
            log.formatted_date = datetime.strptime(log.date, "%d-%m-%Y").strftime("%b %d, %Y") # noqa
        except Exception:
            log.formatted_date = log.date
        try:
            log.formatted_log_time = datetime.strptime(log.log_time, "%d-%m-%Y %H:%M:%S").strftime("%b %d, %Y at %I:%M %p") # noqa
        except Exception:
            log.formatted_log_time = log.log_time
        log.status_label = {
            1: 'Approved',
            2: 'Pending',
            3: 'Rejected'
        }.get(log.status, 'Unknown')

    return render_template('activity.html', logs=logs, student=user)


@student_bp.route('/log')
def logpage():
    if session.get('role') != 'Student':
        abort(403)
    # Get all users who have the 'staff' role (role = 2) to allow students to
    # select staff in charge
    staff_members = User.query.filter_by(role=2).all()

    # Get all groups from the group table, with "Other" at the end for
    # better UX
    groups = Group.query.order_by(
        case(
            (Group.name == "Other", 1),
            else_=0
        ),
        Group.name
    ).all()

    return render_template('student/log.html', staff_members=staff_members, groups=groups) # noqa


@student_bp.route('/api/groups')
def search_groups():
    """
    API endpoint to search for group names matching a query string.
    Returns a JSON list of group names for autocomplete or selection.
    """
    query = request.args.get('q', '')
    groups = Group.query.filter(Group.name.ilike(f'%{query}%')).limit(10).all()
    return jsonify([group.name for group in groups])


# Route to get staff for a given group
@student_bp.route('/api/staff-for-group')
def get_staff_for_group():
    """
    API endpoint to retrieve the staff member responsible for a given group.
    Returns staff label and value for UI selection or displays 404 if not
    found.
    """
    group_name = request.args.get('group', '')
    group = Group.query.filter_by(name=group_name).first()
    if group:
        staff = User.query.filter_by(school_id=group.staff).first()
        if staff:
            return jsonify({
                'label': f"{staff.first_name} {staff.last_name} ({staff.school_id})", # noqa
                'value': f"{staff.first_name} {staff.last_name} ({staff.school_id})" # noqa
            })
    return jsonify(None), 404


@student_bp.route('/api/all-staff')
def get_all_staff():
    """
    API endpoint to retrieve all staff members with roles 2 or 3.
    Returns a JSON list of staff with labels and values for UI elements.
    """
    staff_members = User.query.filter(User.role.in_([2, 3])).all()
    staff_list = [{'value': f"{staff.first_name} {staff.last_name} ({staff.school_id})", # noqa
                   'label': f"{staff.first_name} {staff.last_name} ({staff.school_id})"} for staff in staff_members] # noqa
    return jsonify(staff_list)


@student_bp.route('/submit-hours', methods=['POST'])
@login_required
def submit_hours():
    """
    Handle submission of new service hours by the student. Validates input
    data, prevents duplicate entries for the same date, group, and
    activity, and saves the new log with status pending review.
    """
    user = User.query.filter_by(school_id=session.get('username')).first()
    if not user:
        flash('You must be logged in to submit hours.', 'logpage-error')
        return redirect(url_for('student.logpage'))

    # Get form data from submission
    date = request.form['date']
    group_name = request.form['group']
    staff_label = request.form['person_in_charge']
    activity = request.form['activity']
    activity = request.form['activity'].strip()
    # Validate activity name is neither empty nor too long to ensure
    # meaningful logs
    if not activity or len(activity) > 30:
        flash("Activity name must not be empty or over 30 characters.", "logpage-error")  # noqa
        return redirect(url_for('student.logpage'))
    try:
        hours = float(request.form['hours'])
    except ValueError:
        # Validate hours is a number to prevent invalid data entries
        flash("Hours must be a number.", "logpage-error")
        return redirect(url_for('student.logpage'))
    # Validate hours range and increments to enforce sensible and consistent
    # logging
    if hours < 0.5 or hours > 24 or (hours * 2) % 1 != 0:
        flash("Hours must be between 0.5 and 24, in 0.5 increments.", "logpage-error") # noqa
        return redirect(url_for('student.logpage'))
    details = request.form.get('details', '')

    # Get related group and staff IDs from form inputs
    group = Group.query.filter_by(name=group_name).first()
    staff_school_id = staff_label.split('(')[-1].strip(')')
    staff = User.query.filter_by(school_id=staff_school_id).first()

    # Validate existence of group and staff to prevent invalid references
    if not group or not staff:
        flash("Invalid group or staff member.", "logpage-error")
        return redirect(url_for('student.logpage'))

    # Prevent duplicate entries for same date, group, and activity to maintain
    # data integrity
    existing = ServiceHour.query.filter_by(
        user_id=user.school_id,
        group_id=group.id,
        date=datetime.strptime(date, "%Y-%m-%d").strftime("%d-%m-%Y"),
        description=activity
    ).first()
    if existing:
        flash("You’ve already logged this activity for that date.", "logpage-error") # noqa
        return redirect(url_for('student.logpage'))

    # Create a new service hour record with status pending (2) and current log
    # time
    new_log = ServiceHour(
        user_id=user.school_id,
        group_id=group.id,
        hours=hours,
        date=datetime.strptime(date, "%Y-%m-%d").strftime("%d-%m-%Y"),
        description=details or activity,
        status=2,
        log_time=datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
        staff=staff.school_id
    )

    db.session.add(new_log)
    try:
        db.session.commit()
        flash("Your hours have been submitted for review!", "logpage-success")
    except Exception as e: # noqa
        # Rollback transaction and notify user on failure to save log
        db.session.rollback()
        flash("An error occurred saving your log. Please try again.", "logpage-error") # noqa
    return redirect(url_for('student.logpage'))


def send_award_email(user, milestone):
    gmail_user = "servesync@burnside.school.nz"
    gmail_pass = "ptjm tdom eoge yzbe"  # Gmail App Password

    subject = f"🎉 Congratulations {user.first_name}! You've earned the {milestone['name']} Award!" # noqa
    to_email = user.email

    html_content = f"""
    <div style="font-family: 'Arial', sans-serif; background-color: #f6f9f6; padding: 40px; text-align: center;">
        <div style="max-width: 600px; margin: auto; background: white; border-radius: 12px;
                    box-shadow: 0 6px 16px rgba(0,0,0,0.1); padding: 40px; border: 4px solid {milestone['colour']};">
            <h1 style="color: {milestone['colour']}; font-size: 30px; margin-bottom: 10px;">Certificate of Achievement</h1>
            <hr style="border: 1px solid {milestone['colour']}; width: 60px; margin: 20px auto;">

            <p style="font-size: 18px; color: #444;">This certifies that</p>
            <h2 style="font-size: 28px; color: #222; margin: 10px 0;">{user.first_name} {user.last_name}</h2>

            <p style="font-size: 18px; color: #444;">has achieved the</p>
            <h3 style="font-size: 26px; color: {milestone['colour']}; margin: 10px 0;">{milestone['name']} Award</h3>

            <p style="color: #555;">Thank you for your dedication to community service through ServeSYNC.</p>

            <div style="margin-top: 30px; color: #888; font-size: 14px;">
                <em>Burnside High School · ServeSYNC</em><br>
                <span style="color: #aaa;">{datetime.now().strftime("%B %d, %Y")}</span>
            </div>
        </div>

        <p style="color: #666; margin-top: 25px;">Keep up the great work — next milestone is waiting!</p>
    </div>
    """  # noqa: E501

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = gmail_user
    msg['To'] = to_email
    msg.attach(MIMEText(html_content, 'html'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.ehlo()
        server.starttls()
        server.login(gmail_user, gmail_pass)
        server.sendmail(gmail_user, to_email, msg.as_string())
        server.quit()
        print(f"[EMAIL] Sent award email to {user.email} for {milestone['name']}") # noqa
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send email to {user.email}: {e}")
