from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import os
from sqlalchemy import MetaData, Table
from datetime import datetime


app = Flask(__name__)
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


@app.route('/home')
def homepage():
    return render_template('index.html')


@app.route('/student.dashboard')
def studentpage():
    hour = datetime.now().hour
    if hour < 12:
        greeting = "Good Morning"
    elif hour < 18:
        greeting = "Good Afternoon"
    else:
        greeting = "Good Evening"
    return render_template('student.html', greeting=greeting)

# 404 page to display when a page is not found
# helps re-direct users back to home page
@app.errorhandler(404) # noqa:
def page_not_found(e):
    return render_template('404.html'), 404


@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']  # assuming username is the school_id
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
            print(f"Session set: {session}")
            flash('Login successful!')
            return redirect(url_for('studentpage'))  # Redirect to /student.dashboard
        else:
            flash('Incorrect password!')
    else:
        flash('No user found with that username!')
   
    return redirect(url_for('homepage'))  # Redirect back to the homepage for another attempt

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('homepage'))


if __name__ == "__main__":
    app.run(debug=True)
