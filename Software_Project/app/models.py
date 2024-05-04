from sqlalchemy import ForeignKeyConstraint, UniqueConstraint
from app import db
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from sqlalchemy.dialects.postgresql import UUID
import uuid


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
    journey = db.relationship('JourneyRecord', backref='users', lazy=True)
    sent_requests = db.relationship('FriendRequest', foreign_keys='FriendRequest.requester_id', backref='requester', lazy='dynamic')
    received_requests = db.relationship('FriendRequest', foreign_keys='FriendRequest.requestee_id', backref='requestee', lazy='dynamic')
    friends = db.relationship('User', secondary=friends,
                              primaryjoin=(friends.c.user_id == id),
                              secondaryjoin=(friends.c.friend_id == id),
                              backref=db.backref('added_friends', lazy='dynamic'), lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class FriendRequest(db.Model):
    __tablename__ = 'friend_requests'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    requester_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    requestee_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(10), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class JourneyRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    origin= db.Column(db.String(100))
    destination = db.Column(db.String(100))
    waypoints = db.Column(db.String(500)) # Stored as a JSON string
    time_taken = db.Column(db.Integer) # Assume time is in minutes

    def __repr__(self):
        return f"<Journey {self.origin} to {self.destination}>"



class SubscriptionPlan(db.Model):
    __tablename__ = 'subscription_plan'
    id = db.Column(db.Integer, primary_key=True)
    plan_name = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    duration = db.Column(db.String(20), nullable=False)
    expiration_date = db.Column(db.Date, nullable=True)
    next_plan_id = db.Column(db.Integer, db.ForeignKey('subscription_plan.id', name='fk_next_plan_id'), nullable=True)
    users = db.relationship('User', backref='subscription_plan', lazy=True)
    stripe_price_id = db.Column(db.String(255))
    stripe_customer_id = db.Column(db.String(255), nullable=True, unique=True)
    __table_args__ = (ForeignKeyConstraint(['next_plan_id'], ['subscription_plan.id'], name='fk_next_plan_id'),)

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
