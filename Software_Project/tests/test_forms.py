from contextlib import contextmanager
from unittest.mock import patch
from flask import template_rendered, url_for
import pytest
import stripe
from app import app, db
from app.models import User,FriendRequest


def delete_test_data():
    with app.app_context():
        # Delete the user created during the tests
        User.query.filter(User.email == 'test@example.com').delete()
        # Commit the changes to the database
        db.session.commit()

@contextmanager
def captured_templates(app):
    recorded = []
    def record(sender, template, context, **extra):
        recorded.append((template, context))
    template_rendered.connect(record, app)
    try:
        yield recorded
    finally:
        template_rendered.disconnect(record, app)     


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SERVER_NAME']='localhost.localdomain'
    client = app.test_client()

    with app.app_context():
        db.create_all()

    yield client
     # After the test runs, clean up the test data
    delete_test_data()

@pytest.fixture
def mock_stripe_customer(mocker):
    return mocker.patch('app.views.create_stripe_customer', return_value='fake_stripe_id')

def test_register_get(client):
    with client.application.app_context():  # Ensuring the application context is used here
        response = client.get(url_for('register'))
        assert response.status_code == 200
        assert b'Register' in response.data

def test_register_post_successful(client, mock_stripe_customer):
    with client.application.app_context():  # Ensure the application context is being used here
        response = client.post(url_for('register'), data={
            'username': 'testuser',
            'firstName': 'Test',
            'surName': 'User',
            'dob': '2000-01-01',
            'email': 'test@example.com',
            'phoneNumber': '1234567890',
            'password': 'securepassword123'
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'Congratulations, you are now a registered user!' in response.data
        user = User.query.filter_by(username='testuser').first()
        assert user is not None
        assert user.stripe_customer_id == 'fake_stripe_id'

def test_missing_firstname(client, mock_stripe_customer):
    response = client.post('/register', data={
        'username': 'newuser',
        'firstName': '',  # Intentionally left blank
        'surName': 'Doe',
        'dob': '1990-01-01',
        'email': 'johndoe@example.com',
        'phoneNumber': '12345678901',
        'password': 'ValidPassword1!',
        'confirm_password': 'ValidPassword1!'
    }, follow_redirects=True)
    assert response.status_code == 200
    # Look for any sign of the error being displayed
    assert b'First Name' in response.data and b'error' in response.data


# def test_invalid_email_format(client, mock_stripe_customer):
#     response = client.post('/register', data={
#         'username': 'newuser',
#         'firstName': 'John',
#         'surName': 'Doe',
#         'dob': '1990-01-01',
#         'email': 'invalid-email',
#         'phoneNumber': '12345678901',
#         'password': 'ValidPassword1!',
#         'confirm_password': 'ValidPassword1!'
#     }, follow_redirects=True)
#     print(response.data.decode('utf-8')) 
#     assert response.status_code == 200
#     assert b'Invalid email format' in response.data

# def test_password_mismatch(client, mock_stripe_customer):
#     response = client.post('/register', data={
#         'username': 'newuser',
#         'firstName': 'John',
#         'surName': 'Doe',
#         'dob': '1990-01-01',
#         'email': 'johndoe@example.com',
#         'phoneNumber': '12345678901',
#         'password': 'ValidPassword1!',
#         'confirm_password': 'AnotherPassword1!'
#     }, follow_redirects=True)
#     print(response.data.decode('utf-8'))
#     assert response.status_code == 200
#     assert b'Passwords do not match.' in response.data





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

