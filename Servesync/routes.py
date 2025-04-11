from flask import Flask, render_template # noqa:

app = Flask(__name__)
app.secret_key = 'your_secret_key'


@app.route('/home')
def homepage():
    return render_template('index.html')


@app.route('/student.dashboard')
def studentpage():
    return render_template('student.html')

# 404 page to display when a page is not found
# helps re-direct users back to home page
@app.errorhandler(404) # noqa:
def page_not_found(e):
    return render_template('404.html'), 404


@app.route('/login', methods=['POST'])
def login():
    return render_template('/student.dashboard')


if __name__ == "__main__":
    app.run(debug=True)
