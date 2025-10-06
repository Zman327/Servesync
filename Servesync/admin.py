from flask import Blueprint
from flask import render_template, request, redirect, url_for, flash, jsonify, make_response # noqa
from flask import session, abort
import base64
from fpdf import FPDF
from openpyxl import Workbook
from sqlalchemy import func
from datetime import datetime
from collections import defaultdict
import csv
import io
import pytz
import json
from werkzeug.security import generate_password_hash
import pandas as pd
import requests
import os
from models import User, Award, ServiceHour, Group, db, StaffPasswordToken
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/admin.dashboard')
def adminpage():
    if session.get('role') != 'Admin':
        abort(403)
    nz_timezone = pytz.timezone('Pacific/Auckland')
    now = datetime.now(nz_timezone)
    if now.hour < 12:
        greeting = "Good Morning"
    elif now.hour < 18:
        greeting = "Good Afternoon"
    else:
        greeting = "Good Evening"

    users = User.query.filter_by(role=1).all()  # Only include students
    student_count = User.query.filter_by(role=1).count()
    approved_hours_total = db.session.query(func.sum(User.hours)).scalar() or 0
    total_submissions = ServiceHour.query.count()
    admins = User.query.filter_by(role=3).all()
    staff = User.query.filter_by(role=2).all()

    staff_dicts = []
    for s in staff:
        full_name = f"{s.first_name} {s.last_name}"
        staff_dicts.append({
            'name': full_name,
            'school_id': s.school_id
        })

    admin_dicts = []
    for a in admins:
        full_name = f"{a.first_name} {a.last_name}"
        admin_dicts.append({
            'name': full_name,
            'school_id': a.school_id
        })

    # --- Top student calculation ---
    top_student = (
        db.session.query(User)
        .filter_by(role=1)
        .order_by(User.hours.desc())
        .first()
    )
    top_student_name = f"{top_student.first_name} {top_student.last_name}" if top_student else "N/A" # noqa
    top_student_hours = top_student.hours if top_student else 0

    if top_student and top_student.picture:
        top_student_picture = f"data:image/jpeg;base64,{base64.b64encode(top_student.picture).decode('utf-8')}" # noqa
    else:
        top_student_picture = url_for('static', filename='default-profile.png')

    # --- Fetch all submissions and status counts for admin dashboard ---
    STATUS_MAP = {
        1: 'Approved',
        2: 'Pending',
        3: 'Rejected'
    }

    submission_data = []
    accepted_count = 0
    pending_count = 0
    rejected_count = 0

    logs = ServiceHour.query.all()
    for log in logs:
        status_label = STATUS_MAP.get(log.status, 'Unknown')
        user = User.query.get(log.user_id)
        if user and user.picture:
            encoded_picture = base64.b64encode(user.picture).decode('utf-8')
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
            'picture_url': picture_url
        })

        if log.status == 1:
            accepted_count += 1
        elif log.status == 2:
            pending_count += 1
        elif log.status == 3:
            rejected_count += 1

    # Submissions per month chart (already existing)
    submissions = db.session.query(ServiceHour.log_time).all()
    monthly_counts = defaultdict(int)
    for log in submissions:
        try:
            dt = datetime.strptime(log[0], "%d-%m-%Y %H:%M:%S")
            month_str = dt.strftime("%b %Y")
            monthly_counts[month_str] += 1
        except: # noqa
            continue
    sorted_months = sorted(monthly_counts.items(), key=lambda x: datetime.strptime(x[0], "%b %Y")) # noqa
    chart_labels = [item[0] for item in sorted_months]
    chart_data = [item[1] for item in sorted_months]

    # --- Award distribution for pie chart ---
    awards = Award.query.order_by(Award.threshold.desc()).all()
    award_distribution = {award.name: 0 for award in awards}
    award_distribution['Not achieved'] = 0

    for user in users:
        awarded = False
        user_hours = user.hours or 0  # Handle None hours
        for award in awards:
            if user_hours >= award.threshold:
                award_distribution[award.name] += 1
                awarded = True
                break
        if not awarded:
            award_distribution['Not achieved'] += 1

    award_labels = list(award_distribution.keys())
    award_counts = list(award_distribution.values())

    # Extract award colors
    award_colors = [award.colour for award in awards]
    award_colors.append('#FF3131')  # Fallback for 'Not achieved'

    # --- Build All Students table data ---
    student_table_data = []
    for student in users:
        full_name = f"{student.first_name} {student.last_name}"
        form_class = getattr(student, 'form', None) or 'N/A'
        matched_award = next(
            ((award.name, award.colour) for award in awards if (student.hours or 0) >= award.threshold), # noqa
            ('Not achieved', '#FF3131')
        )
        # Set student image like top student image
        if student.picture:
            encoded_picture = base64.b64encode(student.picture).decode('utf-8')
            picture_url = f"data:image/jpeg;base64,{encoded_picture}"
        else:
            picture_url = url_for('static', filename='default-profile.png')

        student_table_data.append({
            'school_id': student.school_id,
            'name': full_name,
            'form': form_class,
            'hours': student.hours or 0,
            'award': matched_award[0],
            'award_color': matched_award[1],
            'picture_url': picture_url  # Add picture URL here
        })

    return render_template(
        'admin/admin.html',
        greeting=greeting,
        users=users,
        student_count=student_count,
        approved_hours_total=approved_hours_total,
        chart_labels=json.dumps(chart_labels),
        chart_data=json.dumps(chart_data),
        award_labels=json.dumps(award_labels),
        award_counts=json.dumps(award_counts),
        award_colors=json.dumps(award_colors),
        submissions=submission_data,
        pending_submissions=pending_count,
        accepted_count=accepted_count,
        rejected_count=rejected_count,
        pending_count=pending_count,
        top_student_name=top_student_name,
        top_student_hours=top_student_hours,
        top_student_picture=top_student_picture,
        all_students=student_table_data,
        total_submissions=total_submissions,
        all_staff=staff_dicts,
        current_admins=admin_dicts,
        submission_status_data=json.dumps({
            "Approved": accepted_count,
            "Pending": pending_count,
            "Rejected": rejected_count
        })
    )


@admin_bp.route('/promote-to-admin', methods=['POST'])
def promote_to_admin():
    data = request.get_json()
    school_id = data.get('school_id')
    user = User.query.filter_by(school_id=school_id).first()

    if user and user.role != 3:
        user.role = 3  # Promote to admin
        db.session.commit()
        return jsonify(success=True, message=f"{user.first_name} {user.last_name} is now an admin.") # noqa

    return jsonify(success=False, message="User not found or already an admin."), 400 # noqa


@admin_bp.route('/admin/remove', methods=['POST'])
def remove_admin():
    if not request.is_json:
        return jsonify({'status': 'error', 'message': 'Invalid content type. Expected application/json'}), 400 # noqa

    data = request.get_json()
    school_id = data.get('school_id')

    if not school_id:
        return jsonify({'status': 'error', 'message': 'school_id is required'}), 400 # noqa

    user = User.query.filter_by(school_id=school_id).first()
    if not user:
        return jsonify({'status': 'error', 'message': 'User not found'}), 400

    if int(user.role) != 3:
        return jsonify({'status': 'error', 'message': 'User is not an admin'}), 400  # noqa

    user.role = 2
    db.session.commit()
    return jsonify({'status': 'success', 'message': f"{user.first_name} {user.last_name} removed as admin."}) # noqa


@admin_bp.route('/api/current_admins')
def api_current_admins():
    admins = User.query.filter_by(role=3).all()
    result = [{
        'name': f"{a.first_name} {a.last_name}",
        'school_id': a.school_id
    } for a in admins]
    return jsonify(result)


@admin_bp.route('/add-student', methods=['POST'])
def add_student():
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    school_id = request.form['school_id']
    form_class = request.form['form']
    password = request.form['password']
    image_file = request.files['image']

    # Convert image to binary
    picture_data = image_file.read() if image_file else None

    # Hash the password
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

    # Create email from school_id
    email = f"{school_id}@burnside.school.nz"

    # Create a new user object using reflected columns
    new_student = User(
        first_name=first_name,
        last_name=last_name,
        school_id=school_id,
        form=form_class,
        password=hashed_password,
        role=1,  # assuming 1 means student
        picture=picture_data,
        hours=0,  # or any default you want
        email=email
    )

    try:
        db.session.add(new_student)
        db.session.commit()
        flash('Student added successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding student: {e}', 'danger')

    return redirect(url_for('admin.adminpage'))


@admin_bp.route('/bulk-upload-students', methods=['POST'])
def bulk_upload_students():
    file = request.files.get('bulk_file')
    photos = request.files.getlist('photos[]')

    if not file and not photos:
        flash('No file or photos uploaded', 'danger')
        return redirect(url_for('admin.adminpage'))

    added_count = 0

    # Spreadsheet logic only runs if file is provided
    if file:
        filename = file.filename.lower()
        df = None
        try:
            if filename.endswith('.csv'):
                try:
                    df = pd.read_csv(file, encoding='utf-8')
                except UnicodeDecodeError:
                    df = pd.read_csv(file, encoding='latin1')
            elif filename.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(file, engine='openpyxl')
            else:
                flash('Unsupported file format. Please upload a .csv or .xlsx file.', 'danger') # noqa
                return redirect(url_for('admin.adminpage'))
        except Exception as e:
            flash(f'Error reading file: {e}', 'danger')
            return redirect(url_for('admin.adminpage'))

        # Normalize and validate required columns (case-insensitive)
        # Step 1: lowercase and strip all column headers
        df.columns = [col.strip().lower() for col in df.columns]

        # Step 2: Check for all required columns
        required_cols = ['first name', 'last name', 'student id', 'tutor', 'internet - password display - student'] # noqa
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            flash(f"Missing required columns: {[col.title() for col in missing]}", "danger") # noqa
            return redirect(url_for('admin.adminpage'))

        # Step 3: Rename the columns for consistent access later
        rename_map = {
            'first name': 'First Name',
            'last name': 'Last Name',
            'student id': 'Student ID',
            'tutor': 'Tutor',
            'internet - password display - student': 'Password',
            'image': 'Image'  # Optional, handled if present
        }

        # Create a case-insensitive column renaming
        df.rename(columns={col: rename_map[col.strip().lower()] for col in df.columns if col.strip().lower() in rename_map}, inplace=True) # noqa

        for _, row in df.iterrows():
            try:
                first_name = row['First Name']
                last_name = row['Last Name']
                school_id = row['Student ID']
                form_class = row['Tutor']
                raw_pass = row['Password']
                image_val = row.get('Image', None)

                # Hash the password
                hashed_password = generate_password_hash(raw_pass, method='pbkdf2:sha256') # noqa

                # Process image (URL or base64)
                picture_data = None
                if isinstance(image_val, str):
                    val = image_val.strip()
                    if val.lower().startswith(('http://', 'https://')):
                        try:
                            resp = requests.get(val, timeout=5)
                            if resp.status_code == 200:
                                picture_data = resp.content
                        except Exception:
                            picture_data = None
                    else:
                        try:
                            picture_data = base64.b64decode(val)
                        except Exception:
                            picture_data = None

                # Build student email
                email = f"{school_id}@burnside.school.nz"

                if User.query.filter_by(email=email).first():
                    continue

                # Create and stage the student
                new_student = User(
                    first_name=first_name,
                    last_name=last_name,
                    school_id=school_id,
                    form=form_class,
                    password=hashed_password,
                    role=1,
                    picture=picture_data,
                    hours=0,
                    email=email
                )
                db.session.add(new_student)
                added_count += 1

            except KeyError as ke:
                flash(f"Missing column in row: {ke}", "warning")
            except Exception as err:
                flash(f"Error processing a row: {err}", "warning")

        # Commit all new users
        try:
            db.session.commit()
            flash(f'{added_count} students added successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error committing to database: {e}', 'danger')

    # --- Handle bulk photo uploads if provided ---
    # This logic is adapted from the old bulk_upload_student_photos route.
    # Runs if photos are provided, even without spreadsheet.
    if photos:
        updated = 0
        skipped = 0
        allowed_extensions = {'.jpg', '.jpeg', '.png'}

        for photo_file in photos:
            if not photo_file.filename:
                continue
            filename = os.path.basename(photo_file.filename)
            student_id, ext = os.path.splitext(filename)
            if ext.lower() not in allowed_extensions:
                skipped += 1
                continue
            student = User.query.filter_by(school_id=student_id).first()
            if student:
                student.picture = photo_file.read()  # Save as blob
                db.session.add(student)
                updated += 1
            else:
                skipped += 1

        try:
            db.session.commit()
            flash(f"Uploaded {updated} photos. Skipped {skipped} (no matching student).", "success") # noqa
        except Exception as e:
            db.session.rollback()
            flash(f"Error uploading photos: {e}", "danger")

    return redirect(url_for('admin.adminpage'))


@admin_bp.route('/bulk-upload-staff', methods=['POST'])
def bulk_upload_staff():
    file = request.files.get('bulk_file')
    photos = request.files.getlist('photos[]')

    if not file and not photos:
        flash('No file or photos uploaded', 'danger')
        return redirect(url_for('admin.adminpage'))

    added_count = 0

    # Spreadsheet logic only runs if file is provided
    if file:
        filename = file.filename.lower()
        df = None

        try:
            if filename.endswith('.csv'):
                try:
                    df = pd.read_csv(file, encoding='utf-8')
                except UnicodeDecodeError:
                    df = pd.read_csv(file, encoding='latin1')
            elif filename.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(file, engine='openpyxl')
            else:
                flash('Unsupported file format. Please upload a .csv or .xlsx file.', 'danger') # noqa
                return redirect(url_for('admin.adminpage'))
        except Exception as e:
            flash(f'Error reading file: {e}', 'danger')
            return redirect(url_for('admin.adminpage'))

        # Normalize and validate required columns (case-insensitive)
        df.columns = [col.strip().lower() for col in df.columns]

        # Required columns for staff spreadsheet (removed 'email (school)')
        required_cols = [
            'code',
            'last name',
            'first name',
            'internet - password display - staff'
        ]
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            flash(f"Missing required columns: {[col.title() for col in missing]}", "danger") # noqa
            return redirect(url_for('admin.adminpage'))

        # Rename columns for consistent access (removed 'email (school)')
        rename_map = {
            'code': 'School ID',
            'last name': 'Last Name',
            'first name': 'First Name',
            'internet - password display - staff': 'Password'
        }
        df.rename(columns={col: rename_map[col] for col in rename_map if col in df.columns}, inplace=True) # noqa

        for _, row in df.iterrows():
            try:
                first_name = row['First Name']
                last_name = row['Last Name']
                school_id = row['School ID'].lower()
                raw_pass = row['Password']
                # Generate staff email automatically
                email = f"{school_id}@burnside.school.nz"

                hashed_password = generate_password_hash(raw_pass, method='pbkdf2:sha256') # noqa

                if User.query.filter_by(email=email).first():
                    continue

                new_staff = User(
                    first_name=first_name,
                    last_name=last_name,
                    school_id=school_id,
                    form=None,
                    password=hashed_password,
                    role=2,
                    picture=None,
                    hours=None,
                    email=email
                )
                db.session.add(new_staff)
                added_count += 1

            except KeyError as ke:
                flash(f"Missing column in row: {ke}", "warning")
            except Exception as err:
                flash(f"Error processing a row: {err}", "warning")
        # Commit all new staff
        try:
            db.session.commit()
            flash(f'{added_count} Staff members added successfully!', 'success') # noqa
        except Exception as e:
            db.session.rollback()
            flash(f'Error committing to database: {e}', 'danger')

    # --- Handle bulk staff photo uploads if provided ---
    if photos:
        updated = 0
        skipped = 0
        allowed_extensions = {'.jpg', '.jpeg', '.png'}

        for photo in photos:
            if not photo.filename:
                continue
            filename = os.path.basename(photo.filename)
            staff_id, ext = os.path.splitext(filename)
            if ext.lower() not in allowed_extensions:
                skipped += 1
                continue
            staff = User.query.filter_by(school_id=staff_id).first()
            if staff:
                staff.picture = photo.read()
                db.session.add(staff)
                updated += 1
            else:
                skipped += 1

        try:
            db.session.commit()
            flash(f"Uploaded {updated} staff photos. Skipped {skipped} (no matching staff).", "success") # noqa
        except Exception as e:
            db.session.rollback()
            flash(f"Error uploading staff photos: {e}", "danger")

    return redirect(url_for('admin.adminpage'))


@admin_bp.route('/remove-students', methods=['POST'])
def remove_student():
    student_id = request.form.get('student_id')
    student = User.query.filter_by(school_id=student_id).first()
    if student:
        ServiceHour.query.filter_by(user_id=student.school_id).delete()
        db.session.delete(student)
        db.session.commit()
        flash("Student successfully removed.", "success")
    else:
        flash("Student not found.", "error")
    return redirect(url_for('admin.adminpage'))


def send_email(to_email, subject, html_content):
    # Gmail credentials
    gmail_user = "servesync@burnside.school.nz"
    gmail_pass = "ptjm tdom eoge yzbe"  # Replace with your real app password

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = gmail_user
    msg['To'] = to_email
    part = MIMEText(html_content, 'html')
    msg.attach(part)
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.ehlo()
        server.starttls()
        server.login(gmail_user, gmail_pass)
        server.sendmail(gmail_user, to_email, msg.as_string())
        server.quit()
    except Exception as e:
        print(f"[EMAIL] Failed to send email: {e}")


def generate_password_setup_token(email):
    # Use a secure random token plus email hash for uniqueness
    token = secrets.token_urlsafe(32)
    # You could add a timestamp or sign this token for expiry, etc.
    return token


@admin_bp.route('/add-staff', methods=['POST'])
def add_staff():
    # Read form fields
    first_name = request.form.get('first_name', '').strip()
    last_name = request.form.get('last_name', '').strip()
    school_id = request.form.get('school_id', '').strip()
    form_class = request.form.get('form', '').strip()
    image_file = request.files.get('image')
    password = request.form.get('password', '').strip()

    # Convert image to binary
    picture_data = image_file.read() if image_file else None

    # Generate staff email
    email = f"{school_id}@burnside.school.nz"

    # Check if staff already exists
    if User.query.filter_by(email=email).first():
        flash('Staff with this email already exists.', 'danger')
        return redirect(url_for('admin.adminpage'))

    # Hash the password
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

    # Create staff user in DB immediately
    new_staff = User(
        first_name=first_name,
        last_name=last_name,
        school_id=school_id,
        form=form_class,
        password=hashed_password,
        role=2,
        hours=None,
        picture=picture_data,
        email=email
    )
    db.session.add(new_staff)
    db.session.commit()

    # Generate token and store in DB for password setup
    token = generate_password_setup_token(email)
    token_entry = StaffPasswordToken(
        token=token,
        email=email,
        first_name=first_name,
        last_name=last_name,
        school_id=school_id,
        form=form_class,
        picture_data=picture_data,
        created=datetime.utcnow()
    )
    db.session.add(token_entry)
    db.session.commit()

    # Determine base URL depending on environment
    if "127.0.0.1" in request.host_url or "localhost" in request.host_url:
        base_url = "http://127.0.0.1:5000/"
    else:
        base_url = "https://servesync.burnside.school.nz/"

    setup_link = url_for('staff.set_staff_password', token=token, _external=True) # noqa
    setup_link = setup_link.replace(request.host_url, base_url)

    # Compose improved HTML email with green button and nicer layout
    html_content = f"""
    <html>
    <body style="background:#f7fafc;padding:0;margin:0;">
      <div style="max-width:480px;margin:40px auto;background:#fff;border-radius:10px;box-shadow:0 2px 12px rgba(0,0,0,0.06);padding:32px 28px 28px 28px;border:1px solid #e3e7ea;font-family:'Segoe UI',Arial,sans-serif;">
        <div style="text-align:center;">
          <h2 style="color:#197d3a;margin-bottom:8px;">Welcome to ServeSync!</h2>
        </div>
        <p style="font-size:16px;color:#222;margin-bottom:14px;">Hello <b>{first_name} {last_name}</b>,</p>
        <p style="font-size:15px;color:#333;margin-bottom:26px;">
          Your staff account has been created. Please set your password by clicking the button below:
        </p>
        <div style="text-align:center;margin-bottom:24px;">
          <a href="{setup_link}" style="display:inline-block;background:#43a047;color:#fff;padding:14px 32px;text-decoration:none;border-radius:6px;font-size:17px;font-weight:600;box-shadow:0 2px 8px rgba(67,160,71,0.08);transition:background 0.2s;">Set Your Password</a>
        </div>
        <div style="background:#f1f3f6;padding:12px 16px;border-radius:6px;font-size:13px;color:#555;margin-bottom:18px;">
          If the button above doesn't work, copy and paste this link into your browser:<br>
          <a href="{setup_link}" style="color:#1976d2;word-break:break-all;">{setup_link}</a>
        </div>
        <p style="font-size:14px;color:#888;margin-top:20px;">
          Thank you,<br>
          <span style="color:#197d3a;font-weight:500;">The ServeSync Team</span>
        </p>
      </div>
    </body>
    </html>
    """  # noqa: E501
    # Send real email
    send_email(email, "Set up your ServeSync password", html_content)
    flash('Staff added! Password setup email sent.', 'success')
    return redirect(url_for('admin.adminpage'))


# --- Review Student Route ---
@admin_bp.route('/review-student/<user_id>')
def review_student(user_id):
    student = User.query.filter_by(school_id=user_id).first()
    if not student:
        flash("Student not found.", "admin-error")
        return redirect(url_for('admin.adminpage'))
    # You can add more details here as needed
    return render_template('review_student.html', student=student)


# --- Admin Download All Students as CSV ---
@admin_bp.route('/admin/download/students/csv')
def admin_download_students_csv():

    students = User.query.filter_by(role=1).all()  # Assuming role=1 is student

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Admin Export - All Student Data"])
    writer.writerow([])
    writer.writerow([
        'School ID', 'First Name', 'Last Name',
        'Email', 'Form', 'Role', 'Award',
        'Total Hours', 'Last Service Date'
    ])

    for student in students:
        award_name = "Not achieved"
        awards = Award.query.order_by(Award.threshold.desc()).all()
        for award in awards:
            if (student.hours or 0) >= award.threshold:
                award_name = award.name
                break

        logs = ServiceHour.query.filter_by(user_id=student.school_id, status=1).all() # noqa
        total_hours = sum(log.hours for log in logs)
        last_log_date = max((log.date for log in logs), default='N/A')

        role_name = db.session.execute(
            db.text("SELECT name FROM user_role WHERE id = :id"), {"id": student.role} # noqa
        ).scalar()

        writer.writerow([
            student.school_id,
            student.first_name,
            student.last_name,
            student.email,
            student.form,
            role_name or "N/A",
            award_name,
            total_hours,
            last_log_date
        ])

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=all_students_report.csv" # noqa
    response.headers["Content-Type"] = "text/csv"
    return response


# --- Admin Download All Students as Excel ---
@admin_bp.route('/admin/download/students/excel')
def admin_download_students_excel():

    students = User.query.filter_by(role=1).all()
    awards = Award.query.order_by(Award.threshold.desc()).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Student Data"
    ws.append(["Admin Export - All Student Data"])
    ws.append([])
    ws.append([
        'School ID', 'First Name', 'Last Name', 'Email', 'Form', 'Role', 'Award', # noqa
        'Total Hours', 'Last Service Date'
    ])

    for student in students:
        award_name = "Not achieved"
        for award in awards:
            if (student.hours or 0) >= award.threshold:
                award_name = award.name
                break

        logs = ServiceHour.query.filter_by(user_id=student.school_id, status=1).all() # noqa
        total_hours = sum(log.hours for log in logs)
        last_log_date = max((log.date for log in logs), default='N/A')

        role_name = db.session.execute(
            db.text("SELECT name FROM user_role WHERE id = :id"), {"id": student.role} # noqa
        ).scalar()

        ws.append([
            student.school_id,
            student.first_name,
            student.last_name,
            student.email,
            student.form,
            role_name or "N/A",
            award_name,
            total_hours,
            last_log_date
        ])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=all_students_report.xlsx" # noqa
    response.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" # noqa
    return response


# --- Admin Download All Students as PDF ---
@admin_bp.route('/admin/download/students/pdf')
def admin_download_students_pdf():

    students = User.query.filter_by(role=1).all()
    awards = Award.query.order_by(Award.threshold.desc()).all()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Admin Export - All Student Data", ln=True, align='C') # noqa
    pdf.ln(10)

    for student in students:
        award_name = "Not achieved"
        for award in awards:
            if (student.hours or 0) >= award.threshold:
                award_name = award.name
                break

        logs = ServiceHour.query.filter_by(user_id=student.school_id, status=1).all() # noqa
        total_hours = sum(log.hours for log in logs)
        last_log_date = max((log.date for log in logs), default='N/A')

        role_name = db.session.execute(
            db.text("SELECT name FROM user_role WHERE id = :id"), {"id": student.role} # noqa
        ).scalar()

        pdf.cell(200, 10, txt=f"{student.first_name} {student.last_name} ({student.school_id})", ln=True) # noqa
        pdf.cell(200, 10, txt=f"Email: {student.email}, Form: {student.form}, Role: {role_name or 'N/A'}", ln=True) # noqa
        pdf.cell(200, 10, txt=f"Award: {award_name}, Total Hours: {total_hours}, Last Submission: {last_log_date}", ln=True) # noqa
        pdf.ln(5)

    response = make_response(pdf.output(dest='S').encode('latin-1'))
    response.headers["Content-Disposition"] = "attachment; filename=all_students_report.pdf" # noqa
    response.headers["Content-Type"] = "application/pdf"
    return response
