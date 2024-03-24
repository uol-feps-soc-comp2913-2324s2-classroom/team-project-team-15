from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from flask_migrate import Migrate
from flask_login import LoginManager
import stripe
from flask_cors import CORS

stripe.api_key = "sk_test_yourSecretKeyHere"

app = Flask(__name__ ,static_url_path='/static')
login_manager = LoginManager(app)
login_manager.login_view = 'login'
app.config.from_object('config')
db = SQLAlchemy(app)
migrate= Migrate(app,db)
CORS(app)

from app import views
from app.models import User
csrf = CSRFProtect(app)
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))