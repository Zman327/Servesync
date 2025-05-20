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
        all_staff=staff_dicts,
        current_admins=admin_dicts,
        submission_status_data=json.dumps({
            "Approved": accepted_count,
            "Pending": pending_count,
            "Rejected": rejected_count
        })
    )


@app.route('/promote-to-admin', methods=['POST'])
def promote_to_admin():
    data = request.get_json()
    school_id = data.get('school_id')
    user = User.query.filter_by(school_id=school_id).first()

    if user and user.role != 3:
        user.role = 3  # Promote to admin
        db.session.commit()
        return jsonify(success=True, message=f"{user.first_name} {user.last_name} is now an admin.")

    return jsonify(success=False, message="User not found or already an admin."), 400


@app.route('/admin/remove', methods=['POST'])
def remove_admin():
    data = request.get_json()
    school_id = data.get('school_id')
    user = User.query.filter_by(school_id=school_id).first()

    if user and user.role == 3:
        user.role = 2
        db.session.commit()
        return jsonify({'status': 'success', 'message': f"{user.first_name} {user.last_name} removed as admin."})
    return jsonify({'status': 'error', 'message': 'User not found or not an admin.'}), 400


@app.route('/api/current_admins')
def api_current_admins():
    admins = User.query.filter_by(role=3).all()
    result = [{
        'name': f"{a.first_name} {a.last_name}",
        'school_id': a.school_id
    } for a in admins]
    return jsonify(result)


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
    student = User.query.filter_by(school_id=user_id).first()
    if not student:
        flash("Student not found.", "admin-error")
        return redirect(url_for('adminpage'))
    # You can add more details here as needed
    return render_template('review_student.html', student=student)


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