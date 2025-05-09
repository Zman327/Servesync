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
        # Use check_password_hash to verify the password
        if check_password_hash(user.password, password):
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