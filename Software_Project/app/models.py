from app import db
from sqlalchemy import Column, Integer, String, Date,ForeignKey,Text, DateTime, Float
from sqlalchemy.orm import relationship
from flask_login import UserMixin


# friends = db.Table('friends',
#     Column('user_id', Integer, ForeignKey('user.id'), primary_key=True),
#     Column('friend_id', Integer, ForeignKey('user.id'), primary_key=True)
# )


class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    firstname = Column(String(50), nullable=False)
    surname = Column(String(50), nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    phone_number = Column(String(15), unique=True, nullable=False)
    dob = Column(Date, nullable=False)
    password = Column(String(60), nullable=False)
    # friends = db.relationship(
    #     'User', secondary=friends,
    #     primaryjoin=(friends.c.user_id == id),
    #     secondaryjoin=(friends.c.friend_id == id),
    #     backref=db.backref('friends', lazy='dynamic'), lazy='dynamic'
    # )
    #subscription_plan_id = Column(Integer, ForeignKey('subscription_plan.id'))
    #journeys = relationship('Journey', backref='user', lazy=True)

    def __repr__(self):
        return f"User(id='{self.id}', username='{self.username}', email='{self.email}', phone_number='{self.phone_number}', dob='{self.dob}')"
    
# class Journey(db.Model):
#     id = Column(Integer, primary_key=True)
#     journey_name = Column(String(100), nullable=False)
#     start_location = Column(String(100), nullable=False)
#     end_location = Column(String(100), nullable=False)
#     start_time = Column(DateTime, nullable=False)
#     end_time = Column(DateTime, nullable=False)
#     gps_data = Column(Text)
#     user_id = Column(Integer, ForeignKey('user.id'), nullable=False)

# class SubscriptionPlan(db.Model):
#     id = Column(Integer, primary_key=True)
#     plan_name = Column(String(50), nullable=False)
#     price = Column(Float, nullable=False)
#     duration = Column(String(20), nullable=False)  # Weekly, Monthly, Yearly

# class Payment(db.Model):
#     id = Column(Integer, primary_key=True)
#     amount = Column(Float, nullable=False)
#     payment_date = Column(DateTime, nullable=False)
#     payment_status = Column(String(20), nullable=False)  # Paid, Pending
#     user_id = Column(Integer, ForeignKey('user.id'), nullable=False)

# class RevenueEstimate(db.Model):
#     id = Column(Integer, primary_key=True)
#     date = Column(Date, nullable=False)
#     total_revenue = Column(Float, nullable=False)
#     calculation_details = Column(Text)