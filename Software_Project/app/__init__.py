from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from flask_migrate import Migrate


app = Flask(__name__)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate= Migrate(app,db)

from app import views
from app.models import User
csrf = CSRFProtect(app)
