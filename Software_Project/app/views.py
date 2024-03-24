import json
from flask import render_template, redirect, url_for, flash, request,session,jsonify
from app import app, db
from app.models import SubscriptionPlan, User,Payment, Journey
from app.forms import RegistrationForm
from .forms import CSRFProtectForm
from werkzeug.security import generate_password_hash
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import check_password_hash
import stripe
from datetime import datetime, timedelta
stripe.api_key = 'sk_test_51OubkTGiwWWmEjuUTmrjuRowLjdmFXb365kmtoD0YRLYf7rYKIVhFBIEwn3ozE4O1TMSIqcHa9WIk07RcbIqfErC00DyV65frs'

def create_stripe_customer(user):
    try:
        customer = stripe.Customer.create(
            email=user.email,
            name=f"{user.firstname} {user.surname}",
            # You can include additional fields as needed
        )
        return customer.id  # Return the Stripe customer ID
    except Exception as e:
        print(f"Failed to create Stripe customer: {e}")
        return None  # Return None if customer creation fails

@app.route('/', methods=['GET'])
def index():
    return render_template('home.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm(request.form)
    if request.method == 'POST':
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
        stripe_customer_id = create_stripe_customer(user)
        if stripe_customer_id:
            user.stripe_customer_id = stripe_customer_id
            try:
                db.session.add(user)
                db.session.commit()
                flash('Congratulations, you are now a registered user!')
                return redirect(url_for('login'))
            except Exception as e:
                print(e)
                db.session.rollback()
                flash('Registration failed due to an internal error.')
        else:
            flash('Failed to create a Stripe customer account. Please try again.')        
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

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('index'))   


def get_stripe_plans():
    try:
        prices = stripe.Price.list(active=True, expand=["data.product"])
        plans = []
        for price in prices.data:
            plans.append({
                'id': price.id,
                'name': price.product.name,
                'amount': price.unit_amount / 100,  # Convert to dollars
                'currency': price.currency,
                'interval': price.recurring.interval
            })
        return plans
    except Exception as e:
        print(f"Error fetching Stripe plans: {e}")
        return []

@app.route('/choose_subscription', methods=['GET'])
def choose_subscription():
    plans = get_stripe_plans()
    return render_template('choose_subscription.html', plans=plans)

@app.route('/create_checkout_session', methods=['POST'])
@login_required
def create_checkout_session():
    user = current_user
    if not user.stripe_customer_id:
        # Optionally create a Stripe customer here if not already done
        create_stripe_customer(user)
    stripe_price_id = request.form.get('stripe_price_id')
    try:
        checkout_session = stripe.checkout.Session.create(
            customer=current_user.stripe_customer_id,  # Assuming you store Stripe customer IDs in your User model
            payment_method_types=['card'],
            line_items=[{
                'price': stripe_price_id,
                'quantity': 1,
            }],
            mode="subscription",
            success_url=url_for('payment_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('payment_cancel', _external=True),
            client_reference_id=str(user.id),
            metadata={'stripe_price_id': stripe_price_id},
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        flash(f"Failed to create a checkout session: {e}", 'error')
        return redirect(url_for('choose_subscription'))


@app.route('/payment_success', methods=['GET'])
@login_required
def payment_success():
    session_id = request.args.get('session_id')
    if not session_id:
        flash('No payment session found.', 'error')
        return redirect(url_for('index'))

    try:
        session = stripe.checkout.Session.retrieve(session_id)
        subscription_id = session.get('subscription')
        if not subscription_id:
            flash("Subscription ID not found.", 'error')
            return redirect(url_for('index'))

        subscription = stripe.Subscription.retrieve(subscription_id)
        stripe_customer_id = subscription.customer
        stripe_price_id = session.metadata.get('stripe_price_id')
        price = stripe.Price.retrieve(stripe_price_id)
        product = stripe.Product.retrieve(price.product)

        start_date = datetime.utcfromtimestamp(subscription.current_period_start)
        end_date = datetime.utcfromtimestamp(subscription.current_period_end)
        duration_days = (end_date - start_date).days

        subscription_plan = SubscriptionPlan.query.filter_by(stripe_customer_id=stripe_customer_id, stripe_price_id=stripe_price_id).first()
        if not subscription_plan:
            subscription_plan = SubscriptionPlan(stripe_customer_id=stripe_customer_id,stripe_price_id=stripe_price_id)
            db.session.add(subscription_plan)

        subscription_plan.plan_name = product.name
        subscription_plan.price = price.unit_amount / 100
        subscription_plan.duration = str(duration_days)  # Ensure this aligns with your model's field type
        subscription_plan.expiration_date= datetime.utcfromtimestamp(subscription.current_period_end)
        user = User.query.get(int(session.get('client_reference_id')))
        if user:
            user.subscription_start_date = start_date
            # Update user's subscription_end_date if applicable

        payment = Payment(
            user_id=user.id,
            amount=price.unit_amount / 100,
            payment_date=datetime.utcnow(),
            payment_status=subscription.status,
            stripe_session_id=session_id
        )
        db.session.add(payment)
        db.session.commit()
        user = User.query.get(int(session.get('client_reference_id')))
        if user:
            user.subscription_plan_id = subscription_plan.id
        db.session.commit()    

        flash('Your payment was successful! Thank you for subscribing.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'There was an error confirming your payment: {e}', 'error')


    return redirect(url_for('index'))




@app.route('/payment_cancel',methods=['GET'])
@login_required
def payment_cancel():
    # Inform the user that their payment was canceled
    flash('Payment was canceled.', 'warning')
    return redirect(url_for('index'))


############################################################################################


@app.route('/api/journeys', methods=['POST'])
def start_journey():
    data = request.json
    new_journey = Journey(user_id=data['user_id'], start_location=data['start_location'])
    db.session.add(new_journey)
    db.session.commit()
    return jsonify({"message": "Journey started", "journey_id": new_journey.id}), 201

@app.route('/api/journeys/<int:journey_id>', methods=['PATCH'])
def end_journey(journey_id):
    data = request.json
    journey = Journey.query.get_or_404(journey_id)
    journey.end_location = data.get('end_location', journey.end_location)
    journey.end_time = datetime.utcnow()
    db.session.commit()
    return jsonify({"message": "Journey ended"}), 200

@app.route('/gps', methods=['GET'])
@login_required
def gps_page():
    return render_template('index.html')


@app.route('/friends', methods=['GET', 'POST'])
@login_required
def friends():
    return render_template('friends.html')

@app.route('/friendsProfile', methods=['GET', 'POST'])
@login_required
def friendsProfile():
    return render_template('friendsprofile.html')
