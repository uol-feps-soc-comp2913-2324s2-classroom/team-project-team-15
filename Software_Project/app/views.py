from flask import render_template, redirect, url_for, flash, request
from app import app, db
from app.models import SubscriptionPlan, User
from app.forms import RegistrationForm, SubscriptionForm
from werkzeug.security import generate_password_hash
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import check_password_hash


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')



@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm(request.form)
    if request.method == 'POST' and form.validate():
        hashed_password = generate_password_hash(form.password.data, method='pbkdf2:sha256')
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
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            # Check if it's the user's first login or if they haven't selected a subscription plan
            if not user.subscription_plan_id:
                return redirect(url_for('choose_subscription'))
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')


@app.route('/choose_subscription', methods=['GET', 'POST'])
@login_required
def choose_subscription():
    form = SubscriptionForm()
    if form.validate_on_submit():
        selected_plan = SubscriptionPlan.query.filter_by(plan_name=form.subscription_plan.data).first()
        
        if selected_plan:
            current_user.subscription_plan_id = selected_plan.id
            db.session.commit()
            flash('Subscription plan updated successfully.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid subscription plan selected.', 'error')

    return render_template('choose_subscription.html', form=form)
