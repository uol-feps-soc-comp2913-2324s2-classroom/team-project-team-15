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
        db.create_all()

    yield client


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
    assert response.status_code == 302 

    with app.app_context():
        user = User.query.filter_by(username='testuser').first()
        assert user is not None
        assert user.email == 'test@example.com'
