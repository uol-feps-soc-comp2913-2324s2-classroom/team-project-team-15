import pytest
from app import app, db
from app.models import User
from werkzeug.security import check_password_hash

def delete_test_data():
    with app.app_context():
        # Delete the user created during the tests
        User.query.filter(User.email == 'test@example.com').delete()
        # Commit the changes to the database
        db.session.commit()

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    client = app.test_client()

    with app.app_context():
        db.create_all()

    yield client
     # After the test runs, clean up the test data
    delete_test_data()




def test_register_user(client):
    # Simulate form submission
    response = client.post('/register', data={
        'username': 'testuser',
        'firstName': 'Test',
        'surName': 'User',
        'dob': '1990-01-01',
        'email': 'test@example.com',
        'phoneNumber': '1234567890',
        'password': 'StrongPassword123!',
        'confirm_password': 'StrongPassword123!'
    }, follow_redirects=True)

    # Check for successful registration response
    assert response.status_code == 200
    assert b'Congratulations, you are now a registered user!' in response.data


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


