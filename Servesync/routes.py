from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify, make_response
import base64
from flask_sqlalchemy import SQLAlchemy
from fpdf import FPDF
from openpyxl import Workbook
from sqlalchemy import MetaData, Table, func
from datetime import datetime
from collections import defaultdict
import os
import csv
import io
import pytz
import json
from werkzeug.security import generate_password_hash, check_password_hash
from flask_dance.contrib.google import make_google_blueprint, google
import pandas as pd
import requests
from werkzeug.utils import secure_filename


app = Flask(__name__, template_folder='templates')
app.secret_key = 'your_secret_key'

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # Allow HTTP for local dev

google_bp = make_google_blueprint(
    client_id="26915404481-5bcada6j7otusedjet7p5g93pn08rp69.apps.googleusercontent.com",
    client_secret="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",
    redirect_url="http://127.0.0.1:5000/google_login/callback",  # when live use https://zeyad327.pythonanywhere.com/google_login/callback
    scope=[
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile"
    ]
)

app.register_blueprint(google_bp, url_prefix="/google_login")
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

        # If password is hashed, check with check_password_hash
        # If it's plain text, check directly
        if user.password.startswith('pbkdf2') and check_password_hash(user.password, password):
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
        # If password is not hashed, compare directly
        elif user.password == password:
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

    return redirect(url_for('homepage'))


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


@app.route("/google_login/callback")
def google_login_callback():
    if not google.authorized:
        return redirect(url_for("google.login"))

    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        flash("Failed to fetch user info from Google.")
        return redirect(url_for("homepage"))

    user_info = resp.json()
    email = user_info["email"]
    name = user_info["name"]

    user = User.query.filter_by(email=email).first()

    if user:
        session['username'] = user.school_id
        session['name'] = f"{user.first_name} {user.last_name}"
        role_name = db.session.execute(
            db.text("SELECT name FROM user_role WHERE id = :id"), {"id": user.role}
        ).scalar()
        session['role'] = role_name
        if role_name.lower() == 'staff':
            return redirect(url_for('staffpage'))
        elif role_name.lower() == 'admin':
            return redirect(url_for('adminpage'))
        else:
            return redirect(url_for('studentpage'))
    else:
        flash("No account found for this Google email.")
        return redirect(url_for("homepage"))


@app.route('/account')
def accountpage():
    return render_template('account.html')


@app.route('/log')
def logpage():
    # Get all users who have the 'staff' role (role = 2)
    staff_members = User.query.filter_by(role=2).all()

    # Get all groups from the group table
    groups = Group.query.all()

    return render_template('student/log.html', staff_members=staff_members, groups=groups)


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
    top_student_name = f"{top_student.first_name} {top_student.last_name}" if top_student else "N/A"
    top_student_hours = top_student.hours if top_student else 0

    if top_student and top_student.picture:
        top_student_picture = f"data:image/jpeg;base64,{base64.b64encode(top_student.picture).decode('utf-8')}"
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
        except:
            continue
    sorted_months = sorted(monthly_counts.items(), key=lambda x: datetime.strptime(x[0], "%b %Y"))
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
            ((award.name, award.colour) for award in awards if (student.hours or 0) >= award.threshold),
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
        all_staff=staff_dicts, current_admins=admin_dicts
    )


@app.route('/add-student', methods=['POST'])
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

    return redirect(url_for('adminpage'))


@app.route('/bulk-upload-students', methods=['POST'])
def bulk_upload_students():
    file = request.files.get('bulk_file')
    if not file:
        flash('No file uploaded', 'danger')
        return redirect(url_for('adminpage'))

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
            flash('Unsupported file format. Please upload a .csv or .xlsx file.', 'danger')
            return redirect(url_for('adminpage'))
    except Exception as e:
        flash(f'Error reading file: {e}', 'danger')
        return redirect(url_for('adminpage'))

    # Normalize and validate required columns (case-insensitive)
    # Step 1: lowercase and strip all column headers
    df.columns = [col.strip().lower() for col in df.columns]

    # Step 2: Check for all required columns
    required_cols = ['first name', 'last name', 'student id', 'tutor', 'password']
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        flash(f"Missing required columns: {[col.title() for col in missing]}", "danger")
        return redirect(url_for('adminpage'))

    # Step 3: Rename the columns for consistent access later
    rename_map = {
        'first name': 'First Name',
        'last name': 'Last Name',
        'student id': 'Student ID',
        'tutor': 'Tutor',
        'password': 'Password',
        'image': 'Image'  # Optional, handled if present
    }
    df.rename(columns=rename_map, inplace=True)

    added_count = 0

    for _, row in df.iterrows():
        try:
            first_name = row['First Name']
            last_name = row['Last Name']
            school_id = row['Student ID']
            form_class = row['Tutor']
            raw_pass = row['Password']
            image_val = row.get('Image', None)

            # Hash the password
            hashed_password = generate_password_hash(raw_pass, method='pbkdf2:sha256')

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
                continue  # or optionally log/flash a warning about duplicate

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

    return redirect(url_for('adminpage'))


@app.route('/bulk-upload-staff', methods=['POST'])
def bulk_upload_staff():
    file = request.files.get('bulk_file')
    if not file:
        flash('No file uploaded', 'danger')
        return redirect(url_for('adminpage'))

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
            flash('Unsupported file format. Please upload a .csv or .xlsx file.', 'danger')
            return redirect(url_for('adminpage'))
    except Exception as e:
        flash(f'Error reading file: {e}', 'danger')
        return redirect(url_for('adminpage'))

    # Normalize and validate required columns (case-insensitive)
    # Step 1: lowercase and strip all column headers
    df.columns = [col.strip().lower() for col in df.columns]

    # Step 2: Check for all required columns
    required_cols = ['first name', 'last name', 'student id', 'tutor', 'password']
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        flash(f"Missing required columns: {[col.title() for col in missing]}", "danger")
        return redirect(url_for('adminpage'))

    # Step 3: Rename the columns for consistent access later
    rename_map = {
        'first name': 'First Name',
        'last name': 'Last Name',
        'student id': 'Student ID',
        'tutor': 'Tutor',
        'password': 'Password',
        'image': 'Image'  # Optional, handled if present
    }
    df.rename(columns=rename_map, inplace=True)

    added_count = 0

    for _, row in df.iterrows():
        try:
            first_name = row['First Name']
            last_name = row['Last Name']
            school_id = row['Student ID']
            form_class = row['Tutor']
            raw_pass = row['Password']
            image_val = row.get('Image', None)

            # Hash the password
            hashed_password = generate_password_hash(raw_pass, method='pbkdf2:sha256')

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

            # Build staff email
            email = f"{school_id}@burnside.school.nz"

            if User.query.filter_by(email=email).first():
                continue

            # Create and stage the staff
            new_staff = User(
                first_name=first_name,
                last_name=last_name,
                school_id=school_id,
                form=form_class,
                password=hashed_password,
                role=2,
                picture=picture_data,
                hours=None,
                email=email
            )
            db.session.add(new_staff)
            added_count += 1

        except KeyError as ke:
            flash(f"Missing column in row: {ke}", "warning")
        except Exception as err:
            flash(f"Error processing a row: {err}", "warning")

    # Commit all new users
    try:
        db.session.commit()
        flash(f'{added_count} Staff members added successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error committing to database: {e}', 'danger')

    return redirect(url_for('adminpage'))


@app.route('/remove-students', methods=['POST'])
def remove_student():
    student_id = request.form.get('student_id')
    print("🧪 Form student_id received:", student_id)

    student = User.query.filter_by(school_id=student_id).first()

    if student:
        ServiceHour.query.filter_by(user_id=student.school_id).delete()
        db.session.delete(student)
        db.session.commit()
        flash("Student successfully removed.", "success")
    else:
        flash("Student not found.", "error")

    return redirect(url_for('adminpage'))


@app.route('/add-staff', methods=['POST'])
def add_staff():
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
        role=2,
        hours=None,  # or any default you want
        picture=picture_data,
        email=email
    )

    try:
        db.session.add(new_student)
        db.session.commit()
        flash('Staff added successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding Staff: {e}', 'danger')

    return redirect(url_for('adminpage'))


# --- Review Student Route ---
@app.route('/review-student/<user_id>')
def review_student(user_id):
    # Placeholder: implement review logic for student with user_id
    student = User.query.filter_by(school_id=user_id).first()
    if not student:
        flash("Student not found.", "admin-error")
        return redirect(url_for('adminpage'))
    # You can add more details here as needed
    return render_template('review_student.html', student=student)


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

    approved_logs = ServiceHour.query.filter_by(user_id=user.school_id, status=1).all()
    user_hours = sum(log.hours for log in approved_logs) if approved_logs else 0
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
        'staff/staff.html',
        greeting=greeting,
        recent_submissions=recent_logs,
        pending_count=pending_count,
        attached_groups=attached_groups,
        approved_hours_this_year=approved_hours_this_year
    )


@app.route('/activity-history')
def activity_history():
    return render_template('student/activity.html')


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
                'picture_url': picture_url})

            # Count the status categories
            if log.status == 1:
                accepted_count += 1
            elif log.status == 2:
                pending_count += 1
            elif log.status == 3:
                rejected_count += 1

    # Sort by newest first using original log.date format
    submission_data.sort(key=lambda x: datetime.strptime(x["date"], "%b %d, %Y"), reverse=True)

    return render_template('staff/submissions.html', submissions=submission_data,
                           accepted_count=accepted_count,
                           pending_count=pending_count,
                           rejected_count=rejected_count)


@app.route('/about')
def aboutpage():
    return render_template('about.html')


# 404 page to display when a page is not found
# helps re-direct users back to home page
@app.errorhandler(404) # noqa:
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500) # noqa:
def internal_server_error(e):
    return render_template('500.html'), 500


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


# --- Admin Download All Students as CSV ---
@app.route('/admin/download/students/csv')
def admin_download_students_csv():

    students = User.query.filter_by(role=1).all()  # Assuming role=1 is student

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Admin Export - All Student Data"])
    writer.writerow([])
    writer.writerow([
        'School ID', 'First Name', 'Last Name', 'Email', 'Form', 'Role', 'Award',
        'Total Hours', 'Last Service Date'
    ])

    for student in students:
        award_name = "Not achieved"
        awards = Award.query.order_by(Award.threshold.desc()).all()
        for award in awards:
            if (student.hours or 0) >= award.threshold:
                award_name = award.name
                break

        logs = ServiceHour.query.filter_by(user_id=student.school_id, status=1).all()
        total_hours = sum(log.hours for log in logs)
        last_log_date = max((log.date for log in logs), default='N/A')

        role_name = db.session.execute(
            db.text("SELECT name FROM user_role WHERE id = :id"), {"id": student.role}
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
    response.headers["Content-Disposition"] = "attachment; filename=all_students_report.csv"
    response.headers["Content-Type"] = "text/csv"
    return response


# --- Admin Download All Students as Excel ---
@app.route('/admin/download/students/excel')
def admin_download_students_excel():

    students = User.query.filter_by(role=1).all()
    awards = Award.query.order_by(Award.threshold.desc()).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Student Data"
    ws.append(["Admin Export - All Student Data"])
    ws.append([])
    ws.append([
        'School ID', 'First Name', 'Last Name', 'Email', 'Form', 'Role', 'Award',
        'Total Hours', 'Last Service Date'
    ])

    for student in students:
        award_name = "Not achieved"
        for award in awards:
            if (student.hours or 0) >= award.threshold:
                award_name = award.name
                break

        logs = ServiceHour.query.filter_by(user_id=student.school_id, status=1).all()
        total_hours = sum(log.hours for log in logs)
        last_log_date = max((log.date for log in logs), default='N/A')

        role_name = db.session.execute(
            db.text("SELECT name FROM user_role WHERE id = :id"), {"id": student.role}
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
    response.headers["Content-Disposition"] = "attachment; filename=all_students_report.xlsx"
    response.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return response


# --- Admin Download All Students as PDF ---
@app.route('/admin/download/students/pdf')
def admin_download_students_pdf():

    students = User.query.filter_by(role=1).all()
    awards = Award.query.order_by(Award.threshold.desc()).all()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Admin Export - All Student Data", ln=True, align='C')
    pdf.ln(10)

    for student in students:
        award_name = "Not achieved"
        for award in awards:
            if (student.hours or 0) >= award.threshold:
                award_name = award.name
                break

        logs = ServiceHour.query.filter_by(user_id=student.school_id, status=1).all()
        total_hours = sum(log.hours for log in logs)
        last_log_date = max((log.date for log in logs), default='N/A')

        role_name = db.session.execute(
            db.text("SELECT name FROM user_role WHERE id = :id"), {"id": student.role}
        ).scalar()

        pdf.cell(200, 10, txt=f"{student.first_name} {student.last_name} ({student.school_id})", ln=True)
        pdf.cell(200, 10, txt=f"Email: {student.email}, Form: {student.form}, Role: {role_name or 'N/A'}", ln=True)
        pdf.cell(200, 10, txt=f"Award: {award_name}, Total Hours: {total_hours}, Last Submission: {last_log_date}", ln=True)
        pdf.ln(5)

    response = make_response(pdf.output(dest='S').encode('latin-1'))
    response.headers["Content-Disposition"] = "attachment; filename=all_students_report.pdf"
    response.headers["Content-Type"] = "application/pdf"
    return response


if __name__ == "__main__":
    app.run(debug=True)