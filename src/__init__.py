from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.update(DEBUG = True)

db = SQLAlchemy(app)