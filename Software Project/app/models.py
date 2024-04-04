from app import db
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from sqlalchemy.ext.hybrid import hybrid_property


friends = db.Table('friends',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('friend_id', db.Integer, db.ForeignKey('users.id'), primary_key=True)
)

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    firstname = db.Column(db.String(50), nullable=False)
    surname = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone_number = db.Column(db.String(15), unique=True, nullable=False)
    dob = db.Column(db.Date, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    subscription_plan_id = db.Column(db.Integer, db.ForeignKey('subscription_plan.id'))
    subscription_start_date = db.Column(db.Date, nullable=True)
    stripe_customer_id = db.Column(db.String(255), nullable=True, unique=True)
    journeys = db.relationship('Journey', backref='users', lazy=True)
    friends = db.relationship('User', secondary=friends,
                              primaryjoin=(friends.c.user_id == id),
                              secondaryjoin=(friends.c.friend_id == id),
                              backref=db.backref('added_friends', lazy='dynamic'), lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Journey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    journey_name = db.Column(db.String(100), nullable=False)
    start_location = db.Column(db.String(100), nullable=False)
    end_location = db.Column(db.String(100), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    mode_of_transport = db.Column(db.String(50), nullable=False)
    distance_traveled = db.Column(db.Float, nullable=True)  #
    endpoint_location = db.Column(db.String(100), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    @hybrid_property
    def time_taken(self):
        return self.end_time - self.start_time

    @hybrid_property
    def average_speed(self):
        # Ensure distance_traveled is not zero to avoid division by zero
        if self.distance_traveled and self.time_taken.total_seconds() > 0:
            return self.distance_traveled / (self.time_taken.total_seconds() / 3600)  # Speed in km/h or mph
        return 0

    @hybrid_property
    def status(self):
        # Assuming end_location and endpoint_location are comparable strings; you might need more sophisticated comparison based on actual GPS coordinates
        return "complete" if self.end_location == self.endpoint_location else "incomplete"

class SubscriptionPlan(db.Model):
    __tablename__ = 'subscription_plan'
    id = db.Column(db.Integer, primary_key=True)
    plan_name = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    duration = db.Column(db.String(20), nullable=False)
    expiration_date = db.Column(db.Date, nullable=True)
    users = db.relationship('User', backref='subscription_plan', lazy=True)
    stripe_price_id = db.Column(db.String(255))
    stripe_customer_id = db.Column(db.String(255), nullable=True, unique=True)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.DateTime, nullable=False)
    payment_status = db.Column(db.String(20), nullable=False)  # Paid, Pending
    stripe_session_id= db.Column(db.String(255),nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user= db.relationship('User',backref=db.backref('payments',lazy=True))

class RevenueEstimate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    total_revenue = db.Column(db.Float, nullable=False)
    calculation_details = db.Column(db.Text)

