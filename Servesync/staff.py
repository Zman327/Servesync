from flask import Blueprint
from flask import render_template, request, redirect, session, url_for, jsonify, make_response, abort, flash # noqa
import base64
from fpdf import FPDF
from openpyxl import Workbook
from datetime import datetime, timedelta
import csv
import io
import pytz
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from models import db, User, Group, ServiceHour, StaffPasswordToken
from werkzeug.security import generate_password_hash


staff_bp = Blueprint('staff', __name__)
last_notified = {}


@staff_bp.route('/set-staff-password/<token>', methods=['GET', 'POST'])
def set_staff_password(token):
    token_row = StaffPasswordToken.query.filter_by(token=token).first()
    if not token_row:
        print(f"[DEBUG] Token not found for: {token}")
        return render_template('staff/set_staff_password.html', invalid_token=True) # noqa

    token_info = {
        'school_id': token_row.school_id,
        'email': token_row.email,
        'first_name': token_row.first_name,
        'last_name': token_row.last_name
    }
    print(f"[DEBUG] Token info retrieved: {token_info}")

    if request.method == 'POST':
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')
        if not password or not confirm:
            flash("Please enter and confirm your password.", "warning")
            return render_template(
                'staff/set_staff_password.html',
                token=token,
                email=token_info.get('email'),
                first_name=token_info.get('first_name'),
                last_name=token_info.get('last_name')
            )
        if password != confirm:
            flash("Passwords do not match.", "warning")
            return render_template(
                'staff/set_staff_password.html',
                token=token,
                email=token_info.get('email'),
                first_name=token_info.get('first_name'),
                last_name=token_info.get('last_name')
            )
        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "warning")
            return render_template(
                'staff/set_staff_password.html',
                token=token,
                email=token_info.get('email'),
                first_name=token_info.get('first_name'),
                last_name=token_info.get('last_name')
            )

        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
        staff = User.query.filter_by(email=token_info.get('email')).first()
        if staff:
            print(f"[DEBUG] Found existing user: {staff.email}")
            staff.password = hashed_pw
            db.session.merge(staff)
            db.session.commit()
            print(f"[DEBUG] Password updated for {staff.email}")

            # Delete token after commit
            try:
                db.session.delete(token_row)
                db.session.commit()
                print(f"[DEBUG] Token {token} deleted successfully.")
            except Exception as e:
                print(f"[ERROR] Failed to delete token: {e}")

            flash("Your password has been updated successfully. You may now log in.", "success") # noqa
            return redirect('/home')

        print("[DEBUG] No existing staff found — creating new user")
        user = User(
            school_id=token_info.get('school_id'),
            email=token_info.get('email'),
            first_name=token_info.get('first_name'),
            last_name=token_info.get('last_name'),
            password=hashed_pw
        )
        db.session.add(user)
        db.session.commit()

        try:
            db.session.delete(token_row)
            db.session.commit()
            print(f"[DEBUG] Token {token} deleted after new user creation.")
        except Exception as e:
            print(f"[ERROR] Failed to delete token after creating new user: {e}") # noqa

        flash("Your password has been set. You may now log in.", "success")
        return redirect('/home')

    return render_template(
        'staff/set_staff_password.html',
        token=token,
        email=token_info.get('email'),
        first_name=token_info.get('first_name'),
        last_name=token_info.get('last_name')
    )


@staff_bp.route('/reject-log', methods=['POST'])
def reject_log():
    """
    Reject a service log.

    Expects a POST form with 'log_id' of the service log to
    reject. Sets the log status to 'Rejected' (status=3).
    Redirects back to the referring page or the staff dashboard if
    not available.

    Returns:
        A redirect response to the previous page or staff dashboard.
    """
    log_id = request.form.get('log_id')
    if log_id:
        # Fetch the service log by ID
        service_log = ServiceHour.query.get(log_id)
        if service_log:
            service_log.status = 3  # Set status to Rejected
            db.session.commit()
    # Redirect back to the referrer URL or staff page if referrer is
    # not available
    return redirect(request.referrer or url_for('staff.staffpage'))


@staff_bp.route('/approve-all-pending', methods=['POST'])
def approve_all_pending():
    """
    Approve all pending service logs for the current staff user.

    Expects the user to be logged in (username in session).
    Optionally, can specify a 'redirect_to' URL in the form data.

    Returns:
        A redirect response to the specified URL or staff dashboard.
    """
    staff_id = session.get('username')
    if not staff_id:
        return redirect('/login')

    # Approve all pending logs for this staff
    pending_logs = ServiceHour.query.filter_by(
        staff=staff_id, status=2
    ).all()
    for log in pending_logs:
        log.status = 1  # Approved
    db.session.commit()

    # Use redirect target from form if provided
    redirect_to = request.form.get('redirect_to', '/staff.dashboard')
    return redirect(redirect_to)


@staff_bp.route('/create-group', methods=['POST'])
def create_group():
    """
    Create a new group.

    Expects form data with 'group_name' and 'staff_in_charge'
    (formatted as 'Name (ID)'). Only allowed for users with role
    'Admin' or 'Staff'. Redirects to the staff dashboard after
    creation.

    Returns:
        A redirect response to the staff dashboard.
    """
    if session.get('role') not in ['Admin', 'Staff']:
        abort(403)

    group_name = request.form.get('group_name')
    staff_label = request.form.get('staff_in_charge')
    staff_id = None
    if staff_label and "(" in staff_label and ")" in staff_label:
        # Extract staff_id from label in format "Name (ID)"
        staff_id = staff_label.split("(")[-1].strip(")")

    if group_name and staff_id:
        new_group = Group(name=group_name, staff=staff_id)
        db.session.add(new_group)
        db.session.commit()

    return redirect(url_for('staff.staffpage'))


@staff_bp.route('/update-group', methods=['POST'])
def update_group():
    """
    Update an existing group's name or staff in charge.

    Expects form data:
        - 'group_id': ID of the group to update.
        - 'new_group_name': New name for the group (optional).
        - 'staff_in_charge': New staff label in format
          'Name (ID)' (optional).
    Only allowed for users with role 'Admin' or 'Staff'.
    Redirects to the staff dashboard after update.

    Returns:
        A redirect response to the staff dashboard.
    """
    if session.get('role') not in ['Admin', 'Staff']:
        abort(403)

    group_id = request.form.get('group_id')
    new_group_name = request.form.get('new_group_name')
    staff_in_charge = request.form.get('staff_in_charge')

    if not group_id:
        return redirect(url_for('staff.staffpage'))

    group = Group.query.get(group_id)
    if not group:
        return redirect(url_for('staff.staffpage'))

    if new_group_name:
        group.name = new_group_name
    if staff_in_charge and "(" in staff_in_charge and ")" in staff_in_charge:
        # Extract the staff_id from parentheses
        staff_id = staff_in_charge.split("(")[-1].strip(")")
        group.staff = staff_id

    db.session.commit()
    return redirect(url_for('staff.staffpage'))


@staff_bp.route('/delete-group', methods=['POST'])
def delete_group():
    """
    Delete a group.

    Expects form data with 'group_id' of the group to delete.
    Only allowed for users with role 'Admin' or 'Staff'.
    Redirects to the staff dashboard after deletion.

    Returns:
        A redirect response to the staff dashboard.
    """
    if session.get('role') not in ['Admin', 'Staff']:
        abort(403)
    group_id = request.form.get('group_id')
    if not group_id:
        return redirect(url_for('staff.staffpage'))
    group = Group.query.get(group_id)
    if not group:
        return redirect(url_for('staff.staffpage'))
    db.session.delete(group)
    db.session.commit()
    return redirect(url_for('staff.staffpage'))


@staff_bp.route('/search-staff')
def search_staff():
    """
    Autocomplete search for staff.

    Expects a query string parameter 'q' to search by school ID or
    full name. Only accessible to 'Admin' or 'Staff' users.

    Returns:
        JSON list of matching staff with their ID, name, and email.
    """
    if session.get('role') not in ['Admin', 'Staff']:
        abort(403)

    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])

    # Search staff by school_id or full name (case-insensitive)
    staff_matches = User.query.filter(
        (User.user_role.has(name='Staff')) &
        (
            User.school_id.ilike(f"%{query}%") |
            (User.first_name + " " + User.last_name).ilike(f"%{query}%")
        )
    ).limit(10).all()

    results = [
        {
            "id": staff.school_id,
            "name": f"{staff.first_name} {staff.last_name}",
            "email": staff.email
        }
        for staff in staff_matches
    ]
    return jsonify(results)


def send_email(to_email, subject, message_body):
    """
    Send an email via Gmail SMTP.

    Args:
        to_email (str): Recipient's email address.
        subject (str): Email subject.
        message_body (str): Email body (plain text).

    Returns:
        bool: True if sent successfully, False otherwise.
    """
    # Email configuration (should not hardcode in production)
    sender_name = "ServeSYNC"
    sender_email = "servesync@burnside.school.nz"
    sender_password = "ptjm tdom eoge yzbe"  # Gmail App Password NOT Hardcode

    # Create the email message
    msg = MIMEMultipart()
    msg['From'] = sender_name
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(message_body, 'plain'))

    try:
        # Connect to Gmail SMTP and send the email
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()  # Secure the connection
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()

        print("Email sent successfully!")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


def check_and_notify_pending_submissions():
    """
    Check all staff for pending service submissions.

    If a staff member has 10 or more pending logs and hasn't been
    notified in the last 24 hours, send them an email reminder.

    Uses global 'last_notified' dict to track notification times.
    """
    now = datetime.now()

    # Get all users with the 'Staff' role
    staff_users = User.query.filter(User.user_role.has(name='Staff')).all()

    for staff_user in staff_users:
        staff_id = staff_user.school_id
        staff_email = staff_user.email
        full_name = f"{staff_user.first_name} {staff_user.last_name}"

        # Fetch all logs for this staff and count pending
        logs = ServiceHour.query.filter_by(staff=staff_id).all()
        pending_count = sum(1 for log in logs if log.status == 2)

        last_time = last_notified.get(staff_id)
        # Notify if pending_count >= 10 and not notified in the last 24 hours
        if (
            pending_count >= 10 and
            (not last_time or now - last_time > timedelta(hours=24))
        ):
            subject = (
                "Action Required: 10+ Pending Submissions on ServeSYNC"
            )
            message = (
                f"Kia ora {full_name} ({staff_id}),\n\n"
                f"This is a friendly reminder that you currently have "
                f"{pending_count} pending student submissions awaiting "
                f"your review in ServeSYNC.\n\n"
                "We encourage you to log in and process these as soon "
                "as you're able:\n"
                "👉 https://servesync.burnside.school.nz/staff.dashboard\n\n"
                "If you have any questions or need support, please feel "
                "free to reach out.\n\n"
                "Ngā mihi nui,\n"
                "— The ServeSYNC Team"
            )

            try:
                send_email(staff_email, subject, message)
                last_notified[staff_id] = now
            except Exception as e:
                print(
                    f"Failed to send email notification to {staff_email}: {e}"
                )


@staff_bp.route('/staff.dashboard')
def staffpage():
    """
    Staff dashboard page.

    Shows greeting, recent submissions, pending count, attached
    groups, and approved hours this year. Only accessible to users
    with 'Admin' or 'Staff' role. Also triggers notification emails
    for staff with many pending submissions.

    Query Parameters:
        status (str, optional): Filter logs by status label
            ('Approved', 'Pending', 'Rejected').

    Returns:
        Rendered staff dashboard template with relevant context.
    """
    if session.get('role') not in ['Admin', 'Staff']:
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

    staff_id = session.get('username')
    # Notify all staff about pending submissions
    check_and_notify_pending_submissions()
    selected_status = request.args.get('status')

    # Fetch all service logs for the current staff
    logs = ServiceHour.query.filter_by(staff=staff_id).all()
    # Fetch the groups attached to this staff member
    attached_groups = Group.query.filter_by(staff=staff_id).all()
    for group in attached_groups:
        # Calculate total approved hours for each group
        group.total_hours = sum(
            log.hours
            for log in ServiceHour.query.filter_by(
                group_id=group.id, status=1
            ).all()
        )
        group.staff_user = User.query.filter_by(
            school_id=group.staff
        ).first()

    pending_count = sum(1 for log in logs if log.status == 2)

    # Calculate total approved hours this year
    current_year = datetime.now().year
    approved_hours_this_year = sum(
        log.hours
        for log in logs
        if log.status == 1 and
        datetime.strptime(log.date, "%d-%m-%Y").year == current_year
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
            # Get group name if exists
            log.group_name = (
                Group.query.get(log.group_id).name
                if log.group_id else "N/A"
            )
            try:
                log.formatted_date = datetime.strptime(
                    log.date, "%d-%m-%Y"
                ).strftime("%b %d, %Y")
            except Exception:
                log.formatted_date = log.date
            try:
                log.formatted_log_time = datetime.strptime(
                    log.log_time, "%d-%m-%Y %H:%M:%S"
                ).strftime("%b %d, %Y at %I:%M %p")
            except Exception:
                log.formatted_log_time = log.log_time
            user = User.query.get(log.user_id)
            # Build picture URL from BLOB or fallback to default
            if user and user.picture:
                encoded_picture = base64.b64encode(
                    user.picture
                ).decode('utf-8')
                picture_url = f"data:image/jpeg;base64,{encoded_picture}"
            else:
                picture_url = url_for(
                    'static', filename='default-profile.png'
                )

            student_name = (
                f"{user.first_name} {user.last_name}"
                if user else "Unknown"
            )

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
    filtered_logs.sort(
        key=lambda log: datetime.strptime(log["date"], "%d-%m-%Y"),
        reverse=True
    )
    recent_logs = filtered_logs[:5]

    return render_template(
        'staff/staff.html',
        greeting=greeting,
        recent_submissions=recent_logs,
        pending_count=pending_count,
        attached_groups=attached_groups,
        approved_hours_this_year=approved_hours_this_year,
        logged_in_staff=User.query.filter_by(school_id=staff_id).first()
    )


@staff_bp.route('/submissions')
def submissions():
    """
    View all submissions for groups managed by the logged-in staff.

    Only accessible to users with 'Admin' or 'Staff' role.
    Allows filtering by status label via query parameter.

    Query Parameters:
        status (str, optional): Filter logs by status label.

    Returns:
        Rendered submissions template with submission data and status
        counts.
    """
    if session.get('role') not in ['Admin', 'Staff']:
        abort(403)
    staff_id = session.get('username')
    selected_status = request.args.get('status')

    # Get groups this staff manages
    attached_groups = Group.query.filter_by(staff=staff_id).all()
    group_ids = [group.id for group in attached_groups]

    # Get all service logs for the managed groups and this staff
    logs = ServiceHour.query.filter(
        ServiceHour.group_id.in_(group_ids),
        ServiceHour.staff == staff_id
    ).all()

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
            # Build picture URL from BLOB or fallback to default
            if user and user.picture:
                encoded_picture = base64.b64encode(
                    user.picture
                ).decode('utf-8')
                picture_url = f"data:image/jpeg;base64,{encoded_picture}"
            else:
                picture_url = url_for(
                    'static', filename='default-profile.png'
                )
            student_name = (
                f"{user.first_name} {user.last_name}"
                if user else "Unknown"
            )
            group = Group.query.get(log.group_id)
            group_name = group.name if group else "N/A"
            try:
                formatted_date = datetime.strptime(
                    log.date, "%d-%m-%Y"
                ).strftime("%b %d, %Y")
            except Exception:
                formatted_date = log.date
            try:
                formatted_log_time = (
                    datetime.strptime(
                        log.log_time, "%d-%m-%Y %H:%M:%S"
                    ).strftime("%b %d, %Y at %I:%M %p")
                    if log.log_time else "N/A"
                )
            except Exception:
                formatted_log_time = (
                    log.log_time if log.log_time else "N/A"
                )

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
                'picture_url': picture_url
            })

            # Count the status categories
            if log.status == 1:
                accepted_count += 1
            elif log.status == 2:
                pending_count += 1
            elif log.status == 3:
                rejected_count += 1

    # Sort by newest first using original log.date format
    submission_data.sort(
        key=lambda x: datetime.strptime(x["date"], "%b %d, %Y"),
        reverse=True
    )

    return render_template(
        'staff/submissions.html',
        submissions=submission_data,
        accepted_count=accepted_count,
        pending_count=pending_count,
        rejected_count=rejected_count
    )


@staff_bp.route('/update-log-field', methods=['POST'])
def update_log_field():
    """
    Update fields of a service log.

    Expects a JSON payload with:
        - log_id (int): ID of the log to update.
        - description (str): New description.
        - hours (float): New hours value.
        - date (str): New date in '%d-%m-%Y' format.

    Returns:
        JSON indicating success or error.
    """
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


@staff_bp.route('/approve-log', methods=['POST'])
def approve_log():
    """
    Approve a service log.

    Expects a POST form with 'log_id' of the service log to approve.
    Sets the log status to 'Approved' (status=1).
    Redirects back to the referring page or the staff dashboard if
    not available.

    Returns:
        A redirect response to the previous page or staff dashboard.
    """
    log_id = request.form.get('log_id')
    if log_id:
        service_log = ServiceHour.query.get(log_id)
        if service_log:
            service_log.status = 1  # Set status to Approved
            db.session.commit()
    # Redirect back to the referrer URL or staff page if referrer is
    # not available
    return redirect(request.referrer or url_for('staff.staffpage'))


@staff_bp.route('/download/csv')
def download_csv():
    """
    Download a CSV report of approved service hours for the logged-in
    staff. Only approved logs (status=1) are included.

    Returns:
        A CSV file as an HTTP response attachment.
    """
    staff_id = session.get('username')
    staff = User.query.filter_by(school_id=staff_id).first()
    logs = ServiceHour.query.filter_by(staff=staff_id, status=1).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([f"Report for: {staff.first_name} {staff.last_name}"])
    writer.writerow([])
    writer.writerow([
        'Student', 'Activity', 'Hours', 'Date',
        'Date Submitted', 'Group'
    ])

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
    response.headers[
        "Content-Disposition"
    ] = "attachment; filename=service_hours_report.csv"
    response.headers["Content-Type"] = "text/csv"
    return response


@staff_bp.route('/download/excel')
def download_excel():
    """
    Download an Excel (.xlsx) report of approved service hours for
    the logged-in staff. Only approved logs (status=1) are included.

    Returns:
        An Excel file as an HTTP response attachment.
    """
    staff_id = session.get('username')
    staff = User.query.filter_by(school_id=staff_id).first()
    logs = ServiceHour.query.filter_by(staff=staff_id, status=1).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Service Hours"
    ws.append([f"Report for: {staff.first_name} {staff.last_name}"])
    ws.append([])
    ws.append([
        'Student', 'Activity', 'Hours', 'Date',
        'Date Submitted', 'Group'
    ])

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
    response.headers[
        "Content-Disposition"
    ] = "attachment; filename=service_hours_report.xlsx"
    response.headers[
        "Content-Type"
    ] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return response


@staff_bp.route('/download/pdf')
def download_pdf():
    """
    Download a PDF report of approved service hours for the logged-in staff.
    Only approved logs (status=1) are included.

    Returns:
        A PDF file as an HTTP response attachment.
    """
    staff_id = session.get('username')
    staff = User.query.filter_by(school_id=staff_id).first()
    logs = ServiceHour.query.filter_by(staff=staff_id, status=1).all()

    # Table column settings (widths in mm)
    col_widths = [35, 43, 20, 25, 35, 35]
    col_names = ['Student', 'Activity', 'Hours', 'Date', 'Submitted', 'Group']
    col_aligns = ['L', 'L', 'C', 'C', 'C', 'L']

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, txt=f"Report for: {staff.first_name} {staff.last_name}",
             ln=True, align='C')
    pdf.ln(6)

    # Header row: larger bold font
    pdf.set_font("Arial", style="B", size=11)
    for i, name in enumerate(col_names):
        pdf.cell(col_widths[i], 10, name, border=1, align=col_aligns[i])
    pdf.ln()

    # Data rows: alternating background, alignment
    pdf.set_font("Arial", size=10)
    fill = False  # For alternating row color
    for idx, log in enumerate(logs):
        user = User.query.get(log.user_id)
        group = Group.query.get(log.group_id)
        student_val = f"{user.first_name} {user.last_name}" if user else "Unknown" # noqa
        activity_val = log.description
        hours_val = str(log.hours)
        date_val = log.date
        submitted_val = log.log_time
        group_val = group.name if group else "N/A"
        row = [student_val, activity_val, hours_val, date_val, submitted_val, group_val] # noqa

        # Set fill color for alternate rows (light gray)
        if fill:
            pdf.set_fill_color(240, 240, 240)
        else:
            pdf.set_fill_color(255, 255, 255)

        for i, val in enumerate(row):
            align = col_aligns[i]
            # Truncate value if needed to avoid overflow (optional)
            display_val = str(val)
            # Write cell with fill for alternating rows
            pdf.cell(col_widths[i], 8, display_val, border=1, align=align, fill=True) # noqa
        pdf.ln()
        fill = not fill

    response = make_response(pdf.output(dest='S').encode('latin-1'))
    response.headers["Content-Disposition"] = "attachment; filename=service_hours_report.pdf" # noqa
    response.headers["Content-Type"] = "application/pdf"
    return response
