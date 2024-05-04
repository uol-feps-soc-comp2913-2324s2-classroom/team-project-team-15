from datetime import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from flask_migrate import Migrate
from flask_login import LoginManager
import stripe
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
stripe.api_key = "sk_test_yourSecretKeyHere"

app = Flask(__name__ ,static_url_path='/static')
login_manager = LoginManager(app)
login_manager.login_view = 'login'
app.config.from_object('config')
db = SQLAlchemy(app)
migrate= Migrate(app,db)
CORS(app)
csrf = CSRFProtect(app)

# Scheduler setup
scheduler = BackgroundScheduler(daemon=True)

def check_expired_subscriptions():
    with app.app_context():  # Ensure database context is available
        today = datetime.today().date()
        from app.models import User,SubscriptionPlan  # Import here to avoid circular import
        users = User.query.all()
        for user in users:
            if user.subscription_plan and user.subscription_plan.expiration_date < today:
                if user.subscription_plan.next_plan_id:
                    user.subscription_plan_id = user.subscription_plan.next_plan_id
                    user.subscription_plan.next_plan_id = None
                else:
                    user.subscription_plan_id = None
                    db.session.delete(user.subscription_plan)
            db.session.commit()

scheduler.add_job(func=check_expired_subscriptions, trigger='interval', hours=24)
scheduler.start()




from app import views
from app.models import User
@app.before_request
def start_scheduler():
    if not scheduler.running:
        scheduler.start()

@app.teardown_appcontext
def shutdown_scheduler(response_or_exc):
    if scheduler.running:
        scheduler.shutdown()
    return response_or_exc

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
