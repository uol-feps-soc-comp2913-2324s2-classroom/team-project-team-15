import pytest
from app import app, db,User
from app.forms import RegistrationForm

@pytest.fixture
def client():
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
