import re

from flask import flash, render_template, request, send_from_directory

from plotting import get_plot
from models import *
from app import app


def validate(ex):
    ex = ex.rstrip()
    return bool(re.match(r"^[A-Za-z0-9_-]*$", ex))


@app.route('/add', methods=['GET','POST'])
def add():
    error = None
    results = {}
    if request.method == 'GET':
        results['users'] = GHUser.query.filter(GHUser.plot_filename != None)
        return render_template('index.html', **results)
    username = request.form.get('name_field').strip()
    if not validate(username):
        flash('Username is not valid', 'danger')
        results['users'] = GHUser.query.filter(GHUser.plot_filename != None)
        return render_template('index.html', **results)
    plot_filename = query_user(username)
    if not plot_filename:
        _ = get_plot(username)
    results['users'] = GHUser.query.filter(GHUser.plot_filename != None)
    return render_template('index.html', **results)


@app.route("/", methods=['GET','POST'])
def index():
    results = {}
    if request.method == 'GET':
        results['users'] = GHUser.query.filter(GHUser.plot_filename != None)
        return render_template('index.html', **results)
    return render_template('index.html', **results)


@app.route('/uploads/<filename>')
def uploads(filename):
    print(filename)
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)