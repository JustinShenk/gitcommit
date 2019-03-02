import re

from flask import flash, render_template, request, send_from_directory, url_for, redirect

from plotting import get_plot
from models import *
from app import app, db

def validate(ex):
    ex = ex.rstrip()
    if len(ex) > 39:
        return False
    return bool(re.match(r"^[A-Za-z0-9_-]*$", ex))


@app.route('/add', methods=['GET','POST'])
def add():
    error = None
    if request.method == 'GET':
        return redirect(url_for('index'))

    username = request.form.get('name_field').strip()
    if not validate(username):
        flash('Username is not valid', 'danger')
        return redirect(url_for('index'))

    plot_filename = query_user(username)
    if plot_filename:
        # Already in database
        flash('User is already added.','info')
    else:
        plot_filename = get_plot(username)
        db.session.commit()
        if plot_filename is None:
            flash(f'User {username} not found on GitHub.', 'danger')
    return redirect(url_for('index'))


@app.route("/", methods=['GET','POST'])
def index():
    results={}
    users = GHUser.query.filter(GHUser.plot_filename != None)
    return render_template('index.html', users=users)


@app.route('/uploads/<filename>')
def uploads(filename):
    print(filename)
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
