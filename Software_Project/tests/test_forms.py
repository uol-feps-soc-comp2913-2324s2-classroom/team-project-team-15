import pytest
from app import app, db
from app.models import User, SubscriptionPlan

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    test_client = app.test_client()

    with app.app_context():
        db.create_all()  # Create database schema including SubscriptionPlan table

        # Create test subscription plans
        db.session.add(SubscriptionPlan(plan_name='monthly', price=12.99, duration='1 month'))
        db.session.add(SubscriptionPlan(plan_name='annually', price=99.99, duration='12 months'))
        db.session.commit()

        db.session.begin_nested()  # Start a nested transaction

    yield test_client

    # Teardown after test
    with app.app_context():
        db.session.rollback()
        db.session.close()

