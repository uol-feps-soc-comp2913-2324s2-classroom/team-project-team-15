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


def test_register_user(client):
    response = client.post('/register', data={
        'username': 'testuser',
        'firstName': 'Test',
        'surName': 'User',
        'dob': '1990-01-01',
        'email': 'test@example.com',
        'phoneNumber': '1234567890',
        'password': 'StrongPassword123!',
        'confirm_password': 'StrongPassword123!'
    })
    assert response.status_code == 200

    with app.app_context():
        user = User.query.filter_by(username='testuser').first()
        assert user is not None
        assert user.email == 'test@example.com'


def test_login_successful(client):
    # Attempt to log in with the correct credentials
    login_response = client.post('/login', data={
        'username': 'testuser',
        'password': 'StrongPassword123!',
    }, follow_redirects=True)
    
    assert login_response.status_code == 200

def test_login_unsuccessful(client):
    # Attempt to log in with incorrect credentials
    login_response = client.post('/login', data={
        'username': 'testuser',
        'password': 'WrongPassword!',
    }, follow_redirects=True)
    
    assert login_response.status_code == 200
    assert b'Invalid username or password' in login_response.data
