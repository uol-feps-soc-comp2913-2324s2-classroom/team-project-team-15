import io
import json
from operator import or_
import re
from venv import logger
from flask import make_response, render_template, redirect, url_for, flash, request,session,jsonify, current_app, Response
import gpxpy
from app import app, db
from app.models import SubscriptionPlan, User,Payment, FriendRequest, JourneyRecord
from app.forms import RegistrationForm
from .forms import CSRFProtectForm
from werkzeug.security import generate_password_hash
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import check_password_hash
from collections import defaultdict
import stripe
import logging
from datetime import date, datetime, timedelta
from functools import wraps
import csv
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
    
def membership_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = current_user
        today = datetime.today().date()
        if not user.subscription_plan or user.subscription_plan.expiration_date < today:
            flash('Your membership is expired or does not exist. Please renew your membership.', 'warning')
            return redirect(url_for('choose_subscription'))
        return f(*args, **kwargs)
    return decorated_function


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
            if username == 'admin':
                return redirect(url_for('admin'))
            login_user(user)
            # Check if it's the user's first login or if they haven't selected a subscription plan
            if not user.subscription_plan_id:
                return redirect(url_for('choose_subscription'))
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    active_subscriptions = User.query.filter(User.subscription_start_date.isnot(None)).all()

    weekly_revenue = {}
    current_date = datetime.now().date()
    end_date = current_date + timedelta(days=365)
    while current_date <= end_date:
        week_start = current_date - timedelta(days=current_date.weekday())
        weekly_revenue[week_start.strftime('%Y-%m-%d')] = 0
        current_date += timedelta(weeks=1)

    # Calculate billing dates and revenue based on subscription duration
    for user in active_subscriptions:
        subscription_plan = SubscriptionPlan.query.get(user.subscription_plan_id)
        if subscription_plan:
            start_date = user.subscription_start_date
            duration = subscription_plan.plan_name.lower()  # e.g., 'weekly', 'monthly', 'yearly'
            price = subscription_plan.price

            current_date = start_date
            while current_date <= end_date:
                week_start = current_date - timedelta(days=current_date.weekday())
                week_end = week_start + timedelta(days=6)
                if current_date >= start_date and current_date <= week_end:
                    # Increment revenue for the current week
                    weekly_revenue[week_start.strftime('%Y-%m-%d')] = weekly_revenue.get(week_start.strftime('%Y-%m-%d'), 0) + price 
                if duration == 'weekly':
                    current_date += timedelta(weeks=1)
                elif duration == 'monthly':
                    current_date += timedelta(days=30)  # Approximate, adjust as needed
                elif duration == 'annually':
                    current_date += timedelta(days=365)  # Approximate, adjust as needed

    subscription_counts = defaultdict(int)
    for user in User.query.filter(User.subscription_plan_id.isnot(None)).all():
        subscription_counts[user.subscription_plan.plan_name] += 1
    # Sort the revenue data by date
    sorted_weekly_revenue = sorted(weekly_revenue.items())
    print(sorted_weekly_revenue)
    sorted_weekly_revenue = sorted(weekly_revenue.items())

    return render_template('admin.html', revenue_data=sorted_weekly_revenue, subscription_counts=subscription_counts)

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

@app.route('/choose_subscription', methods=['GET','POST'])
@login_required
def choose_subscription():
    plans = get_stripe_plans()
   # Fetch the current user's subscription details
    current_subscription = None
    if current_user.subscription_plan_id:
        subscription_plan = SubscriptionPlan.query.get(current_user.subscription_plan_id)
        if subscription_plan:
            current_subscription = {
                'plan_id': subscription_plan.id,
                'plan_name': subscription_plan.plan_name,
                'start_date': current_user.subscription_start_date,
                'expiration_date': subscription_plan.expiration_date, 
                'price_id':subscription_plan.stripe_price_id,
                'days_left': (subscription_plan.expiration_date - date.today()).days if subscription_plan.expiration_date else None
            }

    user = User.query.get(current_user.id)        
    subscriptions = stripe.Subscription.list(customer=user.stripe_customer_id, status='active', limit=1)
    subscription_details = None
    if subscriptions.data:
        subscription = subscriptions.data[0]
        subscription_details = {
            'is_auto_renewal_on': not subscription.cancel_at_period_end,
        }         

    return render_template('choose_subscription.html', plans=plans, current_subscription=current_subscription,subscription_details=subscription_details)


        

@app.route('/create_checkout_session', methods=['GET','POST'])
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


@app.route('/payment_success', methods=['GET'], endpoint='payment_success')
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
        payment_methods=stripe.PaymentMethod.list(
            customer=user.stripe_customer_id,
            type="card"
        )
        if payment_methods and payment_methods.data:
            card_details=payment_methods.data[0].card
            expiry_date=f"{card_details.exp_month}/{card_details.exp_year}"

        payment = Payment(
            user_id=user.id,
            amount=price.unit_amount / 100,
            payment_date=datetime.utcnow(),
            payment_status=subscription.status,
            stripe_session_id=session_id,
            payment_method_type='card',
            card_expiry_date=expiry_date
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


@app.route('/payment_cancel',methods=['GET'], endpoint='handle_cancel')
@login_required
def payment_cancel():
    # Inform the user that their payment was canceled
    flash('Payment was canceled.', 'warning')
    return redirect(url_for('index'))


def is_payment_card_expired(user):
    if user.payments:
        latest_payment = max(user.payments, key=lambda x: x.payment_date, default=None)
        if latest_payment and latest_payment.card_expiry_date:
            expiry_date = datetime.strptime(latest_payment.card_expiry_date, "%m/%Y")
            if expiry_date <= datetime.utcnow():
                return True
    return False


@app.route('/enable_auto_renewal', methods=['POST'])
@login_required
@membership_required
def enable_auto_renewal():
    user = User.query.get(current_user.id)
    if not user or not user.stripe_customer_id:
        flash('You do not have an active subscription.', 'error')
        return redirect(url_for('index'))



    try:

        subscriptions = stripe.Subscription.list(customer=user.stripe_customer_id)
        subscription_id = None
        for subscription in subscriptions.auto_paging_iter():
            # Assuming you store the Stripe Price ID in subscription_plan.stripe_price_id
            if subscription['items']['data'][0]['price']['id'] == user.subscription_plan.stripe_price_id:
                subscription_id = subscription['id']
                break
        
        if not subscription_id:
            flash('No active subscription found for cancellation.', 'error')
            return redirect(url_for('index'))
        
        # Cancel the subscription at period's end
        stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=False
        )

        # Update your models as necessary
        db.session.commit()

        flash('Your subscription will be automatically renewed at the end of the current billing period.', 'success')
    except Exception as e:
        flash(f'An error occurred while Enabling Auto-Renewal your subscription: {e}', 'error')

    return redirect(url_for('index'))

@app.route('/change_subscription/<string:new_plan_stripe_id>', methods=['POST'])
@login_required
def change_subscription(new_plan_stripe_id):
    # Fetch current user based on session or token
    user = User.query.get(current_user.id)
    if not user:
        flash('No user found.', 'error')
        return redirect(url_for('choose_subscription'))
    if is_payment_card_expired(user):
        flash('Your payment card has expired. Please update your payment method.', 'error')
        return redirect(url_for('update_card_details')) 

    # Fetch plans from Stripe
    plans = get_stripe_plans()
    stripe_plan = next((plan for plan in plans if plan['id'] == new_plan_stripe_id), None)
    if not stripe_plan:
        flash('Plan not found.', 'error')
        return redirect(url_for('choose_subscription'))

    # If the plan is valid, find or create a SubscriptionPlan in local DB
    subscription_plan = SubscriptionPlan.query.filter_by(stripe_price_id=new_plan_stripe_id).first()
    if not subscription_plan:
        # If no local plan exists, create a new one
        subscription_plan = SubscriptionPlan(
            stripe_price_id=new_plan_stripe_id,
            plan_name=stripe_plan['name'],
            price=stripe_plan['amount'],
            duration=stripe_plan['interval'],
            # Assuming other necessary fields are filled accordingly
        )
        db.session.add(subscription_plan)
        db.session.flush()  # Flush to assign an ID if needed

    # Assign the new plan to the user
    if user.subscription_plan and user.subscription_plan.expiration_date and user.subscription_plan.expiration_date > date.today():
        # Plan changes at the end of the current period
        user.subscription_plan.next_plan_id = subscription_plan.id
        user.subscription_plan.cancel_at_period_end = True
        flash('Your subscription will be updated at the end of your current period.', 'success')
    else:
        # Update immediately if no active or expired plan
        user.subscription_plan = subscription_plan
        user.subscription_start_date = date.today()  # Reset the start date
        flash('Your subscription has been updated.', 'success')
    
    db.session.commit()
    return redirect(url_for('choose_subscription'))

@app.route('/update_card_details', methods=['GET'])
@login_required
def update_card_details():
    user = User.query.get(current_user.id)
    try:
        # Create a Stripe Checkout session for updating card details
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            customer=user.stripe_customer_id,
            mode='setup',  # This mode is used for setting up or updating payment details
            success_url=url_for('payment_method_success', _external=True)+ '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('handle_cancel', _external=True),
        )
        return redirect(session.url, code=303)
    except Exception as e:
        flash(f"Failed to initiate payment method update: {e}", 'error')
        return redirect(url_for('choose_subscription'))

@app.route('/payment_method_success')
@login_required
def payment_method_success():
    session_id = request.args.get('session_id')
    if not session_id:
        flash('No payment session found.', 'error')
        return redirect(url_for('choose_subscription'))

    try:
        # Retrieve the session and payment method from Stripe
        session = stripe.checkout.Session.retrieve(session_id)
        new_payment_method = stripe.PaymentMethod.retrieve(session.payment_method)

        if not new_payment_method or new_payment_method.customer != session.customer:
            flash('Mismatch in payment method details.', 'error')
            return redirect(url_for('choose_subscription'))

        # Detach all old payment methods except the new one
        old_payment_methods = stripe.PaymentMethod.list(customer=session.customer, type="card")
        for pm in old_payment_methods.data:
            if pm.id != new_payment_method.id:
                stripe.PaymentMethod.detach(pm.id)

        # Update local database with new card expiry date
        update_local_payment_method(current_user.id, new_payment_method.card.exp_month, new_payment_method.card.exp_year)

        flash('Payment method updated successfully!', 'success')
    except stripe.error.StripeError as e:
        logger.error(f"Stripe API error: {e.user_message}")
        flash(f"Stripe API error: {e.user_message}", 'error')
        return redirect(url_for('choose_subscription'))
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        flash('An unexpected error occurred.', 'error')
        return redirect(url_for('choose_subscription'))

    return redirect(url_for('user_profile'))

def update_local_payment_method(user_id, exp_month, exp_year):
    # Find the latest or appropriate payment record to update
    payment = Payment.query.filter_by(user_id=user_id).order_by(Payment.payment_date.desc()).first()
    if payment:
        payment.card_expiry_date = f"{exp_month}/{exp_year}"
        db.session.commit()
    else:
        # Log or handle the scenario where no payment record is found
        logger.error(f"No payment record found for user ID {user_id}")


@app.route('/cancel_subscription', methods=['POST'])
@login_required
@membership_required
def cancel_subscription():
    user = User.query.get(current_user.id)
    if not user or not user.stripe_customer_id:
        flash('You do not have an active subscription.', 'error')
        return redirect(url_for('index'))

    try:

        subscriptions = stripe.Subscription.list(customer=user.stripe_customer_id)
        subscription_id = None
        for subscription in subscriptions.auto_paging_iter():
            # Assuming you store the Stripe Price ID in subscription_plan.stripe_price_id
            if subscription['items']['data'][0]['price']['id'] == user.subscription_plan.stripe_price_id:
                subscription_id = subscription['id']
                break
        
        if not subscription_id:
            flash('No active subscription found for cancellation.', 'error')
            return redirect(url_for('index'))
        
        # Cancel the subscription at period's end
        stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=True
        )

        # Update your models as necessary
        db.session.commit()

        flash('Your subscription will be cancelled at the end of the current billing period.', 'success')
    except Exception as e:
        flash(f'An error occurred while cancelling your subscription: {e}', 'error')

    return redirect(url_for('index'))

@app.context_processor
def inject_subscription_details():
    details = {
        'subscription_plan_name': 'Not Logged In',
        'stripe_customer_id': None,
        'stripe_price_id': None
    }

    if current_user.is_authenticated:
        user = User.query.get(current_user.id)
        if user.subscription_plan:
            details['subscription_plan_name'] = user.subscription_plan.plan_name
            details['stripe_customer_id'] = user.stripe_customer_id
            details['stripe_price_id'] = user.subscription_plan.stripe_price_id
        else:
            details['subscription_plan_name'] = 'No Subscription'
    
    return details

@app.route('/search-users', methods=['GET'])
@login_required
@membership_required
def search_users():
    query = request.args.get('query', '')
    users = User.query.filter(
        or_(User.username.ilike(f'%{query}%'), User.firstname.ilike(f'%{query}%'))
    ).filter(User.id != current_user.id).all()

    results = []
    for user in users:
        is_friend = user in current_user.friends
        # Check if there is a pending friend request from the current user to this user
        request_sent = FriendRequest.query.filter_by(
            requester_id=current_user.id,
            requestee_id=user.id,
            status='pending'  # assuming 'status' can be 'pending', 'accepted', 'rejected'
        ).first()

        results.append({
            'username': user.username,
            'id': user.id,
            'request_sent': bool(request_sent),
            'can_cancel': bool(request_sent),  # True if a request was sent and is pending
            'is_friend': is_friend
        })

    html_content = render_template('searchResults.html', users=results)
    return jsonify(html=html_content, users=results)


@app.route('/cancel-friend-request/<int:user_id>', methods=['POST'])
@login_required
@membership_required
def cancel_friend_request(user_id):
    # Find the friend request to cancel
    friend_request = FriendRequest.query.filter_by(
        requester_id=current_user.id,
        requestee_id=user_id,
        status='pending'
    ).first()

    if friend_request:
        # Delete the request if it exists and is still pending
        db.session.delete(friend_request)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Friend request cancelled.'})
    else:
        return jsonify({'status': 'error', 'message': 'No pending friend request found.'}), 404


@app.route('/send-friend-request/<int:requestee_id>', methods=['POST'])
@login_required
@membership_required
def send_friend_request(requestee_id):
    # Prevent self-friend requests
    if current_user.id == requestee_id:
        return jsonify({'error': 'Cannot send friend request to yourself'}), 400
    
    potential_friend = User.query.get(requestee_id)
    if potential_friend in current_user.friends:
        return jsonify({'error': 'This user is already your friend.'}), 400

    # Check for existing friend request
    existing_requestOut = FriendRequest.query.filter_by(
        requester_id=current_user.id, 
        requestee_id=requestee_id
    ).first()
    if existing_requestOut:
        error_message = 'Friend request already sent.'
        return jsonify({'error': error_message}), 400
    
    existing_requestIn = FriendRequest.query.filter_by(
        requester_id=requestee_id,
        requestee_id=current_user.id
    ).first()
    if existing_requestIn:
        error_message = 'User has already sent you a friend request.'
        return jsonify({'error': error_message}), 400
    
    try:
        # Create and save the new friend request
        new_request = FriendRequest(
            requester_id=current_user.id, 
            requestee_id=requestee_id, 
            status='pending'
        )
        db.session.add(new_request)
        db.session.commit()
        return jsonify({'message': 'Friend request sent successfully'}), 200
    except Exception as e:
        current_app.logger.error(f"Failed to send friend request: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to send friend request'}), 500


@app.route('/fetch-friend-requests', methods=['GET'])
@login_required
@membership_required
def fetch_friend_requests():
    incoming_requests = FriendRequest.query.filter_by(requestee_id=current_user.id, status='pending').all()
    requests_data = [{'id': req.id, 'username': req.requester.username} for req in incoming_requests]
    return jsonify(requests_data)

@app.route('/respond-friend-request/<request_id>/<action>', methods=['POST'])
@login_required
@membership_required
def respond_friend_request(request_id, action):
    friend_request = FriendRequest.query.get_or_404(request_id)
    if friend_request.requestee_id != current_user.id:
        return jsonify({'error': 'This request is not for the current user.'}), 403

    if action == 'accept':
        # Assuming you have a method or logic to retrieve the User model instance
        requester = User.query.get(friend_request.requester_id)
        requestee = User.query.get(friend_request.requestee_id)

        # Add each user to the other's friends list
        requester.friends.append(requestee)
        requestee.friends.append(requester)

        friend_request.status = 'accepted'
        db.session.delete(friend_request) 
    elif action == 'reject':
        friend_request.status = 'rejected' 
        db.session.delete(friend_request)  
    else:
        return jsonify({'error': 'Invalid action.'}), 400

    db.session.commit()
    return jsonify({'message': f'Friend request {action}ed successfully.'})



def unfriend(user_id, friend_id):
    user = User.query.get(user_id)
    friend = User.query.get(friend_id)

    if friend in user.friends:
        user.friends.remove(friend)
        friend.friends.remove(user)
        db.session.commit()
        return True
    return False


@app.route('/unfriend/<int:friend_id>', methods=['POST'])
@login_required
@membership_required
def handle_unfriend(friend_id):
    result = unfriend(current_user.id, friend_id)
    
    if result:
        return jsonify({'message': 'Friend successfully unfriended.'}), 200
    else:
        return jsonify({'error': 'Could not unfriend the specified user.'}), 400


@app.route('/friends')
@login_required
@membership_required
def friends():
    # Assuming FriendRequest has a 'status' column with values like 'pending', 'accepted', etc.
    incoming_requests = FriendRequest.query.filter_by(requestee_id=current_user.id, status='pending').all()
    # Assuming you have a list of friend User objects for the current user
    friends = current_user.friends  # This will depend on how you've set up the friends relationship

    return render_template('friends.html', friends=friends, requests=incoming_requests)



@app.route('/upload_gps', methods=['GET', 'POST'])
@login_required
def upload_gps():
    if request.method == 'POST':
        file = request.files.get('gpsdata')
        activity_type = request.form.get('type')
        name = request.form.get('name')
        start_time_user = request.form.get('startTime')
        end_time_user = request.form.get('endTime')

        if not file or not activity_type or not name:
            flash('Missing required fields.', 'error')
            return render_template('upload_gps.html')

        try:
            gpx = gpxpy.parse(file.stream)
            coordinates = [{'lat': point.latitude, 'lon': point.longitude}
                           for track in gpx.tracks
                           for segment in track.segments
                           for point in segment.points]

            if not coordinates:
                flash('No GPS data found in file.', 'error')
                return render_template('upload_gps.html')

            # Use user-provided times if available, otherwise extract from file
            if start_time_user and end_time_user:
                start_time = datetime.fromisoformat(start_time_user)
                end_time = datetime.fromisoformat(end_time_user)
            else:
                start_time = min((point.time for track in gpx.tracks for segment in track.segments for point in segment.points), default=datetime.utcnow())
                end_time = max((point.time for track in gpx.tracks for segment in track.segments for point in segment.points), default=datetime.utcnow())

            journey = JourneyRecord(
                user_id=current_user.id,
                name=name,
                type=activity_type,
                start_time=start_time,
                end_time=end_time,
                data={'coordinates': coordinates}
            )
            db.session.add(journey)
            db.session.commit()
            flash('GPS Data successfully uploaded.', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'Error processing file: {str(e)}', 'error')
            return render_template('upload_gps.html')

    else:
        return render_template('upload_gps.html')

@app.route('/journeys')
@login_required
def display_journeys():
    journeys = JourneyRecord.query.filter_by(user_id=current_user.id).all()
    return render_template('display_journey.html', journeys=journeys)

@app.route('/api/journeys')
@login_required
def api_journeys():
    journeys = JourneyRecord.query.filter_by(user_id=current_user.id).all()
    journeys_data = [{
        'id': journey.id,
        'name': journey.name,
        'type': journey.type,
        'duration': journey.calculate_duration(),
        'distance': journey.calculate_distance(),
        'calories': journey.calculate_calories_burned(),
        'speed': journey.calculate_average_speed(),
        'data': journey.data  # This should be a dict that includes 'coordinates' list
    } for journey in journeys]
    return jsonify(journeys_data)

@app.route('/list_journeys')
@login_required
def list_journeys():
    user_journeys = JourneyRecord.query.filter_by(user_id=current_user.id).all()
    return render_template('list_journeys.html', journeys=user_journeys)

@app.route('/list_journeys/view/<int:journey_id>')
@login_required
def view_journey(journey_id):
    journey = JourneyRecord.query.get_or_404(journey_id)
    return render_template('view_journey.html', journey=journey)

@app.route('/list_journeys/delete/<int:journey_id>', methods=['POST'])
@login_required
def delete_journey(journey_id):
    journey = JourneyRecord.query.get_or_404(journey_id)
    db.session.delete(journey)
    db.session.commit()
    flash('Journey deleted successfully.', 'success')
    return redirect(url_for('list_journeys'))

@app.route('/download_journey/<int:journey_id>',methods=['GET'])
@login_required
def download_journey(journey_id):
    journey = JourneyRecord.query.filter_by(id=journey_id, user_id=current_user.id).first()
    if not journey:
        flash('Journey not found.', 'error')
        return redirect(url_for('list_journeys'))

    # Decide the format based on user preference or use a query parameter
    file_format = request.args.get('format', default='json')

    if file_format == 'csv':
        return download_as_csv(journey)
    else:
        return download_as_json(journey)
    

def download_as_json(journey):
    journey_details = {
        'id': journey.id,
        'name': journey.name,
        'type': journey.type,
        'start_time': journey.start_time.isoformat(),
        'end_time': journey.end_time.isoformat(),
        'duration_hours': journey.calculate_duration(),
        'distance_km': journey.calculate_distance(),
        'calories_burned': journey.calculate_calories_burned(),
        'average_speed_km_h': journey.calculate_average_speed(),
        'coordinates': journey.data.get('coordinates', [])
    }
    response = jsonify(journey_details)
    response.headers['Content-Disposition'] = f'attachment; filename=journey_{journey.id}.json'
    return response

def download_as_csv(journey):
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['ID', 'Name', 'Type', 'Start Time', 'End Time', 'Duration (Hours)', 'Distance (km)', 'Calories Burned', 'Average Speed (km/h)', 'Coordinates'])
    cw.writerow([
        journey.id,
        journey.name,
        journey.type,
        journey.start_time.strftime('%Y-%m-%d %H:%M:%S'),
        journey.end_time.strftime('%Y-%m-%d %H:%M:%S'),
        f"{journey.calculate_duration():.2f}",
        f"{journey.calculate_distance():.2f}",
        f"{journey.calculate_calories_burned():.2f}",
        f"{journey.calculate_average_speed():.2f}",
        '; '.join(f"{coord['lat']},{coord['lon']}" for coord in journey.data.get('coordinates', []))
    ])
    
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename=journey_{journey.id}.csv"
    output.headers["Content-type"] = "text/csv"
    return output
