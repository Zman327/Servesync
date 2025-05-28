from flask import Blueprint
from flask import render_template, request, redirect, session, url_for, jsonify, make_response, abort # noqa
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
from models import db, User, Group, ServiceHour


staff_bp = Blueprint('staff', __name__)
last_notified = {}


# Route to reject a service log
@staff_bp.route('/reject-log', methods=['POST'])
def reject_log():
    log_id = request.form.get('log_id')
    if log_id:
        service_log = ServiceHour.query.get(log_id)
        if service_log:
            service_log.status = 3  # Set status to Rejected
            db.session.commit()

# Redirect back to the referrer URL or staff page if referrer is not available
    return redirect(request.referrer or url_for('staff.staffpage'))


@staff_bp.route('/approve-all-pending', methods=['POST'])
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


# Email sending function
def send_email(to_email, subject, message_body):
    # Email configuration
    sender_name = "ServeSYNC"
    sender_email = "servesync.bhs@gmail.com"
    sender_password = "gfun ewwp qbfn rqyq"  # Gmail App Password NOT Hardcode

    # Create the email
    msg = MIMEMultipart()
    msg['From'] = sender_name
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(message_body, 'plain'))

    try:
        # Connect to the server and send the email
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  # Secure the connection
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()

        print("Email sent successfully!")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


# Function to check and notify staff about pending submissions
def check_and_notify_pending_submissions(staff_id, staff_email):
    now = datetime.now()
    logs = ServiceHour.query.filter_by(staff=staff_id).all()
    pending_count = sum(1 for log in logs if log.status == 2)

    last_time = last_notified.get(staff_id)
    if pending_count >= 10 and (not last_time or now - last_time > timedelta(hours=24)):  # noqa
        # Fetch staff name from the database
        staff_user = User.query.filter_by(school_id=staff_id).first()
        full_name = f"{staff_user.first_name} {staff_user.last_name}" if staff_user else "Staff Member"  # noqa

        subject = "Action Required: 10+ Pending Submissions on ServeSYNC"
        message = (
            f"Kia ora {full_name} ({staff_id}),\n\n"
            f"This is a friendly reminder that you currently have *{pending_count}* pending student submissions "  # noqa
            f"awaiting your review in ServeSYNC.\n\n"
            "We encourage you to log in and process these as soon as you're able:\n"  # noqa
            "👉 https://zeyad327.pythonanywhere.com/staff.dashboard\n\n"
            "If you have any questions or need support, please feel free to reach out.\n\n"  # noqa
            "Ngā mihi nui,\n"
            "— The ServeSYNC Team"
        )

        try:
            send_email(staff_email, subject, message)
            last_notified[staff_id] = now
        except Exception as e:
            print(f"Failed to send email notification: {e}")


@staff_bp.route('/staff.dashboard')
def staffpage():
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
    staff_email = None
    staff_user = User.query.filter_by(school_id=staff_id).first()
    if staff_user:
        staff_email = staff_user.email
    if staff_email:
        check_and_notify_pending_submissions(staff_id, staff_email)
    selected_status = request.args.get('status')

    # Fetch all service logs for the current staff
    logs = ServiceHour.query.filter_by(staff=staff_id).all()
    # Fetch the groups attached to this staff member
    attached_groups = Group.query.filter_by(staff=staff_id).all()

    pending_count = sum(1 for log in logs if log.status == 2)

    # Calculate total approved hours this year
    current_year = datetime.now().year
    approved_hours_this_year = sum(
        log.hours for log in logs
        if log.status == 1 and datetime.strptime(log.date, "%d-%m-%Y").year == current_year  # noqa
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
            log.group_name = Group.query.get(log.group_id).name if log.group_id else "N/A" # noqa
            try:
                log.formatted_date = datetime.strptime(log.date, "%d-%m-%Y").strftime("%b %d, %Y") # noqa
            except Exception:
                log.formatted_date = log.date
            try:
                log.formatted_log_time = datetime.strptime(log.log_time, "%d-%m-%Y %H:%M:%S").strftime("%b %d, %Y at %I:%M %p") # noqa
            except Exception:
                log.formatted_log_time = log.log_time
            user = User.query.get(log.user_id)
            # Build picture URL from BLOB or fallback to default
            if user and user.picture:
                encoded_picture = base64.b64encode(user.picture).decode('utf-8') # noqa
                picture_url = f"data:image/jpeg;base64,{encoded_picture}"
            else:
                picture_url = url_for('static', filename='default-profile.png')

            student_name = f"{user.first_name} {user.last_name}" if user else "Unknown" # noqa

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
    filtered_logs.sort(key=lambda log: datetime.strptime(log["date"], "%d-%m-%Y"), reverse=True) # noqa
    recent_logs = filtered_logs[:5]

    return render_template(
        'staff/staff.html',
        greeting=greeting,
        recent_submissions=recent_logs,
        pending_count=pending_count,
        attached_groups=attached_groups,
        approved_hours_this_year=approved_hours_this_year
    )


@staff_bp.route('/submissions')
def submissions():
    if session.get('role') not in ['Admin', 'Staff']:
        abort(403)
    staff_id = session.get('username')
    selected_status = request.args.get('status')

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
                encoded_picture = base64.b64encode(user.picture).decode('utf-8') # noqa
                picture_url = f"data:image/jpeg;base64,{encoded_picture}"
            else:
                picture_url = url_for('static', filename='default-profile.png')
            student_name = f"{user.first_name} {user.last_name}" if user else "Unknown" # noqa
            group = Group.query.get(log.group_id)
            group_name = group.name if group else "N/A"
            try:
                formatted_date = datetime.strptime(log.date, "%d-%m-%Y").strftime("%b %d, %Y") # noqa
            except Exception:
                formatted_date = log.date
            try:
                formatted_log_time = (
                    datetime.strptime(log.log_time, "%d-%m-%Y %H:%M:%S").strftime("%b %d, %Y at %I:%M %p") # noqa
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
                'picture_url': picture_url})

            # Count the status categories
            if log.status == 1:
                accepted_count += 1
            elif log.status == 2:
                pending_count += 1
            elif log.status == 3:
                rejected_count += 1

    # Sort by newest first using original log.date format
    submission_data.sort(key=lambda x: datetime.strptime(x["date"], "%b %d, %Y"), reverse=True) # noqa

    return render_template('staff/submissions.html', submissions=submission_data, # noqa
                           accepted_count=accepted_count,
                           pending_count=pending_count,
                           rejected_count=rejected_count)


@staff_bp.route('/update-log-field', methods=['POST'])
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
@staff_bp.route('/approve-log', methods=['POST'])
def approve_log():
    log_id = request.form.get('log_id')
    if log_id:
        service_log = ServiceHour.query.get(log_id)
        if service_log:
            service_log.status = 1  # Set status to Approved
            db.session.commit()

# Redirect back to the referrer URL or staff page if referrer is not available
    return redirect(request.referrer or url_for('staff.staffpage'))


@staff_bp.route('/download/csv')
def download_csv():
    staff_id = session.get('username')
    staff = User.query.filter_by(school_id=staff_id).first()
    logs = ServiceHour.query.filter_by(staff=staff_id, status=1).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([f"Report for: {staff.first_name} {staff.last_name}"])
    writer.writerow([])
    writer.writerow(['Student', 'Activity', 'Hours', 'Date', 'Date Submitted', 'Group']) # noqa

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
    response.headers["Content-Disposition"] = "attachment; filename=service_hours_report.csv" # noqa
    response.headers["Content-Type"] = "text/csv"
    return response


@staff_bp.route('/download/excel')
def download_excel():
    staff_id = session.get('username')
    staff = User.query.filter_by(school_id=staff_id).first()
    logs = ServiceHour.query.filter_by(staff=staff_id, status=1).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Service Hours"
    ws.append([f"Report for: {staff.first_name} {staff.last_name}"])
    ws.append([])
    ws.append(['Student', 'Activity', 'Hours', 'Date', 'Date Submitted', 'Group']) # noqa

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
    response.headers["Content-Disposition"] = "attachment; filename=service_hours_report.xlsx" # noqa
    response.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" # noqa
    return response


@staff_bp.route('/download/pdf')
def download_pdf():
    staff_id = session.get('username')
    staff = User.query.filter_by(school_id=staff_id).first()
    logs = ServiceHour.query.filter_by(staff=staff_id, status=1).all()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Report for: {staff.first_name} {staff.last_name}", ln=True, align='C') # noqa
    pdf.ln(10)

    pdf.set_font("Arial", size=10)
    for log in logs:
        user = User.query.get(log.user_id)
        group = Group.query.get(log.group_id)
        pdf.multi_cell(0, 10, txt=f"Student: {user.first_name} {user.last_name if user else 'Unknown'}\n" # noqa
                                   f"Activity: {log.description}\n"  # noqa
                                   f"Hours: {log.hours}\n"
                                   f"Date: {log.date}\n"
                                   f"Submitted: {log.log_time}\n"
                                   f"Group: {group.name if group else 'N/A'}\n", border=0) # noqa
        pdf.ln(2)

    response = make_response(pdf.output(dest='S').encode('latin-1'))
    response.headers["Content-Disposition"] = "attachment; filename=service_hours_report.pdf" # noqa
    response.headers["Content-Type"] = "application/pdf"
    return response
