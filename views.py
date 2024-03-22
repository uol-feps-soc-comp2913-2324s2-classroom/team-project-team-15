from flask import render_template, redirect, url_for, flash, request
from app import app, db
from app.models import User
from app.forms import RegistrationForm
# from werkzeug import security
# from werkzeug.security import generate_password_hash


@app.route('/', methods=['GET'])
def index():
    return render_template('base.html')

@app.route('/friends', methods=['GET'])
def friends():
    return render_template('friends.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm(request.form)
    if request.method == 'POST' and form.validate():
        # hashed_password = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        user = User(
            username=form.username.data,
            firstname=form.firstName.data,
            surname=form.surName.data,
            dob=form.dob.data,
            email=form.email.data,
            phone_number=form.phoneNumber.data,
            password_hash=hashed_password,
        )
        # Set default values
        user.journeys = []
        user.friends = [] 
        user.subscription_plan_id = None 
        
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('index'))
    return render_template('register.html', title='Register', form=form)
