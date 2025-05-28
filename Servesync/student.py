from flask import Blueprint
from flask import render_template, request, redirect, session, url_for, flash, jsonify, abort  # noqa
from functools import wraps
from models import db, User, Group, ServiceHour, Award
from sqlalchemy import case
from datetime import datetime
import pytz


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

    approved_logs = ServiceHour.query.filter_by(user_id=user.school_id, status=1).all() # noqa
    user_hours = sum(log.hours for log in approved_logs) if approved_logs else 0 # noqa
    user.hours = user_hours
    db.session.commit()

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
    top_groups = sorted(group_hours.items(), key=lambda item: item[1], reverse=True)[:3] # noqa

    # Find the next award the user hasn't reached yet
    next_award = Award.query.filter(Award.threshold > user_hours).order_by(Award.threshold.asc()).first() # noqa

    # Get the next award's name and threshold
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
    for log in recent_logs:
        log.status = STATUS_MAP.get(log.status, 'Unknown')

    # Attach group name if group_id exists
    for log in recent_logs:
        log.group_name = Group.query.get(log.group_id).name if log.group_id else None # noqa

    for log in recent_logs:
        try:
            log.formatted_date = datetime.strptime(log.date, "%d-%m-%Y").strftime("%b %d").upper() # noqa
        except Exception:
            log.formatted_date = str(log.date)

    # Pass the next_award_threshold and recent_logs to the template
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
def activity_history():
    return render_template('student/activity.html')


# Route: /activity-history/<int:user_id>
@student_bp.route('/activity-history/<int:user_id>')
def activity_history_user(user_id):
    user = User.query.get(user_id)
    if not user:
        flash("User not found.")
        return redirect(url_for('homepage'))

    logs = ServiceHour.query.filter_by(user_id=user.school_id).order_by(ServiceHour.date.desc()).all() # noqa

    for log in logs:
        log.group_name = Group.query.get(log.group_id).name if log.group_id else "N/A" # noqa
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
@login_required
def logpage():
    if session.get('role') != 'Student':
        abort(403)
    # Get all users who have the 'staff' role (role = 2)
    staff_members = User.query.filter_by(role=2).all()

    # Get all groups from the group table, with "Other" at the end
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
    query = request.args.get('q', '')
    groups = Group.query.filter(Group.name.ilike(f'%{query}%')).limit(10).all()
    return jsonify([group.name for group in groups])


# Route to get staff for a given group
@student_bp.route('/api/staff-for-group')
def get_staff_for_group():
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
    staff_members = User.query.filter(User.role.in_([2, 3])).all()
    staff_list = [{'value': f"{staff.first_name} {staff.last_name} ({staff.school_id})", # noqa
                   'label': f"{staff.first_name} {staff.last_name} ({staff.school_id})"} for staff in staff_members] # noqa
    return jsonify(staff_list)


@student_bp.route('/submit-hours', methods=['POST'])
@login_required
def submit_hours():
    user = User.query.filter_by(school_id=session.get('username')).first()
    if not user:
        flash('You must be logged in to submit hours.', 'logpage-error')
        return redirect(url_for('student.logpage'))

    # Get form data
    date = request.form['date']
    group_name = request.form['group']
    staff_label = request.form['person_in_charge']
    activity = request.form['activity']
    activity = request.form['activity'].strip()
    if not activity or len(activity) > 30:
        flash("Activity name must not be empty or over 30 characters.", "logpage-error")  # noqa
        return redirect(url_for('student.logpage'))
    try:
        hours = float(request.form['hours'])
    except ValueError:
        flash("Hours must be a number.", "logpage-error")
        return redirect(url_for('student.logpage'))
    if hours < 0.5 or hours > 24 or (hours * 2) % 1 != 0:
        flash("Hours must be between 0.5 and 24, in 0.5 increments.", "logpage-error") # noqa
        return redirect(url_for('student.logpage'))
    details = request.form.get('details', '')

    # Get related group and staff IDs
    group = Group.query.filter_by(name=group_name).first()
    staff_school_id = staff_label.split('(')[-1].strip(')')
    staff = User.query.filter_by(school_id=staff_school_id).first()

    if not group or not staff:
        flash("Invalid group or staff member.", "logpage-error")
        return redirect(url_for('student.logpage'))

    # Prevent duplicate entries for same date, group, and activity
    existing = ServiceHour.query.filter_by(
        user_id=user.school_id,
        group_id=group.id,
        date=datetime.strptime(date, "%Y-%m-%d").strftime("%d-%m-%Y"),
        description=activity
    ).first()
    if existing:
        flash("You’ve already logged this activity for that date.", "logpage-error") # noqa
        return redirect(url_for('student.logpage'))

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
    try:
        db.session.commit()
        flash("Your hours have been submitted for review!", "logpage-success")
    except Exception as e: # noqa
        db.session.rollback()
        flash("An error occurred saving your log. Please try again.", "logpage-error") # noqa
    return redirect(url_for('student.logpage'))
