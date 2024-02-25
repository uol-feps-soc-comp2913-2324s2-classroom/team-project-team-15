from app import app, db
from flask import render_template, redirect, url_for, flash
from app.models import User
from app.forms import RegistrationForm

@app.route('/')
def index():
    return render_template('index.html')



@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        # Creating a user object with the form data
        user = User(
            username=form.username.data,
            firstname=form.firstName.data,
            surname=form.surName.data,
            dob=form.dob.data,
            email=form.email.data,
            phone_number=form.phoneNumber.data,
            password=form.password.data
        )
        
        # Adding the user to the database
        db.session.add(user)
        db.session.commit()

        # Flashing a success message
        flash('Registration successful! You can now log in.', 'success')
        
        # Redirecting to the index page
        return redirect(url_for('index'))

    # Rendering the registration form template
    return render_template('register.html', form=form)

   
    