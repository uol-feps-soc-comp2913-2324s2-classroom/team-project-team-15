from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///trial.db'
app.config['SECRET_KEY'] = '24'
db = SQLAlchemy(app)

from app import views
csrf = CSRFProtect(app)
