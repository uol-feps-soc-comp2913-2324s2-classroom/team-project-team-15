from flask_wtf import FlaskForm
from wtforms import PasswordField, DateField, SubmitField, StringField, RadioField,NumberField
from wtforms.validators import DataRequired, EqualTo, InputRequired, Length, Regexp, Email, ValidationError
from app.models import User

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    firstName= StringField('Firstname', validators=[DataRequired()])
    surName= StringField('Surname', validators=[DataRequired()])
    dob = DateField('Date of Birth', format='%Y-%m-%d', validators=[
        InputRequired(message="Date of birth is required")
    ])
    email = StringField('Email', validators=[DataRequired(), Email(message="Invalid email format")])
    phoneNumber = StringField('Phone Number', validators=[
        InputRequired(message="Phone number is required"),
        Length(min=10, max=15, message="Phone number must be between 10 and 15 digits"),
        Regexp(regex=r'^[0-9]+$', message="Phone number must contain only digits")
    ])
    password = PasswordField('Password', validators=[
        InputRequired(message="Password is required"),
        Length(min=8, message="Password must be at least 8 characters long"),
        Regexp(regex=r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]+$', 
               message="Password must contain at least one lowercase letter, one uppercase letter, one digit, and one special character")
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        InputRequired(message="Please confirm your password"),
        EqualTo('password', message="Passwords must match")
    ])
    submit = SubmitField('Register')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please use a different email.')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already taken. Please choose a different username.')

    def validate_phoneNumber(self, phoneNumber):
        user = User.query.filter_by(phone_number=phoneNumber.data).first()
        if user:
            raise ValidationError('Phone number already registered. Please use a different phone number.')

    def validate_confirm_password(self, confirm_password):
        if self.password.data != confirm_password.data:
            raise ValidationError('Passwords do not match.')


class CSRFProtectForm(FlaskForm):
    """A simple form just for CSRF protection."""
    pass    