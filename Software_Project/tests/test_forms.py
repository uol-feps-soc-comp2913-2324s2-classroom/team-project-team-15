import pytest
from app import app, db
from app.models import User

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    client = app.test_client()

    with app.app_context():
        db.session.begin_nested()  # Start a nested transaction if supported

    yield client

    # Teardown after test
    with app.app_context():
        db.session.rollback()


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

def test_choose_subscription(client):
    # Assuming a user "testuser" exists; otherwise, create one first.
    client.post('/register', data={
        'username': 'testuser2',
        'firstName': 'Test2',
        'surName': 'User2',
        'dob': '1990-01-02',
        'email': 'test2@example.com',
        'phoneNumber': '0987654321',
        'password': 'StrongPassword123!',
        'confirm_password': 'StrongPassword123!'
    })

    # Log in as the user before choosing a subscription
    client.post('/login', data={
        'username': 'testuser2',
        'password': 'StrongPassword123!',
    }, follow_redirects=True)

    # Choose a subscription plan
    response = client.post('/choose_subscription', data={
        'subscription_plan': 'monthly',
    }, follow_redirects=True)

    assert response.status_code == 200  # Or 302 if it redirects to another page
    
    # Verify the subscription plan was set correctly
    with app.app_context():
        user = User.query.filter_by(username='testuser2').first()
        assert user.subscription_plan_id is not None