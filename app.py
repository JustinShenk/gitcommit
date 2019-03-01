import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from config import Config

app = Flask(__name__)

app.config.from_object(Config)
app.config['UPLOAD_FOLDER'] = os.path.join(app.instance_path, 'uploads')
app.secret_key = 'secret_key_for_app'

db = SQLAlchemy(app)

if __name__ == '__main__':
    from views import *

    # ensure the instance folder exists
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    app.run(host='0.0.0.0', debug=False)

# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'

# def get_activity(username):
#     """Plot activity for Github user"""
#     fig = plot_activity(username)
#     output = io.BytesIO()
#     FigureCanvas(fig).print_png(output)
#     return Response(output.getvalue(), mimetype='image/png')
